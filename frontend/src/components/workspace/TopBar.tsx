"use client";

import { useEffect, useRef, useState } from "react";
import { useWizardStore } from "../../store/wizard";

const PATTERNS = [
  {
    id: "bodice-v1",
    name: "Basic Fitted Bodice",
    description: "Fitted bodice block — ideal for FBA & swayback adjustments",
    pieces: 2,
    comingSoon: false,
  },
  {
    id: "trousers-v1",
    name: "Classic Trouser Block",
    description: "Straight-leg trouser block for waist & hip adjustments",
    pieces: 3,
    comingSoon: true,
  },
];

export function TopBar() {
  const measurementsResponse = useWizardStore((s) => s.measurementsResponse);
  const cascadeScript = useWizardStore((s) => s.cascadeScript);
  const setActiveTool = useWizardStore((s) => s.setActiveTool);
  const activeTool = useWizardStore((s) => s.activeTool);
  const patternId = useWizardStore((s) => s.patternId);
  const setPatternId = useWizardStore((s) => s.setPatternId);

  const [pickerOpen, setPickerOpen] = useState(false);
  const pickerRef = useRef<HTMLDivElement>(null);

  const selectedPattern = PATTERNS.find((p) => p.id === patternId);

  // Close picker on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (pickerRef.current && !pickerRef.current.contains(e.target as Node)) {
        setPickerOpen(false);
      }
    }
    if (pickerOpen) document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [pickerOpen]);

  return (
    <header className="h-[52px] bg-white border-b border-gray-200 flex items-center px-3 gap-3 shrink-0 z-20">
      {/* Logo */}
      <div className="bg-[#1E1B4B] text-white text-sm font-bold px-4 py-1.5 rounded-full select-none">
        muslin
      </div>

      {/* Pattern picker */}
      <div className="relative" ref={pickerRef}>
        <button
          type="button"
          onClick={() => setPickerOpen((o) => !o)}
          className={[
            "text-xs font-medium px-3 py-1.5 rounded-full border transition-colors",
            selectedPattern
              ? "bg-violet-50 text-violet-700 border-violet-200 hover:bg-violet-100"
              : "bg-amber-50 text-amber-700 border-amber-300 hover:bg-amber-100 animate-pulse",
          ].join(" ")}
        >
          {selectedPattern ? `${selectedPattern.name} ▾` : "Select a pattern ▾"}
        </button>

        {pickerOpen && (
          <div className="absolute top-full left-0 mt-2 w-72 bg-white border border-gray-200 rounded-2xl shadow-xl z-50 overflow-hidden">
            <div className="px-4 pt-3 pb-2 border-b border-gray-100">
              <p className="text-xs font-bold text-gray-500 uppercase tracking-wide">Choose a pattern</p>
            </div>
            <div className="p-2 flex flex-col gap-1">
              {PATTERNS.map((p) => (
                <button
                  key={p.id}
                  type="button"
                  disabled={p.comingSoon}
                  onClick={() => {
                    if (!p.comingSoon) {
                      setPatternId(p.id);
                      setPickerOpen(false);
                    }
                  }}
                  className={[
                    "w-full text-left px-3 py-2.5 rounded-xl transition-colors flex items-start gap-3",
                    p.comingSoon
                      ? "opacity-50 cursor-not-allowed"
                      : patternId === p.id
                      ? "bg-violet-50 border border-violet-200"
                      : "hover:bg-gray-50",
                  ].join(" ")}
                >
                  <div
                    className="w-8 h-10 rounded-lg shrink-0 flex items-center justify-center text-[10px] font-bold mt-0.5"
                    style={{ background: "#EDE8E4", color: "#9C8B80" }}
                  >
                    {p.pieces}pc
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="text-xs font-semibold text-gray-800">{p.name}</p>
                      {p.comingSoon && (
                        <span className="text-[10px] bg-gray-100 text-gray-400 px-1.5 py-0.5 rounded-full font-medium">
                          soon
                        </span>
                      )}
                      {patternId === p.id && (
                        <span className="text-[10px] bg-violet-100 text-violet-600 px-1.5 py-0.5 rounded-full font-medium">
                          selected
                        </span>
                      )}
                    </div>
                    <p className="text-[11px] text-gray-400 mt-0.5 leading-snug">{p.description}</p>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Cascade status chip — visible during cascade */}
      {cascadeScript && (
        <div className="bg-violet-900 text-violet-200 text-xs font-medium px-3 py-1.5 rounded-full">
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
