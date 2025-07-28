# MetShield – Healthcare Fraud Detection System 🛡️💡

MetShield is a real-time, AI-powered fraud detection system built during the **Methealth Hack4Health Hackathon 2025** in Windhoek, Namibia. Our project placed **2nd out of 5 finalist teams**, tackling real-world healthcare fraud using modern machine learning and streaming technologies.

It uses a trained machine learning model and real-time Redis streams to identify high-risk medical claims as they occur. Featuring a React dashboard, FastAPI backend, and Freshdesk integration, it’s designed to support internal insurance teams in detecting and responding to healthcare fraud quickly and accurately.

---

## 🚀 Problem Statement

Health insurance fraud is a significant issue in Namibia, resulting in millions lost annually and delayed care for patients. Manual claim review processes are slow and prone to error. There’s a need for an intelligent system that can **automatically flag suspicious medical claims in real time**.

---

## 🧠 Our Solution

We built **MetShield**, an end-to-end fraud detection platform with the following features:

- ✅ **ML-powered classification** of claims into Low, Medium, High, and Critical risk
- 📡 **Real-time event streaming** using **Redis** to simulate live claim activity
- 📊 **Interactive dashboard** for internal staff to monitor claims
- 🚨 **Automated ticket escalation** to **Freshdesk** for high-risk fraud alerts
- 🔄 **Synthetic data generation** for continuous training and testing

---

## 🛠️ Tech Stack

| Layer        | Tools Used                                     |
|--------------|------------------------------------------------|
| Frontend     | React.js, Tailwind CSS                         |
| Backend      | FastAPI (Python), Redis Pub/Sub, PostgreSQL    |
| ML Model     | Scikit-learn, Pandas, Joblib                   |
| DevOps       | Docker, Git, GitHub                            |
| 3rd-party    | Freshdesk API (ticket automation)              |

---

## 🔍 Features

- 🧬 Synthetic data streaming (`synthetic_claim_streamer.py`)
- 🧠 Trained fraud detection ML model (`fraud_model.joblib`)
- 📺 Real-time Live Claims Feed with fraud risk visualization
- 📨 Freshdesk integration for critical claims
- 📂 Admin panel for reviewing historical claims

---

## 📸 Screenshots

### 🔍 Real-Time Dashboard Overview  
Shows fraud risk levels, stats, and live claims stream in a visual, intuitive layout.  
![Dashboard](https://github.com/Tileni97/Metshield-Healthcare-Fraud-Detector/blob/f72f8477bc5ff0c953b20503293a76a3667712c1/Dasboard2.png?raw=true)

---

### 📂 Historical Claims Log  
All submitted claims, tagged by risk level, doctor, patient, and location.  
![Claims Log](https://github.com/Tileni97/Metshield-Healthcare-Fraud-Detector/blob/f72f8477bc5ff0c953b20503293a76a3667712c1/allClaimsGH.png?raw=true)

---

### 🧾 Automated Freshdesk Escalation  
High and critical-risk claims are sent directly to Freshdesk for internal investigation.  
![Freshdesk Ticket](https://github.com/Tileni97/Metshield-Healthcare-Fraud-Detector/blob/f72f8477bc5ff0c953b20503293a76a3667712c1/Freshdesk.png?raw=true)

---

## 👥 Team

Built with passion by a group of student innovators from Namibia:

- Tileni Hango – Machine Learning & System Design  
- Tileni Hango – Backend & API Integration  
- Leo Amwaalwa – Frontend & UI/UX  


---

## 🏁 Getting Started

```bash
# Clone the repo
git clone https://github.com/Tileni97/metshield-Healthcare-Fraud-Detector.git
cd metshield-Healthcare-Fraud-Detector

# Backend setup
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend setup
cd frontend
npm install
npm run dev

🙌 Acknowledgements
Thanks to Methealth Namibia, MTC Namibia, Namibia Medical Care, and NUST for supporting young tech talent.
Special shout-out to the judges and facilitators of Hack4Health 2025.
