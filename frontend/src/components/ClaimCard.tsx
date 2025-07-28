// src/components/ClaimCard.tsx
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { AlertTriangle, CheckCircle, FileText } from "lucide-react";
import { cn } from "@/lib/utils";

interface ClaimCardProps {
  patientId: string;
  procedureCode: string;
  amount: number;
  timestamp: string;
  isFraudFlagged: boolean;
  riskLevel?: "low" | "medium" | "high" | "critical";
}

export function ClaimCard({
  patientId,
  procedureCode,
  amount,
  timestamp,
  isFraudFlagged,
  riskLevel = "low",
}: ClaimCardProps) {
  const formatAmount = (value: number) =>
    new Intl.NumberFormat("en-NA", {
      style: "currency",
      currency: "NAD",
    }).format(value);

  const formatTime = (timeStr: string) =>
    new Date(timeStr).toLocaleTimeString("en-NA", {
      hour: "2-digit",
      minute: "2-digit",
    });

  const getRiskStyles = () => {
    if (!isFraudFlagged) {
      return {
        card: "border-l-green-400 bg-green-50",
        badge: "bg-green-200 text-green-800",
        pulse: false,
      };
    }

    switch (riskLevel) {
      case "critical":
        return {
          card: "border-l-red-700 bg-red-100 animate-pulse",
          badge: "bg-red-700 text-white font-bold",
          pulse: true,
        };
      case "high":
        return {
          card: "border-l-red-500 bg-red-50",
          badge: "bg-red-500 text-white",
          pulse: true,
        };
      case "medium":
        return {
          card: "border-l-yellow-500 bg-yellow-50",
          badge: "bg-yellow-500 text-black",
          pulse: false,
        };
      case "low":
      default:
        return {
          card: "border-l-green-400 bg-green-50",
          badge: "bg-green-200 text-green-800",
          pulse: false,
        };
    }
  };

  const { card, badge } = getRiskStyles();

  return (
    <Card
      className={cn(
        "p-4 transition-all duration-200 hover:shadow-md border-l-4",
        card
      )}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1">
          {/* Header */}
          <div className="flex items-center gap-3 mb-3">
            <div className="flex items-center gap-2">
              <FileText className="h-4 w-4 text-muted-foreground" />
              <span className="font-semibold text-methealth-text">
                Patient: {patientId}
              </span>
            </div>
            <Badge className={cn("text-xs border-0", badge)}>
              {isFraudFlagged ? (
                <>
                  <AlertTriangle className="h-3 w-3 mr-1" />
                  {riskLevel?.toUpperCase()} RISK
                </>
              ) : (
                <>
                  <CheckCircle className="h-3 w-3 mr-1" />
                  VERIFIED
                </>
              )}
            </Badge>
          </div>

          {/* Claim Details */}
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-muted-foreground">Procedure Code</p>
              <p className="font-medium text-methealth-text">{procedureCode}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Amount</p>
              <p className="font-bold text-lg text-methealth-text">
                {formatAmount(amount)}
              </p>
            </div>
          </div>

          {/* Timestamp */}
          <p className="text-xs text-muted-foreground mt-3">
            Submitted at {formatTime(timestamp)}
          </p>
        </div>

        {/* Action Button */}
        {isFraudFlagged && (
          <div className="ml-4">
            <Button
              size="sm"
              className="bg-methealth-primary hover:bg-methealth-secondary text-white"
            >
              Create Investigation
            </Button>
          </div>
        )}
      </div>
    </Card>
  );
}
