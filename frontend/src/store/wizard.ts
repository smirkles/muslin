import { create } from "zustand";
import type { MeasurementsResponse } from "../lib/api";

interface WizardState {
  patternId: string | null;
  measurementsResponse: MeasurementsResponse | null;
  setMeasurementsResponse: (r: MeasurementsResponse) => void;
  reset: () => void;
}

const initialState = {
  patternId: null,
  measurementsResponse: null,
};

export const useWizardStore = create<WizardState>()((set) => ({
  ...initialState,
  setMeasurementsResponse: (r: MeasurementsResponse) =>
    set({ measurementsResponse: r }),
  reset: () => set(initialState),
}));
