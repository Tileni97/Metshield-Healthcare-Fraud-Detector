// src/components/RiskBadge.tsx
import React from "react";
import { cn } from "@/lib/utils";

export type RiskLevel = "MINIMAL" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

const riskColors: Record<RiskLevel, string> = {
  MINIMAL: "bg-gray-300 text-black",
  LOW: "bg-green-500 text-white",
  MEDIUM: "bg-yellow-500 text-black",
  HIGH: "bg-red-500 text-white animate-pulse",
  CRITICAL: "bg-red-700 text-white animate-pulse font-bold",
};

interface RiskBadgeProps {
  level: RiskLevel | string;
}

export const RiskBadge: React.FC<RiskBadgeProps> = ({ level }) => {
  const colorClass =
    riskColors[level as RiskLevel] || "bg-gray-200 text-gray-800";

  return (
    <span
      className={cn(
        "px-2 py-1 rounded text-xs uppercase tracking-wide shadow",
        colorClass
      )}
    >
      {level}
    </span>
  );
};
