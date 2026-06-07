from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

os.makedirs("data", exist_ok=True)

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./data/fintrack.db")
engine       = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base         = declarative_base()


class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, index=True)
    username      = Column(String, unique=True, index=True)
    email         = Column(String, unique=True, index=True)
    password_hash = Column(String, nullable=True)
    user_type     = Column(String, default="worker")
    created_at    = Column(DateTime, default=datetime.now)

    transactions = relationship("Transaction", back_populates="user")
    budgets      = relationship("Budget",      back_populates="user")
    insights     = relationship("Insight",     back_populates="user")


class Transaction(Base):
    __tablename__ = "transactions"

    id               = Column(Integer, primary_key=True, index=True)
    user_id          = Column(Integer, ForeignKey("users.id"))
    amount           = Column(Float)
    description      = Column(String)
    category         = Column(String)
    transaction_type = Column(String, default="expense")
    date             = Column(DateTime, default=datetime.now)
    payment_method   = Column(String, default="card")
    is_anomaly       = Column(Boolean, default=False)
    anomaly_score    = Column(Float, default=0.0)
    created_at       = Column(DateTime, default=datetime.now)

    user = relationship("User", back_populates="transactions")


class Budget(Base):
    __tablename__ = "budgets"

    id            = Column(Integer, primary_key=True, index=True)
    user_id       = Column(Integer, ForeignKey("users.id"))
    category      = Column(String)
    monthly_limit = Column(Float)
    month         = Column(Integer)
    year          = Column(Integer)

    user = relationship("User", back_populates="budgets")


class Insight(Base):
    __tablename__ = "insights"

    id           = Column(Integer, primary_key=True, index=True)
    user_id      = Column(Integer, ForeignKey("users.id"))
    insight_type = Column(String)
    message      = Column(String)
    severity     = Column(String)
    is_read      = Column(Boolean, default=False)
    created_at   = Column(DateTime, default=datetime.now)

    user = relationship("User", back_populates="insights")


class Forecast(Base):
    __tablename__ = "forecasts"

    id                = Column(Integer, primary_key=True, index=True)
    user_id           = Column(Integer)
    forecast_date     = Column(DateTime)
    predicted_balance = Column(Float)
    lower_bound       = Column(Float)
    upper_bound       = Column(Float)
    created_at        = Column(DateTime, default=datetime.now)
