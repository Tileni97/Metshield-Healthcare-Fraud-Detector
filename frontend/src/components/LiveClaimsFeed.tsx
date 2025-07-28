import { useState, useEffect, useRef } from "react";
import { useLiveFeed } from "@/hooks/useApi";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { formatDistanceToNow } from "date-fns";
import { AlertTriangle } from "lucide-react";
import { ClaimDetailModal } from "@/components/ClaimDetailModal";
import { RiskBadge } from "@/components/RiskBadge";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import alertSound from "@/assets/confident-543.mp3";

const formatCurrency = (amount: number) =>
  `N$${new Intl.NumberFormat("en-NA", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount)}`;

export function LiveClaimsFeed() {
  const {
    data = [],
    isConnected = false,
    connect = () => {},
    error = null,
  } = useLiveFeed() || {};

  const [selectedClaimId, setSelectedClaimId] = useState<string | null>(null);
  const [showHighRiskOnly, setShowHighRiskOnly] = useState(false);
  const feedRef = useRef<HTMLDivElement>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const lastAlertedClaimIdRef = useRef<string | null>(null);

  // Initialize audio + unlock autoplay
  useEffect(() => {
    connect();

    const sound = new Audio(alertSound);
    sound.preload = "auto";
    sound.volume = 0.4;
    sound.muted = true;
    audioRef.current = sound;

    const unlock = () => {
      sound
        .play()
        .then(() => {
          sound.pause();
          sound.currentTime = 0;
          sound.muted = false;
          window.removeEventListener("click", unlock);
        })
        .catch(() => {});
    };

    window.addEventListener("click", unlock);
  }, [connect]);

  // Play sound + toast on high-risk or critical
  useEffect(() => {
    const latestClaim = data.at(-1);
    if (
      latestClaim &&
      ["HIGH", "CRITICAL"].includes(latestClaim.risk_level)
    ) {
      feedRef.current?.scrollTo({
        top: feedRef.current.scrollHeight,
        behavior: "smooth",
      });

      if (lastAlertedClaimIdRef.current !== latestClaim.claim_id) {
        toast.warning(`⚠️ ${latestClaim.risk_level} risk claim`, {
          description: `Claim ID: ${latestClaim.claim_id}`,
          duration: 5000,
        });

        try {
          const sound = audioRef.current;
          if (sound) {
            sound.pause();
            sound.currentTime = 0;
            sound.volume = 0.4;
            sound.play().catch((e) => {
              console.warn("🔇 Sound blocked:", e);
            });
          }
        } catch (e) {
          console.warn("🔇 Audio error:", e);
        }

        lastAlertedClaimIdRef.current = latestClaim.claim_id;
      }
    }
  }, [data]);

  const visibleData = showHighRiskOnly
    ? data.filter((c) => ["HIGH", "CRITICAL"].includes(c.risk_level))
    : data;

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between mb-2">
        <h2 className="text-xl font-semibold text-methealth-text">
          Real-Time Claim Activity
        </h2>
        <Badge
          className={`text-xs ${
            isConnected
              ? "bg-green-100 text-green-700"
              : "bg-red-100 text-red-700"
          }`}
        >
          {isConnected ? "Connected" : "Disconnected"}
        </Badge>
      </div>

      {/* High risk filter toggle */}
      <div className="flex items-center gap-2">
        <Switch
          id="high-risk-toggle"
          checked={showHighRiskOnly}
          onCheckedChange={setShowHighRiskOnly}
        />
        <Label htmlFor="high-risk-toggle">Show High-Risk Claims Only</Label>
      </div>

      {error && (
        <div className="text-sm text-red-600 flex items-center gap-2">
          <AlertTriangle className="h-4 w-4" />
          <span>{error}</span>
        </div>
      )}

      {visibleData.length === 0 ? (
        <p className="text-muted-foreground text-sm">
          Waiting for live claim activity...
        </p>
      ) : (
        <div
          ref={feedRef}
          className="space-y-3 max-h-[600px] overflow-y-auto"
        >
          {visibleData.map((claim: any) => {
            const claimAmount = claim.claim_amount || claim.amount || 0;
            const fraudProb =
              claim.fraud_probability ?? (claim.is_fraud ? 0.8 : 0.2);
            const patientAge = claim.patient_age ?? "N/A";
            const patientGender = claim.patient_gender ?? "N/A";
            const riskLevel = claim.risk_level ?? "UNKNOWN";
            const timestamp = claim.timestamp
              ? formatDistanceToNow(new Date(claim.timestamp), {
                  addSuffix: true,
                })
              : "just now";

            return (
              <Card
                key={claim.claim_id}
                className={cn(
                  "p-4 cursor-pointer hover:shadow-md transition border-l-4",
                  riskLevel === "CRITICAL"
                    ? "border-red-700 bg-red-100 animate-pulse"
                    : riskLevel === "HIGH"
                    ? "border-red-500 bg-red-50"
                    : riskLevel === "MEDIUM"
                    ? "border-yellow-400 bg-yellow-50"
                    : "border-green-300 bg-green-50"
                )}
                onClick={() => setSelectedClaimId(claim.claim_id)}
              >
                <div className="flex justify-between items-center">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">
                      Claim ID:{" "}
                      <span className="font-semibold text-methealth-primary">
                        {claim.claim_id}
                      </span>
                    </p>
                    <p className="text-sm text-methealth-text">
                      Amount: {formatCurrency(claimAmount)}
                      {patientAge !== "N/A" && ` • Age: ${patientAge}`}
                      {patientGender !== "N/A" && ` • Gender: ${patientGender}`}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1">
                      {timestamp}
                    </p>
                  </div>
                  <div className="text-right space-y-1">
                    <RiskBadge level={riskLevel} />
                    <p className="text-sm font-semibold text-fraud-alert">
                      {(fraudProb * 100).toFixed(1)}%
                    </p>
                    <p className="text-xs text-muted-foreground">
                      Fraud Probability
                    </p>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {/* Claim modal */}
      <ClaimDetailModal
        claimId={selectedClaimId}
        open={!!selectedClaimId}
        onClose={() => setSelectedClaimId(null)}
      />
    </div>
  );
}
