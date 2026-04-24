import { describe, it, expect } from "vitest";
import { validateMeasurements, type Measurements } from "./measurements";

const VALID: Measurements = {
  bust_cm: 96,
  high_bust_cm: 85,
  apex_to_apex_cm: 18,
  waist_cm: 78,
  hip_cm: 104,
  height_cm: 168,
  back_length_cm: 39.5,
};

describe("validateMeasurements", () => {
  it("returns no errors for a fully valid input", () => {
    const errs = validateMeasurements(VALID);
    Object.values(errs).forEach((e) => expect(e).toBeUndefined());
  });

  // bust_cm: 60–200
  it("accepts bust_cm at minimum (60)", () => {
    expect(validateMeasurements({ ...VALID, bust_cm: 60 }).bust_cm).toBeUndefined();
  });
  it("accepts bust_cm at maximum (200)", () => {
    expect(validateMeasurements({ ...VALID, bust_cm: 200 }).bust_cm).toBeUndefined();
  });
  it("rejects bust_cm below minimum (59)", () => {
    expect(validateMeasurements({ ...VALID, bust_cm: 59 }).bust_cm).toBeDefined();
  });
  it("rejects bust_cm above maximum (201)", () => {
    expect(validateMeasurements({ ...VALID, bust_cm: 201 }).bust_cm).toBeDefined();
  });

  // high_bust_cm: 60–200
  it("accepts high_bust_cm at minimum (60)", () => {
    expect(
      validateMeasurements({ ...VALID, high_bust_cm: 60 }).high_bust_cm,
    ).toBeUndefined();
  });
  it("accepts high_bust_cm at maximum (200)", () => {
    expect(
      validateMeasurements({ ...VALID, high_bust_cm: 200 }).high_bust_cm,
    ).toBeUndefined();
  });
  it("rejects high_bust_cm below minimum (59)", () => {
    expect(
      validateMeasurements({ ...VALID, high_bust_cm: 59 }).high_bust_cm,
    ).toBeDefined();
  });
  it("rejects high_bust_cm above maximum (201)", () => {
    expect(
      validateMeasurements({ ...VALID, high_bust_cm: 201 }).high_bust_cm,
    ).toBeDefined();
  });

  // apex_to_apex_cm: 10–30
  it("accepts apex_to_apex_cm at minimum (10)", () => {
    expect(
      validateMeasurements({ ...VALID, apex_to_apex_cm: 10 }).apex_to_apex_cm,
    ).toBeUndefined();
  });
  it("accepts apex_to_apex_cm at maximum (30)", () => {
    expect(
      validateMeasurements({ ...VALID, apex_to_apex_cm: 30 }).apex_to_apex_cm,
    ).toBeUndefined();
  });
  it("rejects apex_to_apex_cm below minimum (9)", () => {
    expect(
      validateMeasurements({ ...VALID, apex_to_apex_cm: 9 }).apex_to_apex_cm,
    ).toBeDefined();
  });
  it("rejects apex_to_apex_cm above maximum (31)", () => {
    expect(
      validateMeasurements({ ...VALID, apex_to_apex_cm: 31 }).apex_to_apex_cm,
    ).toBeDefined();
  });

  // waist_cm: 40–200
  it("accepts waist_cm at minimum (40)", () => {
    expect(validateMeasurements({ ...VALID, waist_cm: 40 }).waist_cm).toBeUndefined();
  });
  it("rejects waist_cm below minimum (39)", () => {
    expect(validateMeasurements({ ...VALID, waist_cm: 39 }).waist_cm).toBeDefined();
  });
  it("rejects waist_cm above maximum (201)", () => {
    expect(validateMeasurements({ ...VALID, waist_cm: 201 }).waist_cm).toBeDefined();
  });

  // hip_cm: 60–200
  it("rejects hip_cm below minimum (59)", () => {
    expect(validateMeasurements({ ...VALID, hip_cm: 59 }).hip_cm).toBeDefined();
  });

  // height_cm: 120–220
  it("accepts height_cm at minimum (120)", () => {
    expect(
      validateMeasurements({ ...VALID, height_cm: 120 }).height_cm,
    ).toBeUndefined();
  });
  it("rejects height_cm below minimum (119)", () => {
    expect(
      validateMeasurements({ ...VALID, height_cm: 119 }).height_cm,
    ).toBeDefined();
  });
  it("rejects height_cm above maximum (221)", () => {
    expect(
      validateMeasurements({ ...VALID, height_cm: 221 }).height_cm,
    ).toBeDefined();
  });

  // back_length_cm: 30–60
  it("accepts back_length_cm at minimum (30)", () => {
    expect(
      validateMeasurements({ ...VALID, back_length_cm: 30 }).back_length_cm,
    ).toBeUndefined();
  });
  it("rejects back_length_cm above maximum (61)", () => {
    expect(
      validateMeasurements({ ...VALID, back_length_cm: 61 }).back_length_cm,
    ).toBeDefined();
  });

  // NaN / empty string treatment
  it("rejects NaN as empty/missing", () => {
    expect(validateMeasurements({ ...VALID, bust_cm: NaN }).bust_cm).toBeDefined();
  });
});
