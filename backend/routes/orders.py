from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from models import db, Cart, CartItem, Order, OrderItem, Payment, Book, ActivityLog
from datetime import datetime, timezone

orders_bp = Blueprint("orders", __name__)


@orders_bp.route("/cart", methods=["GET"])
@jwt_required()
def get_cart():
    user_id = int(get_jwt_identity())
    cart = _get_or_create_cart(user_id)
    return jsonify(_serialize_cart(cart)), 200


@orders_bp.route("/cart", methods=["POST"])
@jwt_required()
def add_to_cart():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    book = Book.query.get_or_404(data["book_id"])

    if book.stock_quantity < 1:
        return jsonify({"error": "Book is out of stock"}), 400

    cart = _get_or_create_cart(user_id)
    existing = CartItem.query.filter_by(cart_id=cart.id, book_id=book.id).first()
    if existing:
        existing.quantity += data.get("quantity", 1)
    else:
        cart.items.append(CartItem(book_id=book.id, quantity=data.get("quantity", 1)))

    db.session.commit()
    return jsonify(_serialize_cart(cart)), 200


@orders_bp.route("/cart/<int:item_id>", methods=["DELETE"])
@jwt_required()
def remove_from_cart(item_id):
    user_id = int(get_jwt_identity())
    cart = _get_or_create_cart(user_id)
    item = CartItem.query.filter_by(id=item_id, cart_id=cart.id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    return jsonify({"message": "Item removed"}), 200


@orders_bp.route("/checkout", methods=["POST"])
@jwt_required()
def checkout():
    user_id = int(get_jwt_identity())
    cart = _get_or_create_cart(user_id)

    if not cart.items:
        return jsonify({"error": "Cart is empty"}), 400

    total = sum(item.book.price * item.quantity for item in cart.items)
    order = Order(user_id=user_id, total=total, status="pending")
    db.session.add(order)
    db.session.flush()

    for item in cart.items:
        order.items.append(OrderItem(
            book_id=item.book_id,
            quantity=item.quantity,
            price_at_purchase=item.book.price,
        ))
        item.book.stock_quantity -= item.quantity

    data = request.get_json() or {}
    payment = Payment(
        order_id=order.id,
        amount=total,
        method=data.get("payment_method", "credit_card"),
        status="approved",
        transaction_ref="TXN-MOCK",
    )
    db.session.add(payment)
    order.status = "paid"

    db.session.delete(cart)
    db.session.add(ActivityLog(
        user_id=user_id,
        action="order_placed",
        details=f"Order #{order.id} placed — {len(order.items)} item(s), total ${total:.2f}",
    ))
    db.session.commit()
    return jsonify({"order_id": order.id, "total": total, "status": order.status}), 201


@orders_bp.route("/orders", methods=["GET"])
@jwt_required()
def get_orders():
    claims = get_jwt()
    role = claims.get("role", "customer")
    user_id = int(get_jwt_identity())
    if role in ("employee", "manager"):
        orders = Order.query.all()
    else:
        orders = Order.query.filter_by(user_id=user_id).all()
    return jsonify([_serialize_order(o) for o in orders]), 200


@orders_bp.route("/sales-report", methods=["GET"])
@jwt_required()
def sales_report():
    claims = get_jwt()
    if claims.get("role") not in ("employee", "manager"):
        return jsonify({"error": "Access denied."}), 403

    start_str = request.args.get("start")
    end_str = request.args.get("end")

    query = Order.query.filter_by(status="paid")
    try:
        if start_str:
            query = query.filter(Order.created_at >= datetime.strptime(start_str, "%Y-%m-%d"))
        if end_str:
            end_dt = datetime.strptime(end_str, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            query = query.filter(Order.created_at <= end_dt)
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD."}), 400

    orders = query.order_by(Order.created_at.desc()).all()

    total_revenue = sum(o.total for o in orders)
    total_orders = len(orders)
    total_items = sum(sum(i.quantity for i in o.items) for o in orders)

    book_sales = {}
    for o in orders:
        for i in o.items:
            if i.book_id not in book_sales:
                book_sales[i.book_id] = {"title": i.book.title, "author": i.book.author.name, "quantity": 0, "revenue": 0.0}
            book_sales[i.book_id]["quantity"] += i.quantity
            book_sales[i.book_id]["revenue"] += round(i.price_at_purchase * i.quantity, 2)

    top_books = sorted(book_sales.values(), key=lambda x: x["quantity"], reverse=True)

    return jsonify({
        "summary": {
            "total_revenue": round(total_revenue, 2),
            "total_orders": total_orders,
            "total_items_sold": total_items,
        },
        "top_books": top_books,
        "orders": [_serialize_order(o) for o in orders],
    }), 200


@orders_bp.route("/inventory-report", methods=["GET"])
@jwt_required()
def inventory_report():
    claims = get_jwt()
    if claims.get("role") not in ("employee", "manager"):
        return jsonify({"error": "Access denied."}), 403

    category = request.args.get("category", "").strip()
    stock_filter = request.args.get("stock", "all")

    from models import Author
    query = Book.query.join(Author)
    if category:
        query = query.filter(Book.category.ilike(f"%{category}%"))
    if stock_filter == "low":
        query = query.filter(Book.stock_quantity > 0, Book.stock_quantity <= 3)
    elif stock_filter == "out":
        query = query.filter(Book.stock_quantity == 0)
    elif stock_filter == "in":
        query = query.filter(Book.stock_quantity > 3)

    books = query.order_by(Book.stock_quantity.asc()).all()
    total_value = sum(b.price * b.stock_quantity for b in books)

    return jsonify({
        "summary": {
            "total_titles": len(books),
            "total_units": sum(b.stock_quantity for b in books),
            "total_value": round(total_value, 2),
        },
        "books": [{
            "id": b.id,
            "title": b.title,
            "author": b.author.name,
            "category": b.category or "N/A",
            "price": b.price,
            "stock_quantity": b.stock_quantity,
            "stock_value": round(b.price * b.stock_quantity, 2),
        } for b in books],
    }), 200


def _get_or_create_cart(user_id):
    cart = Cart.query.filter_by(user_id=user_id).first()
    if not cart:
        cart = Cart(user_id=user_id)
        db.session.add(cart)
        db.session.commit()
    return cart


def _serialize_cart(cart):
    items = [
        {
            "cart_item_id": i.id,
            "book_id": i.book_id,
            "title": i.book.title,
            "price": i.book.price,
            "quantity": i.quantity,
            "subtotal": round(i.book.price * i.quantity, 2),
        }
        for i in cart.items
    ]
    return {
        "cart_id": cart.id,
        "items": items,
        "total": round(sum(i["subtotal"] for i in items), 2),
    }


def _serialize_order(order):
    return {
        "order_id": order.id,
        "status": order.status,
        "total": order.total,
        "created_at": order.created_at.isoformat(),
        "items": [
            {
                "title": i.book.title,
                "quantity": i.quantity,
                "price_at_purchase": i.price_at_purchase,
            }
            for i in order.items
        ],
    }
