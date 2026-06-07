import numpy as np
import joblib
import os

MODEL_PATH = os.environ.get("MODEL_PATH", "models")

_KEYWORDS = {
    "food":          ["starbucks", "cafe", "restaurant", "kfc", "mcdonald", "burger", "pizza", "dining", "groceries"],
    "transport":     ["uber", "taxi", "bus", "train", "fuel", "gas", "petrol", "lyft"],
    "shopping":      ["amazon", "walmart", "target", "best buy", "mall", "store", "shop"],
    "entertainment": ["netflix", "spotify", "cinema", "movie", "game", "disney"],
    "rent":          ["rent", "apartment", "housing", "lease"],
    "utilities":     ["electric", "water", "gas bill", "internet", "phone", "data charges"],
    "education":     ["tuition", "book", "course", "school", "college", "university"],
    "income":        ["salary", "deposit", "paycheck", "allowance", "freelance"],
}


class MLService:
    def __init__(self):
        self.categorizer      = None
        self.anomaly_detector = None
        self.scaler           = None
        self.label_encoder    = None
        self._load_models()

    def _load_models(self):
        if not os.path.isdir(MODEL_PATH):
            print("No trained models found — using rule-based fallback (normal on first run)")
            return
        try:
            self.categorizer      = joblib.load(os.path.join(MODEL_PATH, "categorization_model.pkl"))
            self.anomaly_detector = joblib.load(os.path.join(MODEL_PATH, "anomaly_model.pkl"))
            self.scaler           = joblib.load(os.path.join(MODEL_PATH, "scaler.pkl"))
            self.label_encoder    = joblib.load(os.path.join(MODEL_PATH, "label_encoder.pkl"))
            print("ML models loaded successfully")
        except Exception as e:
            print(f"Models not found ({e}) — using rule-based fallback")
            self.categorizer = self.anomaly_detector = None

    def predict_category(self, description: str, amount: float = None) -> str:
        if self.categorizer is not None:
            try:
                features = np.array([[len(description), amount or 0]])
                encoded  = self.categorizer.predict(features)[0]
                return self.label_encoder.inverse_transform([encoded])[0]
            except Exception:
                pass

        desc_lower = description.lower()
        for category, kws in _KEYWORDS.items():
            if any(kw in desc_lower for kw in kws):
                return category.capitalize()
        return "Other"

    def detect_anomaly(self, amount: float, day_of_week: int = None, avg_spending: float = None) -> dict:
        if self.anomaly_detector is not None and self.scaler is not None:
            try:
                features        = np.array([[amount, day_of_week or 3, avg_spending or 50]])
                features_scaled = self.scaler.transform(features)
                score           = self.anomaly_detector.decision_function(features_scaled)[0]
                prediction      = self.anomaly_detector.predict(features_scaled)[0]
                return {"is_anomaly": prediction == -1, "score": round(float(score), 4)}
            except Exception:
                pass

        if avg_spending and amount > avg_spending * 3:
            return {"is_anomaly": True, "score": 0.75}
        if amount > 500:
            return {"is_anomaly": True, "score": 0.85}
        return {"is_anomaly": False, "score": 0.0}


ml_service = MLService()
