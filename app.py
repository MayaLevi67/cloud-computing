import datetime
import os
import json
import requests
from flask import Flask, Response, jsonify, request

app = Flask(__name__)
DEFAULT_PORT = 8000
port = int(os.getenv('PORT', DEFAULT_PORT))

def custom_jsonify(data):
    try:
        response_data = json.dumps(data, ensure_ascii=False)
        return Response(response_data, mimetype='application/json; charset=utf-8')
    except Exception as e:
        return Response(json.dumps({"error": "Failed to serialize data to JSON", "details": str(e)}),
                        mimetype='application/json; charset=utf-8'), 500
    
    
# dummy in-memory 'database'
books = []
ratings = []

from flask import abort

@app.route('/books', methods=['POST'])
def add_book():
    expected_fields = {'ISBN', 'title', 'genre'}
    received_fields = set(request.json.keys())

    if received_fields != expected_fields:
        return jsonify({"error": "Only ISBN, title, and genre fields must be provided"}), 400

    isbn = request.json.get('ISBN')
    title = request.json.get('title')
    genre = request.json.get('genre')
    
    existing_book = next((book for book in books if book['ISBN'] == isbn), None)
    if existing_book:
        return jsonify({"error": "A book with this ISBN already exists"}), 422
    
    google_books_url = f'https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}&key=AIzaSyAOu8Qh7n9dRTamVGyhlmpVR6si6OT2QXk'
    response = requests.get(google_books_url)

    try:
        google_books_data = response.json()['items'][0]['volumeInfo']
    except (IndexError, KeyError):
        return jsonify({"error": "Invalid ISBN number; not found in Google Books API"}), 422
    
    authors = google_books_data.get("authors", ["missing"])
    publisher = google_books_data.get("publisher", ["missing"])
    language = google_books_data.get("language", ["missing"])
    summary = google_books_data.get("summary", "missing")
    publishedDate = google_books_data.get("publishedDate", "missing")

    new_id = str(len(books) + 1)  
    book = {
        "id": new_id,
        "ISBN": isbn,
        "title": title,
        "genre": genre,
        "authors": authors,
        "publisher": publisher,
        "publishedDate": publishedDate,
        "language": language,
        "summary": summary
    }
    books.append(book)
    ratings.append({"id": new_id, "title": title, "values": [], "average": 0.0})

    return custom_jsonify(book), 201


@app.route('/books/<book_id>', methods=['GET'])
def get_book(book_id):
    book = next((book for book in books if book['id'] == book_id), None)
    return custom_jsonify(book) if book is not None else (custom_jsonify({"message": "Book not found"}), 404)
    

@app.route('/books', methods=['GET'])
def get_books():
    valid_languages = {'heb', 'eng', 'spa', 'chi'}
    query_params = request.args

    filtered_books = []
    for book in books:
        matches_query = True
        for key, value in query_params.items():
            # Special handling for 'language'
            if key == 'language':
                # Validate that the language value is one of the allowed options
                if value not in valid_languages:
                    return jsonify({"error": f"Invalid language. Must be one of {list(valid_languages)}."}), 400
                # Check if the specified language is included in the book's languages
                if value not in book.get('language', []):
                    matches_query = False
                    break
            elif key in ['summary', 'language']:  # Skip summary and direct filtering on 'language' list
                continue
            elif key in book and str(book.get(key, '')).lower() != value.lower():
                matches_query = False
                break
        if matches_query:
            formatted_book = {
                'id': book['id'],
                'ISBN': book['ISBN'],
                'title': book['title'],
                'genre': book['genre'],
                'authors': book['authors'],
                'publisher': book['publisher'],
                'publishedDate': book['publishedDate'],
                'language': book.get('language', []),
                'summary': book.get('summary', "No summary available")
            }
            filtered_books.append(formatted_book)
    
    return custom_jsonify(filtered_books)


@app.route('/books/<book_id>', methods=['PUT'])
def update_book(book_id):
    required_fields = ['ISBN', 'title', 'genre', 'authors', 'publisher', 'publishedDate', 'language', 'summary']
    book = next((book for book in books if book['id'] == book_id), None)
    if not book:
        return jsonify({"message": "Book not found"}), 404
    
    updated_data = request.json
    if not all(field in updated_data for field in required_fields):
        return jsonify({"error": "All fields must be provided"}), 400

    for field in required_fields:
        book[field] = updated_data[field]

    return jsonify({"id": book_id}), 200



@app.route('/books/<book_id>', methods=['DELETE'])
def delete_book(book_id):
    global books, ratings  # reference global lists
    book = next((book for book in books if book['id'] == book_id), None)
    if book:
        books = [book for book in books if book['id'] != book_id]
        ratings = [rating for rating in ratings if rating['id'] != book_id]
        return jsonify({"message": "Book and its ratings deleted"}),200
    else:
        return jsonify({"message": "Book not found"}), 404


@app.route('/ratings', methods=['GET'])
def get_ratings():
    query_id = request.args.get('id')

    filtered_ratings = []
    for rating in ratings:
        if query_id and rating['id'] != query_id:
            continue

        # Append the rating details
        filtered_ratings.append({
            'id': rating['id'],
            'title': rating['title'],
            'values': rating['values'],
            'average': rating['average']
        })

    return jsonify(filtered_ratings)


@app.route('/ratings/<book_id>', methods=['GET'])
def get_book_ratings(book_id):
    rating_entry = next((rating for rating in ratings if rating['id'] == book_id), None)

    if rating_entry:
        return jsonify({
            'id': rating_entry['id'],
            'title': rating_entry['title'],
            'values': rating_entry['values'],
            'average': rating_entry['average']
        })
    else:
        return jsonify({"message": "Ratings not found for the given book ID"}), 404


@app.route('/ratings/<book_id>/values', methods=['POST'])
def add_rating(book_id):
    new_rating = request.json.get('value')
    if new_rating not in {1, 2, 3, 4, 5}:
        return jsonify({"message": "Invalid rating value. Must be an integer between 1 and 5."}), 400
    rating_entry = next((rating for rating in ratings if rating['id'] == book_id), None)
    if not rating_entry:
        return jsonify({"message": "Book not found"}), 404
    rating_entry['values'].append(new_rating)
    rating_entry['average'] = round(sum(rating_entry['values']) / len(rating_entry['values']), 2)
    return jsonify({"new_average_rating": rating_entry['average']})


@app.route('/top', methods=['GET'])
def get_top_books():
    eligible_books = [rating for rating in ratings if len(rating['values']) >= 3]
    
    eligible_books.sort(key=lambda x: (-x['average'], x['id']))

    if len(eligible_books) >= 3:
        cutoff_average = sorted(set(book['average'] for book in eligible_books), reverse=True)[2]
    else:
        cutoff_average = float('-inf')  

    top_books_details = [
        {
            "id": book["id"],
            "title": book["title"],
            "average": book["average"]
        }
        for book in eligible_books if book["average"] >= cutoff_average
    ]

    return jsonify(top_books_details)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=port)


