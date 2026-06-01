from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from models import db, VendorOrder, Book, ActivityLog
from datetime import datetime, timezone

vendor_orders_bp = Blueprint("vendor_orders", __name__)

VALID_STATUSES = ("Pending", "Partially Received", "Received", "Cancelled")


def _require_employee():
    claims = get_jwt()
    if claims.get("role", "customer") not in ("employee", "manager"):
        from flask import abort
        abort(403)


def _serialize(order):
    return {
        "id": order.id,
        "book_id": order.book_id,
        "book_title": order.book.title,
        "book_author": order.book.author.name,
        "vendor_name": order.vendor_name,
        "quantity_ordered": order.quantity_ordered,
        "quantity_received": order.quantity_received,
        "status": order.status,
        "created_at": order.created_at.strftime("%Y-%m-%d %H:%M") if order.created_at else "",
        "received_at": order.received_at.strftime("%Y-%m-%d %H:%M") if order.received_at else None,
    }


@vendor_orders_bp.route("/", methods=["POST"])
@jwt_required()
def create_vendor_order():
    _require_employee()
    data = request.get_json() or {}

    book_id = data.get("book_id")
    vendor_name = (data.get("vendor_name") or "").strip()
    quantity_ordered = data.get("quantity_ordered")

    if not isinstance(book_id, int):
        return jsonify({"error": "book_id must be a number"}), 400
    if not vendor_name:
        return jsonify({"error": "vendor_name is required"}), 400
    if not isinstance(quantity_ordered, int) or quantity_ordered <= 0:
        return jsonify({"error": "quantity_ordered must be a positive whole number"}), 400

    book = Book.query.get(book_id)
    if not book:
        return jsonify({"error": "Book not found"}), 404

    order = VendorOrder(
        book_id=book.id,
        vendor_name=vendor_name,
        quantity_ordered=quantity_ordered,
        status="Pending",
    )
    db.session.add(order)
    db.session.flush()
    db.session.add(ActivityLog(
        user_id=int(get_jwt_identity()),
        action="vendor_order_created",
        details=f"Vendor order #{order.id} created — {quantity_ordered}x '{book.title}' from {vendor_name}",
    ))
    db.session.commit()
    return jsonify(_serialize(order)), 201


@vendor_orders_bp.route("/", methods=["GET"])
@jwt_required()
def list_vendor_orders():
    _require_employee()
    status_filter = request.args.get("status", "").strip()
    query = VendorOrder.query.order_by(VendorOrder.created_at.desc())
    if status_filter and status_filter in VALID_STATUSES:
        query = query.filter(VendorOrder.status == status_filter)
    orders = query.all()
    return jsonify([_serialize(o) for o in orders]), 200


@vendor_orders_bp.route("/<int:order_id>/receive", methods=["POST"])
@jwt_required()
def receive_vendor_order(order_id):
    _require_employee()
    data = request.get_json() or {}
    quantity_received = data.get("quantity_received")

    if not isinstance(quantity_received, int) or quantity_received <= 0:
        return jsonify({"error": "quantity_received must be a positive whole number"}), 400

    order = VendorOrder.query.get_or_404(order_id)

    if order.status == "Cancelled":
        return jsonify({"error": "Cannot receive stock on a cancelled order"}), 400
    if order.status == "Received":
        return jsonify({"error": "Order already fully received"}), 400

    order.quantity_received += quantity_received
    order.book.stock_quantity += quantity_received

    if order.quantity_received >= order.quantity_ordered:
        order.status = "Received"
        order.received_at = datetime.now(timezone.utc)
    else:
        order.status = "Partially Received"

    db.session.add(ActivityLog(
        user_id=int(get_jwt_identity()),
        action="vendor_order_received",
        details=f"Received {quantity_received}x '{order.book.title}' on order #{order.id} — new stock: {order.book.stock_quantity}",
    ))
    db.session.commit()
    return jsonify(_serialize(order)), 200


@vendor_orders_bp.route("/<int:order_id>/cancel", methods=["POST"])
@jwt_required()
def cancel_vendor_order(order_id):
    _require_employee()
    order = VendorOrder.query.get_or_404(order_id)

    if order.status in ("Received", "Cancelled"):
        return jsonify({"error": f"Cannot cancel an order with status '{order.status}'"}), 400

    order.status = "Cancelled"
    db.session.add(ActivityLog(
        user_id=int(get_jwt_identity()),
        action="vendor_order_cancelled",
        details=f"Vendor order #{order.id} for '{order.book.title}' cancelled",
    ))
    db.session.commit()
    return jsonify(_serialize(order)), 200
