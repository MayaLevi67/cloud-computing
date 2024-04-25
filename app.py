import os
import requests
from flask import Flask, jsonify, request

app = Flask(__name__)
DEFAULT_PORT = 8000
port = int(os.getenv('PORT', DEFAULT_PORT))


# dummy in-memory 'database'
books = []
ratings = []

from flask import abort

@app.route('/books', methods=['POST'])
def add_book():
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
        return jsonify({"error": "No items returned from Google Book API for given ISBN number"}), 400
    
    authors = google_books_data.get("authors", ["missing"])
    publisher = google_books_data.get("publisher", ["missing"])
    publishedDate = google_books_data.get("publishedDate", "missing")
    language = google_books_data.get("language", ["missing"])
    summary = google_books_data.get("summary", "missing")
    
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
    
    ratings.append({
        "id": new_id,
        "title": book["title"],
        "values": [],
        "average": 0.0
    })

    return jsonify(book), 201


@app.route('/books/<book_id>', methods=['GET'])
def get_book(book_id):
    book = next((book for book in books if book['id'] == book_id), None)
    if book is not None:
        return jsonify(book)
    else:
        return jsonify({"message": "Book not found"}), 404
    

@app.route('/books', methods=['GET'])
def get_books():
    query_params = request.args

    filtered_books = []
    for book in books:
        matches_query = True
        for key, value in query_params.items():
            if key.startswith('language contains'):
                language = key.split()[-1]
                if language not in book.get('language', []):
                    matches_query = False
                    break
            elif key == 'authors':
                if not any(value.lower() == author.lower() for author in book.get(key, [])):
                    matches_query = False
                    break
            elif key in book and key not in ['summary', 'language'] and str(book.get(key, '')).lower() != value.lower():
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
    
    return jsonify(filtered_books)


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
    query_average = request.args.get('average')
    op = None
    value = None

    if query_average:
        for symbol in ['<', '<=', '=', '>', '>=']:
            if symbol in query_average:
                op, value = query_average.split(symbol, 1)
                value = float(value)  
                break

    filtered_ratings = []
    for rating in ratings:
        if query_id and rating['id'] != query_id:
            continue

        if query_average and op and value is not None:
            comparison_result = False
            if op == '<':
                comparison_result = rating['average'] < value
            elif op == '<=':
                comparison_result = rating['average'] <= value
            elif op == '=':
                comparison_result = rating['average'] == value
            elif op == '>':
                comparison_result = rating['average'] > value
            elif op == '>=':
                comparison_result = rating['average'] >= value

            if not comparison_result:
                continue

        filtered_ratings.append(rating)

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


#TOOD - check if it works good
@app.route('/top', methods=['GET'])
def get_top_books():
    book_ratings = {book['id']: [] for book in books}

    
    for rating in ratings:
        book_ratings[rating['book_id']].append(rating['rating'])

    # filter books with at least 3 ratings and calculate average ratings
    avg_ratings = [
        {"book_id": book_id, "average_rating": sum(book_ratings) / len(book_ratings)}
        for book_id, book_ratings in book_ratings.items() if len(book_ratings) >= 3
    ]

    # sort by average rating, then by id to ensure a consistent order for books with the same rating
    avg_ratings.sort(key=lambda x: (-x["average_rating"], x["book_id"]))

    # determine the cut-off average rating for the top books (the 3rd highest average rating)
    # but include all books that share this rating
    if len(avg_ratings) >= 3:
        cutoff_average = sorted(set(x["average_rating"] for x in avg_ratings), reverse=True)[2]
    else:
        cutoff_average = float('-inf')  # if less than 3 books have ratings, include all

    top_books_details = [
        {"id": book["id"], "title": book["title"], "average": avg_rating["average_rating"]}
        for avg_rating in avg_ratings
        for book in books
        if book["id"] == avg_rating["book_id"] and avg_rating["average_rating"] >= cutoff_average
    ]

    return jsonify(top_books_details)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=port)


