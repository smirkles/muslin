"use client";

import { useState } from "react";
import { PanelShell } from "./PanelShell";
import { MeasurementForm } from "../MeasurementForm";
import { useWizardStore } from "../../store/wizard";
import type { Measurements } from "../../lib/measurements";
import { postMeasurements, gradePattern } from "../../lib/api";

export function MeasurementsPanel() {
  const setMeasurementsResponse = useWizardStore((s) => s.setMeasurementsResponse);
  const setGradedPatternId = useWizardStore((s) => s.setGradedPatternId);
  const setActiveTool = useWizardStore((s) => s.setActiveTool);
  const patternId = useWizardStore((s) => s.patternId);
  const measurementsResponse = useWizardStore((s) => s.measurementsResponse);

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(measurements: Measurements) {
    setIsLoading(true);
    setError(null);
    try {
      const result = await postMeasurements(measurements);
      setMeasurementsResponse(result);

      const graded = await gradePattern(patternId!, result.measurement_id);
      setGradedPatternId(graded.graded_pattern_id);

      // Advance to photo upload
      setActiveTool("photos");
    } catch {
      setError("Something went wrong — please try again.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <PanelShell icon="📏" title="Measurements" headerBg="#10B981">
      <div className="px-4 py-4 flex flex-col gap-4">
        <p className="text-xs text-gray-400">
          We&apos;ll grade the pattern to your size and update the 3D body model.
        </p>

        {measurementsResponse && (
          <div className="bg-emerald-50 border border-emerald-200 rounded-xl px-3 py-2 text-xs text-emerald-700 font-medium">
            ✓ Measurements saved — body model is live
          </div>
        )}

        {error && (
          <div role="alert" className="bg-red-50 border border-red-200 rounded-xl px-3 py-2 text-xs text-red-600">
            {error}
          </div>
        )}

        {/* Existing MeasurementForm component */}
        <MeasurementForm onSubmit={handleSubmit} isLoading={isLoading} />

        <p className="text-[11px] text-gray-300 text-center">
          The 3D body updates live as you type each measurement.
        </p>
      </div>
    </PanelShell>
  );
}
