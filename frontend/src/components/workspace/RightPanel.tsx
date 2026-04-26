"use client";

import dynamic from "next/dynamic";
import { useWizardStore } from "../../store/wizard";

// Three.js touches window/document at import time — must not run under SSR
const BodyViewer = dynamic(() => import("../BodyViewer").then((m) => m.BodyViewer), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full flex items-center justify-center">
      <div className="text-xs text-gray-400 animate-pulse">Loading body model…</div>
    </div>
  ),
});

export function RightPanel() {
  const measurementsResponse = useWizardStore((s) => s.measurementsResponse);
  const measurements = useWizardStore((s) => s.measurements);
  const bodyGender = useWizardStore((s) => s.bodyGender);
  const setBodyGender = useWizardStore((s) => s.setBodyGender);
  const diagnosisResult = useWizardStore((s) => s.diagnosisResult);
  const cascadeScript = useWizardStore((s) => s.cascadeScript);
  const setActiveTool = useWizardStore((s) => s.setActiveTool);

  return (
    <aside
      className="w-80 shrink-0 flex flex-col border-l overflow-hidden"
      style={{ background: "#FDF8F5", borderColor: "#E8DDD4" }}
    >
      {/* ── Body viewer ─────────────────────────────────────────────────── */}
      <div className="flex flex-col" style={{ height: "420px" }}>
        <div className="px-4 pt-3 pb-1">
          <h2 className="text-xs font-bold text-gray-400 uppercase tracking-wide">
            Body preview
          </h2>
          {measurementsResponse && (
            <span className="text-xs text-emerald-500 font-medium">● Live</span>
          )}
        </div>

        <div className="flex-1 relative">
          {measurementsResponse ? (
            <BodyViewer
              measurements={measurements}
              gender={bodyGender}
              onGenderChange={setBodyGender}
              className="w-full h-full"
            />
          ) : (
            <div className="w-full h-full flex flex-col items-center justify-center gap-2 text-center px-4">
              <div
                className="w-28 h-48 rounded-2xl flex items-center justify-center text-gray-300 text-xs"
                style={{ background: "#EDE8E4" }}
              >
                3D body
              </div>
              <p className="text-xs text-gray-400">
                Enter measurements to see your body model
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Divider */}
      <div className="h-px" style={{ background: "#E8DDD4" }} />

      {/* ── Contextual bottom section ────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto px-4 py-4">
        {cascadeScript ? (
          <CascadeContext />
        ) : diagnosisResult ? (
          <DiagnosisContext />
        ) : (
          <EmptyGuide onToolSelect={setActiveTool} />
        )}
      </div>
    </aside>
  );
}

function EmptyGuide({ onToolSelect }: { onToolSelect: (t: "measurements" | "photos" | "diagnosis" | "cascade" | "download") => void }) {
  const steps = [
    { icon: "📏", label: "Enter measurements", tool: "measurements" as const, color: "bg-emerald-50 border-emerald-200 text-emerald-700" },
    { icon: "📷", label: "Upload muslin photos", tool: "photos" as const, color: "bg-sky-50 border-sky-200 text-sky-700" },
    { icon: "🧠", label: "Run diagnosis", tool: "diagnosis" as const, color: "bg-rose-50 border-rose-200 text-rose-700" },
    { icon: "✨", label: "Apply adjustments", tool: "cascade" as const, color: "bg-violet-50 border-violet-200 text-violet-700" },
  ];

  return (
    <div className="flex flex-col gap-3">
      <h2 className="text-sm font-bold text-gray-700">Get started</h2>
      <p className="text-xs text-gray-400">Use the tools on the left to begin fitting your pattern.</p>
      {steps.map((s) => (
        <button
          key={s.tool}
          type="button"
          onClick={() => onToolSelect(s.tool)}
          className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl border text-xs font-medium text-left transition-all hover:scale-[1.01] ${s.color}`}
        >
          <span className="text-base">{s.icon}</span>
          {s.label}
        </button>
      ))}
    </div>
  );
}

function DiagnosisContext() {
  const diagnosisResult = useWizardStore((s) => s.diagnosisResult);
  const setActiveTool = useWizardStore((s) => s.setActiveTool);
  if (!diagnosisResult) return null;

  return (
    <div className="flex flex-col gap-3">
      <h2 className="text-sm font-bold text-gray-700">Fit issues found</h2>
      {diagnosisResult.issues.map((issue) => (
        <div key={issue.issue_type} className="bg-white rounded-xl border border-gray-100 p-3 text-xs">
          <p className="font-semibold text-gray-700 mb-1">{issue.issue_type}</p>
          <p className="text-gray-400 mb-2">{issue.description}</p>
          <div className="w-full bg-gray-100 rounded-full h-1.5">
            <div
              className="bg-rose-400 h-1.5 rounded-full"
              style={{ width: `${issue.confidence * 100}%` }}
            />
          </div>
          <p className="text-gray-400 mt-1">{Math.round(issue.confidence * 100)}% confidence</p>
        </div>
      ))}
      <button
        type="button"
        onClick={() => setActiveTool("cascade")}
        className="w-full bg-violet-600 text-white text-xs font-semibold py-2.5 rounded-xl hover:bg-violet-700 transition-colors"
      >
        Apply {diagnosisResult.cascade_type} →
      </button>
    </div>
  );
}

function CascadeContext() {
  const cascadeScript = useWizardStore((s) => s.cascadeScript);
  const currentStepIndex = useWizardStore((s) => s.currentStepIndex);
  if (!cascadeScript) return null;

  const totalSteps = cascadeScript.steps.length;
  const activeStep = cascadeScript.steps[currentStepIndex];
  const progressPct = ((currentStepIndex + 1) / totalSteps) * 100;

  return (
    <div className="flex flex-col gap-3">
      <h2 className="text-sm font-bold text-gray-700">
        {cascadeScript.adjustment_type} in progress
      </h2>
      <div className="bg-violet-50 rounded-xl border border-violet-100 p-3 text-xs">
        <p className="text-violet-600 font-medium mb-1">
          Adding {cascadeScript.amount_cm} cm at bust apex
        </p>
        {/* Progress bar driven by currentStepIndex */}
        <div className="w-full bg-violet-100 rounded-full h-1.5 mt-2">
          <div
            className="bg-violet-500 h-1.5 rounded-full"
            style={{ width: `${progressPct}%` }}
          />
        </div>
        <p className="text-violet-400 mt-1">
          Step {currentStepIndex + 1} of {totalSteps}
        </p>
      </div>
      {/* Narration callout driven by current step */}
      <div className="bg-violet-50 rounded-xl border border-violet-100 p-3 text-xs text-violet-700 italic">
        &ldquo;{activeStep?.narration}&rdquo;
      </div>
    </div>
  );
}
