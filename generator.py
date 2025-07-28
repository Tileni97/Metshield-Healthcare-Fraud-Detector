import random
import pandas as pd
import uuid
import numpy as np

class HealthcareFraudDetector:
    def __init__(self):
        self.icd10_codes = [
            "A15.9", "B50.9", "A09", "J44.1", "J06.9", "K59.0", "R50.9", "M79.1", "I10", "E11.9",
            "E43", "O80", "Z30.9", "S72.0", "S06.9", "T14.9", "Z51.1", "I25.1"
        ]
        self.locations = [
            "Windhoek", "Swakopmund", "Rundu", "Oshakati", "Walvis Bay", "Katima Mulilo",
            "Rehoboth", "Gobabis", "Otjiwarongo", "Grootfontein"
        ]
        self.schemes = ["PSEMAS", "Namibia Medical Care"]
        self.genders = ["M", "F"]
        self.doctors, self.provider_fraud_profiles = self.generate_doctor_profiles()

    def generate_doctor_profiles(self):
        doctors = []
        profiles = {}
        for i in range(1, 151):  # 150 doctors
            if i <= 5:
                doc_id = f"DR_X_{i:03d}"
                fraud_prob = 0.8
                volume = random.uniform(25, 50)
                upcoding = 0.9
            else:
                doc_id = f"DR_{i:03d}"
                fraud_prob = random.uniform(0.05, 0.25)
                volume = random.uniform(3, 15)
                upcoding = random.uniform(0.1, 0.3)

            doctors.append(doc_id)
            profiles[doc_id] = {
                'fraud_probability': fraud_prob,
                'avg_claims_per_day': volume,
                'upcoding_tendency': upcoding
            }
        return doctors, profiles

    def generate_synthetic_data(self, n_samples=1):
        records = []
        for _ in range(n_samples):
            doctor_id = random.choice(self.doctors)
            profile = self.provider_fraud_profiles[doctor_id]
            is_fraud = random.random() < profile['fraud_probability']
            gender = random.choice(self.genders)
            age = random.randint(1, 90)
            diagnosis_code = random.choice(self.icd10_codes)
            facility = random.choice(self.locations)
            amount = round(random.uniform(200, 15000), 2)
            provider = f"Dr. {uuid.uuid4().hex[:8].title()}"  # Generate unique doctor name

            record = {
                "claim_id": str(uuid.uuid4()),
                "patient_id": f"PT-{uuid.uuid4().hex[:6]}",
                "doctor_id": doctor_id,
                "patient_age": age,
                "patient_gender": gender,
                "medical_scheme": random.choice(self.schemes),
                "diagnosis_code": diagnosis_code,
                "claim_amount": amount,
                "facility_location": facility,
                "patient_location": random.choice(self.locations),
                "biometric_verified": not is_fraud if random.random() < 0.7 else is_fraud,
                "patient_present": not is_fraud,
                "patient_deceased": is_fraud if random.random() < 0.4 else False,
                "emergency_case": random.choice([True, False]),
                "weekend_claim": is_fraud if random.random() < 0.4 else False,
                "after_hours_claim": is_fraud if random.random() < 0.3 else False,
                "travel_distance_suspicious": is_fraud if random.random() < 0.5 else False,
                "is_fraud": is_fraud
            }
            records.append(record)
        return pd.DataFrame(records)