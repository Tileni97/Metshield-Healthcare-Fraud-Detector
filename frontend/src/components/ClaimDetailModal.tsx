// components/ClaimDetailModal.tsx
import React from "react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { useQuery } from "@tanstack/react-query"
import { getClaimDetails } from "@/hooks/useApi"
import { Loader2 } from "lucide-react"

interface ClaimDetailModalProps {
  claimId: string | null
  open: boolean
  onClose: () => void
}

export const ClaimDetailModal: React.FC<ClaimDetailModalProps> = ({
  claimId,
  open,
  onClose,
}) => {
  const { data, isLoading, error } = useQuery({
    queryKey: ["claimDetails", claimId],
    queryFn: () => getClaimDetails(claimId!),
    enabled: !!claimId,
  })

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Claim Details</DialogTitle>
        </DialogHeader>

        {isLoading ? (
          <div className="flex justify-center py-10">
            <Loader2 className="animate-spin w-6 h-6" />
          </div>
        ) : error ? (
          <p className="text-red-500">Failed to load claim details</p>
        ) : !data ? (
          <p className="text-sm text-muted-foreground">No data available.</p>
        ) : (
          <div className="space-y-3">
            <p>
              <strong>Claim ID:</strong> {data.claim_id}
            </p>
            <p>
              <strong>Amount:</strong> N${data.claim_details.amount.toLocaleString()}
            </p>
            <p>
              <strong>Diagnosis Code:</strong> {data.claim_details.diagnosis_code}
            </p>
            <p>
              <strong>Scheme:</strong> {data.claim_details.medical_scheme}
            </p>
            <p>
              <strong>Timestamp:</strong>{" "}
              {new Date(data.claim_details.timestamp).toLocaleString()}
            </p>

            <hr />

            <p>
              <strong>Patient:</strong> {data.patient_info.name}, Age{" "}
              {data.patient_info.age}, {data.patient_info.gender}
            </p>
            <p>
              <strong>Provider:</strong> {data.provider_info.facility} -{" "}
              {data.provider_info.doctor}
            </p>

            <hr />

            <p>
              <strong>Fraud Risk:</strong> {data.fraud_analysis.risk_level}
              {data.fraud_analysis.is_fraud && (
                <span className="ml-2 text-red-600 font-semibold">
                  (Flagged as Fraud)
                </span>
              )}
            </p>
            {data.fraud_analysis.flags?.length > 0 && (
              <ul className="list-disc pl-5">
                {data.fraud_analysis.flags.map((flag: string, idx: number) => (
                  <li key={idx}>{flag}</li>
                ))}
              </ul>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
