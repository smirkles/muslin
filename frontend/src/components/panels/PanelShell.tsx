"use client";

import { useWizardStore } from "../../store/wizard";

interface PanelShellProps {
  icon: string;
  title: string;
  headerBg: string;
  children: React.ReactNode;
}

/** Shared outer wrapper for every fly-out panel. */
export function PanelShell({ icon, title, headerBg, children }: PanelShellProps) {
  const setActiveTool = useWizardStore((s) => s.setActiveTool);

  return (
    <div className="h-full flex flex-col bg-white shadow-2xl overflow-hidden">
      {/* Coloured header bar */}
      <div
        className="flex items-center justify-between px-4 py-4 shrink-0"
        style={{ background: headerBg }}
      >
        <h2 className="text-white font-bold text-base">
          {icon}&nbsp;&nbsp;{title}
        </h2>
        <button
          type="button"
          onClick={() => setActiveTool(null)}
          className="text-white/60 hover:text-white transition-colors text-xl leading-none"
          aria-label="Close panel"
        >
          ×
        </button>
      </div>

      {/* Scrollable body */}
      <div className="flex-1 overflow-y-auto">{children}</div>
    </div>
  );
}
