from flask import session, jsonify
from functools import wraps
from .models import SessionLocal


def get_db():
    return SessionLocal()


def logged_in():
    return "user" in session


def current_user_id():
    return session.get("user", {}).get("id")


def require_login(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not logged_in():
            return jsonify({"ok": False, "error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated


def tx_to_dict(t):
    amount = t.amount if t.transaction_type == "income" else -abs(t.amount)
    return {
        "id":         t.id,
        "name":       t.description,
        "amount":     amount,
        "category":   t.category,
        "date":       t.date.strftime("%Y-%m-%d") if t.date else "",
        "type":       t.transaction_type,
        "is_anomaly": t.is_anomaly,
    }
