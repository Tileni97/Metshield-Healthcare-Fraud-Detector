import { useQuery } from '@tanstack/react-query';
import { ApiService } from '@/services/api';
import { Skeleton } from '@/components/ui/skeleton';
import { ClaimCard } from '@/components/ClaimCard';
import type { Claim } from '@/services/api';

const AllClaims = () => {
  const { data, isLoading, isError } = useQuery<Claim[]>({
    queryKey: ['claims'],
    queryFn: ApiService.getAllClaims,
  });

  return (
    <div className="p-4 space-y-6">
      <h1 className="text-2xl font-bold">📄 All Claims</h1>

      {isLoading && (
        <div className="space-y-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-24 w-full rounded-xl" />
          ))}
        </div>
      )}

      {isError && (
        <div className="text-red-500">Failed to load claims. Please try again.</div>
      )}

      {!isLoading && data?.length === 0 && (
        <div className="text-muted-foreground">No claims available yet.</div>
      )}

      <div className="space-y-4">
        {data?.map((claim) => (
          <ClaimCard
            key={claim.claim_id}
            patientId={claim.patient_id}
            procedureCode={claim.diagnosis_code}
            amount={claim.claim_amount}
            timestamp={claim.submission_timestamp}
            isFraudFlagged={claim.is_fraud}
            riskLevel={claim.risk_level.toLowerCase() as 'low' | 'medium' | 'high'}
          />
        ))}
      </div>
    </div>
  );
};

export default AllClaims;
