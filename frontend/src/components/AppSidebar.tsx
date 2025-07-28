import { NavLink } from "react-router-dom";
import {
  BarChart3,
  Shield,
  FileText,
  Settings,
  Activity,
} from "lucide-react";

import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from "@/components/ui/sidebar";

const navItems = [
  { title: "Dashboard", path: "/", icon: BarChart3 },
  { title: "Real-Time Monitor", path: "/real-time", icon: Activity },
  { title: "All Claims", path: "/claims", icon: FileText },
  { title: "Admin Settings", path: "/settings", icon: Settings },
];

export function AppSidebar() {
  const { state } = useSidebar();
  const collapsed = state === "collapsed";

  const getNavClass = ({ isActive }: { isActive: boolean }) =>
    isActive
      ? "bg-methealth-primary text-white font-semibold rounded-md px-3 py-2"
      : "text-black hover:text-methealth-primary hover:bg-gray-200 px-3 py-2 rounded-md transition";

  return (
    <Sidebar
      className={`${
        collapsed ? "w-14" : "w-64"
      } bg-gray-100 border-r border-gray-300 shadow-sm`}
      collapsible="icon"
    >
      <SidebarContent>
        {/* Logo / Title */}
        <div className="flex items-center gap-2 p-4 border-b border-gray-300">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-methealth-primary">
            <Shield className="h-4 w-4 text-white" />
          </div>
          {!collapsed && (
            <div className="flex flex-col">
              <span className="text-sm font-bold text-black">MetShield</span>
              <span className="text-xs text-gray-600">Fraud Detection System</span>
            </div>
          )}
        </div>

        {/* Navigation */}
        <SidebarGroup className="px-0">
          <SidebarGroupLabel className="px-4 py-2 text-xs font-semibold text-gray-700 uppercase tracking-wide">
            {!collapsed && "Navigation"}
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {navItems.map((item) => (
                <SidebarMenuItem key={item.path}>
                  <SidebarMenuButton asChild className="mx-2">
                    <NavLink to={item.path} end className={getNavClass}>
                      <item.icon className="h-4 w-4" />
                      {!collapsed && (
                        <span className="ml-2 text-black">{item.title}</span>
                      )}
                    </NavLink>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
    </Sidebar>
  );
}
