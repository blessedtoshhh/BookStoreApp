from flask import Flask
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from models import db
from routes.auth import auth_bp
from routes.books import books_bp
from routes.orders import orders_bp

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///bookstore.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JWT_SECRET_KEY"] = "change-this-secret-before-production"

db.init_app(app)
JWTManager(app)
CORS(app)

app.register_blueprint(auth_bp, url_prefix="/auth")
app.register_blueprint(books_bp, url_prefix="/books")
app.register_blueprint(orders_bp, url_prefix="/store")

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)
