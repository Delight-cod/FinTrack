from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from ..models import Transaction
from ..helpers import get_db, current_user_id, require_login
from ..constants import CATEGORIES, CATEGORY_COLOR, CATEGORY_ICON
from ..services.recommendation import RecommendationEngine

analytics_bp = Blueprint("analytics", __name__)


@analytics_bp.route("/api/balance")
@require_login
def api_balance():
    uid = current_user_id()
    db  = get_db()
    try:
        txns    = db.query(Transaction).filter(Transaction.user_id == uid).all()
        income  = sum(t.amount for t in txns if t.transaction_type == "income")
        expense = sum(t.amount for t in txns if t.transaction_type == "expense")
        return jsonify({"balance": round(income - expense, 2), "change_pct": 0, "direction": "up"})
    finally:
        db.close()


@analytics_bp.route("/api/summary")
@require_login
def api_summary():
    uid = current_user_id()
    now = datetime.now()
    db  = get_db()
    try:
        start = datetime(now.year, now.month, 1)
        end   = datetime(now.year, now.month + 1, 1) if now.month < 12 else datetime(now.year + 1, 1, 1)
        txns  = db.query(Transaction).filter(
            Transaction.user_id == uid,
            Transaction.date >= start,
            Transaction.date < end,
        ).all()
        income   = sum(t.amount for t in txns if t.transaction_type == "income")
        expenses = sum(t.amount for t in txns if t.transaction_type == "expense")
        savings  = income - expenses
        return jsonify({
            "income":      round(income, 2),
            "expenses":    round(expenses, 2),
            "savings":     round(savings, 2),
            "savings_pct": round((savings / income * 100) if income > 0 else 0, 1),
        })
    finally:
        db.close()


@analytics_bp.route("/api/categories")
@require_login
def api_categories():
    uid = current_user_id()
    now = datetime.now()
    db  = get_db()
    try:
        start = datetime(now.year, now.month, 1)
        end   = datetime(now.year, now.month + 1, 1) if now.month < 12 else datetime(now.year + 1, 1, 1)
        txns  = db.query(Transaction).filter(
            Transaction.user_id == uid,
            Transaction.date >= start,
            Transaction.date < end,
            Transaction.transaction_type == "expense",
        ).all()

        if not txns:
            return jsonify([])

        totals = {}
        for t in txns:
            totals[t.category] = totals.get(t.category, 0) + t.amount

        grand = sum(totals.values()) or 1
        return jsonify([
            {
                "label": cat,
                "icon":  CATEGORY_ICON.get(cat, "💡"),
                "pct":   round(amt / grand * 100),
                "color": CATEGORY_COLOR.get(cat, "#94a3b8"),
            }
            for cat, amt in sorted(totals.items(), key=lambda x: -x[1])
        ])
    finally:
        db.close()


@analytics_bp.route("/api/insights")
@require_login
def api_insights():
    uid = current_user_id()
    now = datetime.now()
    db  = get_db()
    try:
        recs     = RecommendationEngine(db).generate_monthly_insights(uid, now.year, now.month)
        messages = [r["message"] for r in recs] or ["Add transactions to start receiving AI-powered insights."]
        return jsonify(messages)
    finally:
        db.close()


@analytics_bp.route("/api/analytics")
@require_login
def api_analytics():
    uid   = current_user_id()
    now   = datetime.now()
    year  = int(request.args.get("year",  now.year))
    month = int(request.args.get("month", now.month))
    db    = get_db()
    try:
        start = datetime(year, month, 1)
        end   = datetime(year, month + 1, 1) if month < 12 else datetime(year + 1, 1, 1)
        txns  = db.query(Transaction).filter(
            Transaction.user_id == uid,
            Transaction.date >= start,
            Transaction.date < end,
        ).all()

        income   = sum(t.amount for t in txns if t.transaction_type == "income")
        expenses = sum(t.amount for t in txns if t.transaction_type == "expense")
        savings  = income - expenses

        cat_data = {}
        for t in txns:
            if t.transaction_type == "expense":
                cat_data[t.category] = cat_data.get(t.category, 0) + t.amount

        top  = sorted(cat_data.items(), key=lambda x: x[1], reverse=True)[:5]
        recs = RecommendationEngine(db).generate_monthly_insights(uid, year, month)

        return jsonify({
            "total_income":            round(income, 2),
            "total_expenses":          round(expenses, 2),
            "savings":                 round(savings, 2),
            "savings_rate":            round((savings / income * 100) if income > 0 else 0, 1),
            "category_breakdown":      {k: round(v, 2) for k, v in cat_data.items()},
            "top_spending_categories": [{"category": c, "amount": round(a, 2)} for c, a in top],
            "recommendations":         [r["message"] for r in recs],
        })
    finally:
        db.close()


@analytics_bp.route("/api/forecast")
@require_login
def api_forecast():
    uid  = current_user_id()
    days = int(request.args.get("days", 30))
    db   = get_db()
    try:
        start = datetime.now() - timedelta(days=60)
        txns  = db.query(Transaction).filter(
            Transaction.user_id == uid,
            Transaction.date >= start,
        ).order_by(Transaction.date).all()

        balance, balances = 0.0, []
        for t in txns:
            balance += t.amount if t.transaction_type == "income" else -t.amount
            balances.append(balance)

        avg_change  = ((balances[-1] - balances[-7]) / 7) if len(balances) > 7 else 0
        current_bal = balances[-1] if balances else 0.0

        dates, predicted, lower, upper = [], [], [], []
        for i in range(days):
            d = datetime.now() + timedelta(days=i + 1)
            p = current_bal + avg_change * (i + 1)
            dates.append(d.strftime("%Y-%m-%d"))
            predicted.append(round(p, 2))
            lower.append(round(p * 0.85, 2))
            upper.append(round(p * 1.15, 2))

        alerts = [
            f"Low balance predicted on {dates[i]}: FCFA {int(predicted[i]):,}"
            for i in range(len(predicted))
            if predicted[i] < 10000
        ]

        return jsonify({
            "dates":              dates,
            "predicted_balances": predicted,
            "lower_bounds":       lower,
            "upper_bounds":       upper,
            "alerts":             alerts,
        })
    finally:
        db.close()


@analytics_bp.route("/api/category-list")
def api_category_list():
    return jsonify(CATEGORIES)
