# app/main.py
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import pandas as pd
import io

from app.database import SessionLocal, engine, Base, Transaction, User, Budget, Insight, Forecast
from app.schemas import *
from app.ml_services import ml_service
from app.recommender import RecommendationEngine

# Create tables
Base.metadata.create_all(bind=engine)

# Initialize FastAPI
app = FastAPI(title="FinTrack API", description="ML-Powered Personal Finance Tracker", version="1.0.0")

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ========== HEALTH CHECK ==========
@app.get("/")
def root():
    return {"message": "FinTrack API is running!", "status": "healthy"}

# ========== USER ENDPOINTS ==========
@app.post("/users", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    db_user = User(username=user.username, email=user.email, user_type=user.user_type)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# ========== TRANSACTION ENDPOINTS ==========
@app.post("/transactions", response_model=TransactionResponse)
def create_transaction(tx: TransactionCreate, db: Session = Depends(get_db)):
    # Predict category if not provided
    if not tx.category:
        tx.category = ml_service.predict_category(tx.description, tx.amount)
    
    # Detect anomaly
    anomaly_result = ml_service.detect_anomaly(tx.amount, datetime.now().weekday(), 50)
    
    db_tx = Transaction(
        user_id=tx.user_id,
        amount=tx.amount,
        description=tx.description,
        category=tx.category,
        transaction_type=tx.transaction_type,
        date=tx.date or datetime.now(),
        payment_method=tx.payment_method,
        is_anomaly=anomaly_result['is_anomaly'],
        anomaly_score=anomaly_result['score']
    )
    db.add(db_tx)
    db.commit()
    db.refresh(db_tx)
    
    return db_tx

@app.get("/transactions/{user_id}", response_model=list[TransactionResponse])
def get_user_transactions(
    user_id: int, 
    skip: int = 0, 
    limit: int = 100,
    category: str = None,
    db: Session = Depends(get_db)
):
    query = db.query(Transaction).filter(Transaction.user_id == user_id)
    if category:
        query = query.filter(Transaction.category == category)
    transactions = query.order_by(Transaction.date.desc()).offset(skip).limit(limit).all()
    return transactions

# ========== BUDGET ENDPOINTS ==========
@app.post("/budgets", response_model=BudgetResponse)
def create_budget(budget: BudgetCreate, user_id: int, db: Session = Depends(get_db)):
    db_budget = Budget(
        user_id=user_id,
        category=budget.category,
        monthly_limit=budget.monthly_limit,
        month=budget.month,
        year=budget.year
    )
    db.add(db_budget)
    db.commit()
    db.refresh(db_budget)
    return db_budget

@app.get("/budgets/{user_id}")
def get_user_budgets(user_id: int, month: int, year: int, db: Session = Depends(get_db)):
    budgets = db.query(Budget).filter(
        Budget.user_id == user_id,
        Budget.month == month,
        Budget.year == year
    ).all()
    return budgets

# ========== ANALYTICS ENDPOINTS ==========
@app.get("/analytics/spending-analysis/{user_id}", response_model=SpendingAnalysisResponse)
def spending_analysis(user_id: int, year: int, month: int, db: Session = Depends(get_db)):
    start_date = datetime(year, month, 1)
    end_date = datetime(year, month + 1, 1) if month < 12 else datetime(year + 1, 1, 1)
    
    transactions = db.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.date >= start_date,
        Transaction.date < end_date
    ).all()
    
    income = sum(t.amount for t in transactions if t.transaction_type == "income")
    expenses = sum(t.amount for t in transactions if t.transaction_type == "expense")
    savings = income - expenses
    savings_rate = (savings / income * 100) if income > 0 else 0
    
    # Category breakdown
    category_data = {}
    for t in transactions:
        if t.transaction_type == "expense":
            category_data[t.category] = category_data.get(t.category, 0) + t.amount
    
    # Top spending categories
    top_categories = sorted(category_data.items(), key=lambda x: x[1], reverse=True)[:5]
    top_categories_list = [{"category": cat, "amount": amt} for cat, amt in top_categories]
    
    # Generate recommendations
    recommender = RecommendationEngine(db)
    recommendations_data = recommender.generate_monthly_insights(user_id, year, month)
    
    recommendations_response = [
        RecommendationResponse(
            insight_type=r['type'],
            message=r['message'],
            action_items=[r.get('action', 'Review your spending')],
            potential_savings=r.get('potential_savings'),
            priority='high' if 'alert' in r['type'] else 'medium'
        ) for r in recommendations_data
    ]
    
    return SpendingAnalysisResponse(
        total_income=income,
        total_expenses=expenses,
        savings=savings,
        savings_rate=savings_rate,
        category_breakdown=category_data,
        top_spending_categories=top_categories_list,
        monthly_trend={},
        recommendations=recommendations_response
    )

# ========== FORECAST ENDPOINTS ==========
@app.get("/forecast/{user_id}", response_model=ForecastResponse)
def cash_flow_forecast(user_id: int, days: int = 30, db: Session = Depends(get_db)):
    # Get last 60 days of balance data
    start_date = datetime.now() - timedelta(days=60)
    transactions = db.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.date >= start_date
    ).order_by(Transaction.date).all()
    
    # Calculate running balance
    balance = 0
    balances = []
    dates = []
    
    for t in transactions:
        if t.transaction_type == "income":
            balance += t.amount
        else:
            balance -= t.amount
        balances.append(balance)
        dates.append(t.date)
    
    # Simple forecast (moving average)
    if len(balances) > 7:
        avg_change = (balances[-1] - balances[-7]) / 7
    else:
        avg_change = 0
    
    forecast_dates = []
    forecast_balances = []
    lower_bounds = []
    upper_bounds = []
    
    current_balance = balances[-1] if balances else 0
    
    for i in range(days):
        forecast_date = datetime.now() + timedelta(days=i+1)
        predicted = current_balance + (avg_change * (i+1))
        forecast_dates.append(forecast_date.strftime("%Y-%m-%d"))
        forecast_balances.append(predicted)
        lower_bounds.append(predicted * 0.85)
        upper_bounds.append(predicted * 1.15)
    
    # Generate alerts
    alerts = []
    for i, balance in enumerate(forecast_balances):
        if balance < 100:
            alerts.append(f"Low balance predicted on {forecast_dates[i]}: ${balance:.2f}")
        elif balance < 0:
            alerts.append(f"⚠️ Overdraft predicted on {forecast_dates[i]}")
    
    # Save forecast to database
    for i in range(min(7, days)):
        forecast = Forecast(
            user_id=user_id,
            forecast_date=datetime.now() + timedelta(days=i+1),
            predicted_balance=forecast_balances[i],
            lower_bound=lower_bounds[i],
            upper_bound=upper_bounds[i]
        )
        db.add(forecast)
    db.commit()
    
    return ForecastResponse(
        dates=forecast_dates,
        predicted_balances=forecast_balances,
        lower_bounds=lower_bounds,
        upper_bounds=upper_bounds,
        alerts=alerts
    )

# ========== CSV UPLOAD ENDPOINT ==========
@app.post("/upload-csv/{user_id}", response_model=CSVUploadResponse)
async def upload_csv(user_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Please upload a CSV file")
    
    contents = await file.read()
    df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
    
    # Expected columns: date, description, amount, transaction_type
    required_columns = ['date', 'description', 'amount']
    for col in required_columns:
        if col not in df.columns:
            raise HTTPException(status_code=400, detail=f"Missing column: {col}")
    
    transactions_added = 0
    anomalies_detected = 0
    
    for _, row in df.iterrows():
        category = ml_service.predict_category(row['description'], row['amount'])
        anomaly = ml_service.detect_anomaly(row['amount'])
        
        if anomaly['is_anomaly']:
            anomalies_detected += 1
        
        transaction = Transaction(
            user_id=user_id,
            amount=row['amount'],
            description=row['description'],
            category=category,
            transaction_type=row.get('transaction_type', 'expense'),
            date=pd.to_datetime(row['date']),
            is_anomaly=anomaly['is_anomaly'],
            anomaly_score=anomaly['score']
        )
        db.add(transaction)
        transactions_added += 1
        
        # Commit every 100 transactions
        if transactions_added % 100 == 0:
            db.commit()
    
    db.commit()
    
    # Generate recommendations from uploaded data
    recommender = RecommendationEngine(db)
    recommendations = recommender.generate_monthly_insights(user_id, datetime.now().year, datetime.now().month)
    
    return CSVUploadResponse(
        message="CSV processed successfully",
        transactions_added=transactions_added,
        anomalies_detected=anomalies_detected,
        recommendations_generated=len(recommendations)
    )

# ========== MANUAL TRANSACTION WITH CATEGORY BUTTONS ==========
@app.post("/manual-transaction")
def manual_transaction(tx: TransactionCreate, db: Session = Depends(get_db)):
    """Endpoint for manual transaction entry with category selection"""
    # Category is provided by the frontend buttons
    anomaly = ml_service.detect_anomaly(tx.amount)
    
    db_tx = Transaction(
        user_id=tx.user_id,
        amount=tx.amount,
        description=tx.description,
        category=tx.category,  # Provided by user from category buttons
        transaction_type=tx.transaction_type,
        date=tx.date or datetime.now(),
        payment_method=tx.payment_method,
        is_anomaly=anomaly['is_anomaly'],
        anomaly_score=anomaly['score']
    )
    db.add(db_tx)
    db.commit()
    db.refresh(db_tx)
    
    return {"message": "Transaction added", "transaction": db_tx, "anomaly_detected": anomaly['is_anomaly']}

# ========== RECOMMENDATIONS ENDPOINT ==========
@app.get("/recommendations/{user_id}")
def get_recommendations(user_id: int, db: Session = Depends(get_db)):
    recommender = RecommendationEngine(db)
    recommendations = recommender.get_recommendations(user_id)
    return {"recommendations": recommendations}

# ========== CATEGORIES LIST ==========
@app.get("/categories")
def get_categories():
    """Return list of available categories for manual entry"""
    categories = [
        {"name": "Food", "icon": "🍔", "color": "#2563EB"},
        {"name": "Transport", "icon": "🚗", "color": "#10B981"},
        {"name": "Rent", "icon": "🏠", "color": "#F59E0B"},
        {"name": "Shopping", "icon": "🛍️", "color": "#8B5CF6"},
        {"name": "Entertainment", "icon": "🎬", "color": "#EC4899"},
        {"name": "Data Charges", "icon": "📱", "color": "#06B6D4"},
        {"name": "Education", "icon": "📚", "color": "#3B82F6"},
        {"name": "Utilities", "icon": "💡", "color": "#F97316"},
        {"name": "Healthcare", "icon": "🏥", "color": "#EF4444"},
        {"name": "Income", "icon": "💰", "color": "#22C55E"},
        {"name": "Other", "icon": "📦", "color": "#6B7280"}
    ]
    return {"categories": categories}