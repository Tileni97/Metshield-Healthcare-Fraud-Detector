import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";

interface Props {
  open: boolean;
  stat: string | null;
  stats: any;
  onClose: () => void;
}

export function OverviewStatsModal({ open, stat, stats, onClose }: Props) {
  const getStatDescription = () => {
    switch (stat) {
      case "total_claims_today":
        return "Total number of claims submitted and processed by the system today.";
      case "fraud_detected_today":
        return "Number of claims flagged as potential fraud and requiring review.";
      case "fraud_rate_today":
        return `Today's fraud detection rate is ${(stats?.fraud_rate_today ?? 0).toFixed(2)}%. This is the ratio of flagged claims to total claims.`;
      default:
        return "No details available.";
    }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="capitalize">{stat?.replace(/_/g, " ")}</DialogTitle>
        </DialogHeader>
        <div className="py-2 text-muted-foreground">{getStatDescription()}</div>
      </DialogContent>
    </Dialog>
  );
}
