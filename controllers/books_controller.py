import requests
from flask import jsonify
from data.database import books, ratings
from models.book import Book
from models.rating import Rating
from util.jsonify_tools import custom_jsonify

def add_book(data):
    expected_fields = {'ISBN', 'title', 'genre'}
    received_fields = set(data.keys())

    if received_fields != expected_fields:
        return jsonify({"error": "ISBN, title, and genre fields (and only them) must be provided"}), 422

    isbn = data['ISBN']
    title = data['title']
    genre = data['genre']

    existing_book = next((book for book in books if book.ISBN == isbn), None)
    if existing_book:
        return jsonify({"error": "A book with this ISBN already exists"}), 422
    
    google_books_url = f'https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}&key=AIzaSyAOu8Qh7n9dRTamVGyhlmpVR6si6OT2QXk'
    try:
        response = requests.get(google_books_url)
        response.raise_for_status()
        google_books_data = response.json()['items'][0]['volumeInfo']
    except requests.exceptions.HTTPError as e:
        return jsonify({"error": f"Unable to connect to Google service", "details": str(e)}), 500
    except (IndexError, KeyError):
        return jsonify({"error": "Invalid ISBN number; not found in Google Books API"}), 422

    authors = google_books_data.get("authors", ["missing"])
    publisher = google_books_data.get("publisher", ["missing"])
    language = google_books_data.get("language", ["missing"])
    summary = google_books_data.get("summary", "missing")
    publishedDate = google_books_data.get("publishedDate", "missing")

    new_id = str(len(books) + 1)
    new_book = Book(new_id, isbn, title, genre, authors, publisher, publishedDate, language, summary)
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
    valid_languages = {"heb", 'eng', 'spa', 'chi'}
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
                continue
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

