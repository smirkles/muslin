import { describe, it, expect, beforeEach } from "vitest";
import { useWizardStore } from "./wizard";

const MOCK_RESPONSE = {
  bust_cm: 96,
  high_bust_cm: 85,
  apex_to_apex_cm: 18,
  waist_cm: 78,
  hip_cm: 104,
  height_cm: 168,
  back_length_cm: 39.5,
  measurement_id: "abc-123",
  size_label: "14",
};

describe("useWizardStore", () => {
  beforeEach(() => {
    // Reset state before each test
    useWizardStore.getState().reset();
  });

  it("has measurementsResponse as null in initial state", () => {
    const state = useWizardStore.getState();
    expect(state.measurementsResponse).toBeNull();
  });

  it("has patternId as null in initial state (user must select from picker)", () => {
    const state = useWizardStore.getState();
    expect(state.patternId).toBeNull();
  });

  it("setMeasurementsResponse stores the response", () => {
    useWizardStore.getState().setMeasurementsResponse(MOCK_RESPONSE);
    expect(useWizardStore.getState().measurementsResponse).toEqual(MOCK_RESPONSE);
  });

  it("reset clears measurementsResponse back to null", () => {
    useWizardStore.getState().setMeasurementsResponse(MOCK_RESPONSE);
    useWizardStore.getState().reset();
    expect(useWizardStore.getState().measurementsResponse).toBeNull();
  });

  it("reset clears patternId back to null", () => {
    useWizardStore.getState().setPatternId("bodice-v1");
    useWizardStore.getState().reset();
    expect(useWizardStore.getState().patternId).toBeNull();
  });

  it("has currentStepIndex as 0 in initial state", () => {
    const state = useWizardStore.getState();
    expect(state.currentStepIndex).toBe(0);
  });

  it("setCurrentStepIndex updates the store", () => {
    useWizardStore.getState().setCurrentStepIndex(3);
    expect(useWizardStore.getState().currentStepIndex).toBe(3);
  });

  it("reset zeroes currentStepIndex back to 0", () => {
    useWizardStore.getState().setCurrentStepIndex(5);
    useWizardStore.getState().reset();
    expect(useWizardStore.getState().currentStepIndex).toBe(0);
  });
});
