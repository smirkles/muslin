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

export interface PhotoRecord {
  photo_id: string;
  view_label: string;
  filename: string;
}

export class ApiValidationError extends Error {
  detail: FastApiValidationError[];

  constructor(detail: FastApiValidationError[]) {
    super("Validation error");
    this.detail = detail;
    this.name = "ApiValidationError";
  }
}

/** Post photos to the backend and return the list of PhotoRecord objects. */
export async function postPhotos(
  measurementId: string,
  files: File[],
  viewLabels: string[],
): Promise<PhotoRecord[]> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const form = new FormData();
  form.append("measurement_id", measurementId);
  for (const file of files) {
    form.append("photos", file);
  }
  for (const label of viewLabels) {
    form.append("view_labels", label);
  }
  const res = await fetch(`${apiUrl}/photos/upload`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: `API error ${res.status}` }));
    throw new Error(body.detail ?? `API error ${res.status}`);
  }
  return res.json();
}

// ── Grading ───────────────────────────────────────────────────────────────────

export interface GradedPatternResponse {
  graded_pattern_id: string;
  pattern_id: string;
  measurement_id: string;
  svg: string;
  adjustments_cm: Record<string, number>;
}

/** Grade a pattern to a set of measurements and return the graded result. */
export async function gradePattern(
  patternId: string,
  measurementId: string,
): Promise<GradedPatternResponse> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const res = await fetch(`${apiUrl}/patterns/${patternId}/grade`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ measurement_id: measurementId }),
  });
  if (!res.ok) {
    throw new Error(`API error ${res.status}`);
  }
  return res.json();
}

// ── Segmentation ──────────────────────────────────────────────────────────────

export interface SegmentationResponse {
  photo_id: string;
  mask_path: string;
  cropped_path: string;
  confidence: number;
}

/** Segment the muslin garment from a previously uploaded photo. */
export async function segmentPhoto(photoId: string): Promise<SegmentationResponse> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const res = await fetch(`${apiUrl}/photos/${photoId}/segment`, {
    method: "POST",
  });
  if (!res.ok) {
    throw new Error(`API error ${res.status}`);
  }
  return res.json();
}

// ── Diagnosis ─────────────────────────────────────────────────────────────────

export interface DiagnosisIssue {
  issue_type: string;
  confidence: number;
  description: string;
  recommended_adjustment: string;
}

export interface DiagnosisResponse {
  issues: DiagnosisIssue[];
  primary_recommendation: string;
  cascade_type: "fba" | "swayback" | "none";
}

/** Run fit diagnosis using measurements and uploaded photos. */
export async function runDiagnosis(
  measurementId: string,
  photoIds: string[],
): Promise<DiagnosisResponse> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const res = await fetch(`${apiUrl}/diagnosis/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ measurement_id: measurementId, photo_ids: photoIds }),
  });
  if (!res.ok) {
    throw new Error(`API error ${res.status}`);
  }
  return res.json();
}

// ── Download ──────────────────────────────────────────────────────────────────

/** Download a graded pattern as SVG or PDF and return the raw Blob. */
export async function downloadPattern(
  gradedPatternId: string,
  format: "svg" | "pdf",
): Promise<Blob> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const res = await fetch(
    `${apiUrl}/patterns/download/${gradedPatternId}?format=${format}`,
    { method: "GET" },
  );
  if (!res.ok) {
    throw new Error(`API error ${res.status}`);
  }
  return res.blob();
}

// ── Pattern fetch ─────────────────────────────────────────────────────────────

export interface PatternDetail {
  id: string;
  name: string;
  description: string;
  piece_count: number;
  svg: string;
}

/** Fetch a pattern by ID and return the full detail including SVG. */
export async function fetchPattern(patternId: string): Promise<PatternDetail> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const res = await fetch(`${apiUrl}/patterns/${patternId}`, {
    method: "GET",
  });
  if (!res.ok) {
    throw new Error(`API error ${res.status}`);
  }
  return res.json();
}

// ── Cascade ───────────────────────────────────────────────────────────────────

export interface CascadeStepApiResponse {
  step_number: number;
  narration: string;
  svg: string;
}

export interface CascadeScriptApiResponse {
  adjustment_type: string;
  pattern_id: string;
  amount_cm: number;
  steps: CascadeStepApiResponse[];
  seam_adjustments: Record<string, number>;
}

/** Apply a fit adjustment cascade and return the step-by-step script. */
export async function applyAdjustment(
  patternId: string,
  adjustmentType: string,
  amountCm: number,
): Promise<CascadeScriptApiResponse> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const res = await fetch(`${apiUrl}/cascades/apply-adjustment`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      pattern_id: patternId,
      adjustment_type: adjustmentType,
      amount_cm: amountCm,
    }),
  });
  if (!res.ok) {
    throw new Error(`API error ${res.status}`);
  }
  return res.json();
}

// ── Measurements ──────────────────────────────────────────────────────────────

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
