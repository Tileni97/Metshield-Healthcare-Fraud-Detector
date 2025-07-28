# backend/app/redis_client.py
import redis
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class RedisService:
    """
    Redis service for caching predictions, storing real-time data, and managing alerts
    """

    def __init__(self, host="localhost", port=6379, db=0):
        try:
            self.client = redis.Redis(
                host=host,
                port=port,
                db=db,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True,
            )

            # Test connection
            self.client.ping()
            logger.info(f"Redis connected successfully at {host}:{port}")

            # Cache expiry times (in seconds)
            self.PREDICTION_EXPIRY = 3600  # 1 hour
            self.PATIENT_EXPIRY = 86400  # 24 hours
            self.PROVIDER_EXPIRY = 21600  # 6 hours
            self.DAILY_COUNTER_EXPIRY = 604800  # 1 week
            self.ALERT_EXPIRY = 86400 * 7  # 1 week

        except Exception as e:
            logger.error(f"Redis connection failed: {str(e)}")
            self.client = None

    def ping(self) -> bool:
        """Test Redis connection"""
        try:
            if self.client:
                self.client.ping()
                return True
        except:
            pass
        return False

    def close(self):
        """Close Redis connection"""
        if self.client:
            self.client.close()

    def _generate_cache_key(self, claim_data: Dict[str, Any]) -> str:
        """Generate consistent cache key for claim data"""
        # Use key fields to create hash
        key_fields = {
            "patient_id": claim_data.get("patient_id", ""),
            "doctor_id": claim_data.get("doctor_id", ""),
            "diagnosis_code": claim_data.get("diagnosis_code", ""),
            "claim_amount": claim_data.get("claim_amount", 0),
            "timestamp_day": claim_data.get("timestamp", "")[:10],  # Date only
        }

        key_string = json.dumps(key_fields, sort_keys=True)
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        return f"fraud_prediction:{key_hash}"

    def cache_prediction(
        self, claim_data: Dict[str, Any], prediction_result: Dict[str, Any]
    ) -> bool:
        """Cache fraud prediction result"""
        if not self.client:
            return False

        try:
            cache_key = self._generate_cache_key(claim_data)

            cache_data = {
                "prediction": prediction_result,
                "cached_at": datetime.now().isoformat(),
                "claim_id": claim_data.get("claim_id", "unknown"),
                "cache_version": "1.0",
            }

            success = self.client.setex(
                cache_key, self.PREDICTION_EXPIRY, json.dumps(cache_data)
            )

            if success:
                logger.debug(f"Cache stored: {cache_key}")

            return success

        except Exception as e:
            logger.error(f"Cache write failed: {str(e)}")
            return False

    def get_cached_prediction(
        self, claim_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Retrieve cached prediction"""
        if not self.client:
            return None

        try:
            cache_key = self._generate_cache_key(claim_data)
            cached_data = self.client.get(cache_key)

            if cached_data:
                cache_obj = json.loads(cached_data)
                logger.debug(f"Cache hit: {cache_key}")
                return cache_obj["prediction"]

            return None

        except Exception as e:
            logger.error(f"Cache read failed: {str(e)}")
            return None

    def increment_counter(self, counter_name: str) -> int:
        """Increment daily counter"""
        if not self.client:
            return 0

        try:
            today = datetime.now().strftime("%Y-%m-%d")
            key = f"counter:{counter_name}:{today}"

            count = self.client.incr(key)

            # Set expiry for new keys
            if count == 1:
                self.client.expire(key, self.DAILY_COUNTER_EXPIRY)

            return count

        except Exception as e:
            logger.error(f"Counter increment failed: {str(e)}")
            return 0

    def get_daily_stats(self, date: Optional[str] = None) -> Dict[str, int]:
        """Get daily statistics"""
        if not self.client:
            return {}

        try:
            if date is None:
                date = datetime.now().strftime("%Y-%m-%d")

            pattern = f"counter:*:{date}"
            keys = self.client.keys(pattern)

            stats = {}
            for key in keys:
                try:
                    counter_name = key.split(":")[1]
                    count = int(self.client.get(key) or 0)
                    stats[counter_name] = count
                except:
                    continue

            return stats

        except Exception as e:
            logger.error(f"Daily stats retrieval failed: {str(e)}")
            return {}

    def store_alert(self, alert_data: Dict[str, Any]) -> bool:
        """Store high-risk claim alert"""
        if not self.client:
            return False

        try:
            alert_id = (
                f"alert:{alert_data['claim_id']}:{int(datetime.now().timestamp())}"
            )

            alert_record = {
                **alert_data,
                "alert_id": alert_id,
                "created_at": datetime.now().isoformat(),
                "status": "active",
            }

            # Store alert
            success = self.client.setex(
                alert_id, self.ALERT_EXPIRY, json.dumps(alert_record)
            )

            if success:
                # Add to active alerts list
                self.client.zadd(
                    "active_alerts", {alert_id: datetime.now().timestamp()}
                )

                # Increment alert counter
                self.increment_counter("alerts_created")

                logger.info(f"Alert stored: {alert_id}")

            return success

        except Exception as e:
            logger.error(f"Alert storage failed: {str(e)}")
            return False

    def get_recent_alerts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent alerts for live feed"""
        if not self.client:
            return []

        try:
            # Get recent alert IDs (last 'limit' alerts)
            alert_ids = self.client.zrevrange("active_alerts", 0, limit - 1)

            alerts = []
            for alert_id in alert_ids:
                alert_data = self.client.get(alert_id)
                if alert_data:
                    try:
                        alert_obj = json.loads(alert_data)
                        alerts.append(alert_obj)
                    except:
                        continue

            return alerts

        except Exception as e:
            logger.error(f"Recent alerts retrieval failed: {str(e)}")
            return []

    def get_active_alerts_count(self) -> int:
        """Get count of active alerts"""
        if not self.client:
            return 0

        try:
            # Count alerts from last 24 hours
            yesterday = datetime.now() - timedelta(days=1)
            count = self.client.zcount(
                "active_alerts", yesterday.timestamp(), datetime.now().timestamp()
            )
            return count

        except Exception as e:
            logger.error(f"Active alerts count failed: {str(e)}")
            return 0

    def acknowledge_alert(self, alert_id: str, reviewer_id: str) -> bool:
        """Mark alert as acknowledged"""
        if not self.client:
            return False

        try:
            alert_data = self.client.get(alert_id)
            if not alert_data:
                return False

            alert_obj = json.loads(alert_data)
            alert_obj.update(
                {
                    "status": "acknowledged",
                    "acknowledged_by": reviewer_id,
                    "acknowledged_at": datetime.now().isoformat(),
                }
            )

            # Update alert
            success = self.client.setex(
                alert_id, self.ALERT_EXPIRY, json.dumps(alert_obj)
            )

            if success:
                # Remove from active alerts
                self.client.zrem("active_alerts", alert_id)
                logger.info(f"Alert acknowledged: {alert_id}")

            return success

        except Exception as e:
            logger.error(f"Alert acknowledgment failed: {str(e)}")
            return False

    def cache_provider_risk(self, provider_id: str, risk_data: Dict[str, Any]) -> bool:
        """Cache provider risk profile"""
        if not self.client:
            return False

        try:
            key = f"provider_risk:{provider_id}"

            risk_record = {
                **risk_data,
                "provider_id": provider_id,
                "updated_at": datetime.now().isoformat(),
            }

            success = self.client.setex(
                key, self.PROVIDER_EXPIRY, json.dumps(risk_record)
            )

            return success

        except Exception as e:
            logger.error(f"Provider risk cache failed: {str(e)}")
            return False

    def get_provider_risk(self, provider_id: str) -> Optional[Dict[str, Any]]:
        """Get cached provider risk profile"""
        if not self.client:
            return None

        try:
            key = f"provider_risk:{provider_id}"
            cached_data = self.client.get(key)

            if cached_data:
                return json.loads(cached_data)

            return None

        except Exception as e:
            logger.error(f"Provider risk retrieval failed: {str(e)}")
            return None

    def cache_patient_profile(
        self, patient_id: str, profile_data: Dict[str, Any]
    ) -> bool:
        """Cache patient profile data"""
        if not self.client:
            return False

        try:
            key = f"patient_profile:{patient_id}"

            profile_record = {
                **profile_data,
                "patient_id": patient_id,
                "updated_at": datetime.now().isoformat(),
            }

            success = self.client.setex(
                key, self.PATIENT_EXPIRY, json.dumps(profile_record)
            )

            return success

        except Exception as e:
            logger.error(f"Patient profile cache failed: {str(e)}")
            return False

    def get_patient_profile(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """Get cached patient profile"""
        if not self.client:
            return None

        try:
            key = f"patient_profile:{patient_id}"
            cached_data = self.client.get(key)

            if cached_data:
                return json.loads(cached_data)

            return None

        except Exception as e:
            logger.error(f"Patient profile retrieval failed: {str(e)}")
            return None

    def rate_limit_check(
        self, identifier: str, limit: int = 100, window_seconds: int = 3600
    ) -> bool:
        """Check if identifier exceeds rate limit"""
        if not self.client:
            return False  # Allow if Redis is down

        try:
            key = f"rate_limit:{identifier}"
            current_count = self.client.incr(key)

            if current_count == 1:
                self.client.expire(key, window_seconds)

            return current_count <= limit

        except Exception as e:
            logger.error(f"Rate limit check failed: {str(e)}")
            return True  # Allow if check fails

    def store_system_metrics(self, metrics: Dict[str, Any]) -> bool:
        """Store system performance metrics"""
        if not self.client:
            return False

        try:
            timestamp = int(datetime.now().timestamp())
            key = f"system_metrics:{timestamp}"

            success = self.client.setex(key, 3600, json.dumps(metrics))  # 1 hour expiry

            # Keep only recent metrics (sliding window)
            if success:
                pattern = "system_metrics:*"
                keys = self.client.keys(pattern)

                # Remove old metrics (keep last 100)
                if len(keys) > 100:
                    old_keys = sorted(keys)[:-100]
                    if old_keys:
                        self.client.delete(*old_keys)

            return success

        except Exception as e:
            logger.error(f"System metrics storage failed: {str(e)}")
            return False

    def get_system_metrics(self, last_n: int = 10) -> List[Dict[str, Any]]:
        """Get recent system metrics"""
        if not self.client:
            return []

        try:
            pattern = "system_metrics:*"
            keys = self.client.keys(pattern)

            # Sort by timestamp and get latest
            sorted_keys = sorted(keys, reverse=True)[:last_n]

            metrics = []
            for key in sorted_keys:
                data = self.client.get(key)
                if data:
                    try:
                        metric_obj = json.loads(data)
                        metrics.append(metric_obj)
                    except:
                        continue

            return metrics

        except Exception as e:
            logger.error(f"System metrics retrieval failed: {str(e)}")
            return []

    def clear_cache(self, pattern: str = None) -> bool:
        """Clear cache entries matching pattern"""
        if not self.client:
            return False

        try:
            if pattern:
                keys = self.client.keys(pattern)
            else:
                # Clear all fraud detection related keys
                patterns = [
                    "fraud_prediction:*",
                    "counter:*",
                    "alert:*",
                    "active_alerts",
                    "provider_risk:*",
                    "patient_profile:*",
                    "rate_limit:*",
                    "system_metrics:*",
                ]

                keys = []
                for p in patterns:
                    keys.extend(self.client.keys(p))

            if keys:
                deleted = self.client.delete(*keys)
                logger.info(f"Cleared {deleted} cache entries")
                return True

            return True

        except Exception as e:
            logger.error(f"Cache clear failed: {str(e)}")
            return False

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not self.client:
            return {}

        try:
            info = self.client.info()

            # Count different key types
            patterns = {
                "predictions": "fraud_prediction:*",
                "counters": "counter:*",
                "alerts": "alert:*",
                "provider_profiles": "provider_risk:*",
                "patient_profiles": "patient_profile:*",
            }

            key_counts = {}
            for name, pattern in patterns.items():
                key_counts[name] = len(self.client.keys(pattern))

            stats = {
                "redis_version": info.get("redis_version", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_human": info.get("used_memory_human", "0B"),
                "total_keys": (
                    info.get("db0", {}).get("keys", 0) if "db0" in info else 0
                ),
                "key_counts": key_counts,
                "uptime_in_seconds": info.get("uptime_in_seconds", 0),
            }

            return stats

        except Exception as e:
            logger.error(f"Cache stats retrieval failed: {str(e)}")
            return {}
