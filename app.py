from flask import Flask
from routes.book_routes import book_routes
from routes.rating_routes import rating_routes

app = Flask(__name__)
app.register_blueprint(book_routes)
app.register_blueprint(rating_routes)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)
