from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from models import db, Book, Author, ActivityLog

books_bp = Blueprint("books", __name__)


@books_bp.route("/", methods=["GET"])
def get_books():
    search = request.args.get("q", "").strip()
    search_type = request.args.get("type", "all")
    query = Book.query.join(Author)
    if search:
        if search_type == "title":
            query = query.filter(Book.title.ilike(f"%{search}%"))
        elif search_type == "author":
            query = query.filter(Author.name.ilike(f"%{search}%"))
        elif search_type == "category":
            query = query.filter(Book.category.ilike(f"%{search}%"))
        else:
            query = query.filter(
                Book.title.ilike(f"%{search}%") |
                Author.name.ilike(f"%{search}%") |
                Book.category.ilike(f"%{search}%")
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
    db.session.flush()
    db.session.add(ActivityLog(
        user_id=int(get_jwt_identity()),
        action="book_added",
        details=f"Added '{book.title}' by {author.name} (stock: {book.stock_quantity})",
    ))
    db.session.commit()
    return jsonify(_serialize(book)), 201


@books_bp.route("/<int:book_id>", methods=["PUT"])
@jwt_required()
def update_book(book_id):
    _require_employee()
    book = Book.query.get_or_404(book_id)
    data = request.get_json()
    old_stock = book.stock_quantity
    for field in ("title", "price", "stock_quantity", "category", "description", "isbn"):
        if field in data:
            setattr(book, field, data[field])
    if "stock_quantity" in data and data["stock_quantity"] != old_stock:
        db.session.add(ActivityLog(
            user_id=int(get_jwt_identity()),
            action="stock_updated",
            details=f"'{book.title}' stock changed from {old_stock} to {book.stock_quantity}",
        ))
    db.session.commit()
    return jsonify(_serialize(book)), 200


def _require_employee():
    claims = get_jwt()
    if claims.get("role", "customer") not in ("employee", "manager"):
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

@books_bp.route("/<int:book_id>/receive-stock", methods=["POST"])
@jwt_required()
def receive_vendor_stock(book_id):

    employee_check = _require_employee()
    if employee_check:
        return employee_check

    data = request.get_json() or {}
    quantity_received = data.get("quantity_received")

    if not isinstance(quantity_received, int) or quantity_received <= 0:
        return jsonify({
            "error": "quantity_received must be a positive whole number"
        }), 400

    book = Book.query.get(book_id)

    if not book:
        return jsonify({"error": "Book not found"}), 404

    book.stock_quantity += quantity_received
    db.session.commit()

    return jsonify({
        "message": "Vendor stock received successfully",
        "book_id": book.id,
        "title": book.title,
        "quantity_received": quantity_received,
        "new_stock_quantity": book.stock_quantity
    }), 200
