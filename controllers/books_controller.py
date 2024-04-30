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

def add_book(data):
    expected_fields = {'ISBN', 'title', 'genre'}
    received_fields = set(data.keys())

    if received_fields != expected_fields:
        return jsonify({"error": "ISBN, title, and genre fields (and only them) must be provided"}), 422

    isbn = data['ISBN']
    title = data['title']
    genre = data['genre']

    # Check if the book already exists
    existing_book = next((book for book in books if book.ISBN == isbn), None)
    if existing_book:
        return jsonify({"error": "A book with this ISBN already exists"}), 422

    # fetch data from Google Books API
    google_books_url = f'https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}'
    try:
        response = requests.get(google_books_url)
        response.raise_for_status()
        google_books_data = response.json()['items'][0]['volumeInfo']
    except requests.exceptions.HTTPError as e:
        return jsonify({"error": f"Unable to connect to Google Books API", "details": str(e)}), 500
    except (IndexError, KeyError):
        return jsonify({"error": "Invalid ISBN number; not found in Google Books API"}), 422

    authors_list = google_books_data.get('authors', ["missing"])
    authors = " and ".join(authors_list)
    publisher = google_books_data.get("publisher", "missing")
    published_date = google_books_data.get("publishedDate", "missing")
    if published_date != "missing":
        valid_date_formats = [
        r"^\d{4}$",  # YYYY
        r"^\d{4}-\d{2}-\d{2}$",  # YYYY-MM-DD
    ]
    
    if not any(re.match(pattern, published_date) for pattern in valid_date_formats):
        published_date = "missing"

    # Fetch data from OpenLibrary API
    open_library_url = f'https://openlibrary.org/search.json?q={isbn}&fields=key,title,author_name,language'
    try:
        open_lib_response = requests.get(open_library_url)
        open_lib_response.raise_for_status()
        open_lib_data = open_lib_response.json().get('docs', [])
        if not open_lib_data:
            raise ValueError("No information available from OpenLibrary.")
    except (requests.exceptions.HTTPError, ValueError) as e:
        return jsonify({"error": f"Unable to retrieve information from OpenLibrary", "details": str(e)}), 422

    language = open_lib_data[0].get("language", ["missing"])
    if not language:
        language = ["missing"]

    # Fetch summary using Google Gemini API
    model = genai.GenerativeModel('gemini-pro', 
                                  safety_settings=[
            {
                "category": "HARM_CATEGORY_DANGEROUS",
                "threshold": "BLOCK_NONE",
            },
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_NONE",
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_NONE",
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_NONE",
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_NONE",
            },
        ])
    

    prompt = f'Summarize the book "{title}" by {authors} in 5 sentences or less. If you dont know the book, return the word "missing" and only this word'
    try:
        llm_response = model.generate_content(prompt)
        summary = llm_response.text if llm_response else "missing"
    except Exception as e:
        summary = "missing"

    # create and add the new book
    new_id = str(len(books) + 1)
    new_book = Book(new_id, isbn, title, genre, authors, publisher, published_date, language, summary)
    books.append(new_book)

    ratings.append(Rating(new_id, title))

    return custom_jsonify(new_book.to_dict()), 201


def get_book(book_id):
    book = next((book for book in books if book.id == book_id), None)
    if book:
        return custom_jsonify(book.to_dict()), 200
    else:
        return custom_jsonify({"message": "Book not found"}), 404


#TODO - languages do not filtered good
def get_books(query_params):
    valid_languages = {'heb', 'eng', 'spa', 'chi'}
    filtered_books = []
    for book in books:
        matches_query = True
        for key, value in query_params.items():
            if key == 'language':
                if value not in valid_languages:
                    return jsonify({"error": f"Invalid language request. Must be one of {list(valid_languages)}."}), 400
                if value not in book.language:
                    matches_query = False
                    break
            if key == 'summery':
                break
            if key in book.to_dict() and str(getattr(book, key, '')).lower() != value.lower():
                matches_query = False
                break
        if matches_query:
            filtered_books.append(book.to_dict())
    return custom_jsonify(filtered_books), 200


#TODO - how to take care of the publishDate??
def update_book(book_id, updated_data):
    book = next((book for book in books if book.id == book_id), None)
    if not book:
        return jsonify({"error": "Book not found"}), 404
    
    required_fields = ['ISBN', 'title', 'genre', 'authors', 'publisher', 'publishedDate', 'language', 'summary']
    if not all(field in updated_data for field in required_fields):
        return jsonify({"error": "All fields must be provided"}), 422

    accepted_genres = ['Fiction', 'Children', 'Biography', 'Science', 'Science Fiction', 'Fantasy', 'Other']
    if updated_data['genre'] not in accepted_genres:
        return jsonify({"error": "Genre is not one of the accepted values"}), 422
    
    #TODO - check with yonatan if we need to consider possible days and month of the year
    published_date = updated_data.get("publishedDate", "missing")

    if published_date != "missing":
        # Check for valid formats
        valid_date_formats = [
            r"^\d{4}$",  # YYYY
            r"^\d{4}-\d{2}-\d{2}$",  # YYYY-MM-DD
        ]
        
        # Check if published_date matches any valid format
        if not any(re.match(pattern, published_date) for pattern in valid_date_formats):
            published_date = "missing"
    
    # Update the book data
    updated_data["publishedDate"] = published_date
    
    if any(other_book for other_book in books if other_book.ISBN == updated_data['ISBN'] and other_book.id != book_id):
        return jsonify({"error": "A book with this ISBN already exists"}), 422

    for field in required_fields:
        setattr(book, field, updated_data[field])

    return jsonify({"id": book_id}), 200


def delete_book(book_id):
    global books, ratings
    book = next((book for book in books if book.id == book_id), None)
    if not book:
        return jsonify({"message": "Book not found"}), 404
    
    books = [b for b in books if b.id != book_id]
    ratings = [r for r in ratings if r.id != book_id]
    return jsonify({"message": "Book and its ratings deleted"}), 200

