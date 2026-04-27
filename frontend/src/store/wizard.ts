import { create } from "zustand";
import type { MeasurementsResponse } from "../lib/api";
import type { Measurements } from "../lib/measurements";
import type { ToolId } from "../lib/tools";

export type BodyGender = "male" | "female";

// ── Domain types (mirror backend response shapes) ─────────────────────────────

export interface DiagnosisIssue {
  issue_type: string;
  confidence: number;
  description: string;
  recommended_adjustment: string;
}

export interface DiagnosisResult {
  issues: DiagnosisIssue[];
  primary_recommendation: string;
  cascade_type: string;
}

export interface CascadeStep {
  step_number: number;
  narration: string;
  svg: string;
}

export interface CascadeScript {
  adjustment_type: string;
  pattern_id: string;
  amount_cm: number;
  steps: CascadeStep[];
  seam_adjustments: Record<string, number>;
}

// ── Store ─────────────────────────────────────────────────────────────────────

export interface PhotoRecord {
  photo_id: string;
  view_label: string;
}

interface WizardState {
  patternId: string | null;
  gradedPatternId: string | null;
  measurementsResponse: MeasurementsResponse | null;
  measurements: Measurements | null;
  bodyGender: BodyGender;
  photos: PhotoRecord[];
  diagnosisResult: DiagnosisResult | null;
  cascadeScript: CascadeScript | null;
  currentStepIndex: number;
  activeTool: ToolId | null;
  selectedIssueIndex: number | null;

  setPatternId: (id: string) => void;
  setGradedPatternId: (id: string) => void;
  setMeasurementsResponse: (r: MeasurementsResponse) => void;
  setMeasurements: (m: Measurements) => void;
  setBodyGender: (g: BodyGender) => void;
  setPhotos: (photos: PhotoRecord[]) => void;
  setDiagnosisResult: (r: DiagnosisResult) => void;
  setCascadeScript: (s: CascadeScript) => void;
  setCurrentStepIndex: (i: number) => void;
  setActiveTool: (tool: ToolId | null) => void;
  setSelectedIssueIndex: (i: number | null) => void;
  reset: () => void;
}

const initialState = {
  patternId: null as string | null,
  gradedPatternId: null,
  measurementsResponse: null,
  measurements: null,
  bodyGender: "female" as BodyGender,
  photos: [] as PhotoRecord[],
  diagnosisResult: null,
  cascadeScript: null,
  currentStepIndex: 0,
  activeTool: null,
  selectedIssueIndex: null as number | null,
};

export const useWizardStore = create<WizardState>()((set) => ({
  ...initialState,
  setPatternId: (id) => set({ patternId: id }),
  setGradedPatternId: (id) => set({ gradedPatternId: id }),
  setMeasurementsResponse: (r) => set({ measurementsResponse: r }),
  setMeasurements: (m) => set({ measurements: m }),
  setBodyGender: (g) => set({ bodyGender: g }),
  setPhotos: (photos) => set({ photos }),
  setDiagnosisResult: (r) => set({ diagnosisResult: r }),
  setCascadeScript: (s) => set({ cascadeScript: s }),
  setCurrentStepIndex: (i) => set({ currentStepIndex: i }),
  setActiveTool: (tool) => set({ activeTool: tool }),
  setSelectedIssueIndex: (i) => set({ selectedIssueIndex: i }),
  reset: () => set(initialState),
}));
