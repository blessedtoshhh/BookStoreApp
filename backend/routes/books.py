from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Book, Author

books_bp = Blueprint("books", __name__)


@books_bp.route("/", methods=["GET"])
def get_books():
    search = request.args.get("q", "").strip()
    query = Book.query.join(Author)
    if search:
        query = query.filter(
            Book.title.ilike(f"%{search}%") | Author.name.ilike(f"%{search}%")
        )
    books = query.all()
    return jsonify([_serialize(b) for b in books]), 200


@books_bp.route("/<int:book_id>", methods=["GET"])
def get_book(book_id):
    book = Book.query.get_or_404(book_id)
    return jsonify(_serialize(book)), 200


@books_bp.route("/", methods=["POST"])
@jwt_required()
def create_book():
    _require_employee()
    data = request.get_json()
    author = Author.query.get(data["author_id"]) if data.get("author_id") else None
    if not author:
        author = Author(name=data.get("author_name", "Unknown"))
        db.session.add(author)
        db.session.flush()

    book = Book(
        title=data["title"],
        author_id=author.id,
        isbn=data.get("isbn"),
        price=data["price"],
        stock_quantity=data.get("stock_quantity", 0),
        category=data.get("category"),
        description=data.get("description"),
    )
    db.session.add(book)
    db.session.commit()
    return jsonify(_serialize(book)), 201


@books_bp.route("/<int:book_id>", methods=["PUT"])
@jwt_required()
def update_book(book_id):
    _require_employee()
    book = Book.query.get_or_404(book_id)
    data = request.get_json()
    for field in ("title", "price", "stock_quantity", "category", "description", "isbn"):
        if field in data:
            setattr(book, field, data[field])
    db.session.commit()
    return jsonify(_serialize(book)), 200


def _require_employee():
    identity = get_jwt_identity()
    if identity["role"] not in ("employee", "manager"):
        from flask import abort
        abort(403)


def _serialize(book):
    return {
        "id": book.id,
        "title": book.title,
        "author": book.author.name,
        "isbn": book.isbn,
        "price": book.price,
        "stock_quantity": book.stock_quantity,
        "category": book.category,
        "description": book.description,
    }
