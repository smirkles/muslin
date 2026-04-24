import type { Measurements, FastApiValidationError } from "./measurements";

export interface MeasurementsResponse {
  bust_cm: number;
  high_bust_cm: number;
  apex_to_apex_cm: number;
  waist_cm: number;
  hip_cm: number;
  height_cm: number;
  back_length_cm: number;
  measurement_id: string;
  size_label: string;
}

export class ApiValidationError extends Error {
  detail: FastApiValidationError[];

  constructor(detail: FastApiValidationError[]) {
    super("Validation error");
    this.detail = detail;
    this.name = "ApiValidationError";
  }
}

/** Post measurements to the backend and return the typed response. */
export async function postMeasurements(
  m: Measurements,
): Promise<MeasurementsResponse> {
  const apiUrl =
    process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const res = await fetch(`${apiUrl}/measurements`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(m),
  });
  if (res.status === 422) {
    const body = await res.json();
    throw new ApiValidationError(body.detail);
  }
  if (!res.ok) {
    throw new Error(`API error ${res.status}`);
  }
  return res.json();
}
