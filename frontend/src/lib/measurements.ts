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

export function validateMeasurements(
  values: Partial<Measurements>,
): ValidationErrors {
  const errors = {} as ValidationErrors;
  for (const key of FIELD_ORDER) {
    const { min, max } = FIELD_META[key];
    const val = values[key];
    if (val === undefined || val === null || isNaN(val)) {
      errors[key] = `Required`;
    } else if (val < min || val > max) {
      errors[key] = `Must be between ${min} and ${max} cm`;
    } else {
      errors[key] = undefined;
    }
  }
  return errors;
}

export interface StandardSize {
  label: string;
  measurements: Measurements;
}

/** UK/Aus standard women's sizes. Height fixed at 168cm (industry chart baseline). */
export const UK_AUS_SIZES: StandardSize[] = [
  {
    label: "UK 6 / Aus 6",
    measurements: {
      bust_cm: 80, high_bust_cm: 76, apex_to_apex_cm: 17.5,
      waist_cm: 62, hip_cm: 87, height_cm: 168, back_length_cm: 38.5,
    },
  },
  {
    label: "UK 8 / Aus 8",
    measurements: {
      bust_cm: 83, high_bust_cm: 79, apex_to_apex_cm: 18.0,
      waist_cm: 65, hip_cm: 90, height_cm: 168, back_length_cm: 39.0,
    },
  },
  {
    label: "UK 10 / Aus 10",
    measurements: {
      bust_cm: 87, high_bust_cm: 83, apex_to_apex_cm: 18.5,
      waist_cm: 69, hip_cm: 94, height_cm: 168, back_length_cm: 39.5,
    },
  },
  {
    label: "UK 12 / Aus 12",
    measurements: {
      bust_cm: 92, high_bust_cm: 88, apex_to_apex_cm: 19.0,
      waist_cm: 74, hip_cm: 99, height_cm: 168, back_length_cm: 40.0,
    },
  },
  {
    label: "UK 14 / Aus 14",
    measurements: {
      bust_cm: 97, high_bust_cm: 93, apex_to_apex_cm: 19.5,
      waist_cm: 79, hip_cm: 104, height_cm: 168, back_length_cm: 40.5,
    },
  },
  {
    label: "UK 16 / Aus 16",
    measurements: {
      bust_cm: 102, high_bust_cm: 98, apex_to_apex_cm: 20.0,
      waist_cm: 84, hip_cm: 109, height_cm: 168, back_length_cm: 41.0,
    },
  },
  {
    label: "UK 18 / Aus 18",
    measurements: {
      bust_cm: 107, high_bust_cm: 103, apex_to_apex_cm: 20.5,
      waist_cm: 89, hip_cm: 114, height_cm: 168, back_length_cm: 41.5,
    },
  },
  {
    label: "UK 20 / Aus 20",
    measurements: {
      bust_cm: 112, high_bust_cm: 108, apex_to_apex_cm: 21.0,
      waist_cm: 94, hip_cm: 119, height_cm: 168, back_length_cm: 42.0,
    },
  },
  {
    label: "UK 22 / Aus 22",
    measurements: {
      bust_cm: 117, high_bust_cm: 113, apex_to_apex_cm: 21.5,
      waist_cm: 99, hip_cm: 124, height_cm: 168, back_length_cm: 42.5,
    },
  },
];

export interface FastApiValidationError {
  loc: string[];
  msg: string;
  type: string;
}

/** Translates a FastAPI 422 detail array into per-field error strings for the serverErrors prop. */
export function parseServerErrors(
  detail: FastApiValidationError[],
): Partial<Record<keyof Measurements, string>> {
  const result: Partial<Record<keyof Measurements, string>> = {};
  const fieldKeys = new Set(Object.keys(FIELD_META));
  for (const err of detail) {
    const field = err.loc[err.loc.length - 1];
    if (fieldKeys.has(field)) {
      result[field as keyof Measurements] = err.msg;
    }
  }
  return result;
}
