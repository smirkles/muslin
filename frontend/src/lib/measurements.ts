export interface Measurements {
  bust_cm: number;
  high_bust_cm: number;
  apex_to_apex_cm: number;
  waist_cm: number;
  hip_cm: number;
  height_cm: number;
  back_length_cm: number;
}

type ValidationErrors = Record<keyof Measurements, string | undefined>;

const RULES: Record<keyof Measurements, { min: number; max: number; label: string }> = {
  bust_cm: { min: 60, max: 200, label: "Full bust" },
  high_bust_cm: { min: 60, max: 200, label: "High bust" },
  apex_to_apex_cm: { min: 10, max: 30, label: "Bust point to bust point" },
  waist_cm: { min: 40, max: 200, label: "Waist" },
  hip_cm: { min: 60, max: 200, label: "Hip" },
  height_cm: { min: 120, max: 220, label: "Height" },
  back_length_cm: { min: 30, max: 60, label: "Back length" },
};

export function validateMeasurements(
  values: Partial<Measurements>,
): ValidationErrors {
  const errors = {} as ValidationErrors;
  for (const key of Object.keys(RULES) as (keyof Measurements)[]) {
    const { min, max } = RULES[key];
    const val = values[key];
    if (val === undefined || val === null || isNaN(val as number)) {
      errors[key] = `Required`;
    } else if ((val as number) < min || (val as number) > max) {
      errors[key] = `Must be between ${min} and ${max} cm`;
    } else {
      errors[key] = undefined;
    }
  }
  return errors;
}

export const FIELD_META: Record<
  keyof Measurements,
  { label: string; helper: string; min: number; max: number }
> = {
  bust_cm: {
    label: "Full bust",
    helper: "Around the fullest part of your bust, parallel to the floor",
    min: 60,
    max: 200,
  },
  high_bust_cm: {
    label: "High bust",
    helper: "Around your chest above the bust, level with your armpits",
    min: 60,
    max: 200,
  },
  apex_to_apex_cm: {
    label: "Bust point to bust point",
    helper: "Distance between your two bust points (nipples)",
    min: 10,
    max: 30,
  },
  waist_cm: {
    label: "Waist",
    helper: "Around your natural waist, the narrowest point",
    min: 40,
    max: 200,
  },
  hip_cm: {
    label: "Hip",
    helper: "Around the fullest part of your hips, usually 20–23cm below your waist",
    min: 60,
    max: 200,
  },
  height_cm: {
    label: "Height",
    helper: "Standing straight, without shoes",
    min: 120,
    max: 220,
  },
  back_length_cm: {
    label: "Back length",
    helper: "From the most prominent neck vertebra to your natural waist",
    min: 30,
    max: 60,
  },
};

export const FIELD_ORDER: (keyof Measurements)[] = [
  "bust_cm",
  "high_bust_cm",
  "apex_to_apex_cm",
  "waist_cm",
  "hip_cm",
  "height_cm",
  "back_length_cm",
];
