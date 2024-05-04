import re
import requests
from flask import jsonify
from data.database import books, ratings
from models.book import Book
from models.rating import Rating
from util.jsonify_tools import custom_jsonify
from dotenv import load_dotenv
import requests
import google.generativeai as genai
import os

# initialize the generative AI configuration
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_KEY"))
current_max_id = 0

def add_book(data):
    expected_fields = {'ISBN', 'title', 'genre'}
    received_fields = set(data.keys())

    if received_fields != expected_fields:
        return jsonify({"error": "ISBN, title, and genre fields (and only them) must be provided"}), 422

    isbn = data['ISBN']
    title = data['title']
    genre = data['genre']

    valid_genres = ['Fiction', 'Children', 'Biography', 'Science', 'Science Fiction', 'Fantasy', 'Other']
    if genre not in valid_genres:
        return jsonify({"error": "Invalid genre; acceptable genres are Fiction, Children, Biography, Science, Science Fiction, Fantasy, Other"}), 422

    existing_book = [book for book in books if book.ISBN == isbn]
    if existing_book:
        return jsonify({"error": "A book with this ISBN already exists"}), 422

    # fetch data from Google Books API
    google_books_url = f'https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}'
    try:
        response = requests.get(google_books_url)
        response.raise_for_status()
        google_books_data = response.json()['items'][0]['volumeInfo']
    except requests.exceptions.HTTPError as e:
        return jsonify({"error": f"Unable to connect to Google Books API"}), 500
    except (IndexError, KeyError):
        return jsonify({"error": "Invalid ISBN number; not found in Google Books API"}), 422

    authors_list = google_books_data.get('authors', ["missing"])
    authors = " and ".join(authors_list)

    publisher = google_books_data.get("publisher", "missing")

    published_date = google_books_data.get("publishedDate", "missing")
    if published_date != "missing":
        valid_date_formats = [
        r"^\d{4}$", #YYYY
        r"^\d{4}-\d{2}-\d{2}$", #YYYY-MM-DD
    ]
    
    if not any(re.match(pattern, published_date) for pattern in valid_date_formats):
        published_date = "missing"

    # fetch data from OpenLibrary API
    open_library_url = f'https://openlibrary.org/search.json?q={isbn}&fields=key,title,author_name,language'
    try:
        open_lib_response = requests.get(open_library_url)
        open_lib_response.raise_for_status()
        open_lib_data = open_lib_response.json().get('docs', [])
        
        if not open_lib_data:
            language = ["missing"]
        else:
            language = open_lib_data[0].get("language", ["missing"])
    except (requests.exceptions.HTTPError, ValueError):
        language = ["missing"]

    # fetch summary using Google Gemini API
    prompt = f'Summarize the book "{title}" by {authors} in 5 sentences or less. If you don\'t know the book, return the word "missing" and only this word."'

    try:
        model = genai.GenerativeModel('gemini-pro', 
            safety_settings=[
                {"category": "HARM_CATEGORY_DANGEROUS", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
            ]
        )

        llm_response = model.generate_content(prompt)
        summary = llm_response.text if llm_response else "missing"
    
    except Exception as e:
        return jsonify({"error": "Unable to connect to Gemini"}), 500

    # create and add the new book
    global current_max_id
    current_max_id += 1
    new_id = str(current_max_id)

    new_book = Book(new_id, isbn, title, genre, authors, publisher, published_date, language, summary)
    books.append(new_book)

    ratings.append(Rating(new_id, title))

    return jsonify({"id": new_id}), 201


def get_book(book_id):
    for book in books:
        if book.id == book_id:
            return custom_jsonify(book.to_dict()), 200

    return custom_jsonify({"message": "Book not found"}), 404


def get_books(query_params):
    valid_languages = {'heb', 'eng', 'spa', 'chi'}
    filtered_books = []
    for book in books:
        matches_query = True
        for key, value in query_params.items():
            if key == 'language':
                if value not in valid_languages:
                    return jsonify({"error": f"Invalid language request. Must be one of {list(valid_languages)}."}), 422
                if not any(value.lower() == lang.lower() for lang in book.language):
                    matches_query = False
                    break
            elif key == 'summery':
                continue
            elif str(getattr(book, key, '')).lower() != value.lower():
                matches_query = False
                break
        if matches_query:
            filtered_books.append(book.to_dict())
    return jsonify(filtered_books), 200


def update_book(book_id, updated_data):
    book = None
    for b in books:
        if b.id == book_id:
            book = b
            break

    if not book:
        return jsonify({"error": "Book not found"}), 404
    
    required_fields = ['ISBN', 'title', 'genre', 'authors', 'publisher', 'publishedDate', 'language', 'summary']
    if not all(field in updated_data for field in required_fields):
        return jsonify({"error": "All fields must be provided"}), 422

    valid_genres = ['Fiction', 'Children', 'Biography', 'Science', 'Science Fiction', 'Fantasy', 'Other']
    if updated_data['genre'] not in valid_genres:
        return jsonify({"error": "Invalid genre; acceptable genres are Fiction, Children, Biography, Science, Science Fiction, Fantasy, Other"}), 422
    
    published_date = updated_data.get("publishedDate", "missing")

    if published_date != "missing":
        valid_date_formats = [
            r"^\d{4}$", #YYYY
            r"^\d{4}-\d{2}-\d{2}$", #YYYY-MM-DD
        ]
        
        if not any(re.match(pattern, published_date) for pattern in valid_date_formats):
            published_date = "missing"
    
    updated_data["publishedDate"] = published_date
    
    if any(other_book for other_book in books if other_book.ISBN == updated_data['ISBN'] and other_book.id != book_id):
        return jsonify({"error": "A book with this ISBN already exists"}), 422

    for field in required_fields:
        setattr(book, field, updated_data[field])

    return jsonify({"id": book_id}), 200


def delete_book(book_id):
    global books, ratings  

    book_to_delete = None

    for book in books:
        if book.id == book_id:
            book_to_delete = book
            break

    if not book_to_delete:
        return jsonify({"message": "Book not found"}), 404

    books = [b for b in books if b.id != book_id]
    ratings = [r for r in ratings if r.id != book_id]

    return jsonify({"id": book_id}), 200

