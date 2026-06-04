"""
FinTrack – Flask Backend
Run:
  pip install flask werkzeug
  python app.py
Open: http://localhost:5000
Place signup.html and dashboard.html in the same folder as app.py.
"""

from flask import Flask, request, session, redirect, url_for, jsonify, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__, static_folder=".", template_folder=".")
app.secret_key = "fintrack-dev-secret-change-in-prod"

# ── In-memory data store ────────────────────────────────────────────────────
USERS = {}  # email -> { name, password_hash }

TRANSACTIONS = [
    {"id":1,"name":"Salary Deposit",        "amount": 2450.00,"category":"Income",       "date":"2026-05-31","type":"income"},
    {"id":2,"name":"Rent Payment",           "amount":-750.00, "category":"Rent",          "date":"2026-06-01","type":"expense"},
    {"id":3,"name":"Grocery Store",          "amount": -92.40, "category":"Food",          "date":"2026-05-28","type":"expense"},
    {"id":4,"name":"Monthly Bus Pass",       "amount": -45.00, "category":"Transport",     "date":"2026-05-30","type":"expense"},
    {"id":5,"name":"Netflix Subscription",   "amount": -14.99, "category":"Entertainment", "date":"2026-05-29","type":"expense"},
    {"id":6,"name":"Lunch – Café Lemon",     "amount": -18.50, "category":"Food",          "date":"2026-06-01","type":"expense"},
    {"id":7,"name":"Electronics Store",      "amount":-200.00, "category":"Shopping",      "date":"2026-05-29","type":"expense"},
    {"id":8,"name":"Freelance Payment",      "amount": 620.00, "category":"Income",        "date":"2026-05-27","type":"income"},
]

SPENDING_CATEGORIES = [
    {"label":"Food",          "icon":"🍔","pct":35,"color":"#0d9e75"},
    {"label":"Rent",          "icon":"🏠","pct":25,"color":"#3b82f6"},
    {"label":"Transport",     "icon":"🚗","pct":15,"color":"#f59e0b"},
    {"label":"Shopping",      "icon":"🛍️","pct":10,"color":"#ec4899"},
    {"label":"Entertainment", "icon":"🎬","pct":10,"color":"#6366f1"},
    {"label":"Other",         "icon":"💡","pct": 5,"color":"#94a3b8"},
]

MONTHLY_SUMMARY = {
    "income":   2450.00,
    "expenses": 1890.00,
    "savings":   560.00,
    "savings_pct": 22,
}

AI_INSIGHTS = [
    "Your food spending is 15% above your typical pattern this month.",
    "You could save $45 this month by reducing dining out twice a week.",
    "Low balance predicted for Feb 5. Consider adjusting your spending.",
    "Unusual transaction detected: $200 at Electronics Store on May 29.",
]


# ── Auth helpers ─────────────────────────────────────────────────────────────
def logged_in():
    return "user" in session


# ── Page routes ──────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return redirect(url_for("dashboard") if logged_in() else url_for("signup_page"))


@app.route("/signup")
def signup_page():
    return send_file("signup.html")


@app.route("/dashboard")
def dashboard():
    if not logged_in():
        # Demo: auto-login for quick preview
        session["user"] = {"name": "John Doe", "email": "demo@fintrack.com"}
    return send_file("dashboard.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("signup_page"))


# ── Auth API ──────────────────────────────────────────────────────────────────
@app.route("/api/signup", methods=["POST"])
def api_signup():
    data  = request.get_json() or {}
    name  = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    pwd   = data.get("password", "")

    if not name or not email or not pwd:
        return jsonify({"ok": False, "error": "All fields required"}), 400
    if email in USERS:
        return jsonify({"ok": False, "error": "Email already registered"}), 409
    if len(pwd) < 8:
        return jsonify({"ok": False, "error": "Password too short"}), 400

    USERS[email] = {"name": name, "password_hash": generate_password_hash(pwd)}
    session["user"] = {"name": name, "email": email}
    return jsonify({"ok": True, "redirect": "/dashboard"})


@app.route("/api/login", methods=["POST"])
def api_login():
    data  = request.get_json() or {}
    email = data.get("email", "").strip().lower()
    pwd   = data.get("password", "")
    user  = USERS.get(email)
    if not user or not check_password_hash(user["password_hash"], pwd):
        return jsonify({"ok": False, "error": "Invalid email or password"}), 401
    session["user"] = {"name": user["name"], "email": email}
    return jsonify({"ok": True, "redirect": "/dashboard"})


# ── Data API ──────────────────────────────────────────────────────────────────
@app.route("/api/balance")
def api_balance():
    return jsonify({
        "balance":     3245.50,
        "change_pct":  12,
        "direction":   "up",
    })


@app.route("/api/summary")
def api_summary():
    return jsonify(MONTHLY_SUMMARY)


@app.route("/api/categories")
def api_categories():
    return jsonify(SPENDING_CATEGORIES)


@app.route("/api/insights")
def api_insights():
    return jsonify(AI_INSIGHTS)


@app.route("/api/transactions", methods=["GET"])
def api_transactions():
    page     = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 10))
    cat      = request.args.get("category", "").lower()
    tx_type  = request.args.get("type", "").lower()

    data = TRANSACTIONS
    if cat:
        data = [t for t in data if t["category"].lower() == cat]
    if tx_type:
        data = [t for t in data if t["type"] == tx_type]

    total = len(data)
    start = (page - 1) * per_page
    return jsonify({
        "transactions": data[start : start + per_page],
        "total":        total,
        "page":         page,
        "pages":        (total + per_page - 1) // per_page,
    })


@app.route("/api/transactions", methods=["POST"])
def api_add_transaction():
    data = request.get_json() or {}
    required = ("name", "amount", "category", "date", "type")
    missing = [k for k in required if k not in data]
    if missing:
        return jsonify({"ok": False, "error": f"Missing: {', '.join(missing)}"}), 400

    new_tx = {
        "id":       max((t["id"] for t in TRANSACTIONS), default=0) + 1,
        "name":     data["name"],
        "amount":   float(data["amount"]),
        "category": data["category"],
        "date":     data["date"],
        "type":     data["type"],
    }
    TRANSACTIONS.insert(0, new_tx)
    return jsonify({"ok": True, "transaction": new_tx}), 201


@app.route("/api/transactions/<int:tx_id>", methods=["DELETE"])
def api_delete_transaction(tx_id):
    global TRANSACTIONS
    before = len(TRANSACTIONS)
    TRANSACTIONS = [t for t in TRANSACTIONS if t["id"] != tx_id]
    if len(TRANSACTIONS) == before:
        return jsonify({"ok": False, "error": "Not found"}), 404
    return jsonify({"ok": True})


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n  FinTrack → http://localhost:5000\n")
    print("  Endpoints:")
    print("    GET  /             → redirects to dashboard or signup")
    print("    GET  /signup       → signup page")
    print("    GET  /dashboard    → dashboard page")
    print("    POST /api/signup   → register { name, email, password }")
    print("    POST /api/login    → login    { email, password }")
    print("    GET  /api/balance  → current balance")
    print("    GET  /api/summary  → monthly summary")
    print("    GET  /api/categories → spending categories")
    print("    GET  /api/insights → AI insights")
    print("    GET  /api/transactions?page=1&per_page=10&category=&type=")
    print("    POST /api/transactions → add transaction")
    print("    DELETE /api/transactions/<id> → remove transaction\n")
    app.run(debug=True, port=5000)
