# backend/app/fraud_detection.py

import joblib
import pandas as pd
import numpy as np
import os
import json
import time
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor
import threading
from dataclasses import dataclass
import hashlib

from backend.config.settings import MODEL_DIR, ENCODER_DIR, RISK_THRESHOLDS

logger = logging.getLogger(__name__)


@dataclass
class PredictionCache:
    """Cache for recent predictions to detect patterns"""

    claim_id: str
    prediction: Dict[str, Any]
    timestamp: datetime
    features_hash: str


class FraudDetectionService:
    """
    Enhanced service wrapper for fraud detection with real-time capabilities
    """

    def __init__(self, model_path: str = MODEL_DIR, encoder_path: str = ENCODER_DIR):
        self.model_path = model_path
        self.encoder_path = encoder_path
        self.model = None
        self.scaler = None
        self.encoders = {}
        self.feature_names = []
        self.model_metadata = {}
        self.risk_thresholds = RISK_THRESHOLDS

        # Enhanced attributes for real-time processing
        self.thread_pool = ThreadPoolExecutor(max_workers=4)
        self.prediction_cache = {}  # For detecting patterns
        self.model_stats = {
            "predictions_made": 0,
            "fraud_detected": 0,
            "avg_processing_time": 0.0,
            "model_load_time": None,
        }
        self.lock = threading.Lock()

        # Pattern detection
        self.suspicious_patterns = {}
        self.doctor_claim_counts = {}
        self.patient_claim_counts = {}
        self.recent_claims = []  # Last 1000 claims for pattern detection

        self._load_model_pipeline()
        self._initialize_pattern_detection()

    def _load_model_pipeline(self):
        """Enhanced model loading with better error handling and validation"""
        try:
            start_time = time.time()
            logger.info("Loading enhanced fraud detection model pipeline...")

            # Load main model
            model_files = [
                f
                for f in os.listdir(self.model_path)
                if f.startswith("final_") and f.endswith("_model.pkl")
            ]
            if not model_files:
                raise FileNotFoundError("No trained model found in models directory")

            model_file = model_files[0]
            model_full_path = os.path.join(self.model_path, model_file)
            self.model = joblib.load(model_full_path)
            logger.info(f"Model loaded: {model_file}")

            # Validate model has required methods
            if not hasattr(self.model, "predict_proba"):
                raise ValueError("Model must support predict_proba method")

            # Load scaler
            scaler_path = os.path.join(self.model_path, "feature_scaler.pkl")
            if os.path.exists(scaler_path):
                self.scaler = joblib.load(scaler_path)
                logger.info("Scaler loaded")
            else:
                logger.warning("No scaler found - predictions may be less accurate")

            # Load feature information
            feature_info_path = os.path.join(self.model_path, "feature_info.json")
            if os.path.exists(feature_info_path):
                with open(feature_info_path, "r") as f:
                    feature_info = json.load(f)
                    self.feature_names = feature_info.get("feature_names", [])
                    self.model_metadata = feature_info
                logger.info(f"Feature info loaded: {len(self.feature_names)} features")

            # Load encoders
            if os.path.exists(self.encoder_path):
                encoder_files = [
                    f
                    for f in os.listdir(self.encoder_path)
                    if f.endswith("_encoder.pkl")
                ]
                for encoder_file in encoder_files:
                    name = encoder_file.replace("_encoder.pkl", "")
                    path = os.path.join(self.encoder_path, encoder_file)
                    self.encoders[name] = joblib.load(path)
                logger.info(f"Loaded {len(self.encoders)} encoders")

            # Model validation
            self._validate_model()

            load_time = time.time() - start_time
            self.model_stats["model_load_time"] = load_time
            logger.info(
                f"Enhanced fraud detection pipeline loaded successfully in {load_time:.2f}s!"
            )

        except Exception as e:
            logger.error(f"Failed to load model pipeline: {str(e)}")
            raise

    def _validate_model(self):
        """Validate model with dummy data"""
        try:
            dummy_claim = {
                "claim_id": "TEST_001",
                "patient_age": 30,
                "claim_amount": 1000.0,
                "patient_gender": "M",
                "medical_scheme": "PSEMAS",
                "diagnosis_code": "Z00.0",
                "facility_location": "WINDHOEK",
                "timestamp": datetime.now().isoformat(),
            }

            # Test feature preparation
            df = self._prepare_features(dummy_claim)

            # Test prediction
            df_scaled = self.scaler.transform(df) if self.scaler else df
            prob = self.model.predict_proba(df_scaled)[0][1]

            if not (0 <= prob <= 1):
                raise ValueError(f"Model returned invalid probability: {prob}")

            logger.info("Model validation successful")

        except Exception as e:
            logger.error(f"Model validation failed: {e}")
            raise

    def _initialize_pattern_detection(self):
        """Initialize pattern detection mechanisms"""
        self.pattern_thresholds = {
            "same_doctor_multiple_claims": 10,  # claims per hour
            "same_patient_multiple_claims": 5,  # claims per hour
            "identical_claim_amounts": 3,  # identical amounts in short time
            "rapid_fire_claims": 20,  # claims per minute from same source
        }

    def is_model_loaded(self) -> bool:
        """Check if model is properly loaded"""
        return self.model is not None and hasattr(self.model, "predict_proba")

    def get_model_stats(self) -> Dict[str, Any]:
        """Get current model statistics"""
        with self.lock:
            return self.model_stats.copy()

    async def predict_fraud_async(self, claim_data: Dict[str, Any]) -> Dict[str, Any]:
        """Async wrapper for fraud prediction"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.thread_pool, self.predict_fraud, claim_data
        )

    def predict_fraud(self, claim_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced fraud prediction with pattern detection"""
        try:
            start_time = time.time()
            claim_id = claim_data.get("claim_id", f"UNKNOWN_{int(time.time())}")

            # Check for cached predictions (duplicate claims)
            features_hash = self._hash_claim_features(claim_data)
            if features_hash in self.prediction_cache:
                cached = self.prediction_cache[features_hash]
                if (datetime.now() - cached.timestamp).seconds < 300:  # 5 minutes
                    logger.info(
                        f"Returning cached prediction for similar claim: {claim_id}"
                    )
                    result = cached.prediction.copy()
                    result["flags"].append("duplicate_claim_detected")
                    result["from_cache"] = True
                    return result

            # Prepare features
            df = self._prepare_features(claim_data)

            # Get base prediction
            df_scaled = self.scaler.transform(df) if self.scaler else df
            prob = self.model.predict_proba(df_scaled)[0][1]
            prediction = int(prob >= 0.5)

            # Pattern-based risk adjustment
            pattern_adjustment, pattern_flags = self._analyze_patterns(claim_data, prob)
            adjusted_prob = min(1.0, prob + pattern_adjustment)

            # Determine risk level
            risk_level = self._determine_risk_level(adjusted_prob)

            # Generate comprehensive flags
            flags = self._generate_comprehensive_flags(df, adjusted_prob, claim_data)
            flags.extend(pattern_flags)

            # Calculate confidence score
            confidence_score = self._calculate_confidence_score(
                adjusted_prob, df, pattern_adjustment
            )

            processing_time = (time.time() - start_time) * 1000

            result = {
                "is_fraud": bool(int(adjusted_prob >= 0.5)),
                "fraud_probability": round(adjusted_prob, 4),
                "base_probability": round(prob, 4),
                "pattern_adjustment": round(pattern_adjustment, 4),
                "risk_level": risk_level,
                "confidence_score": round(confidence_score, 4),
                "flags": flags,
                "processing_time_ms": round(processing_time, 2),
                "model_version": self.model_metadata.get("version", "unknown"),
                "feature_count": len(df.columns),
                "from_cache": False,
            }

            # Update statistics and cache
            self._update_statistics(result, processing_time)
            self._cache_prediction(claim_id, result, features_hash)
            self._update_pattern_tracking(claim_data, result)

            logger.info(
                f"Fraud prediction completed for {claim_id}: {risk_level} "
                f"({adjusted_prob:.3f}) in {processing_time:.2f}ms"
            )

            return result

        except Exception as e:
            logger.error(
                f"Prediction failed for claim {claim_data.get('claim_id', 'UNKNOWN')}: {str(e)}"
            )
            return {
                "error": str(e),
                "is_fraud": False,
                "fraud_probability": 0.0,
                "risk_level": "ERROR",
                "confidence_score": 0.0,
                "flags": ["processing_error"],
                "processing_time_ms": 0,
                "from_cache": False,
            }

    def _prepare_features(self, claim_data: Dict[str, Any]) -> pd.DataFrame:
        """Enhanced feature preparation with better handling"""
        try:
            features = {}

            # Temporal features
            timestamp = claim_data.get("timestamp", datetime.now().isoformat())
            dt = pd.to_datetime(timestamp)
            features.update(
                {
                    "hour": dt.hour,
                    "day_of_week": dt.dayofweek,
                    "day_of_month": dt.day,
                    "month": dt.month,
                    "quarter": (dt.month - 1) // 3 + 1,
                    "is_weekend": int(dt.dayofweek >= 5),
                    "is_after_hours": int(dt.hour < 7 or dt.hour > 18),
                    "is_holiday": int(
                        self._is_holiday(dt)
                    ),  # You'd implement holiday detection
                }
            )

            # Basic features
            features.update(
                {
                    "patient_age": max(
                        0, min(120, claim_data.get("patient_age", 0))
                    ),  # Constrain age
                    "claim_amount": max(0, claim_data.get("claim_amount", 0)),
                }
            )

            # Binary flags with safer extraction
            binary_flags = [
                "biometric_verified",
                "patient_present",
                "patient_deceased",
                "weekend_claim",
                "after_hours_claim",
                "emergency_case",
                "travel_distance_suspicious",
            ]
            for flag in binary_flags:
                features[flag] = int(bool(claim_data.get(flag, False)))

            # Derived features
            claim_amount = features["claim_amount"]
            features.update(
                {
                    "expected_cost_min": claim_amount * 0.7,
                    "expected_cost_max": claim_amount * 1.3,
                    "cost_deviation": 0.0,  # Would be calculated from historical data
                    "cost_ratio": 1.0,
                    "cost_outlier_flag": int(claim_amount > 10000),
                    "log_claim_amount": np.log1p(
                        claim_amount
                    ),  # Log transform for better distribution
                    "claim_amount_category": self._categorize_claim_amount(
                        claim_amount
                    ),
                }
            )

            # Provider and location features
            doctor_id = claim_data.get("doctor_id", "")
            features.update(
                {
                    "is_high_risk_doctor": int(
                        "DR_X" in doctor_id or self._is_high_risk_doctor(doctor_id)
                    ),
                    "provider_claims_today": self._get_provider_claim_count(doctor_id),
                    "location_mismatch": int(
                        claim_data.get("patient_location", "")
                        != claim_data.get("facility_location", "")
                    ),
                }
            )

            # Age group encoding
            age = features["patient_age"]
            age_group = self._get_age_group(age)
            features["age_group"] = age_group

            # Categorical feature encoding
            categorical_features = {
                "patient_gender": claim_data.get("patient_gender", "M"),
                "medical_scheme": claim_data.get("medical_scheme", "PSEMAS"),
                "diagnosis_code": claim_data.get("diagnosis_code", "Z00.0"),
                "facility_location": claim_data.get("facility_location", "UNKNOWN"),
                "age_group": age_group,
            }

            # Enhanced categorical encoding
            for feature_name, value in categorical_features.items():
                encoded_name = f"{feature_name}_encoded"
                if feature_name in self.encoders:
                    try:
                        # Handle unknown categories gracefully
                        encoder = self.encoders[feature_name]
                        if (
                            hasattr(encoder, "classes_")
                            and str(value) not in encoder.classes_
                        ):
                            features[encoded_name] = -1  # Unknown category
                        else:
                            features[encoded_name] = encoder.transform([str(value)])[0]
                    except Exception as e:
                        logger.warning(
                            f"Encoding failed for {feature_name}={value}: {e}"
                        )
                        features[encoded_name] = -1
                else:
                    # Fallback: stable hash-based encoding
                    features[encoded_name] = hash(str(value)) % 1000

            # Create DataFrame
            df = pd.DataFrame([features])

            # Ensure all expected features are present
            if self.feature_names:
                for feature in self.feature_names:
                    if feature not in df.columns:
                        df[feature] = 0
                df = df[self.feature_names]

            return df

        except Exception as e:
            logger.error(f"Feature preparation failed: {str(e)}")
            raise

    def _analyze_patterns(
        self, claim_data: Dict[str, Any], base_prob: float
    ) -> Tuple[float, List[str]]:
        """Analyze claim patterns for additional risk assessment"""
        adjustment = 0.0
        flags = []

        try:
            doctor_id = claim_data.get("doctor_id", "")
            patient_id = claim_data.get("patient_id", "")
            claim_amount = claim_data.get("claim_amount", 0)

            # Check doctor patterns
            doctor_claims_recent = self.doctor_claim_counts.get(doctor_id, 0)
            if (
                doctor_claims_recent
                > self.pattern_thresholds["same_doctor_multiple_claims"]
            ):
                adjustment += 0.2
                flags.append("high_frequency_doctor")

            # Check patient patterns
            patient_claims_recent = self.patient_claim_counts.get(patient_id, 0)
            if (
                patient_claims_recent
                > self.pattern_thresholds["same_patient_multiple_claims"]
            ):
                adjustment += 0.15
                flags.append("high_frequency_patient")

            # Check for identical amounts (potential template fraud)
            identical_amount_count = sum(
                1
                for claim in self.recent_claims[-50:]
                if abs(claim.get("claim_amount", 0) - claim_amount) < 0.01
            )
            if (
                identical_amount_count
                >= self.pattern_thresholds["identical_claim_amounts"]
            ):
                adjustment += 0.1
                flags.append("identical_amounts_pattern")

            # Time-based patterns
            current_time = datetime.now()
            recent_claims_count = sum(
                1
                for claim in self.recent_claims[-100:]
                if (
                    current_time
                    - datetime.fromisoformat(
                        claim.get("timestamp", current_time.isoformat())
                    )
                ).total_seconds()
                < 300
            )  # 5 minutes

            if recent_claims_count > self.pattern_thresholds["rapid_fire_claims"]:
                adjustment += 0.25
                flags.append("rapid_fire_claims")

        except Exception as e:
            logger.warning(f"Pattern analysis failed: {e}")

        return min(0.4, adjustment), flags  # Cap adjustment at 0.4

    def _determine_risk_level(self, probability: float) -> str:
        """Determine risk level based on probability and thresholds"""
        for level in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            if probability >= self.risk_thresholds[level]:
                return level
        return "MINIMAL"

    def _calculate_confidence_score(
        self, prob: float, df: pd.DataFrame, pattern_adj: float
    ) -> float:
        """Calculate confidence score based on multiple factors"""
        base_confidence = prob if prob > 0.5 else (1 - prob)

        # Adjust based on feature completeness
        feature_completeness = (df.notna().sum().sum()) / (df.shape[0] * df.shape[1])

        # Adjust based on pattern adjustment
        pattern_confidence_boost = min(0.2, pattern_adj * 0.5)

        return min(
            1.0, base_confidence * feature_completeness + pattern_confidence_boost
        )

    def _generate_comprehensive_flags(
        self, df: pd.DataFrame, prob: float, claim_data: Dict[str, Any]
    ) -> List[str]:
        """Generate comprehensive flags for interpretability"""
        flags = []
        row = df.iloc[0]

        # Probability-based flags
        if prob >= 0.9:
            flags.append("very_high_confidence_fraud")
        elif prob >= 0.8:
            flags.append("high_confidence_fraud")
        elif prob >= 0.6:
            flags.append("moderate_confidence_fraud")

        # Feature-based flags
        if row.get("location_mismatch", 0):
            flags.append("location_mismatch")
        if row.get("claim_amount", 0) > 10000:
            flags.append("high_claim_amount")
        if row.get("claim_amount", 0) > 50000:
            flags.append("extremely_high_claim_amount")
        if row.get("is_high_risk_doctor", 0):
            flags.append("high_risk_provider")
        if row.get("emergency_case", 0) and row.get("is_after_hours", 0):
            flags.append("emergency_after_hours")
        if row.get("patient_deceased", 0):
            flags.append("deceased_patient_claim")
        if not row.get("biometric_verified", 0):
            flags.append("no_biometric_verification")
        if not row.get("patient_present", 0):
            flags.append("patient_not_present")

        # Age-based flags
        age = row.get("patient_age", 0)
        if age < 1:
            flags.append("newborn_claim")
        elif age > 100:
            flags.append("centenarian_claim")

        return flags

    # Helper methods
    def _hash_claim_features(self, claim_data: Dict[str, Any]) -> str:
        """Create hash of claim features for duplicate detection"""
        key_features = {
            "patient_id": claim_data.get("patient_id"),
            "doctor_id": claim_data.get("doctor_id"),
            "claim_amount": claim_data.get("claim_amount"),
            "diagnosis_code": claim_data.get("diagnosis_code"),
            "facility_location": claim_data.get("facility_location"),
        }
        return hashlib.md5(
            json.dumps(key_features, sort_keys=True).encode()
        ).hexdigest()

    def _is_holiday(self, dt: datetime) -> bool:
        """Check if date is a holiday (implement your holiday logic)"""
        # Placeholder - implement actual holiday checking
        return False

    def _categorize_claim_amount(self, amount: float) -> str:
        """Categorize claim amount"""
        if amount < 100:
            return "low"
        elif amount < 1000:
            return "medium"
        elif amount < 10000:
            return "high"
        else:
            return "very_high"

    def _get_age_group(self, age: int) -> str:
        """Get age group category"""
        if age < 18:
            return "child"
        elif age < 35:
            return "young_adult"
        elif age < 50:
            return "adult"
        elif age < 65:
            return "middle_aged"
        else:
            return "senior"

    def _is_high_risk_doctor(self, doctor_id: str) -> bool:
        """Check if doctor is in high-risk list"""
        # Implement your high-risk doctor logic
        high_risk_patterns = ["DR_X", "TEMP_", "LOCUM_"]
        return any(pattern in doctor_id for pattern in high_risk_patterns)

    def _get_provider_claim_count(self, doctor_id: str) -> int:
        """Get recent claim count for provider"""
        return self.doctor_claim_counts.get(doctor_id, 0)

    def _update_statistics(self, result: Dict[str, Any], processing_time: float):
        """Update model statistics"""
        with self.lock:
            self.model_stats["predictions_made"] += 1
            if result.get("is_fraud", False):
                self.model_stats["fraud_detected"] += 1

            # Update average processing time
            total_predictions = self.model_stats["predictions_made"]
            current_avg = self.model_stats["avg_processing_time"]
            self.model_stats["avg_processing_time"] = (
                current_avg * (total_predictions - 1) + processing_time
            ) / total_predictions

    def _cache_prediction(
        self, claim_id: str, result: Dict[str, Any], features_hash: str
    ):
        """Cache prediction for pattern detection"""
        self.prediction_cache[features_hash] = PredictionCache(
            claim_id=claim_id,
            prediction=result,
            timestamp=datetime.now(),
            features_hash=features_hash,
        )

        # Clean old cache entries (keep last 1000)
        if len(self.prediction_cache) > 1000:
            oldest_key = min(
                self.prediction_cache.keys(),
                key=lambda k: self.prediction_cache[k].timestamp,
            )
            del self.prediction_cache[oldest_key]

    def _update_pattern_tracking(
        self, claim_data: Dict[str, Any], result: Dict[str, Any]
    ):
        """Update pattern tracking data"""
        # Update doctor claim counts
        doctor_id = claim_data.get("doctor_id", "")
        if doctor_id:
            self.doctor_claim_counts[doctor_id] = (
                self.doctor_claim_counts.get(doctor_id, 0) + 1
            )

        # Update patient claim counts
        patient_id = claim_data.get("patient_id", "")
        if patient_id:
            self.patient_claim_counts[patient_id] = (
                self.patient_claim_counts.get(patient_id, 0) + 1
            )

        # Add to recent claims
        self.recent_claims.append(claim_data)
        if len(self.recent_claims) > 1000:
            self.recent_claims.pop(0)

        # Clean old counts (reset daily)
        # This would typically be done by a scheduled task
