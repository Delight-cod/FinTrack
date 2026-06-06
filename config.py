import os


class Config:
    SECRET_KEY   = os.environ.get("SECRET_KEY",   "fintrack-dev-secret-change-in-prod")
    DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./data/fintrack.db")
    MODEL_PATH   = os.environ.get("MODEL_PATH",   "models")
