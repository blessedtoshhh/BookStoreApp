from flask import Flask, send_from_directory
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from models import db
from routes.auth import auth_bp
from routes.books import books_bp
from routes.orders import orders_bp
from routes.feedback import feedback_bp
from routes.vendor_orders import vendor_orders_bp
import os

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend")

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///bookstore.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["JWT_SECRET_KEY"] = "change-this-secret-before-production"

db.init_app(app)
JWTManager(app)
CORS(app)

app.register_blueprint(auth_bp, url_prefix="/auth")
app.register_blueprint(books_bp, url_prefix="/books")
app.register_blueprint(orders_bp, url_prefix="/store")
app.register_blueprint(feedback_bp, url_prefix="/feedback")
app.register_blueprint(vendor_orders_bp, url_prefix="/vendor-orders")

@app.route("/")
@app.route("/<path:path>")
def serve_frontend(path="index.html"):
    return send_from_directory(FRONTEND_DIR, path if path else "index.html")

with app.app_context():
    db.create_all()
    from sqlalchemy import text, inspect
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()

    existing_feedback_cols = [c["name"] for c in inspector.get_columns("feedback")] if "feedback" in tables else []
    with db.engine.connect() as conn:
        if "status" not in existing_feedback_cols:
            conn.execute(text("ALTER TABLE feedback ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'new'"))
            conn.commit()
        if "internal_note" not in existing_feedback_cols:
            conn.execute(text("ALTER TABLE feedback ADD COLUMN internal_note TEXT"))
            conn.commit()
        if "updated_at" not in existing_feedback_cols:
            conn.execute(text("ALTER TABLE feedback ADD COLUMN updated_at DATETIME"))
            conn.commit()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
