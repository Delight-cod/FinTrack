import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from ..models import Transaction, Insight, Budget


class RecommendationEngine:
    def __init__(self, db_session: Session):
        self.db = db_session

    def generate_monthly_insights(self, user_id: int, year: int, month: int) -> list:
        start_date = datetime(year, month, 1)
        end_date   = datetime(year, month + 1, 1) if month < 12 else datetime(year + 1, 1, 1)

        transactions = self.db.query(Transaction).filter(
            Transaction.user_id == user_id,
            Transaction.date >= start_date,
            Transaction.date < end_date,
            Transaction.transaction_type == "expense",
        ).all()

        if not transactions:
            return []

        df                = pd.DataFrame([{"amount": t.amount, "category": t.category} for t in transactions])
        category_spending = df.groupby("category")["amount"].sum().sort_values(ascending=False)
        total_spent       = df["amount"].sum()
        recommendations   = []

        for category, amount in category_spending.head(3).items():
            pct = (amount / total_spent) * 100
            if pct > 30:
                recommendations.append({
                    "type":     "high_spending",
                    "category": category,
                    "amount":   amount,
                    "message":  f"Your {category} spending is {pct:.0f}% of total expenses.",
                    "action":   f"Consider reducing {category} expenses by setting a monthly budget of ${amount * 0.8:.0f}",
                })

        avg_daily = total_spent / 30
        if avg_daily > 50:
            recommendations.append({
                "type":              "savings_opportunity",
                "message":           f"You spend ${avg_daily:.0f} per day on average.",
                "action":            "Try reducing daily expenses by 10% to save $150 this month.",
                "potential_savings": total_spent * 0.1,
            })

        prev_txns = self.db.query(Transaction).filter(
            Transaction.user_id == user_id,
            Transaction.date >= start_date - timedelta(days=30),
            Transaction.date < start_date,
            Transaction.transaction_type == "expense",
        ).all()

        if prev_txns:
            prev_total = sum(t.amount for t in prev_txns)
            change     = ((total_spent - prev_total) / prev_total) * 100
            if change > 10:
                recommendations.append({
                    "type":    "increase_alert",
                    "message": f"Your spending increased by {change:.0f}% compared to last month.",
                    "action":  "Review your recent transactions to identify spending increases.",
                })
            elif change < -10:
                recommendations.append({
                    "type":    "improvement",
                    "message": f"Great job! Your spending decreased by {abs(change):.0f}% from last month.",
                    "action":  "Keep up the good habits!",
                })

        budgets = self.db.query(Budget).filter(
            Budget.user_id == user_id,
            Budget.month   == month,
            Budget.year    == year,
        ).all()

        for budget in budgets:
            spent = category_spending.get(budget.category, 0)
            if spent > budget.monthly_limit:
                recommendations.append({
                    "type":     "budget_alert",
                    "category": budget.category,
                    "message":  f"You've exceeded your {budget.category} budget by ${spent - budget.monthly_limit:.0f}.",
                    "action":   f"Increase your {budget.category} budget or reduce spending.",
                })

        anomalies = [t for t in transactions if t.is_anomaly]
        if anomalies:
            recommendations.append({
                "type":    "anomaly_alert",
                "message": f"Detected {len(anomalies)} unusual transactions this month.",
                "action":  "Review these transactions to ensure they are legitimate.",
            })

        for rec in recommendations:
            self.db.add(Insight(
                user_id      = user_id,
                insight_type = rec.get("type", "general"),
                message      = rec.get("message", ""),
                severity     = "high" if "alert" in rec.get("type", "") else "medium",
            ))
        self.db.commit()

        return recommendations

    def get_recommendations(self, user_id: int, limit: int = 5) -> list:
        insights = self.db.query(Insight).filter(
            Insight.user_id == user_id,
            Insight.is_read == False,
        ).order_by(Insight.created_at.desc()).limit(limit).all()

        return [{
            "id":       i.id,
            "type":     i.insight_type,
            "message":  i.message,
            "severity": i.severity,
            "date":     i.created_at,
        } for i in insights]
