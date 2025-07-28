# fraud_pipeline.py
import joblib
import pandas as pd


class FraudDetectionPipeline:
    def __init__(self):
        self.model = joblib.load("models/final_random_forest_model.pkl")
        self.scaler = joblib.load("models/feature_scaler.pkl")
        self.features = self.model.feature_names_in_

    def predict(self, claim_data: dict):
        df = pd.DataFrame([claim_data])

        for col in self.features:
            if col not in df.columns:
                df[col] = 0

        df = df[self.features]
        df_scaled = self.scaler.transform(df)
        prob = self.model.predict_proba(df_scaled)[0][1]
        is_fraud = int(prob >= 0.5)

        if prob >= 0.8:
            risk = "CRITICAL"
        elif prob >= 0.6:
            risk = "HIGH"
        elif prob >= 0.4:
            risk = "MEDIUM"
        elif prob >= 0.2:
            risk = "LOW"
        else:
            risk = "MINIMAL"

        return {
            "is_fraud": bool(is_fraud),
            "fraud_probability": round(prob, 4),
            "risk_level": risk,
        }
