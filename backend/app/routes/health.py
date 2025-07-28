from fastapi import APIRouter
from datetime import datetime

router = APIRouter()


@router.get("/api/v1/health")
def get_health():
    return {
        "status": "ok",
        "api": "ClaimWatch API",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": 12345,
        "services": {
            "fraud_detection": "running",
            "redis_cache": "running",
            "database": "connected",
        },
        "version": "1.0.0",
    }
