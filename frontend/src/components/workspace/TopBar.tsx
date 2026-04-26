"use client";

import { useWizardStore } from "../../store/wizard";

export function TopBar() {
  const measurementsResponse = useWizardStore((s) => s.measurementsResponse);
  const cascadeScript = useWizardStore((s) => s.cascadeScript);
  const setActiveTool = useWizardStore((s) => s.setActiveTool);
  const activeTool = useWizardStore((s) => s.activeTool);

  return (
    <header className="h-[52px] bg-white border-b border-gray-200 flex items-center px-3 gap-3 shrink-0 z-20">
      {/* Logo */}
      <div className="bg-[#1E1B4B] text-white text-sm font-bold px-4 py-1.5 rounded-full select-none">
        muslin
      </div>

      {/* Cascade status chip — visible during cascade */}
      {cascadeScript && (
        <div className="bg-violet-900 text-violet-200 text-xs font-medium px-3 py-1.5 rounded-full">
          {/* TODO: show active step name from CascadePlayer */}
          Applying adjustments…
        </div>
      )}

      {/* Pause / Restart — visible during cascade */}
      {cascadeScript && activeTool === "cascade" && (
        <div className="flex gap-2 ml-1">
          <button
            type="button"
            className="text-xs text-violet-600 bg-violet-50 border border-violet-200 px-3 py-1.5 rounded-lg hover:bg-violet-100 transition-colors"
          >
            ⏸ Pause
          </button>
          <button
            type="button"
            className="text-xs text-gray-500 bg-gray-50 border border-gray-200 px-3 py-1.5 rounded-lg hover:bg-gray-100 transition-colors"
          >
            ↺ Restart
          </button>
        </div>
      )}

      {/* Measurements status badge */}
      {measurementsResponse && (
        <span className="text-xs text-emerald-600 bg-emerald-50 border border-emerald-200 px-2 py-1 rounded-full">
          ✓ Measurements set
        </span>
      )}

      <div className="ml-auto flex items-center gap-2">
        <button
          type="button"
          className="text-xs text-violet-600 bg-violet-50 border border-violet-200 px-3 py-1.5 rounded-lg hover:bg-violet-100 transition-colors"
          onClick={() => setActiveTool("download")}
        >
          Save ↓
        </button>
        <button
          type="button"
          className="text-xs text-white bg-violet-600 px-3 py-1.5 rounded-lg hover:bg-violet-700 transition-colors font-medium"
          onClick={() => setActiveTool("download")}
        >
          Export
        </button>
        <button
          type="button"
          className="text-gray-400 hover:text-gray-600 text-lg w-8 h-8 flex items-center justify-center rounded-lg hover:bg-gray-100 transition-colors"
          aria-label="Help"
        >
          ?
        </button>
      </div>
    </header>
  );
}
