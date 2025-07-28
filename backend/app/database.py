# backend/app/database.py

import sqlite3
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
import logging

from backend.config.settings import DATABASE_PATH, MODEL_VERSION

logger = logging.getLogger(__name__)


class DatabaseService:
    """
    Database service for persistent storage of claims, predictions, and feedback.
    """

    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self.connection = None
        self._initialize_database()

    def _initialize_database(self):
        try:
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row
            self._create_tables()
            logger.info(f"Database initialized at {self.db_path}")
        except Exception as e:
            logger.error(f"Database initialization failed: {str(e)}")
            raise

    def _create_tables(self):
        cursor = self.connection.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS claims (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                claim_id TEXT UNIQUE NOT NULL,
                patient_id TEXT NOT NULL,
                doctor_id TEXT NOT NULL,
                patient_age INTEGER,
                patient_gender TEXT,
                medical_scheme TEXT,
                diagnosis_code TEXT,
                claim_amount REAL,
                facility_location TEXT,
                patient_location TEXT,
                submission_timestamp TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                raw_data TEXT
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                claim_id TEXT NOT NULL,
                is_fraud INTEGER NOT NULL,
                fraud_probability REAL NOT NULL,
                risk_level TEXT NOT NULL,
                confidence_score REAL,
                processing_time_ms REAL,
                model_version TEXT,
                flags TEXT,
                recommended_action TEXT,
                prediction_timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                from_cache INTEGER DEFAULT 0,
                FOREIGN KEY (claim_id) REFERENCES claims (claim_id)
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                claim_id TEXT NOT NULL,
                is_actually_fraud INTEGER NOT NULL,
                reviewer_notes TEXT,
                reviewer_id TEXT,
                confidence_in_decision INTEGER,
                feedback_timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (claim_id) REFERENCES claims (claim_id)
            )
        """
        )

        self.connection.commit()

    def is_connected(self) -> bool:
        try:
            self.connection.execute("SELECT 1")
            return True
        except:
            return False

    def close(self):
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")

    def store_prediction(
        self, claim_data: Dict[str, Any], prediction_data: Dict[str, Any]
    ) -> bool:
        try:
            cursor = self.connection.cursor()

            cursor.execute(
                """
                INSERT OR IGNORE INTO claims (
                    claim_id, patient_id, doctor_id, patient_age, patient_gender,
                    medical_scheme, diagnosis_code, claim_amount, facility_location,
                    patient_location, submission_timestamp, raw_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    claim_data.get("claim_id"),
                    claim_data.get("patient_id"),
                    claim_data.get("doctor_id"),
                    claim_data.get("patient_age"),
                    claim_data.get("patient_gender"),
                    claim_data.get("medical_scheme"),
                    claim_data.get("diagnosis_code"),
                    claim_data.get("claim_amount"),
                    claim_data.get("facility_location"),
                    claim_data.get("patient_location"),
                    claim_data.get("timestamp"),
                    json.dumps(claim_data),
                ),
            )

            cursor.execute(
                """
                INSERT INTO predictions (
                    claim_id, is_fraud, fraud_probability, risk_level,
                    confidence_score, processing_time_ms, model_version,
                    flags, recommended_action, from_cache
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    prediction_data.get("claim_id"),
                    int(prediction_data.get("is_fraud")),
                    prediction_data.get("fraud_probability"),
                    prediction_data.get("risk_level"),
                    prediction_data.get("confidence_score"),
                    prediction_data.get("processing_time_ms"),
                    MODEL_VERSION,
                    json.dumps(prediction_data.get("flags", [])),
                    prediction_data.get("recommended_action"),
                    int(prediction_data.get("from_cache", False)),
                ),
            )

            self.connection.commit()
            return True

        except Exception as e:
            logger.error(f"Failed to store prediction: {str(e)}")
            return False

    def store_feedback(self, feedback_data: Dict[str, Any]) -> bool:
        try:
            cursor = self.connection.cursor()

            cursor.execute(
                """
                INSERT INTO feedback (
                    claim_id, is_actually_fraud, reviewer_notes,
                    reviewer_id, confidence_in_decision
                ) VALUES (?, ?, ?, ?, ?)
            """,
                (
                    feedback_data.get("claim_id"),
                    int(feedback_data.get("is_actually_fraud")),
                    feedback_data.get("reviewer_notes"),
                    feedback_data.get("reviewer_id"),
                    feedback_data.get("confidence_in_decision"),
                ),
            )

            self.connection.commit()
            return True

        except Exception as e:
            logger.error(f"Failed to store feedback: {str(e)}")
            return False

    def get_claim_by_id(self, claim_id: str) -> Optional[Dict[str, Any]]:
        try:
            cursor = self.connection.cursor()

            cursor.execute("SELECT * FROM claims WHERE claim_id = ?", (claim_id,))
            claim_row = cursor.fetchone()
            if not claim_row:
                return None

            claim_data = dict(claim_row)

            cursor.execute(
                """
                SELECT * FROM predictions WHERE claim_id = ?
                ORDER BY prediction_timestamp DESC LIMIT 1
            """,
                (claim_id,),
            )
            prediction_row = cursor.fetchone()
            prediction_data = dict(prediction_row) if prediction_row else {}

            cursor.execute(
                """
                SELECT * FROM feedback WHERE claim_id = ?
                ORDER BY feedback_timestamp DESC LIMIT 1
            """,
                (claim_id,),
            )
            feedback_row = cursor.fetchone()
            feedback_data = dict(feedback_row) if feedback_row else {}

            return {
                "claim_id": claim_data.get("claim_id"),
                "patient_info": {
                    "patient_id": claim_data.get("patient_id"),
                    "age": claim_data.get("patient_age"),
                    "gender": claim_data.get("patient_gender"),
                    "location": claim_data.get("patient_location"),
                },
                "provider_info": {
                    "doctor_id": claim_data.get("doctor_id"),
                    "facility_location": claim_data.get("facility_location"),
                    "scheme": claim_data.get("medical_scheme"),
                },
                "claim_details": {
                    "diagnosis_code": claim_data.get("diagnosis_code"),
                    "claim_amount": claim_data.get("claim_amount"),
                    "submitted_at": claim_data.get("submission_timestamp"),
                },
                "fraud_analysis": prediction_data,
                "history": [],
                "related_claims": [],
                "feedback": feedback_data,
            }

        except Exception as e:
            logger.error(f"Failed to retrieve claim {claim_id}: {str(e)}")
            return None

    def get_all_claims(self, limit: int = 100) -> List[Dict[str, Any]]:
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                """
                SELECT 
                    c.claim_id,
                    c.patient_id,
                    c.doctor_id,
                    c.patient_age,
                    c.patient_gender,
                    c.medical_scheme,
                    c.diagnosis_code,
                    c.claim_amount,
                    c.facility_location,
                    c.patient_location,
                    c.submission_timestamp,
                    p.is_fraud,
                    p.fraud_probability,
                    p.risk_level,
                    p.prediction_timestamp
                FROM claims c
                LEFT JOIN predictions p ON c.claim_id = p.claim_id
                ORDER BY c.submission_timestamp DESC
                LIMIT ?
            """,
                (limit,),
            )

            rows = cursor.fetchall()
            return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to retrieve all claims: {str(e)}")
            return []

    def get_summary_stats(self) -> Dict[str, Any]:
        try:
            cursor = self.connection.cursor()

            cursor.execute(
                """
                SELECT COUNT(*) FROM predictions
                WHERE date(prediction_timestamp) = date('now')
            """
            )
            total_today = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT AVG(processing_time_ms) FROM predictions
                WHERE date(prediction_timestamp) = date('now')
            """
            )
            avg_time = cursor.fetchone()[0] or 0

            return {
                "total_predictions_today": total_today,
                "avg_processing_time": avg_time,
            }

        except Exception as e:
            logger.error(f"Failed to get summary stats: {str(e)}")
            return {}
