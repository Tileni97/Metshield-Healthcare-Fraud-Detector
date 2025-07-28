import { OverviewPanel } from "@/components/OverviewPanel";
import { LiveClaimsFeed } from "@/components/LiveClaimsFeed";

const Dashboard = () => {
  return (
    <div className="space-y-6">
      <OverviewPanel />
      <LiveClaimsFeed />
    </div>
  );
};

export default Dashboard;
