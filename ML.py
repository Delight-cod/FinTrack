# app/ml_services.py
import numpy as np
import pandas as pd
import joblib
from datetime import datetime, timedelta
import os

# Model paths
MODEL_PATH = "FinTrack.ipynb"

class MLService:
    def __init__(self):
        self.load_models()
    
    def load_models(self):
        """Load all trained ML models"""
        try:
            self.categorizer = joblib.load(os.path.join(MODEL_PATH, 'categorization_model.pkl'))
            self.anomaly_detector = joblib.load(os.path.join(MODEL_PATH, 'anomaly_model.pkl'))
            self.scaler = joblib.load(os.path.join(MODEL_PATH, 'scaler.pkl'))
            self.label_encoder = joblib.load(os.path.join(MODEL_PATH, 'label_encoder.pkl'))
            print("✅ All ML models loaded successfully")
        except Exception as e:
            print(f"⚠️ Models not found: {e}")
            print("Using fallback rule-based methods")
            self.categorizer = None
            self.anomaly_detector = None
    
    def predict_category(self, description: str, amount: float = None) -> str:
        """Predict transaction category from description"""
        # Predefined categories for fallback
        categories = {
            'food': ['starbucks', 'cafe', 'restaurant', 'kfc', 'mcdonald', 'burger', 'pizza', 'dining', 'groceries'],
            'transport': ['uber', 'taxi', 'bus', 'train', 'fuel', 'gas', 'petrol', 'lyft'],
            'shopping': ['amazon', 'walmart', 'target', 'best buy', 'mall', 'store', 'shop'],
            'entertainment': ['netflix', 'spotify', 'cinema', 'movie', 'game', 'disney'],
            'rent': ['rent', 'apartment', 'housing', 'lease'],
            'utilities': ['electric', 'water', 'gas bill', 'internet', 'phone', 'data charges'],
            'education': ['tuition', 'book', 'course', 'school', 'college', 'university'],
            'income': ['salary', 'deposit', 'paycheck', 'allowance', 'freelance']
        }
        
        # Use ML model if available
        if self.categorizer is not None:
            try:
                # Create features (adjust based on your model training)
                features = np.array([[len(description), amount if amount else 0]])
                encoded = self.categorizer.predict(features)[0]
                category = self.label_encoder.inverse_transform([encoded])[0]
                return category
            except:
                pass  # Fall back to rule-based
        
        # Rule-based fallback
        desc_lower = description.lower()
        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword in desc_lower:
                    return category.capitalize()
        return "Other"
    
    def detect_anomaly(self, amount: float, day_of_week: int = None, avg_spending: float = None) -> dict:
        """Detect if a transaction is anomalous"""
        if self.anomaly_detector is not None and self.scaler is not None:
            try:
                features = np.array([[amount, day_of_week or 3, avg_spending or 50]])
                features_scaled = self.scaler.transform(features)
                score = self.anomaly_detector.decision_function(features_scaled)[0]
                prediction = self.anomaly_detector.predict(features_scaled)[0]
                return {
                    'is_anomaly': prediction == -1,
                    'score': round(float(score), 4)
                }
            except:
                pass
        
        # Simple rule-based anomaly detection (amount > 3x average)
        if avg_spending and amount > avg_spending * 3:
            return {'is_anomaly': True, 'score': 0.75}
        elif amount > 500:
            return {'is_anomaly': True, 'score': 0.85}
        return {'is_anomaly': False, 'score': 0.0}

# Singleton instance
ml_service = MLService()