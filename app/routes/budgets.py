import io
from flask import Blueprint, request, jsonify
from datetime import datetime
import pandas as pd
from ..models import Budget, Transaction
from ..helpers import get_db, current_user_id, require_login
from ..services.ml_service import ml_service
from ..services.recommendation import RecommendationEngine

budgets_bp = Blueprint("budgets", __name__)


@budgets_bp.route("/api/budgets", methods=["GET"])
@require_login
def api_get_budgets():
    uid   = current_user_id()
    now   = datetime.now()
    month = int(request.args.get("month", now.month))
    year  = int(request.args.get("year",  now.year))
    db    = get_db()
    try:
        budgets = db.query(Budget).filter(
            Budget.user_id == uid,
            Budget.month   == month,
            Budget.year    == year,
        ).all()
        return jsonify([{
            "id": b.id, "category": b.category,
            "monthly_limit": b.monthly_limit,
            "month": b.month, "year": b.year,
        } for b in budgets])
    finally:
        db.close()


@budgets_bp.route("/api/budgets", methods=["POST"])
@require_login
def api_create_budget():
    uid  = current_user_id()
    data = request.get_json() or {}
    required = ("category", "monthly_limit", "month", "year")
    missing  = [k for k in required if k not in data]
    if missing:
        return jsonify({"ok": False, "error": f"Missing: {', '.join(missing)}"}), 400
    db = get_db()
    try:
        budget = Budget(
            user_id=uid,
            category=data["category"],
            monthly_limit=float(data["monthly_limit"]),
            month=int(data["month"]),
            year=int(data["year"]),
        )
        db.add(budget)
        db.commit()
        db.refresh(budget)
        return jsonify({"ok": True, "id": budget.id}), 201
    finally:
        db.close()


@budgets_bp.route("/api/recommendations")
@require_login
def api_recommendations():
    uid = current_user_id()
    db  = get_db()
    try:
        recs = RecommendationEngine(db).get_recommendations(uid)
        return jsonify({"recommendations": recs})
    finally:
        db.close()


@budgets_bp.route("/api/upload-csv", methods=["POST"])
@require_login
def api_upload_csv():
    uid = current_user_id()
    if "file" not in request.files:
        return jsonify({"ok": False, "error": "No file provided"}), 400
    f = request.files["file"]
    if not f.filename.lower().endswith(".csv"):
        return jsonify({"ok": False, "error": "Please upload a CSV file"}), 400

    db = get_db()
    try:
        df = pd.read_csv(io.StringIO(f.read().decode("utf-8")))
        required_cols = ["date", "description", "amount"]
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            return jsonify({"ok": False, "error": f"Missing columns: {', '.join(missing)}"}), 400

        added, anomalies = 0, 0
        for _, row in df.iterrows():
            category = ml_service.predict_category(str(row["description"]), float(row["amount"]))
            anomaly  = ml_service.detect_anomaly(float(row["amount"]))
            if anomaly["is_anomaly"]:
                anomalies += 1
            tx = Transaction(
                user_id=uid,
                amount=abs(float(row["amount"])),
                description=str(row["description"]),
                category=category,
                transaction_type=str(row.get("transaction_type", "expense")),
                date=pd.to_datetime(row["date"]),
                is_anomaly=anomaly["is_anomaly"],
                anomaly_score=anomaly["score"],
            )
            db.add(tx)
            added += 1
            if added % 100 == 0:
                db.commit()
        db.commit()

        now  = datetime.now()
        recs = RecommendationEngine(db).generate_monthly_insights(uid, now.year, now.month)
        return jsonify({
            "ok": True,
            "transactions_added":         added,
            "anomalies_detected":         anomalies,
            "recommendations_generated":  len(recs),
        })
    finally:
        db.close()
