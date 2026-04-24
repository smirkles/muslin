"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { MeasurementForm } from "../../../components/MeasurementForm";
import { postMeasurements, ApiValidationError } from "../../../lib/api";
import { parseServerErrors } from "../../../lib/measurements";
import { useWizardStore } from "../../../store/wizard";
import type { Measurements } from "../../../lib/measurements";

export default function MeasurePage() {
  const router = useRouter();
  const setMeasurementsResponse = useWizardStore(
    (s) => s.setMeasurementsResponse,
  );
  const [isLoading, setIsLoading] = useState(false);
  const [serverErrors, setServerErrors] = useState<
    Partial<Record<keyof Measurements, string>>
  >({});
  const [genericError, setGenericError] = useState<string | null>(null);

  async function handleSubmit(measurements: Measurements) {
    setIsLoading(true);
    setGenericError(null);
    setServerErrors({});
    try {
      const result = await postMeasurements(measurements);
      setMeasurementsResponse(result);
      router.push("/app/photos");
    } catch (err) {
      if (err instanceof ApiValidationError) {
        setServerErrors(parseServerErrors(err.detail));
      } else {
        setGenericError("Something went wrong — please try again");
      }
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="mx-auto max-w-lg px-4 py-10">
      <h1 className="mb-6 text-2xl font-bold">Your measurements</h1>
      {genericError && (
        <p role="alert" className="mb-4 rounded border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-700">
          {genericError}
        </p>
      )}
      <MeasurementForm
        onSubmit={handleSubmit}
        isLoading={isLoading}
        serverErrors={serverErrors}
      />
    </main>
  );
}
