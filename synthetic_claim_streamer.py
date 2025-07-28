# \Project\synthetic_claim_streamer.py

import requests
import time
import random
import argparse
from datetime import datetime
from generator import HealthcareFraudDetector

# Constants
DEFAULT_API_ENDPOINT = "http://localhost:8000/api/v1/detect-fraud"

# Initialize generator
generator = HealthcareFraudDetector()


def convert_claim_for_api_format(row):
    return {
        "claim_id": row["claim_id"],
        "patient_id": row["patient_id"],
        "doctor_id": row["doctor_id"],
        "patient_age": row["patient_age"],
        "patient_gender": row["patient_gender"],
        "medical_scheme": random.choice(["PSEMAS", "Namibia Medical Care"]),
        "diagnosis_code": row["diagnosis_code"],
        "claim_amount": row["claim_amount"],
        "facility_location": row["facility_location"],
        "patient_location": row["patient_location"],
        "biometric_verified": row["biometric_verified"],
        "patient_present": row["patient_present"],
        "patient_deceased": row["patient_deceased"],
        "emergency_case": row["emergency_case"],
        "weekend_claim": row["weekend_claim"],
        "after_hours_claim": row["after_hours_claim"],
        "travel_distance_suspicious": row["travel_distance_suspicious"],
        "timestamp": datetime.now().isoformat(),
        "submission_source": "synthetic_generator",
    }


def stream_claims(api_url, sleep_range=(3, 15), limit=0):
    count = 0
    while True:
        if limit and count >= limit:
            print("🎯 Reached claim limit. Exiting.")
            break

        try:
            df = generator.generate_synthetic_data(n_samples=1)
            row = df.iloc[0].to_dict()
            payload = convert_claim_for_api_format(row)

            print(
                f"🚀 Sending claim {payload['claim_id']} ({'FRAUD' if row['is_fraud'] else 'LEGIT'})..."
            )
            response = requests.post(api_url, json=payload)

            if response.status_code == 200:
                print("✅ Claim submitted successfully.")
            else:
                print(f"❌ Failed to submit: {response.status_code} - {response.text}")

            wait_time = random.randint(*sleep_range)
            print(f"⏱️ Waiting {wait_time}s before next claim...\n")
            time.sleep(wait_time)
            count += 1

        except Exception as e:
            print(f"💥 Error: {e}")
            time.sleep(10)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MetShield Synthetic Claim Generator")
    parser.add_argument(
        "--api", type=str, default=DEFAULT_API_ENDPOINT, help="API endpoint URL"
    )
    parser.add_argument(
        "--min-delay", type=int, default=3, help="Minimum seconds between claims"
    )
    parser.add_argument(
        "--max-delay", type=int, default=15, help="Maximum seconds between claims"
    )
    parser.add_argument(
        "--count", type=int, default=0, help="Number of claims to send (0 = infinite)"
    )

    args = parser.parse_args()
    sleep_range = (args.min_delay, args.max_delay)

    print(f"🧬 Starting synthetic claim generator...")
    print(f"🔗 Endpoint: {args.api}")
    print(f"🎯 Count: {args.count or '∞'}, Delay: {sleep_range} seconds\n")

    stream_claims(api_url=args.api, sleep_range=sleep_range, limit=args.count)
