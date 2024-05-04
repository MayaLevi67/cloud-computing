from flask import Blueprint, jsonify, request
from controllers.books_controller import add_book, get_book, get_books, update_book, delete_book

book_routes = Blueprint('book_routes', __name__)

@book_routes.route('/books', methods=['POST'])
def route_add_book():
    if request.content_type != 'application/json':
        return jsonify({"error": "Unsupported media type"}), 415
    try:
        data = request.get_json()
    except:
        return jsonify({"error": "Invalid JSON data."}), 422
    return add_book(data)

@book_routes.route('/books/<book_id>', methods=['GET'])
def route_get_book(book_id):
    return get_book(book_id)

@book_routes.route('/books', methods=['GET'])
def route_get_books():
    return get_books(request.args) 

@book_routes.route('/books/<book_id>', methods=['PUT'])
def route_update_book(book_id):
    if request.content_type != 'application/json':
        return jsonify({"error": "Unsupported media type"}), 415
    try:
        updated_data = request.get_json()
    except:
        return jsonify({"error": "Invalid JSON data."}), 422
    return update_book(book_id, updated_data)

@book_routes.route('/books/<book_id>', methods=['DELETE'])
def route_delete_book(book_id):
    return delete_book(book_id)
