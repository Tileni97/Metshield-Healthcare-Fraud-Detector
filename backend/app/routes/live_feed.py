# \routes\live_feed.py
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import asyncio
import json
import random
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/api/v1/live-feed")
async def live_feed():
    """Live feed endpoint that streams realistic claim objects"""

    async def event_generator():
        connection_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        logger.info(f"Live feed connection started: {connection_id}")
        claim_counter = 0

        try:
            # Initial connection message
            yield f"data: {json.dumps({'type': 'connected', 'connection_id': connection_id})}\n\n"

            while True:
                fraud_probability = round(random.uniform(0.1, 0.95), 3)
                is_fraud = fraud_probability > 0.7

                # Determine risk level
                if fraud_probability >= 0.9:
                    risk_level = "CRITICAL"
                elif fraud_probability >= 0.7:
                    risk_level = "HIGH"
                elif fraud_probability >= 0.5:
                    risk_level = "MEDIUM"
                elif fraud_probability >= 0.3:
                    risk_level = "LOW"
                else:
                    risk_level = "MINIMAL"

                # Generate realistic claim payload
                claim = {
                    "claim_id": f"CLAIM{random.randint(10000, 99999)}",
                    "patient_id": f"PAT{random.randint(1000, 9999)}",
                    "doctor_id": f"DOC{random.randint(100, 999)}",
                    "claim_amount": round(random.uniform(150.0, 9500.0), 2),
                    "patient_age": random.randint(1, 90),
                    "patient_gender": random.choice(["M", "F"]),
                    "is_fraud": is_fraud,
                    "fraud_probability": fraud_probability,
                    "risk_level": risk_level,
                    "confidence_score": round(random.uniform(0.6, 0.99), 3),
                    "timestamp": datetime.now().isoformat(),
                    "processing_time_ms": random.randint(50, 400),
                    "flags": random.sample(
                        [
                            "after_hours",
                            "high_amount",
                            "travel_distance",
                            "frequent_claims",
                            "biometric_mismatch",
                            "duplicate_claim",
                        ],
                        k=random.randint(0, 2),
                    ),
                    "from_cache": False,
                }

                # Yield the claim directly (flat structure)
                yield f"data: {json.dumps(claim)}\n\n"

                # Send every 2–5 seconds
                await asyncio.sleep(random.uniform(2, 5))

        except asyncio.CancelledError:
            logger.info(f"Live feed connection cancelled: {connection_id}")
        except Exception as e:
            logger.error(f"Live feed error: {str(e)}")
            error_event = {
                "type": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat(),
                "connection_id": connection_id,
            }
            yield f"data: {json.dumps(error_event)}\n\n"
        finally:
            logger.info(f"Live feed connection ended: {connection_id}")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        },
    )
