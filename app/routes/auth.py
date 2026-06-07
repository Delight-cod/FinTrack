from flask import Blueprint, request, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from ..models import User
from ..helpers import get_db

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/api/me")
def api_me():
    user = session.get("user", {})
    return jsonify({"name": user.get("name", "User"), "email": user.get("email", "")})


@auth_bp.route("/api/signup", methods=["POST"])
def api_signup():
    data  = request.get_json() or {}
    name  = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    pwd   = data.get("password", "")

    if not name or not email or not pwd:
        return jsonify({"ok": False, "error": "All fields required"}), 400
    if len(pwd) < 8:
        return jsonify({"ok": False, "error": "Password too short (min 8 chars)"}), 400

    db = get_db()
    try:
        if db.query(User).filter(User.email == email).first():
            return jsonify({"ok": False, "error": "Email already registered"}), 409
        user = User(
            username=name,
            email=email,
            password_hash=generate_password_hash(pwd),
            user_type=data.get("user_type", "worker"),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        session["user"] = {"id": user.id, "name": name, "email": email}
        return jsonify({"ok": True, "redirect": "/dashboard"})
    finally:
        db.close()


@auth_bp.route("/api/login", methods=["POST"])
def api_login():
    data  = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    pwd   = data.get("password", "")

    db = get_db()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user or not user.password_hash or not check_password_hash(user.password_hash, pwd):
            return jsonify({"ok": False, "error": "Invalid email or password"}), 401
        session["user"] = {"id": user.id, "name": user.username, "email": email}
        return jsonify({"ok": True, "redirect": "/dashboard"})
    finally:
        db.close()
