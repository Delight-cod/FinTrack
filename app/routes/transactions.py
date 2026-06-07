from flask import Blueprint, request, jsonify
from datetime import datetime
from ..models import Transaction
from ..helpers import get_db, current_user_id, require_login, tx_to_dict
from ..services.ml_service import ml_service

transactions_bp = Blueprint("transactions", __name__)


@transactions_bp.route("/api/transactions", methods=["GET"])
@require_login
def api_transactions():
    uid      = current_user_id()
    page     = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 10))
    cat      = request.args.get("category", "").strip().lower()
    tx_type  = request.args.get("type", "").strip().lower()

    db = get_db()
    try:
        query = db.query(Transaction).filter(Transaction.user_id == uid)
        if cat:
            query = query.filter(Transaction.category.ilike(cat))
        if tx_type:
            query = query.filter(Transaction.transaction_type == tx_type)

        total = query.count()
        txns  = query.order_by(Transaction.date.desc()).offset((page - 1) * per_page).limit(per_page).all()

        return jsonify({
            "transactions": [tx_to_dict(t) for t in txns],
            "total": total,
            "page":  page,
            "pages": (total + per_page - 1) // per_page,
        })
    finally:
        db.close()


@transactions_bp.route("/api/transactions", methods=["POST"])
@require_login
def api_add_transaction():
    uid  = current_user_id()
    data = request.get_json() or {}
    required = ("name", "amount", "category", "date", "type")
    missing  = [k for k in required if k not in data]
    if missing:
        return jsonify({"ok": False, "error": f"Missing fields: {', '.join(missing)}"}), 400

    db = get_db()
    try:
        amount  = abs(float(data["amount"]))
        anomaly = ml_service.detect_anomaly(amount)

        tx = Transaction(
            user_id=uid,
            amount=amount,
            description=data["name"],
            category=data["category"],
            transaction_type=data["type"],
            date=datetime.strptime(data["date"], "%Y-%m-%d"),
            payment_method=data.get("payment_method", "card"),
            is_anomaly=anomaly["is_anomaly"],
            anomaly_score=anomaly["score"],
        )
        db.add(tx)
        db.commit()
        db.refresh(tx)
        return jsonify({"ok": True, "transaction": tx_to_dict(tx)}), 201
    finally:
        db.close()


@transactions_bp.route("/api/transactions/<int:tx_id>", methods=["DELETE"])
@require_login
def api_delete_transaction(tx_id):
    uid = current_user_id()
    db  = get_db()
    try:
        tx = db.query(Transaction).filter(
            Transaction.id == tx_id,
            Transaction.user_id == uid,
        ).first()
        if not tx:
            return jsonify({"ok": False, "error": "Not found"}), 404
        db.delete(tx)
        db.commit()
        return jsonify({"ok": True})
    finally:
        db.close()
