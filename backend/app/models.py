# backend/app/models.py
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class RiskLevel(str, Enum):
    MINIMAL = "MINIMAL"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ClaimRequest(BaseModel):
    """Request model for fraud detection"""

    claim_id: str = Field(..., description="Unique claim identifier")
    patient_id: str = Field(..., description="Patient identifier")
    patient_name: Optional[str] = Field(None, description="Patient full name")
    doctor_id: str = Field(..., description="Doctor/Provider identifier")
    doctor_name: Optional[str] = Field(None, description="Doctor full name")
    patient_age: int = Field(..., ge=0, le=120, description="Patient age")
    patient_gender: str = Field(..., description="Patient gender (M/F)")
    medical_scheme: str = Field(..., description="Medical scheme name")
    diagnosis_code: str = Field(..., description="ICD-10 diagnosis code")
    claim_amount: float = Field(..., ge=0, description="Claim amount in NAD")
    facility_location: str = Field(..., description="Healthcare facility location")
    patient_location: Optional[str] = Field(None, description="Patient location")

    # Optional fields with defaults
    biometric_verified: Optional[bool] = Field(
        False, description="Biometric verification status"
    )
    patient_present: Optional[bool] = Field(
        True, description="Patient present during service"
    )
    patient_deceased: Optional[bool] = Field(
        False, description="Patient deceased status"
    )
    emergency_case: Optional[bool] = Field(False, description="Emergency case flag")
    weekend_claim: Optional[bool] = Field(False, description="Weekend submission flag")
    after_hours_claim: Optional[bool] = Field(
        False, description="After hours submission flag"
    )
    travel_distance_suspicious: Optional[bool] = Field(
        False, description="Suspicious travel distance"
    )

    # Timestamps and metadata
    timestamp: Optional[str] = Field(None, description="Claim submission timestamp")
    submission_source: Optional[str] = Field("api", description="Submission source")

    @validator("timestamp", pre=True, always=True)
    def set_timestamp(cls, v):
        return v or datetime.now().isoformat()

    @validator("patient_gender")
    def validate_gender(cls, v):
        if v.upper() not in ["M", "F", "MALE", "FEMALE"]:
            raise ValueError("Gender must be M, F, Male, or Female")
        return v.upper()[0]  # Convert to M or F

    @validator("diagnosis_code")
    def validate_icd_code(cls, v):
        # Basic ICD-10 format validation
        if not v or len(v) < 3:
            raise ValueError("Invalid ICD-10 code format")
        return v.upper()


class FraudResponse(BaseModel):
    """Response model for fraud detection results"""

    claim_id: str
    is_fraud: bool = Field(..., description="Binary fraud prediction")
    fraud_probability: float = Field(
        ..., ge=0, le=1, description="Fraud probability (0-1)"
    )
    risk_level: RiskLevel = Field(..., description="Risk categorization")
    confidence_score: float = Field(0.0, ge=0, le=1, description="Model confidence")
    flags: List[str] = Field(
        default_factory=list, description="Specific fraud indicators"
    )
    processing_time_ms: float = Field(
        0.0, description="Processing time in milliseconds"
    )
    timestamp: str = Field(..., description="Processing timestamp")
    from_cache: bool = Field(False, description="Result retrieved from cache")

    # Additional context
    recommended_action: Optional[str] = Field(None, description="Recommended action")
    review_required: bool = Field(False, description="Manual review required")


class HealthResponse(BaseModel):
    """Health check response model"""

    status: str = Field(..., description="Overall system status")
    api: str = Field(..., description="API status")
    timestamp: str
    uptime_seconds: float
    services: Dict[str, str] = Field(..., description="Individual service statuses")
    version: Optional[str] = Field("1.0.0", description="API version")


class StatsResponse(BaseModel):
    total_claims_today: int = Field(0, description="Total claims processed today")
    fraud_detected_today: int = Field(0, description="Fraud cases detected today")
    cache_hit_rate: float = Field(0.0, ge=0, le=1, description="Cache hit rate")
    average_processing_time_ms: float = Field(
        0.0, description="Average processing time"
    )
    high_risk_claims_today: int = Field(0, description="High risk claims today")
    system_load: float = Field(0.0, description="Current system load percentage")
    active_alerts: int = Field(0, description="Number of active alerts")
    timestamp: str

    # ✅ Newly added
    total_amount: Optional[float] = Field(0.0, description="Total NAD claimed today")
    most_common_procedure: Optional[str] = Field(
        None, description="Most common diagnosis code today"
    )

    # Optional metrics
    fraud_rate_today: Optional[float] = Field(None, description="Today's fraud rate")
    top_risk_providers: Optional[List[Dict[str, Any]]] = Field(
        None, description="Top risk providers"
    )


class AlertModel(BaseModel):
    """Alert model for high-risk claims"""

    alert_id: str
    claim_id: str
    risk_level: RiskLevel
    fraud_probability: float
    patient_id: str
    doctor_id: str
    claim_amount: float
    timestamp: str
    status: str = Field("pending_review", description="Alert status")
    assigned_reviewer: Optional[str] = Field(None, description="Assigned reviewer")
    resolution_notes: Optional[str] = Field(None, description="Resolution notes")


class FeedbackRequest(BaseModel):
    """Feedback request for model improvement"""

    claim_id: str
    is_actually_fraud: bool
    reviewer_id: Optional[str] = Field(None, description="Reviewer identifier")
    reviewer_notes: Optional[str] = Field(None, description="Additional reviewer notes")
    confidence_in_decision: Optional[int] = Field(
        None, ge=1, le=5, description="Reviewer confidence (1-5)"
    )


class ClaimDetailsResponse(BaseModel):
    """Detailed claim information response"""

    claim_id: str
    patient_info: Dict[str, Any]
    provider_info: Dict[str, Any]
    claim_details: Dict[str, Any]
    fraud_analysis: Dict[str, Any]
    history: List[Dict[str, Any]] = Field(
        default_factory=list, description="Claim processing history"
    )
    related_claims: List[str] = Field(
        default_factory=list, description="Related claim IDs"
    )


class BatchClaimRequest(BaseModel):
    """Batch processing request"""

    claims: List[ClaimRequest] = Field(..., min_items=1, max_items=100)
    priority: Optional[str] = Field("normal", description="Processing priority")
    callback_url: Optional[str] = Field(None, description="Callback URL for results")


class BatchClaimResponse(BaseModel):
    """Batch processing response"""

    batch_id: str
    total_claims: int
    processed_claims: int
    failed_claims: int
    results: List[FraudResponse]
    processing_time_ms: float
    timestamp: str


# Configuration models
class SystemConfig(BaseModel):
    """System configuration model"""

    fraud_threshold: float = Field(
        0.7, ge=0, le=1, description="Fraud probability threshold"
    )
    high_risk_threshold: float = Field(
        0.5, ge=0, le=1, description="High risk threshold"
    )
    auto_approve_threshold: float = Field(
        0.2, ge=0, le=1, description="Auto-approve threshold"
    )
    cache_expiry_hours: int = Field(24, ge=1, description="Cache expiry in hours")
    max_daily_claims_per_provider: int = Field(
        100, ge=1, description="Max daily claims per provider"
    )
    enable_real_time_alerts: bool = Field(True, description="Enable real-time alerting")


# Error models
class ErrorResponse(BaseModel):
    """Error response model"""

    error: str
    message: str
    timestamp: str
    request_id: Optional[str] = None


class ValidationError(BaseModel):
    """Validation error details"""

    field: str
    message: str
    invalid_value: Any
