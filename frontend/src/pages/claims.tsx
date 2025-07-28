// src/pages/Claims.tsx

import { useQuery } from '@tanstack/react-query';
import { getAllClaims, Claim } from '@/services/api'; // ✅ Correct path
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';

// ✅ Currency formatter for N$
const NAD = new Intl.NumberFormat('en-NA', {
  style: 'currency',
  currency: 'NAD',
  minimumFractionDigits: 2,
});

export default function ClaimsPage() {
  const { data, isLoading, isError } = useQuery<Claim[]>({
    queryKey: ['claims'],
    queryFn: getAllClaims,
  });

  return (
    <div className="space-y-6 p-4">
      <h1 className="text-2xl font-bold">📑 All Claims</h1>

      {isLoading && (
        <div className="space-y-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-24 w-full rounded-lg" />
          ))}
        </div>
      )}

      {isError && (
        <p className="text-red-600">Failed to load claims. Please try again.</p>
      )}

      {!isLoading && data?.length === 0 && (
        <p className="text-muted-foreground">No claims found.</p>
      )}

      <div className="grid gap-4">
        {data?.map((claim) => (
          <Card key={claim.claim_id}>
            <CardContent className="space-y-1 py-4">
              <div className="flex justify-between items-center">
                <div>
                  <p className="font-semibold">{claim.patient_name ?? 'Unknown Patient'}</p>
                  <p className="text-sm text-gray-500">{claim.provider ?? 'Unknown Provider'}</p>
                  <p className="text-sm text-muted-foreground">{claim.service ?? '—'}</p>
                </div>
                <div className="text-right space-y-1">
                  <p className="text-base font-medium">
                    {NAD.format(claim.amount ?? 0)}
                  </p>
                  <Badge
                    variant={claim.is_fraud ? 'destructive' : 'outline'}
                    className="text-sm"
                  >
                    {claim.is_fraud ? 'Fraud' : 'Legit'}
                  </Badge>
                  <p className="text-xs text-gray-400">
                    {new Date(claim.timestamp).toLocaleString()}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
