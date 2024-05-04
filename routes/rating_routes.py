from data.database import ratings
from flask import Blueprint, app, jsonify, request
from controllers.ratings_controller import get_ratings, get_book_ratings, add_rating, get_top_books

rating_routes = Blueprint('rating_routes', __name__)

@rating_routes.route('/ratings', methods=['GET'])
def route_get_ratings():
    query_id = request.args.get('id')
    return get_ratings(query_id)

@rating_routes.route('/ratings/<book_id>', methods=['GET'])
def route_get_book_ratings(book_id):
    return get_book_ratings(book_id)

@rating_routes.route('/ratings/<book_id>/values', methods=['POST'])
def route_add_rating(book_id):
    if request.content_type != 'application/json':
        return jsonify({"error": "Unsupported media type"}), 415
    
    data = request.get_json()
    new_rating = data.get('value')
    
    return add_rating(book_id, new_rating)

@rating_routes.route('/top', methods=['GET'])
def top_books():
    try:
        return get_top_books(ratings)
    except Exception as e:
        return jsonify({'error': 'Internal Server Error', 'message': str(e)}), 500
