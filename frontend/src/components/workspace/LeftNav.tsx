"use client";

import { useState } from "react";
import { TOOLS } from "../../lib/tools";
import { useWizardStore } from "../../store/wizard";

export function LeftNav() {
  const activeTool = useWizardStore((s) => s.activeTool);
  const setActiveTool = useWizardStore((s) => s.setActiveTool);
  const [hoveredTool, setHoveredTool] = useState<string | null>(null);

  function handleToolClick(id: typeof TOOLS[number]["id"]) {
    // Clicking active tool toggles the panel closed
    setActiveTool(activeTool === id ? null : id);
  }

  return (
    <nav
      className="w-14 shrink-0 flex flex-col items-center py-4 gap-1 z-20"
      style={{ background: "#1E1B4B" }}
      aria-label="Tools"
    >
      {TOOLS.map((tool) => {
        const isActive = activeTool === tool.id;
        return (
          <div key={tool.id} className="relative w-full flex justify-center">
            <button
              type="button"
              aria-label={tool.label}
              aria-pressed={isActive}
              onClick={() => handleToolClick(tool.id)}
              onMouseEnter={() => setHoveredTool(tool.id)}
              onMouseLeave={() => setHoveredTool(null)}
              className={[
                "w-10 h-10 rounded-xl flex flex-col items-center justify-center transition-all duration-150",
                isActive ? tool.navActiveBg + " ring-1 ring-white/20" : "hover:bg-white/10",
              ].join(" ")}
            >
              <span className="text-xl leading-none">{tool.icon}</span>
            </button>

            {/* Tooltip */}
            {hoveredTool === tool.id && (
              <div
                className="absolute left-[52px] top-1/2 -translate-y-1/2 bg-gray-900 text-white text-xs font-medium px-2.5 py-1.5 rounded-lg whitespace-nowrap pointer-events-none z-50"
                role="tooltip"
              >
                {tool.label}
                <div className="absolute right-full top-1/2 -translate-y-1/2 border-4 border-transparent border-r-gray-900" />
              </div>
            )}
          </div>
        );
      })}

      {/* Spacer */}
      <div className="flex-1" />

      {/* Settings */}
      <button
        type="button"
        aria-label="Settings"
        className="w-10 h-10 rounded-xl flex items-center justify-center text-white/30 hover:text-white/60 hover:bg-white/10 transition-all duration-150"
      >
        ⚙
      </button>
    </nav>
  );
}
