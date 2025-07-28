# backend/config/settings.py

import os
from dotenv import load_dotenv

load_dotenv()

# General settings
DATABASE_PATH = os.getenv("DATABASE_PATH", "fraud_detection.db")
MODEL_VERSION = os.getenv("MODEL_VERSION", "1.0")

# Model pipeline settings
MODEL_DIR = os.getenv("MODEL_DIR", "models/")
ENCODER_DIR = os.getenv("ENCODER_DIR", "encoders/")

# Risk thresholds
RISK_THRESHOLDS = {
    "CRITICAL": float(os.getenv("RISK_CRITICAL", 0.8)),
    "HIGH": float(os.getenv("RISK_HIGH", 0.6)),
    "MEDIUM": float(os.getenv("RISK_MEDIUM", 0.4)),
    "LOW": float(os.getenv("RISK_LOW", 0.2)),
}
