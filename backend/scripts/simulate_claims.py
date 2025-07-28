import redis
import json
import time
import random
from datetime import datetime

# Connect to Redis
redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

STREAM_KEY = "health_claims_stream"


def random_claim():
    # Generate a synthetic health claim with some random/fraud flags
    claim_id = f"CLAIM-{random.randint(100000, 999999)}"
    patient_id = f"PAT-{random.randint(10000, 99999)}"
    doctor_id = f"DR-{random.choice(['X123', 'A456', 'B789', 'C012'])}"
    patient_age = random.randint(1, 90)
    patient_gender = random.choice(["M", "F"])
    medical_scheme = random.choice(["PSEMAS", "NHIF", "PRIVATE"])
    diagnosis_code = random.choice(["Z00.0", "I10", "E11", "J45", "K21"])
    claim_amount = round(random.uniform(50, 15000), 2)
    facility_location = random.choice(["Windhoek", "Swakopmund", "Walvis Bay"])
    patient_location = random.choice(
        ["Windhoek", "Swakopmund", "Walvis Bay", "Outskirts"]
    )

    # Flags for suspicious claims
    biometric_verified = random.choice([True, False])
    patient_present = random.choice([True, False])
    patient_deceased = random.choice([False] * 99 + [True])  # Rarely deceased
    emergency_case = random.choice([False] * 9 + [True])
    weekend_claim = random.choice([False] * 6 + [True] * 4)
    after_hours_claim = random.choice([False] * 7 + [True] * 3)
    travel_distance_suspicious = patient_location != facility_location

    claim = {
        "claim_id": claim_id,
        "patient_id": patient_id,
        "doctor_id": doctor_id,
        "patient_age": patient_age,
        "patient_gender": patient_gender,
        "medical_scheme": medical_scheme,
        "diagnosis_code": diagnosis_code,
        "claim_amount": claim_amount,
        "facility_location": facility_location,
        "patient_location": patient_location,
        "biometric_verified": biometric_verified,
        "patient_present": patient_present,
        "patient_deceased": patient_deceased,
        "emergency_case": emergency_case,
        "weekend_claim": weekend_claim,
        "after_hours_claim": after_hours_claim,
        "travel_distance_suspicious": travel_distance_suspicious,
        "timestamp": datetime.now().isoformat(),
        "submission_source": "simulated_script",
    }

    return claim


def stream_claims(rate_per_sec=5):
    """
    Continuously generate claims and push to Redis Stream at specified rate.
    """
    interval = 1.0 / rate_per_sec
    print(f"Starting claim stream with {rate_per_sec} claims/second...")

    try:
        while True:
            claim = random_claim()
            # Redis Streams require a dict of strings for XADD fields
            claim_str_dict = {
                k: json.dumps(v) if isinstance(v, (dict, list)) else str(v)
                for k, v in claim.items()
            }
            redis_client.xadd(STREAM_KEY, claim_str_dict)
            print(f"Streamed claim: {claim['claim_id']}")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("Claim streaming stopped.")


if __name__ == "__main__":
    stream_claims(rate_per_sec=10)  # Tune this as needed
