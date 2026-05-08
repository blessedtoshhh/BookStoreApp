from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import db, Cart, CartItem, Order, OrderItem, Payment, Book

orders_bp = Blueprint("orders", __name__)


@orders_bp.route("/cart", methods=["GET"])
@jwt_required()
def get_cart():
    user_id = get_jwt_identity()["id"]
    cart = _get_or_create_cart(user_id)
    return jsonify(_serialize_cart(cart)), 200


@orders_bp.route("/cart", methods=["POST"])
@jwt_required()
def add_to_cart():
    user_id = get_jwt_identity()["id"]
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
    user_id = get_jwt_identity()["id"]
    cart = _get_or_create_cart(user_id)
    item = CartItem.query.filter_by(id=item_id, cart_id=cart.id).first_or_404()
    db.session.delete(item)
    db.session.commit()
    return jsonify({"message": "Item removed"}), 200


@orders_bp.route("/checkout", methods=["POST"])
@jwt_required()
def checkout():
    user_id = get_jwt_identity()["id"]
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
    db.session.commit()
    return jsonify({"order_id": order.id, "total": total, "status": order.status}), 201


@orders_bp.route("/orders", methods=["GET"])
@jwt_required()
def get_orders():
    identity = get_jwt_identity()
    if identity["role"] in ("employee", "manager"):
        orders = Order.query.all()
    else:
        orders = Order.query.filter_by(user_id=identity["id"]).all()
    return jsonify([_serialize_order(o) for o in orders]), 200


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
