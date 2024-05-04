from collections import defaultdict
from flask import jsonify
from data.database import ratings
from flask import jsonify, current_app as app


def get_ratings(query_id=None):
    filtered_ratings = [rating.to_dict() for rating in ratings if not query_id or rating.id == query_id]
    return jsonify(filtered_ratings), 200


def get_book_ratings(book_id):
    rating_entry = None

    for rating in ratings:
        if rating.id == book_id:
            rating_entry = rating
            break

    if rating_entry:
        return jsonify(rating_entry.to_dict()), 200
    else:
        return jsonify({"message": "Ratings not found for the given book ID"}), 404
    

def add_rating(book_id, value):
    rating_entry = None

    for rating in ratings:
        if rating.id == book_id:
            rating_entry = rating
            break

    if not rating_entry:
        return jsonify({"error": "Book not found"}), 404

    if value not in {1, 2, 3, 4, 5}:
        return jsonify({"error": "Invalid rating value. Must be an integer between 1 and 5"}), 422

    rating_entry.add_value(value)

    return jsonify({"new_average_rating": rating_entry.average}), 201


def get_top_books(ratings):
    try:
        eligible_books = [rating for rating in ratings if len(rating.values) >= 3]

        if not eligible_books:
            return jsonify([])

        rating_groups = defaultdict(list)
        for book in eligible_books:
            rating_groups[book.average].append(book)

        top_ratings = sorted(rating_groups.keys(), reverse=True)[:3]

        top_books = []
        for rating in top_ratings:
            top_books.extend(rating_groups[rating])

        sorted_books_dicts = [book.to_dict() for book in top_books]
        return jsonify(sorted_books_dicts)

    except Exception as e:
        return jsonify({"error": "Failed to retrieve top books"})


