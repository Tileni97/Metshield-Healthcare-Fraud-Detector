#!/usr/bin/env python
# coding: utf-8

# ### Setup & Imports 

# In[1]:


# === Core Data & ML ===
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import (classification_report, 
                           confusion_matrix, 
                           roc_auc_score)
import joblib

# === Redis Integration ===
REDIS_ENABLED = False  # Toggle based on your needs
if REDIS_ENABLED:
    try:
        import redis
        import hashlib
        import json
        r = redis.Redis(host='localhost', port=6379, db=0)
        print("✅ Redis connected - real-time checks enabled")
    except Exception as e:
        print(f"⚠️ Redis connection failed: {str(e)}")
        REDIS_ENABLED = False

# === Logging & Debugging ===
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("fraud_detection.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# === Configuration ===
class Config:
    FRAUD_TYPES = {
        0: "legitimate",
        1: "ghost_patient",
        2: "upcoding",
        3: "duplicate"
    }
    RISK_THRESHOLDS = {
        'low': 0.3,
        'medium': 0.7,
        'high': 0.9
    }

print("\n⚡ Fraud Detection System Initialized")
print(f"   - Redis: {'ON' if REDIS_ENABLED else 'OFF'}")
print(f"   - Logging: Active (fraud_detection.log)")


#  ### Data Generation Classes & Constants 

# In[2]:


# === Constants: Namibian Locations & Facilities ===
LOCATIONS_FACILITIES = {
    'Windhoek': ['Windhoek Central Hospital', 'Roman Catholic Hospital', 'Mediclinic Windhoek', 'KHKI Medical Clinic', 'TFFA Medical Clinic'],
    'Swakopmund': ['Swakopmund State Hospital', 'Welwitschia Hospital'],
    'Walvis_Bay': ['Walvis Bay State Hospital', 'Welmed Hospital'],
    'Oshakati': ['Oshakati State Hospital', 'Oshakati Private Hospital'],
    'Rundu': ['Rundu State Hospital', 'Rundu Private Clinic'],
    'Katima_Mulilo': ['Katima Mulilo State Hospital'],
    'Rehoboth': ['Rehoboth District Hospital'],
    'Gobabis': ['Gobabis District Hospital'],
    'Otjiwarongo': ['Otjiwarongo District Hospital'],
    'Grootfontein': ['Grootfontein District Hospital']
}

# === Medical Aid Schemes in Namibia ===
MEDICAL_SCHEMES = [
    'PSEMAS', 'GIPF Medical Scheme', 'Bankmed Namibia', 'Momentum Health', 
    'Namibia Medical Care', 'Metropolitan Health', 'Discovery Health Namibia'
]

# === ICD-10 Diagnoses with Namibian Costs ===
DIAGNOSES = {
    'A15.9': {'name': 'Tuberculosis', 'cost_range': (800, 2500), 'frequency': 0.15},
    'B50.9': {'name': 'Malaria', 'cost_range': (350, 1200), 'frequency': 0.12},
    'A09': {'name': 'Diarrhea_gastroenteritis', 'cost_range': (200, 600), 'frequency': 0.10},
    'J44.1': {'name': 'COPD_exacerbation', 'cost_range': (1500, 4000), 'frequency': 0.08},
    'J06.9': {'name': 'Upper_respiratory_infection', 'cost_range': (250, 600), 'frequency': 0.20},
    'K59.0': {'name': 'Constipation', 'cost_range': (150, 400), 'frequency': 0.05},
    'R50.9': {'name': 'Fever_unspecified', 'cost_range': (200, 500), 'frequency': 0.08},
    'M79.1': {'name': 'Myalgia', 'cost_range': (300, 700), 'frequency': 0.06},
    'I10': {'name': 'Hypertension', 'cost_range': (500, 1500), 'frequency': 0.12},
    'E11.9': {'name': 'Type_2_diabetes', 'cost_range': (800, 2200), 'frequency': 0.08},
    'E43': {'name': 'Malnutrition', 'cost_range': (600, 1800), 'frequency': 0.04},
    'O80': {'name': 'Normal_delivery', 'cost_range': (3500, 8000), 'frequency': 0.03},
    'Z30.9': {'name': 'Family_planning', 'cost_range': (200, 500), 'frequency': 0.04},
    'S72.0': {'name': 'Femur_fracture', 'cost_range': (8000, 25000), 'frequency': 0.01},
    'S06.9': {'name': 'Head_injury', 'cost_range': (2000, 12000), 'frequency': 0.02},
    'T14.9': {'name': 'Multiple_injuries', 'cost_range': (1500, 8000), 'frequency': 0.02},
    'Z51.1': {'name': 'Chemotherapy', 'cost_range': (15000, 45000), 'frequency': 0.005},
    'I25.1': {'name': 'Heart_surgery', 'cost_range': (50000, 150000), 'frequency': 0.002}
}

# === Multi-Class Fraud Labels ===
FRAUD_CLASSES = {
    0: "normal",
    1: "ghost_patient",
    2: "geographic_anomaly",
    3: "cost_outlier",
    4: "duplicate_claim",
    5: "diagnosis_mismatch",
    6: "volume_anomaly"
}

# === Rule Table for Simulation/Labeling ===
RULE_TABLE = {
    "ghost_patient": lambda row: not row.get("biometric_verified", True),
    "geographic_anomaly": lambda row: row.get("travel_distance_suspicious", False),
    "cost_outlier": lambda row: row.get("claim_amount", 0) > row.get("expected_cost_max", 1) * 1.5,
    "diagnosis_mismatch": lambda row: row.get("diagnosis_code") not in DIAGNOSES,
    "volume_anomaly": lambda row: row.get("provider_claims_today", 0) > 20,
    "duplicate_claim": lambda row: False  # TODO: Add logic if needed
}

# === Core Fraud Detection Class (used for simulation/training) ===
class HealthcareFraudDetector:
    def __init__(self):
        self.rule_weights = {
            'impossible_volume': 30,
            'weekend_non_emergency': 15,
            'diagnosis_mismatch': 25,
            'cost_outlier': 20,
            'ghost_patient': 40,
            'geographic_anomaly': 15
        }
        self.anomaly_model = None
        self.scaler = None
        self.is_trained = False

print("🗂️ Namibian constants and fraud rules loaded.")


# In[3]:


def generate_doctor_profiles_with_fraud_patterns():
    """Generate synthetic Namibian doctor profiles with embedded fraud behavior patterns."""
    
    doctors = []
    for i in range(1, 151):  # 150 doctors total
        if i <= 5:
            doctors.append(f"DR_X_{i:03d}")  # Known high-risk doctors (case-study based)
        else:
            doctors.append(f"DR_{i:03d}")

    provider_fraud_profiles = {}
    for doctor in doctors:
        if 'DR_X' in doctor:
            provider_fraud_profiles[doctor] = {
                'fraud_probability': 0.8,
                'avg_claims_per_day': np.random.uniform(25, 50),  # High volume anomaly
                'upcoding_tendency': 0.9
            }
        else:
            provider_fraud_profiles[doctor] = {
                'fraud_probability': np.random.uniform(0.05, 0.25),
                'avg_claims_per_day': np.random.uniform(3, 15),
                'upcoding_tendency': np.random.uniform(0.1, 0.3)
            }
    
    print(f"👨‍⚕️ Generated {len(doctors)} doctor profiles.")
    print(f"   🚨 High-risk doctors: {len([d for d in doctors if 'DR_X' in d])}")
    
    return doctors, provider_fraud_profiles

# Generate and store doctor profiles globally
DOCTORS, PROVIDER_FRAUD_PROFILES = generate_doctor_profiles_with_fraud_patterns()


# In[6]:


def generate_patient_population(n_samples):
    """Generate synthetic patient population"""
    
    print("👥 Generating patient pool...")
    
    # Generate main patient pool
    patient_pool = []
    for i in range(n_samples):
        patient_pool.append({
            'patient_id': f"NAM_{np.random.randint(100000, 999999):06d}",
            'age': max(0, int(np.random.normal(35, 18))),
            'gender': np.random.choice(['M', 'F']),
            'location': np.random.choice(list(LOCATIONS_FACILITIES.keys()), 
                       p=[0.35, 0.12, 0.10, 0.15, 0.08, 0.05, 0.05, 0.04, 0.03, 0.03]),
            'medical_scheme': np.random.choice(MEDICAL_SCHEMES),
            'is_deceased': np.random.random() < 0.02
        })
    
    # Add some deceased patients for fraud scenarios
    deceased_patients = []
    for i in range(50):  # Add 50 deceased patients for fraud testing
        deceased_patients.append({
            'patient_id': f"NAM_DEC_{i:04d}",
            'age': np.random.randint(50, 90),
            'gender': np.random.choice(['M', 'F']),
            'location': np.random.choice(list(LOCATIONS_FACILITIES.keys())),
            'medical_scheme': np.random.choice(MEDICAL_SCHEMES),
            'is_deceased': True
        })
    
    all_patients = patient_pool + deceased_patients
    
    print(f"   ✅ Generated {len(patient_pool)} regular patients")
    print(f"   ⚰️ Added {len(deceased_patients)} deceased patients for fraud testing")
    
    return all_patients


# ### Synthetic Data Generation 

# In[7]:


def generate_synthetic_data(self, n_samples=5000):
    """Generate synthetic healthcare claims data for ML training."""
    
    print(f"🏥 Generating {n_samples} synthetic Namibian healthcare claims...")
    np.random.seed(42)
    
    all_patients = generate_patient_population(n_samples)
    data = []

    for i in range(n_samples):
        if i % 500 == 0:
            print(f"   ➕ {i}/{n_samples} claims generated...")

        patient = all_patients[i % len(all_patients)]
        doctor_id = np.random.choice(DOCTORS)
        doctor_profile = PROVIDER_FRAUD_PROFILES[doctor_id]

        # Decide location logic
        location = patient['location'] if np.random.rand() < 0.7 else np.random.choice(list(LOCATIONS_FACILITIES.keys()))
        facility = np.random.choice(LOCATIONS_FACILITIES[location])

        # Timestamp creation
        days_ago = np.random.exponential(30)
        timestamp = datetime.now() - timedelta(days=min(days_ago, 365))
        if timestamp.weekday() >= 5 and np.random.rand() < 0.7:
            timestamp -= timedelta(days=np.random.randint(1, 3))
            
        # Diagnosis selection
        frequencies = np.array([d['frequency'] for d in DIAGNOSES.values()])
        frequencies /= frequencies.sum()  # Ensure the sum is 1.0
        diagnosis_code = np.random.choice(list(DIAGNOSES.keys()), p=frequencies)
        diagnosis_info = DIAGNOSES[diagnosis_code]
        base_cost = np.random.uniform(*diagnosis_info['cost_range'])

        # Fraud logic
        is_fraud = False
        fraud_type = 'normal'
        fraud_roll = np.random.rand()

        if fraud_roll < doctor_profile['fraud_probability']:
            is_fraud = True
            ft_roll = np.random.rand()

            if ft_roll < 0.3:
                fraud_type = 'ghost_patient'
                if not patient['is_deceased']:
                    patient = np.random.choice([p for p in all_patients if p['is_deceased']])
            elif ft_roll < 0.5:
                fraud_type = 'volume_anomaly'
            elif ft_roll < 0.7:
                fraud_type = 'cost_outlier'
                base_cost *= np.random.uniform(2.0, 5.0)
            elif ft_roll < 0.85:
                fraud_type = 'weekend_non_emergency'
                timestamp += timedelta(days=(5 - timestamp.weekday()) % 7 or 1)
            else:
                fraud_type = 'geographic_anomaly'
                location = np.random.choice([loc for loc in LOCATIONS_FACILITIES if loc != patient['location']])
                facility = np.random.choice(LOCATIONS_FACILITIES[location])

        biometric_verified = np.random.rand() < (0.3 if is_fraud else 0.85)
        patient_present = np.random.rand() < (0.4 if is_fraud else 0.95)

        emergency_codes = ['S72.0', 'S06.9', 'T14.9', 'O80']
        emergency_case = diagnosis_code in emergency_codes or np.random.rand() < 0.05
        travel_distance_suspicious = abs(
            list(LOCATIONS_FACILITIES).index(location) - list(LOCATIONS_FACILITIES).index(patient['location'])
        ) > 2 and not emergency_case

        # Final claim
        claim = {
            'claim_id': f"NAM_CLM_{i:06d}",
            'patient_id': patient['patient_id'],
            'patient_age': patient['age'],
            'patient_gender': patient['gender'],
            'patient_location': patient['location'],
            'patient_deceased': patient['is_deceased'],
            'medical_scheme': patient['medical_scheme'],
            'doctor_id': doctor_id,
            'facility_name': facility,
            'facility_location': location,
            'timestamp': timestamp,
            'diagnosis_code': diagnosis_code,
            'diagnosis_name': diagnosis_info['name'],
            'claim_amount': round(base_cost, 2),
            'expected_cost_min': diagnosis_info['cost_range'][0],
            'expected_cost_max': diagnosis_info['cost_range'][1],
            'biometric_verified': biometric_verified,
            'patient_present': patient_present,
            'weekend_claim': timestamp.weekday() >= 5,
            'after_hours_claim': timestamp.hour < 7 or timestamp.hour > 18,
            'emergency_case': emergency_case,
            'travel_distance_suspicious': travel_distance_suspicious,
            'provider_claims_today': int(doctor_profile['avg_claims_per_day']),
            'is_fraud': is_fraud,
            'fraud_type': fraud_type
        }

        data.append(claim)

    df = pd.DataFrame(data)
    df.loc[np.random.rand(len(df)) < 0.05, 'biometric_verified'] = None  # Add 5% missingness
    return df

# Attach to class
HealthcareFraudDetector.generate_synthetic_data = generate_synthetic_data
print("🔧 Synthetic data generation attached to HealthcareFraudDetector.")


# In[8]:


def generate_patient_population(n=5000):
    """Generate synthetic patient demographic and health data."""
    print(f"👥 Generating {n} synthetic patient profiles...")

    patient_population = []
    genders = ['Male', 'Female']
    locations = list(LOCATIONS_FACILITIES.keys())
    schemes = MEDICAL_SCHEMES

    for i in range(n):
        patient = {
            'patient_id': f"PAT_{i:05d}",
            'age': int(np.clip(np.random.normal(35, 15), 0, 90)),  # Age between 0–90
            'gender': np.random.choice(genders),
            'location': np.random.choice(locations),
            'medical_scheme': np.random.choice(schemes),
            'is_deceased': np.random.rand() < 0.03  # ~3% deceased
        }
        patient_population.append(patient)

    return patient_population


# In[9]:


# Create the detector instance
detector = HealthcareFraudDetector()

# Generate synthetic data
print("🚀 Starting data generation...")
df = detector.generate_synthetic_data(n_samples=5000)


#  ### Basic Data Analysis

# In[10]:


# === Basic Overview ===
print(f"✅ Generated {len(df)} Namibian healthcare claims")
print(f"   📊 Fraud count: {df['is_fraud'].sum()} ({df['is_fraud'].mean():.1%})")
print(f"   🏥 Facilities: {df['facility_name'].nunique()} in {df['facility_location'].nunique()} locations")
print(f"   👨‍⚕️ Providers: {df['doctor_id'].nunique()} doctors")
print(f"   💰 Claim amount range: NAD {df['claim_amount'].min():,.0f} – {df['claim_amount'].max():,.0f}")

# === Fraud Pattern Breakdown ===
fraud_patterns = df[df['is_fraud']]['fraud_type'].value_counts()
print(f"   🚨 Fraud Types Distribution: {dict(fraud_patterns)}")

# === Metadata Summary ===
print(f"\n📊 Dataset shape: {df.shape}")
print(f"📋 Columns: {list(df.columns)}")

# === Sample Rows ===
print("\n📋 Legitimate Claim Samples:")
print(df[df['is_fraud'] == False].head(3)[[
    'claim_id', 'patient_id', 'doctor_id', 'diagnosis_name', 
    'claim_amount', 'facility_location', 'fraud_type'
]])

print("\n🚨 Fraudulent Claim Samples:")
print(df[df['is_fraud'] == True].head(3)[[
    'claim_id', 'patient_id', 'doctor_id', 'diagnosis_name', 
    'claim_amount', 'facility_location', 'fraud_type'
]])

# === Aggregated Fraud Analysis ===
print("\n📈 BASIC DATA ANALYSIS")
print("=" * 50)

# Fraud rates by doctor type
print("\n👨‍⚕️ Fraud by Doctor Type:")
fraud_by_doctor = df.groupby(df['doctor_id'].str.contains('DR_X'))['is_fraud'].agg(['count', 'sum', 'mean'])
fraud_by_doctor.index = ['Regular Doctors', 'High-Risk Doctors (DR_X)']
print(fraud_by_doctor)

# Fraud rates by location
print("\n🗺️ Fraud by Facility Location:")
location_fraud = df.groupby('facility_location')['is_fraud'].agg(['count', 'sum', 'mean']).sort_values('mean', ascending=False)
print(location_fraud)

# Claim value distribution by fraud type
print("\n💰 Claim Amounts by Fraud Type:")
amount_by_fraud = df.groupby('fraud_type')['claim_amount'].agg(['count', 'mean', 'std']).round(2)
print(amount_by_fraud)


# In[9]:


# Basic analysis
print("📈 BASIC DATA ANALYSIS")
print("=" * 50)

# Fraud by doctor type
print("\n👨‍⚕️ Fraud by Doctor Type:")
fraud_by_doctor = df.groupby(df['doctor_id'].str.contains('DR_X'))['is_fraud'].agg(['count', 'sum', 'mean'])
fraud_by_doctor.index = ['Regular Doctors', 'High-Risk Doctors (DR_X)']
print(fraud_by_doctor)

# Fraud by location
print("\n🗺️ Fraud by Location:")
location_fraud = df.groupby('facility_location')['is_fraud'].agg(['count', 'sum', 'mean']).sort_values('mean', ascending=False)
print(location_fraud)

# Average claim amounts by fraud type
print("\n💰 Average Claim Amounts by Type:")
amount_by_fraud = df.groupby('fraud_type')['claim_amount'].agg(['count', 'mean', 'std']).round(2)
print(amount_by_fraud)


# In[13]:


# ===== END OF DATA GENERATION NOTEBOOK =====

# Save synthetic data to CSV
output_filename = 'namibian_healthcare_claims.csv'
df.to_csv(output_filename, index=False)
print(f"💾 Dataset successfully saved as '{output_filename}'")

# Optional: Load real Kaggle dataset here (if available and needed later)
combined_df = df.copy()
print("ℹ️ Using only synthetic data (no external dataset loaded)")

print("\n" + "="*60)
print("🎉 DATA GENERATION COMPLETE!")
print(f"📊 Total records generated: {len(df)}")
print(f"📁 Data saved to: {output_filename}")
print("➡️ Next: Open the model training notebook to train fraud detection models")
print("="*60)

