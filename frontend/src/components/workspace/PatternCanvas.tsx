"use client";

import { useEffect, useState } from "react";
import { useWizardStore } from "../../store/wizard";
import { fetchPattern } from "../../lib/api";

export function PatternCanvas() {
  const cascadeScript = useWizardStore((s) => s.cascadeScript);

  return (
    <main
      className="flex-1 relative overflow-hidden flex flex-col"
      style={{ background: "#FFFEF9" }}
      aria-label="Pattern canvas"
    >
      {/* Dot grid */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          backgroundImage: "radial-gradient(circle, #ccc 1px, transparent 1px)",
          backgroundSize: "32px 32px",
          opacity: 0.4,
        }}
      />

      {/* Canvas content */}
      <div className="relative flex-1 flex items-center justify-center">
        {cascadeScript ? (
          <CascadeCanvas />
        ) : (
          <PatternDisplay />
        )}
      </div>

      {/* Bottom bar — zoom controls */}
      <div className="absolute bottom-4 right-4 flex items-center gap-2">
        <div className="bg-white/80 border border-gray-200 rounded-full px-3 py-1 flex items-center gap-2 text-xs text-gray-500 shadow-sm">
          <button type="button" className="hover:text-gray-800 transition-colors">−</button>
          <span className="select-none">100%</span>
          <button type="button" className="hover:text-gray-800 transition-colors">+</button>
        </div>
      </div>

      {/* Step progress bar — visible during cascade */}
      {cascadeScript && <CascadeProgressBar />}
    </main>
  );
}

function PatternDisplay() {
  const gradedPatternId = useWizardStore((s) => s.gradedPatternId);
  const [svg, setSvg] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!gradedPatternId) {
      setSvg(null);
      return;
    }
    let cancelled = false;
    setIsLoading(true);
    setError(null);
    fetchPattern(gradedPatternId)
      .then((detail) => {
        if (!cancelled) {
          setSvg(detail.svg);
          setIsLoading(false);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setError("Failed to load pattern.");
          setIsLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [gradedPatternId]);

  if (!gradedPatternId) {
    return (
      <div className="flex flex-col items-center gap-4 text-center">
        <div className="w-48 h-64 border-2 border-dashed border-violet-200 rounded-lg flex items-center justify-center">
          <span className="text-violet-300 text-sm">Pattern loads here</span>
        </div>
        <p className="text-sm text-gray-400 max-w-xs">
          Enter your measurements to grade the pattern to your size
        </p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex flex-col items-center gap-3">
        <div className="w-8 h-8 border-2 border-violet-200 border-t-violet-600 rounded-full animate-spin" />
        <p className="text-xs text-gray-400">Loading pattern…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center gap-3 text-center">
        <p className="text-xs text-red-500">{error}</p>
      </div>
    );
  }

  if (svg) {
    return (
      <div
        className="w-full h-full flex items-center justify-center p-8"
        dangerouslySetInnerHTML={{ __html: svg }}
      />
    );
  }

  return null;
}

function CascadeCanvas() {
  const cascadeScript = useWizardStore((s) => s.cascadeScript);
  const currentStepIndex = useWizardStore((s) => s.currentStepIndex);
  if (!cascadeScript) return null;

  const stepSvg = cascadeScript.steps[currentStepIndex]?.svg ?? "";

  return (
    <div className="w-full h-full flex items-center justify-center p-8">
      <div
        className="border-2 border-violet-200 rounded-lg p-4 w-full max-w-2xl h-[480px] flex items-center justify-center overflow-hidden"
        style={{ background: "rgba(124,58,237,0.03)" }}
        dangerouslySetInnerHTML={{ __html: stepSvg }}
      />
    </div>
  );
}

function CascadeProgressBar() {
  const cascadeScript = useWizardStore((s) => s.cascadeScript);
  const currentStepIndex = useWizardStore((s) => s.currentStepIndex);
  if (!cascadeScript) return null;

  return (
    <div className="absolute bottom-0 left-0 right-0 h-10 bg-violet-50 border-t border-violet-100 flex items-center px-6 gap-4">
      {/* Step dots */}
      <div className="flex items-center gap-2">
        {cascadeScript.steps.map((step, i) => (
          <div key={step.step_number} className="flex flex-col items-center gap-0.5">
            <div
              className={[
                "rounded-full transition-all",
                i === currentStepIndex ? "w-3 h-3 bg-violet-600" : "w-2 h-2 bg-violet-200",
              ].join(" ")}
            />
          </div>
        ))}
      </div>
      <span className="text-xs text-violet-500 font-medium">
        Step {currentStepIndex + 1} of {cascadeScript.steps.length}
      </span>
    </div>
  );
}
