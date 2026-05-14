from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt, verify_jwt_in_request
from models import db, Feedback, User
from datetime import datetime, timezone

feedback_bp = Blueprint("feedback", __name__)

VALID_STATUSES = ("new", "reviewed", "actioned")


def _serialize(f):
    return {
        "id": f.id,
        "name": f.name or "Anonymous",
        "email": f.email or "",
        "rating": f.rating,
        "category": f.category or "general",
        "message": f.message,
        "status": f.status or "new",
        "internal_note": f.internal_note or "",
        "created_at": f.created_at.strftime("%Y-%m-%d %H:%M") if f.created_at else "",
        "updated_at": f.updated_at.strftime("%Y-%m-%d %H:%M") if f.updated_at else "",
    }


@feedback_bp.route("/", methods=["POST"])
def submit_feedback():
    data = request.get_json()

    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"error": "Message is required."}), 400

    rating = data.get("rating")
    if not isinstance(rating, int) or rating < 1 or rating > 5:
        return jsonify({"error": "Rating must be an integer between 1 and 5."}), 400

    user_id = None
    name = (data.get("name") or "").strip() or "Anonymous"
    email = (data.get("email") or "").strip()

    try:
        verify_jwt_in_request(optional=True)
        identity = get_jwt_identity()
        if identity:
            user_id = int(identity)
            user = User.query.get(user_id)
            if user:
                name = user.name
                email = user.email
    except Exception:
        pass

    feedback = Feedback(
        user_id=user_id,
        name=name,
        email=email,
        rating=rating,
        category=data.get("category", "general"),
        message=message,
        status="new",
    )
    db.session.add(feedback)
    db.session.commit()

    return jsonify({"message": "Thank you for your feedback!"}), 201


@feedback_bp.route("/public", methods=["GET"])
def get_public_feedback():
    entries = (
        Feedback.query
        .filter(Feedback.status.in_(["reviewed", "actioned"]))
        .order_by(Feedback.created_at.desc())
        .all()
    )
    result = []
    for f in entries:
        result.append({
            "id": f.id,
            "name": f.name or "Anonymous",
            "rating": f.rating,
            "category": f.category or "general",
            "message": f.message,
            "status": f.status,
            "response": f.internal_note if f.status == "actioned" and f.internal_note else None,
            "created_at": f.created_at.strftime("%B %d, %Y") if f.created_at else "",
        })
    total = Feedback.query.filter(Feedback.status.in_(["reviewed", "actioned"])).count()
    all_ratings = [f.rating for f in Feedback.query.filter(Feedback.status.in_(["reviewed", "actioned"])).all()]
    avg = round(sum(all_ratings) / len(all_ratings), 1) if all_ratings else None
    return jsonify({"entries": result, "avg": avg, "total": total}), 200


@feedback_bp.route("/", methods=["GET"])
@jwt_required()
def get_feedback():
    claims = get_jwt()
    role = claims.get("role", "customer")
    if role not in ("employee", "manager"):
        return jsonify({"error": "Access denied."}), 403

    status_filter = request.args.get("status")
    query = Feedback.query.order_by(Feedback.created_at.desc())
    if status_filter and status_filter in VALID_STATUSES:
        query = query.filter(Feedback.status == status_filter)

    entries = query.all()
    counts = {s: Feedback.query.filter(Feedback.status == s).count() for s in VALID_STATUSES}
    counts["all"] = Feedback.query.count()

    return jsonify({"entries": [_serialize(f) for f in entries], "counts": counts}), 200


@feedback_bp.route("/<int:feedback_id>", methods=["PATCH"])
@jwt_required()
def update_feedback(feedback_id):
    claims = get_jwt()
    role = claims.get("role", "customer")
    if role not in ("employee", "manager"):
        return jsonify({"error": "Access denied."}), 403

    f = Feedback.query.get_or_404(feedback_id)
    data = request.get_json()

    if "status" in data:
        if data["status"] not in VALID_STATUSES:
            return jsonify({"error": "Invalid status."}), 400
        f.status = data["status"]

    if "internal_note" in data:
        f.internal_note = data["internal_note"]

    f.updated_at = datetime.now(timezone.utc)
    db.session.commit()

    return jsonify(_serialize(f)), 200
