from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime
import random

router = APIRouter()


class ClaimRequest(BaseModel):
    claim_id: str
    patient_id: str
    doctor_id: str
    patient_age: int
    patient_gender: str
    medical_scheme: str
    diagnosis_code: str
    claim_amount: float
    facility_location: str
    patient_location: str | None = None
    biometric_verified: bool | None = None
    patient_present: bool | None = None
    patient_deceased: bool | None = None
    emergency_case: bool | None = None
    weekend_claim: bool | None = None
    after_hours_claim: bool | None = None
    travel_distance_suspicious: bool | None = None
    timestamp: str | None = None
    submission_source: str | None = None


@router.post("/api/v1/detect-fraud")
def detect_fraud(claim: ClaimRequest):
    # Dummy logic for now
    fraud_probability = round(random.uniform(0, 1), 2)
    is_fraud = fraud_probability > 0.6
    risk_level = (
        "CRITICAL"
        if fraud_probability > 0.9
        else (
            "HIGH"
            if fraud_probability > 0.75
            else (
                "MEDIUM"
                if fraud_probability > 0.6
                else "LOW" if fraud_probability > 0.3 else "MINIMAL"
            )
        )
    )

    return {
        "claim_id": claim.claim_id,
        "is_fraud": is_fraud,
        "fraud_probability": fraud_probability,
        "risk_level": risk_level,
        "confidence_score": round(random.uniform(0.7, 0.99), 2),
        "flags": ["pattern_match", "unusual_amount"] if is_fraud else [],
        "processing_time_ms": random.randint(80, 300),
        "timestamp": datetime.utcnow().isoformat(),
        "from_cache": False,
        "recommended_action": "Escalate for manual review" if is_fraud else "Approve",
        "review_required": is_fraud,
    }
