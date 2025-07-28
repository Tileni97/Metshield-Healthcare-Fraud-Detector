# backend/app/main.py
import sys
import io

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse

from fastapi import Query

from backend.app.models import ClaimRequest
from typing import List, Dict, Any
from fastapi import Path

import uvicorn
import json
import asyncio
from datetime import datetime
from typing import Optional
import logging
from contextlib import asynccontextmanager
import traceback

from .utils.freshdesk import submit_freshdesk_ticket


# Dummy system metrics (replace with real logic later)
def get_system_load() -> float:
    """Returns CPU load as a value between 0 and 1."""
    try:
        import psutil

        return round(psutil.cpu_percent(interval=0.5) / 100, 2)
    except Exception:
        return 0.0


def get_active_alerts_count() -> int:
    """Returns active alert count (placeholder logic)"""
    return 2  # Or fetch from Redis or DB if needed


from .models import ClaimRequest, FraudResponse, HealthResponse, StatsResponse
from .fraud_detection import FraudDetectionService
from .redis_client import RedisService
from .database import DatabaseService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("api.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

fraud_service = None
redis_service = None
db_service = None
startup_time = datetime.now()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global fraud_service, redis_service, db_service
    logger.info("Starting Healthcare Fraud Detection API...")
    try:
        fraud_service = FraudDetectionService(model_path="models/")
        redis_service = RedisService()
        db_service = DatabaseService()

        if not fraud_service.is_model_loaded():
            logger.warning("ML model failed to load")
        if not redis_service.ping():
            logger.warning("Redis connection failed")
        if not db_service.is_connected():
            logger.warning("Database connection failed")

        logger.info("All services initialized successfully")
        yield
    except Exception as e:
        logger.error(f"Initialization error: {e}")
        logger.error(traceback.format_exc())
        yield
    finally:
        logger.info("Shutting down services...")
        try:
            if redis_service:
                redis_service.close()
        except Exception as e:
            logger.error(f"Error closing Redis: {e}")
        try:
            if db_service:
                db_service.close()
        except Exception as e:
            logger.error(f"Error closing Database: {e}")


app = FastAPI(
    title="Healthcare Fraud Detection API",
    description="Real-time fraud detection system",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_fraud_service():
    if not fraud_service:
        raise HTTPException(status_code=503, detail="Fraud service unavailable")
    return fraud_service


def get_redis_service():
    if not redis_service:
        raise HTTPException(status_code=503, detail="Redis unavailable")
    return redis_service


def get_db_service():
    if not db_service:
        raise HTTPException(status_code=503, detail="DB unavailable")
    return db_service


@app.get("/")
async def root():
    return {"message": "Fraud Detection API", "status": "running"}


@app.get("/api/v1/claims", response_model=List[Dict[str, Any]])
def get_all_claims(
    limit: int = Query(100, ge=1, le=500),
    db_service: DatabaseService = Depends(get_db_service),
):
    try:
        return db_service.get_all_claims(limit=limit)
    except Exception as e:
        logger.error(f"Failed to retrieve claims: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve claims")


@app.post("/api/v1/detect-fraud", response_model=FraudResponse)
async def detect_fraud(
    claim: ClaimRequest,
    background_tasks: BackgroundTasks,
    fraud_service: FraudDetectionService = Depends(get_fraud_service),
    redis_service: RedisService = Depends(get_redis_service),
    db_service: DatabaseService = Depends(get_db_service),
):
    try:
        logger.info(f"Detecting fraud for claim {claim.claim_id}")
        cached = redis_service.get_cached_prediction(claim.dict())
        if cached:
            redis_service.increment_counter("cache_hits")
            return FraudResponse(**cached, from_cache=True)

        result = fraud_service.predict_fraud(claim.dict())
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])

        response = FraudResponse(
            claim_id=claim.claim_id,
            is_fraud=result["is_fraud"],
            fraud_probability=result["fraud_probability"],
            risk_level=result["risk_level"],
            confidence_score=result.get("confidence_score", 0.0),
            flags=result.get("flags", []),
            processing_time_ms=result.get("processing_time_ms", 0),
            timestamp=datetime.now().isoformat(),
            from_cache=False,
        )

        redis_service.cache_prediction(claim.dict(), response.dict())
        redis_service.increment_counter("predictions_made")

        log_data = {
            "claim_id": claim.claim_id,
            "claim_amount": claim.claim_amount,
            "patient_age": claim.patient_age,
            "patient_gender": claim.patient_gender,
            "timestamp": response.timestamp,
            "fraud_probability": response.fraud_probability,
            "risk_level": response.risk_level,
            "is_fraud": response.is_fraud,
        }

        logger.info(f"🔁 Publishing live claim data: {json.dumps(log_data)}")
        redis_service.client.publish("live-claims", json.dumps(log_data))

        if response.risk_level in ["HIGH", "CRITICAL"]:
            redis_service.increment_counter("high_risk_claims")
            background_tasks.add_task(process_high_risk_claim, response, claim)

        background_tasks.add_task(store_prediction_result, db_service, claim, response)
        return response

    except Exception as e:
        logger.error(f"Fraud detection error: {e}")
        raise HTTPException(status_code=500, detail="Internal error")


@app.get("/api/v1/health", response_model=HealthResponse)
async def health_check():
    uptime = (datetime.now() - startup_time).total_seconds()
    return HealthResponse(
        api="healthy",
        timestamp=datetime.now().isoformat(),
        uptime_seconds=uptime,
        services={
            "ml_model": (
                "healthy"
                if fraud_service and fraud_service.is_model_loaded()
                else "unhealthy"
            ),
            "redis": (
                "healthy" if redis_service and redis_service.ping() else "unhealthy"
            ),
            "database": (
                "healthy" if db_service and db_service.is_connected() else "unhealthy"
            ),
        },
        status="healthy",
    )


@app.get("/api/v1/live-feed")
async def live_feed(request: Request):
    pubsub = redis_service.client.pubsub()
    pubsub.subscribe("live-claims")

    async def event_generator():
        while True:
            if await request.is_disconnected():
                break
            message = pubsub.get_message(ignore_subscribe_messages=True, timeout=1)
            if message and message["type"] == "message":
                data = message["data"]
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
                yield f"data: {data}\n\n"
            await asyncio.sleep(0.1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/v1/stats", response_model=StatsResponse)
async def stats():
    try:
        daily = redis_service.get_daily_stats() if redis_service else {}
        db_stats = db_service.get_summary_stats() if db_service else {}
        return StatsResponse(
            total_claims_today=daily.get("predictions_made", 0),
            fraud_detected_today=daily.get("high_risk_claims", 0),
            cache_hit_rate=daily.get("cache_hits", 0)
            / max(daily.get("predictions_made", 1), 1),
            average_processing_time_ms=db_stats.get("avg_processing_time", 0),
            high_risk_claims_today=daily.get("high_risk_claims", 0),
            system_load=get_system_load(),
            active_alerts=get_active_alerts_count(),
            timestamp=datetime.now().isoformat(),
        )
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail="Stats failed")


async def process_high_risk_claim(response: FraudResponse, claim: ClaimRequest):
    try:
        alert_data = {
            "claim_id": response.claim_id,
            "risk_level": response.risk_level,
            "fraud_probability": response.fraud_probability,
            "patient_id": claim.patient_id,
            "doctor_id": claim.doctor_id,
            "claim_amount": claim.claim_amount,
            "timestamp": datetime.now().isoformat(),
            "status": "pending_review",
        }

        redis_service.store_alert(alert_data)

        # 🎯 Send to Freshdesk
        subject = f"🚨 {response.risk_level} Risk Claim Detected – ID: {claim.claim_id}"
        description = (
            f"A {response.risk_level} risk claim was detected.\n\n"
            f"• Claim ID: {claim.claim_id}\n"
            f"• Amount: N${claim.claim_amount}\n"
            f"• Patient ID: {claim.patient_id}\n"
            f"• Doctor ID: {claim.doctor_id}\n"
            f"• Fraud Probability: {response.fraud_probability:.2f}\n"
            f"• Risk Level: {response.risk_level}\n"
            f"• Timestamp: {alert_data['timestamp']}"
        )

        submit_freshdesk_ticket(subject, description)

    except Exception as e:
        logger.error(f"Failed to process alert or send ticket: {e}")


async def store_prediction_result(
    db_service, claim: ClaimRequest, response: FraudResponse
):
    try:

        full_claim = {
            "claim_id": claim.claim_id,
            "claim_details": {
                "amount": claim.claim_amount,
                "diagnosis_code": claim.diagnosis_code,
                "medical_scheme": claim.medical_scheme,
                "timestamp": response.timestamp,
            },
            "patient_info": {
                "name": claim.patient_name or f"Patient {claim.patient_id[-4:]}",
                "age": claim.patient_age,
                "gender": claim.patient_gender,
            },
            "provider_info": {
                "facility": claim.facility_location,
                "doctor": claim.doctor_name
                or f"Dr. {claim.doctor_id[-4:]}",  # Placeholder
            },
            "fraud_analysis": {
                "risk_level": response.risk_level,
                "is_fraud": response.is_fraud,
                "flags": response.flags,
            },
        }

        key = f"claim:{claim.claim_id}"
        redis_service.client.set(key, json.dumps(full_claim))
        logger.info(f"Stored full claim in Redis: {key}")

        # Also save to database
        db_service.store_prediction(claim.dict(), response.dict())
    except Exception as e:
        logger.error(f"Failed to store prediction: {e}")


from fastapi import Path


@app.get("/api/v1/claims/{claim_id}")
async def get_claim_details(
    claim_id: str = Path(..., description="The ID of the claim to retrieve"),
    redis_service: RedisService = Depends(get_redis_service),
):
    try:
        key = f"claim:{claim_id}"
        raw = redis_service.client.get(key)
        if not raw:
            raise HTTPException(status_code=404, detail="Claim not found")

        return json.loads(raw)
    except Exception as e:
        logger.error(f"Error fetching claim {claim_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve claim details")


@app.options("/{path:path}")
async def options(path: str):
    return JSONResponse(
        content={"message": "OK"},
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        },
    )


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
