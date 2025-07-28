// \services\api.ts

import axios from 'axios';


// ------------------- Types -------------------
export interface ClaimDetail {
  claim_id: string;
  claim_details: {
    amount: number;
    diagnosis_code: string;
    medical_scheme: string;
    timestamp: string;
  };
  patient_info: {
    name: string;
    age: number;
    gender: string;
  };
  provider_info: {
    facility: string;
    doctor: string;
  };
  fraud_analysis: {
    risk_level: string;
    is_fraud: boolean;
    flags: string[];
  };
}

export interface ClaimRequest {
  claim_id: string;
  patient_id: string;
  doctor_id: string;
  patient_age: number;
  patient_gender: string;
  medical_scheme: string;
  diagnosis_code: string;
  claim_amount: number;
  facility_location: string;
  patient_location?: string;
  biometric_verified?: boolean;
  patient_present?: boolean;
  patient_deceased?: boolean;
  emergency_case?: boolean;
  weekend_claim?: boolean;
  after_hours_claim?: boolean;
  travel_distance_suspicious?: boolean;
  timestamp?: string;
  submission_source?: string;
}

export interface FraudResponse {
  claim_id: string;
  is_fraud: boolean;
  fraud_probability: number;
  risk_level: 'MINIMAL' | 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  confidence_score: number;
  flags: string[];
  processing_time_ms: number;
  timestamp: string;
  from_cache: boolean;
  recommended_action?: string;
  review_required?: boolean;
}

export interface HealthResponse {
  status: string;
  api: string;
  timestamp: string;
  uptime_seconds: number;
  services: Record<string, string>;
  version?: string;
}

export interface StatsResponse {
  total_claims_today: number;
  fraud_detected_today: number;
  fraud_rate_today: number;
  cache_hit_rate: number;
  average_processing_time_ms: number;
  high_risk_claims_today: number;
  system_load: number;
  active_alerts: number;
  timestamp: string;
  top_risk_providers?: Array<{
    provider_id: string;
    risk_score: number;
  }>;
}



export interface ClaimDetailsResponse {
  claim_id: string;
  patient_info: Record<string, any>;
  provider_info: Record<string, any>;
  claim_details: Record<string, any>;
  fraud_analysis: Record<string, any>;
  history: Array<Record<string, any>>;
  related_claims: string[];
  feedback?: Record<string, any>;
}

export interface FeedbackRequest {
  claim_id: string;
  is_actually_fraud: boolean;
  reviewer_id?: string;
  reviewer_notes?: string;
  confidence_in_decision?: number;
}

export interface Claim {
  claim_id: string;
  patient_id: string;
  doctor_id: string;
  patient_age: number;
  patient_gender: string;
  medical_scheme: string;
  diagnosis_code: string;
  claim_amount: number;
  facility_location: string;
  patient_location: string;
  submission_timestamp: string;
  is_fraud: boolean;
  fraud_probability: number;
  risk_level: "LOW" | "MEDIUM" | "HIGH";
  prediction_timestamp: string;
}


// ------------------- API Setup -------------------
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

api.interceptors.request.use(
  (config) => {
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => Promise.reject(error)
);

api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

// ------------------- API Service -------------------
export class ApiService {
  static async getRoot(): Promise<any> {
    const res = await api.get('/');
    return res.data;
  }

  static async detectFraud(claim: ClaimRequest): Promise<FraudResponse> {
    const res = await api.post('/api/v1/detect-fraud', claim);
    return res.data;
  }

  static async getHealth(): Promise<HealthResponse> {
    const res = await api.get('/api/v1/health');
    return res.data;
  }

  static async getStats(): Promise<StatsResponse> {
    const res = await api.get('/api/v1/stats');
    return res.data;
  }

  static createLiveFeed(): EventSource {
    return new EventSource(`${API_BASE_URL}/api/v1/live-feed`);
  }

  static async submitFeedback(
    claimId: string,
    isActuallyFraud: boolean,
    reviewerNotes?: string
  ): Promise<any> {
    const res = await api.post('/api/v1/feedback', null, {
      params: {
        claim_id: claimId,
        is_actually_fraud: isActuallyFraud,
        reviewer_notes: reviewerNotes,
      },
    });
    return res.data;
  }

  static async getClaimDetails(claimId: string): Promise<ClaimDetailsResponse> {
    const res = await api.get(`/api/v1/claims/${claimId}`);
    return res.data;
  }

  static async checkConnectivity(): Promise<boolean> {
    try {
      await this.getRoot();
      return true;
    } catch (error) {
      console.error('API connectivity check failed:', error);
      return false;
    }
  }

  static async getAllClaims(): Promise<Claim[]> {
    const res = await api.get('/api/v1/claims');
    return res.data;
  }
}
