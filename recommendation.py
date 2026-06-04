# app/recommender.py
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.database import Transaction, Insight, Budget

class RecommendationEngine:
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def generate_monthly_insights(self, user_id: int, year: int, month: int) -> list:
        """Generate monthly spending insights and recommendations"""
        recommendations = []
        
        # Get user's transactions for the month
        start_date = datetime(year, month, 1)
        end_date = datetime(year, month + 1, 1) if month < 12 else datetime(year + 1, 1, 1)
        
        transactions = self.db.query(Transaction).filter(
            Transaction.user_id == user_id,
            Transaction.date >= start_date,
            Transaction.date < end_date,
            Transaction.transaction_type == "expense"
        ).all()
        
        if not transactions:
            return recommendations
        
        # Convert to DataFrame for analysis
        data = [{
            'amount': t.amount,
            'category': t.category,
            'date': t.date
        } for t in transactions]
        df = pd.DataFrame(data)
        
        # 1. Category spending analysis
        category_spending = df.groupby('category')['amount'].sum().sort_values(ascending=False)
        total_spent = df['amount'].sum()
        
        # Identify top spending categories
        for category, amount in category_spending.head(3).items():
            percentage = (amount / total_spent) * 100
            if percentage > 30:
                recommendations.append({
                    'type': 'high_spending',
                    'category': category,
                    'amount': amount,
                    'percentage': percentage,
                    'message': f"Your {category} spending is {percentage:.0f}% of total expenses.",
                    'action': f"Consider reducing {category} expenses by setting a monthly budget of ${amount * 0.8:.0f}"
                })
        
        # 2. Savings opportunity analysis
        avg_daily = total_spent / 30
        if avg_daily > 50:
            recommendations.append({
                'type': 'savings_opportunity',
                'message': f"You spend ${avg_daily:.0f} per day on average.",
                'action': "Try reducing daily expenses by 10% to save $150 this month.",
                'potential_savings': total_spent * 0.1
            })
        
        # 3. Compare to previous month
        prev_start = start_date - timedelta(days=30)
        prev_end = start_date
        prev_transactions = self.db.query(Transaction).filter(
            Transaction.user_id == user_id,
            Transaction.date >= prev_start,
            Transaction.date < prev_end,
            Transaction.transaction_type == "expense"
        ).all()
        
        if prev_transactions:
            prev_total = sum(t.amount for t in prev_transactions)
            change = ((total_spent - prev_total) / prev_total) * 100
            if change > 10:
                recommendations.append({
                    'type': 'increase_alert',
                    'message': f"Your spending increased by {change:.0f}% compared to last month.",
                    'action': "Review your recent transactions to identify spending increases."
                })
            elif change < -10:
                recommendations.append({
                    'type': 'improvement',
                    'message': f"Great job! Your spending decreased by {abs(change):.0f}% from last month.",
                    'action': "Keep up the good habits!"
                })
        
        # 4. Check budgets
        budgets = self.db.query(Budget).filter(
            Budget.user_id == user_id,
            Budget.month == month,
            Budget.year == year
        ).all()
        
        for budget in budgets:
            spent = category_spending.get(budget.category, 0)
            if spent > budget.monthly_limit:
                recommendations.append({
                    'type': 'budget_alert',
                    'category': budget.category,
                    'message': f"You've exceeded your {budget.category} budget by ${spent - budget.monthly_limit:.0f}.",
                    'action': f"Increase your {budget.category} budget or reduce spending."
                })
        
        # 5. Anomaly alerts
        anomalies = [t for t in transactions if t.is_anomaly]
        if anomalies:
            recommendations.append({
                'type': 'anomaly_alert',
                'message': f"Detected {len(anomalies)} unusual transactions this month.",
                'action': "Review these transactions to ensure they are legitimate."
            })
        
        # Save insights to database
        for rec in recommendations:
            insight = Insight(
                user_id=user_id,
                insight_type=rec.get('type', 'general'),
                message=rec.get('message', ''),
                severity='high' if 'alert' in rec.get('type', '') else 'medium'
            )
            self.db.add(insight)
        
        self.db.commit()
        
        return recommendations
    
    def get_recommendations(self, user_id: int, limit: int = 5) -> list:
        """Get recent recommendations for user"""
        insights = self.db.query(Insight).filter(
            Insight.user_id == user_id,
            Insight.is_read == False
        ).order_by(Insight.created_at.desc()).limit(limit).all()
        
        return [{
            'id': i.id,
            'type': i.insight_type,
            'message': i.message,
            'severity': i.severity,
            'date': i.created_at
        } for i in insights]