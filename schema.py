# app/schemas.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

# ========== TRANSACTION SCHEMAS ==========
class TransactionBase(BaseModel):
    amount: float
    description: str
    category: Optional[str] = None
    transaction_type: str = "expense"
    date: Optional[datetime] = None
    payment_method: str = "card"

class TransactionCreate(TransactionBase):
    user_id: int

class TransactionResponse(TransactionBase):
    id: int
    user_id: int
    is_anomaly: bool
    anomaly_score: float
    created_at: datetime
    
    class Config:
        from_attributes = True

# ========== BUDGET SCHEMAS ==========
class BudgetCreate(BaseModel):
    category: str
    monthly_limit: float
    month: int
    year: int

class BudgetResponse(BudgetCreate):
    id: int
    user_id: int
    
    class Config:
        from_attributes = True

# ========== INSIGHT SCHEMAS ==========
class InsightResponse(BaseModel):
    id: int
    insight_type: str
    message: str
    severity: str
    is_read: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# ========== USER SCHEMAS ==========
class UserCreate(BaseModel):
    username: str
    email: str
    user_type: str = "student"

class UserResponse(UserCreate):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# ========== RECOMMENDATION SCHEMAS ==========
class RecommendationResponse(BaseModel):
    insight_type: str
    message: str
    action_items: List[str]
    potential_savings: Optional[float] = None
    priority: str  # high, medium, low

class SpendingAnalysisResponse(BaseModel):
    total_income: float
    total_expenses: float
    savings: float
    savings_rate: float
    category_breakdown: dict
    top_spending_categories: List[dict]
    monthly_trend: dict
    recommendations: List[RecommendationResponse]

# ========== FORECAST SCHEMAS ==========
class ForecastResponse(BaseModel):
    dates: List[str]
    predicted_balances: List[float]
    lower_bounds: List[float]
    upper_bounds: List[float]
    alerts: List[str]

# ========== CSV UPLOAD ==========
class CSVUploadResponse(BaseModel):
    message: str
    transactions_added: int
    anomalies_detected: int
    recommendations_generated: int