# main.py
from fastapi import FastAPI
from pydantic import BaseModel
from fraud_pipeline import FraudDetectionPipeline

app = FastAPI(title="Healthcare Fraud Detection API")
pipeline = FraudDetectionPipeline()


class Claim(BaseModel):
    claim_id: str
    claim_amount: float
    expected_cost_max: float
    patient_age: int
    biometric_verified: int
    patient_present: int
    is_high_risk_doctor: int
    weekend_claim: int
    emergency_case: int
    location_mismatch: int


@app.post("/predict")
def predict_fraud(claim: Claim):
    prediction = pipeline.predict(claim.dict())
    prediction["claim_id"] = claim.claim_id
    return prediction
