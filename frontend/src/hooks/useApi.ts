// \hooks\useApi.ts

import { useState, useRef, useCallback, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import type {
  ClaimRequest,
  FeedbackRequest,
  StatsResponse,
  ClaimDetailsResponse, 
} from "@/services/api";
import { ApiService } from "@/services/api";




// --- Types ---
interface Claim {
  claim_id: string;
  claim_amount: number;
  timestamp: string;
  patient_age?: number;
  patient_gender?: string;
  risk_level: string;
  fraud_probability: number;
  is_fraud?: boolean;
}

interface Stats {
  total_claims: number;
  total_flagged: number;
  total_amount: number;
  most_common_procedure: string;
}

// --- Query Keys ---
export const queryKeys = {
  health: ['health'] as const,
  stats: ['stats'] as const,
  claimDetails: (claimId: string) => ['claim-details', claimId] as const,
  connectivity: ['connectivity'] as const,
};

// --- Queries ---
export const useHealth = () =>
  useQuery({
    queryKey: queryKeys.health,
    queryFn: ApiService.getHealth,
    refetchInterval: 30000,
    retry: 3,
    staleTime: 20000,
  });

  export const useStats = () =>
    useQuery<StatsResponse>({
      queryKey: queryKeys.stats,
      queryFn: ApiService.getStats,
      refetchInterval: 30000, // every 30s
      retry: 2,
      staleTime: 5000,
    });

export const useClaimDetails = (claimId: string | null) =>
  useQuery({
    queryKey: queryKeys.claimDetails(claimId || ""),
    queryFn: () => ApiService.getClaimDetails(claimId!),
    enabled: !!claimId,
    retry: 2,
  });

export const useApiConnectivity = () =>
  useQuery({
    queryKey: queryKeys.connectivity,
    queryFn: ApiService.checkConnectivity,
    refetchInterval: 30000,
    retry: 1,
    staleTime: 25000,
  });

// --- Mutations ---
export const useFraudDetection = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (claim: ClaimRequest) => ApiService.detectFraud(claim),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.stats });
    },
    onError: (error) => {
      console.error("Fraud detection failed:", error);
    },
  });
};

export async function getClaimDetails(claimId: string): Promise<ClaimDetailsResponse> {
  return await ApiService.getClaimDetails(claimId);
}




export const useFeedbackSubmission = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      claimId,
      isActuallyFraud,
      reviewerNotes,
    }: {
      claimId: string;
      isActuallyFraud: boolean;
      reviewerNotes?: string;
    }) => ApiService.submitFeedback(claimId, isActuallyFraud, reviewerNotes),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.claimDetails(variables.claimId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.stats });
    },
  });
};

// --- Dashboard Combined Hook ---
export const useDashboardData = () => {
  const healthQuery = useHealth();
  const statsQuery = useStats();
  const connectivityQuery = useApiConnectivity();

  return {
    health: healthQuery.data,
    stats: statsQuery.data,
    isConnected: connectivityQuery.data,
    isLoading:
      healthQuery.isLoading || statsQuery.isLoading || connectivityQuery.isLoading,
    isError:
      healthQuery.isError || statsQuery.isError || connectivityQuery.isError,
    error: healthQuery.error || statsQuery.error || connectivityQuery.error,
    refetch: () => {
      healthQuery.refetch();
      statsQuery.refetch();
      connectivityQuery.refetch();
    },
  };
};

// --- Form State Management ---
export const useFraudDetectionForm = () => {
  const [formData, setFormData] = useState<Partial<ClaimRequest>>({
    patient_gender: "M",
    medical_scheme: "PSEMAS",
    biometric_verified: false,
    patient_present: true,
    patient_deceased: false,
    emergency_case: false,
    weekend_claim: false,
    after_hours_claim: false,
    travel_distance_suspicious: false,
    submission_source: "web_ui",
  });

  const updateField = useCallback((field: keyof ClaimRequest, value: any) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  }, []);

  const resetForm = useCallback(() => {
    setFormData({
      patient_gender: "M",
      medical_scheme: "PSEMAS",
      biometric_verified: false,
      patient_present: true,
      patient_deceased: false,
      emergency_case: false,
      weekend_claim: false,
      after_hours_claim: false,
      travel_distance_suspicious: false,
      submission_source: "web_ui",
    });
  }, []);

  const isValidForm = useCallback(() => {
    const required = [
      "claim_id",
      "patient_id",
      "doctor_id",
      "patient_age",
      "diagnosis_code",
      "claim_amount",
      "facility_location",
    ];
    return required.every((field) => {
      const value = formData[field as keyof ClaimRequest];
      return value !== undefined && value !== null && value !== "";
    });
  }, [formData]);

  return {
    formData,
    updateField,
    resetForm,
    isValidForm,
  };
};

// --- SSE Live Feed Hook ---
export const useLiveFeed = () => {
  const [data, setData] = useState<Claim[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  const connect = useCallback(() => {
    if (eventSourceRef.current) return;

    const source = ApiService.createLiveFeed();
    eventSourceRef.current = source;

    source.onopen = () => {
      setIsConnected(true);
      setError(null);
      console.log("[SSE] Connected");
    };

    source.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data);
        console.log("[SSE] Live event:", parsed); // ⬅ Add this
        setData((prev) => [parsed, ...prev.slice(0, 49)]);
      } catch (err) {
        console.error("[SSE] Failed to parse SSE message", err);
      }
    };
    

    source.onerror = (err) => {
      console.error("[SSE] Error:", err);
      setError("Live feed connection lost.");
      setIsConnected(false);
      source.close();
      eventSourceRef.current = null;
    };
  }, []);

  const disconnect = useCallback(() => {
    eventSourceRef.current?.close();
    eventSourceRef.current = null;
    setIsConnected(false);
  }, []);

  const reconnect = useCallback(() => {
    disconnect();
    connect();
  }, [connect, disconnect]);

  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  return {
    data,
    isConnected,
    error,
    connect,
    disconnect,
    reconnect,
  };
};
