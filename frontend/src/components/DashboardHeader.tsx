import { SidebarTrigger } from "@/components/ui/sidebar"

export function DashboardHeader() {
  const userInitials = "MT" // Replace with dynamic initials if you add auth

  return (
    <header
      className="flex items-center justify-between px-6 py-4 shadow-md bg-methealth-primary text-methealth-white"
      role="banner"
    >
      {/* Left: Sidebar + Page Info */}
      <div className="flex items-center gap-4">
        <SidebarTrigger
          className="text-methealth-white hover:bg-methealth-secondary/20"
          aria-label="Toggle sidebar"
        />
        <div>
          <h1 className="text-xl font-bold">Claims Dashboard</h1>
          <p className="text-sm text-methealth-accent">Real-Time Fraud Detection & Monitoring</p>
        </div>
      </div>

      {/* Right: User info */}
      <div className="flex items-center gap-4">
        <div className="text-right">
          <p className="text-sm text-methealth-accent">Welcome back</p>
          <p className="font-medium">Claims Review Team</p>
        </div>
        <div
          className="h-8 w-8 rounded-full bg-methealth-accent flex items-center justify-center"
          aria-label="User initials"
        >
          <span className="text-xs font-bold text-methealth-primary">{userInitials}</span>
        </div>
      </div>
    </header>
  )
}
