"use client";

import { useEffect, useState } from "react";
import { PanelShell } from "./PanelShell";
import { useWizardStore } from "../../store/wizard";
import { applyAdjustment } from "../../lib/api";

export function CascadePanel() {
  const diagnosisResult = useWizardStore((s) => s.diagnosisResult);
  const cascadeScript = useWizardStore((s) => s.cascadeScript);
  const setCascadeScript = useWizardStore((s) => s.setCascadeScript);
  const patternId = useWizardStore((s) => s.patternId);
  const setActiveTool = useWizardStore((s) => s.setActiveTool);
  const currentStepIndex = useWizardStore((s) => s.currentStepIndex);
  const setCurrentStepIndex = useWizardStore((s) => s.setCurrentStepIndex);

  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Auto-fetch cascade script when panel opens
  useEffect(() => {
    if (!cascadeScript && diagnosisResult && patternId) {
      loadCascade();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Play auto-advance: advance every 2s while isPlaying
  useEffect(() => {
    if (!isPlaying || !cascadeScript) return;

    const totalSteps = cascadeScript.steps.length;
    const interval = setInterval(() => {
      const i = useWizardStore.getState().currentStepIndex;
      if (i >= totalSteps - 1) {
        setIsPlaying(false);
        clearInterval(interval);
      } else {
        setCurrentStepIndex(i + 1);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [isPlaying, cascadeScript, setCurrentStepIndex]);

  async function loadCascade() {
    if (!diagnosisResult || !patternId) { setError("Run diagnosis first."); return; }
    setIsLoading(true);
    setError(null);
    try {
      const amountCm = diagnosisResult.cascade_type === "fba" ? 2.0 : 1.2;
      const script = await applyAdjustment(patternId, diagnosisResult.cascade_type, amountCm);
      setCascadeScript(script);
      setCurrentStepIndex(0);
    } catch {
      setError("Failed to load adjustment — please try again.");
    } finally {
      setIsLoading(false);
    }
  }

  const totalSteps = cascadeScript?.steps.length ?? 0;
  const activeStep = cascadeScript?.steps[currentStepIndex];

  return (
    <PanelShell icon="✨" title="Adjusting" headerBg="#7C3AED">
      <div className="px-4 py-4 flex flex-col gap-4">

        {isLoading && (
          <div className="flex flex-col items-center gap-3 py-8">
            <div className="w-8 h-8 border-2 border-violet-200 border-t-violet-600 rounded-full animate-spin" />
            <p className="text-xs text-gray-400 text-center">Loading adjustment cascade…</p>
          </div>
        )}

        {error && (
          <div role="alert" className="bg-red-50 border border-red-200 rounded-xl px-3 py-2 text-xs text-red-600 flex flex-col gap-2">
            {error}
            <button type="button" onClick={loadCascade} className="underline text-left">Try again</button>
          </div>
        )}

        {cascadeScript && (
          <>
            {/* Step dots */}
            <div className="flex items-center gap-1.5">
              {cascadeScript.steps.map((_, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => setCurrentStepIndex(i)}
                  className={[
                    "rounded-full transition-all",
                    i === currentStepIndex
                      ? "w-3 h-3 bg-violet-600"
                      : i < currentStepIndex
                      ? "w-2 h-2 bg-violet-300"
                      : "w-2 h-2 bg-gray-200",
                  ].join(" ")}
                  aria-label={`Go to step ${i + 1}`}
                />
              ))}
              <span className="text-[11px] text-gray-400 ml-auto">
                {currentStepIndex + 1} of {totalSteps}
              </span>
            </div>

            {/* Step title */}
            <h3 className="text-sm font-bold text-gray-800">
              Step {currentStepIndex + 1} — {cascadeScript.adjustment_type}
            </h3>

            <div className="h-px bg-gray-100" />

            {/* Narration block */}
            {activeStep && (
              <div className="bg-violet-50 border border-violet-100 rounded-xl p-3 text-xs text-gray-700 leading-relaxed">
                {activeStep.narration}
              </div>
            )}

            {/* Before / After thumbnails */}
            <div className="flex gap-2">
              <div className="flex-1 flex flex-col gap-1">
                <span className="text-[11px] font-semibold text-rose-400">Before</span>
                <div
                  className="h-20 bg-rose-50 border border-rose-100 rounded-lg overflow-hidden flex items-center justify-center"
                  dangerouslySetInnerHTML={{ __html: cascadeScript.steps[0].svg }}
                />
              </div>
              <div className="flex-1 flex flex-col gap-1">
                <span className="text-[11px] font-semibold text-emerald-500">After</span>
                <div
                  className="h-20 bg-emerald-50 border border-emerald-100 rounded-lg overflow-hidden flex items-center justify-center"
                  dangerouslySetInnerHTML={{ __html: cascadeScript.steps[cascadeScript.steps.length - 1].svg }}
                />
              </div>
            </div>

            {/* Playback controls */}
            <div className="bg-gray-50 rounded-xl border border-gray-100 flex items-center justify-between px-4 py-2">
              <button
                type="button"
                onClick={() => setCurrentStepIndex(Math.max(0, currentStepIndex - 1))}
                disabled={currentStepIndex === 0}
                className="text-violet-500 disabled:text-gray-300 text-sm font-medium transition-colors hover:text-violet-700"
                aria-label="Previous step"
              >
                ◀ Prev
              </button>
              <button
                type="button"
                onClick={() => setIsPlaying((p) => !p)}
                className="text-violet-600 text-lg"
                aria-label={isPlaying ? "Pause" : "Play"}
              >
                {isPlaying ? "⏸" : "▶"}
              </button>
              <button
                type="button"
                onClick={() => setCurrentStepIndex(Math.min(totalSteps - 1, currentStepIndex + 1))}
                disabled={currentStepIndex >= totalSteps - 1}
                className="text-violet-500 disabled:text-gray-300 text-sm font-medium transition-colors hover:text-violet-700"
                aria-label="Next step"
              >
                Next ▶
              </button>
            </div>

            {/* All steps list */}
            <div className="flex flex-col gap-1">
              <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wide">All steps</p>
              {cascadeScript.steps.map((step, i) => (
                <button
                  key={step.step_number}
                  type="button"
                  onClick={() => setCurrentStepIndex(i)}
                  className={[
                    "text-left text-xs px-3 py-2 rounded-lg transition-colors",
                    i === currentStepIndex
                      ? "bg-violet-100 text-violet-700 font-semibold"
                      : i < currentStepIndex
                      ? "text-gray-400"
                      : "text-gray-300",
                  ].join(" ")}
                >
                  {i < currentStepIndex ? "✓  " : ""}{i + 1}. {step.narration.split(".")[0]}
                </button>
              ))}
            </div>

            {/* Proceed to download */}
            {currentStepIndex >= totalSteps - 1 && (
              <button
                type="button"
                onClick={() => setActiveTool("download")}
                className="w-full bg-amber-500 text-white text-xs font-semibold py-3 rounded-xl hover:bg-amber-600 transition-colors"
              >
                Download adjusted pattern →
              </button>
            )}
          </>
        )}
      </div>
    </PanelShell>
  );
}
