"use client";

import { useEffect, useState } from "react";
import { PanelShell } from "./PanelShell";
import { useWizardStore } from "../../store/wizard";
import { runDiagnosis as runDiagnosisApi } from "../../lib/api";

export function DiagnosisPanel() {
  const measurementsResponse = useWizardStore((s) => s.measurementsResponse);
  const photoIds = useWizardStore((s) => s.photoIds);
  const diagnosisResult = useWizardStore((s) => s.diagnosisResult);
  const setDiagnosisResult = useWizardStore((s) => s.setDiagnosisResult);
  const setActiveTool = useWizardStore((s) => s.setActiveTool);

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Auto-run diagnosis when panel opens if we have the prerequisites
  useEffect(() => {
    if (!diagnosisResult && measurementsResponse && photoIds.length > 0) {
      runDiagnosis();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function runDiagnosis() {
    if (!measurementsResponse) { setError("Enter measurements first."); return; }
    if (photoIds.length === 0) { setError("Upload photos first."); return; }

    setIsLoading(true);
    setError(null);
    try {
      const result = await runDiagnosisApi(measurementsResponse.measurement_id, photoIds);
      setDiagnosisResult(result);
    } catch {
      setError("Diagnosis failed — please try again.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <PanelShell icon="🧠" title="Fit diagnosis" headerBg="#F43F5E">
      <div className="px-4 py-4 flex flex-col gap-4">

        {isLoading && (
          <div className="flex flex-col items-center gap-3 py-8">
            <div className="w-8 h-8 border-2 border-rose-200 border-t-rose-500 rounded-full animate-spin" />
            <p className="text-xs text-gray-400 text-center">
              Specialist agents are analysing your photos…
            </p>
            <div className="w-full flex flex-col gap-1.5 mt-2">
              {["Shoulder agent", "Bust agent", "Waist/hip agent", "Coordinator"].map((agent) => (
                <div key={agent} className="flex items-center gap-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-rose-200 animate-pulse" />
                  <span className="text-[11px] text-gray-400">{agent}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {error && (
          <div role="alert" className="bg-red-50 border border-red-200 rounded-xl px-3 py-2 text-xs text-red-600 flex flex-col gap-2">
            {error}
            <button type="button" onClick={runDiagnosis} className="underline text-left">Try again</button>
          </div>
        )}

        {!isLoading && !diagnosisResult && !error && (
          <div className="flex flex-col items-center gap-3 py-8 text-center">
            <span className="text-3xl">🧠</span>
            <p className="text-xs text-gray-400">
              Upload photos and click below to run diagnosis.
            </p>
            <button
              type="button"
              onClick={runDiagnosis}
              className="bg-rose-500 text-white text-xs font-semibold px-4 py-2.5 rounded-xl hover:bg-rose-600 transition-colors"
            >
              Run diagnosis
            </button>
          </div>
        )}

        {diagnosisResult && (
          <>
            <p className="text-xs text-gray-400">
              {diagnosisResult.issues.length} issue{diagnosisResult.issues.length !== 1 ? "s" : ""} found
            </p>

            {/* Issue cards */}
            <div className="flex flex-col gap-3">
              {diagnosisResult.issues.map((issue) => (
                <div
                  key={issue.issue_type}
                  className="bg-white rounded-xl border border-gray-100 p-3 text-xs shadow-sm"
                >
                  <div className="flex items-start justify-between mb-1">
                    <p className="font-semibold text-gray-700">{issue.issue_type}</p>
                    <span className="text-rose-400 font-medium text-[11px]">
                      {Math.round(issue.confidence * 100)}%
                    </span>
                  </div>
                  <p className="text-gray-400 mb-2 leading-relaxed">{issue.description}</p>
                  {/* Confidence bar */}
                  <div className="w-full bg-gray-100 rounded-full h-1">
                    <div
                      className="bg-rose-400 h-1 rounded-full transition-all"
                      style={{ width: `${issue.confidence * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>

            {/* Recommendation callout */}
            <div className="bg-rose-50 border border-rose-100 rounded-xl p-3 text-xs">
              <p className="font-semibold text-rose-700 mb-1">Recommended</p>
              <p className="text-gray-600 leading-relaxed">
                {diagnosisResult.primary_recommendation}
              </p>
            </div>

            {/* CTA */}
            <button
              type="button"
              onClick={() => setActiveTool("cascade")}
              className="w-full bg-rose-500 text-white text-xs font-semibold py-3 rounded-xl hover:bg-rose-600 transition-colors"
            >
              Apply {diagnosisResult.cascade_type} →
            </button>

            <button
              type="button"
              onClick={runDiagnosis}
              className="w-full text-xs text-gray-400 hover:text-gray-600 transition-colors py-1"
            >
              Re-run diagnosis
            </button>
          </>
        )}
      </div>
    </PanelShell>
  );
}
