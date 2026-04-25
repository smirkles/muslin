export type ToolId = "measurements" | "photos" | "diagnosis" | "cascade" | "download";

export interface Tool {
  id: ToolId;
  icon: string;
  label: string;
  /** CSS hex — used for panel header background */
  headerBg: string;
  /** Tailwind classes for active nav icon background */
  navActiveBg: string;
}

export const TOOLS: Tool[] = [
  { id: "measurements", icon: "📏", label: "Measure",  headerBg: "#10B981", navActiveBg: "bg-emerald-900/40" },
  { id: "photos",       icon: "📷", label: "Photos",   headerBg: "#0EA5E9", navActiveBg: "bg-sky-900/40"     },
  { id: "diagnosis",    icon: "🧠", label: "Diagnose", headerBg: "#F43F5E", navActiveBg: "bg-rose-900/40"    },
  { id: "cascade",      icon: "✨", label: "Adjust",   headerBg: "#7C3AED", navActiveBg: "bg-violet-900/40"  },
  { id: "download",     icon: "⬇",  label: "Download", headerBg: "#F59E0B", navActiveBg: "bg-amber-900/40"  },
];
