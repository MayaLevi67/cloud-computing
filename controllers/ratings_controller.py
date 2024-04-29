from flask import jsonify
from data.database import ratings

def get_ratings(query_id=None):
    filtered_ratings = [rating.to_dict() for rating in ratings if not query_id or rating.id == query_id]
    return jsonify(filtered_ratings), 200


def get_book_ratings(book_id):
    rating_entry = next((rating for rating in ratings if rating.id == book_id), None)
    if rating_entry:
        return jsonify(rating_entry.to_dict()), 200
    else:
        return jsonify({"message": "Ratings not found for the given book ID"}), 404
    

def add_rating(book_id, value):
    rating_entry = next((rating for rating in ratings if rating.id == book_id), None)
    if not rating_entry:
        return jsonify({"error": "Book not found"}), 404

    if value not in {1, 2, 3, 4, 5}:
        return jsonify({"error": "Invalid rating value. Must be an integer between 1 and 5."}), 422

    rating_entry.add_value(value)

    return jsonify({"new_average_rating": rating_entry.average}), 201


#TODO - not working good - why ? 
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

    return jsonify(top_books_details), 200
