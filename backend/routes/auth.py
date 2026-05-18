from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, LoginActivity

auth_bp = Blueprint("auth", __name__)


def _get_ua():
    return (request.headers.get("User-Agent") or "")[:300]


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    if not data or not data.get("email") or not data.get("password") or not data.get("name"):
        return jsonify({"error": "name, email, and password are required"}), 400

    if User.query.filter_by(email=data["email"]).first():
        return jsonify({"error": "Email already registered"}), 409

    user = User(
        name=data["name"],
        email=data["email"],
        password_hash=generate_password_hash(data["password"]),
        role="customer",
    )
    db.session.add(user)
    db.session.commit()
    return jsonify({"message": "User registered successfully"}), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    if not data or not data.get("email") or not data.get("password"):
        return jsonify({"error": "email and password are required"}), 400

    email = data["email"]
    user = User.query.filter_by(email=email).first()
    success = bool(user and check_password_hash(user.password_hash, data["password"]))

    activity = LoginActivity(
        email=email,
        user_id=user.id if success else None,
        success=success,
        user_agent=_get_ua(),
    )
    db.session.add(activity)
    db.session.commit()

    if not success:
        return jsonify({"error": "Invalid credentials"}), 401

    token = create_access_token(identity=str(user.id), additional_claims={"role": user.role})
    return jsonify({"token": token, "role": user.role}), 200


@auth_bp.route("/login-activity", methods=["GET"])
@jwt_required()
def login_activity():
    claims = get_jwt()
    if claims.get("role") != "manager":
        return jsonify({"error": "Managers only"}), 403

    limit = min(int(request.args.get("limit", 200)), 500)
    rows = (LoginActivity.query
            .order_by(LoginActivity.timestamp.desc())
            .limit(limit)
            .all())

    return jsonify([{
        "id": r.id,
        "email": r.email,
        "user_name": r.user.name if r.user else None,
        "success": r.success,
        "user_agent": r.user_agent,
        "timestamp": r.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"),
    } for r in rows]), 200
