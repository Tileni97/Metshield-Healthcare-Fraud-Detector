import { useState } from "react";
import { Card } from "@/components/ui/card";
import { FileText, Shield, TrendingUp, Clock } from "lucide-react";
import { useStats } from "@/hooks/useApi";
import { OverviewStatsModal } from "@/components/OverviewStatsModal";

export function OverviewPanel() {
  const { data: stats, isLoading } = useStats();
  const [selectedStat, setSelectedStat] = useState<string | null>(null);

  const handleClick = (stat: string) => setSelectedStat(stat);
  const closeModal = () => setSelectedStat(null);

  return (
    <>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 p-6">
        <Card
          className="p-6 border-l-4 border-l-methealth-primary cursor-pointer hover:shadow-lg transition"
          onClick={() => handleClick("total_claims_today")}
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-muted-foreground">Total Claims Processed</p>
              <p className="text-3xl font-bold text-methealth-text">
                {isLoading ? "..." : stats?.total_claims_today ?? "--"}
              </p>
              <p className="text-xs text-muted-foreground mt-1">Today</p>
            </div>
            <div className="h-12 w-12 rounded-lg bg-methealth-accent flex items-center justify-center">
              <FileText className="h-6 w-6 text-methealth-primary" />
            </div>
          </div>
        </Card>

        <Card
          className="p-6 border-l-4 border-l-fraud-alert cursor-pointer hover:shadow-lg transition"
          onClick={() => handleClick("fraud_detected_today")}
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-muted-foreground">Fraud Cases Detected</p>
              <p className="text-3xl font-bold text-fraud-alert">
                {isLoading ? "..." : stats?.fraud_detected_today ?? "--"}
              </p>
              <p className="text-xs text-muted-foreground mt-1">Requires Review</p>
            </div>
            <div className="h-12 w-12 rounded-lg bg-fraud-alert-bg flex items-center justify-center">
              <Shield className="h-6 w-6 text-fraud-alert" />
            </div>
          </div>
        </Card>

        <Card
          className="p-6 border-l-4 border-l-methealth-secondary cursor-pointer hover:shadow-lg transition"
          onClick={() => handleClick("fraud_rate_today")}
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-muted-foreground">Fraud Detection Rate</p>
              <p className="text-3xl font-bold text-methealth-text">
                {isLoading ? "..." : `${(stats?.fraud_rate_today ?? 0).toFixed(2)}%`}
              </p>
              <p className="text-xs text-safe-indicator mt-1">↓ 0.3% from yesterday</p>
            </div>
            <div className="h-12 w-12 rounded-lg bg-methealth-accent flex items-center justify-center">
              <TrendingUp className="h-6 w-6 text-methealth-secondary" />
            </div>
          </div>
        </Card>

        <Card className="p-6 border-l-4 border-l-muted-foreground">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-muted-foreground">Last Updated</p>
              <p className="text-lg font-bold text-methealth-text">
                {new Date().toLocaleTimeString([], {
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </p>
              <p className="text-xs text-muted-foreground mt-1">Auto-refresh: 30s</p>
            </div>
            <div className="h-12 w-12 rounded-lg bg-muted flex items-center justify-center">
              <Clock className="h-6 w-6 text-muted-foreground" />
            </div>
          </div>
        </Card>
      </div>

      {/* Modal for Stat Detail */}
      <OverviewStatsModal
        open={!!selectedStat}
        stat={selectedStat}
        stats={stats}
        onClose={closeModal}
      />
    </>
  );
}
