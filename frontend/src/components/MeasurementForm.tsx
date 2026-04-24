"use client";

import { useState } from "react";
import {
  type Measurements,
  FIELD_META,
  FIELD_ORDER,
  validateMeasurements,
} from "../lib/measurements";

interface MeasurementFormProps {
  onSubmit: (measurements: Measurements) => void;
  isLoading?: boolean;
  serverErrors?: Partial<Record<keyof Measurements, string>>;
}

type FieldValues = Record<keyof Measurements, string>;
type Touched = Record<keyof Measurements, boolean>;
type FieldErrors = Record<keyof Measurements, string | undefined>;

const EMPTY_VALUES: FieldValues = {
  bust_cm: "",
  high_bust_cm: "",
  apex_to_apex_cm: "",
  waist_cm: "",
  hip_cm: "",
  height_cm: "",
  back_length_cm: "",
};

const UNTOUCHED: Touched = {
  bust_cm: false,
  high_bust_cm: false,
  apex_to_apex_cm: false,
  waist_cm: false,
  hip_cm: false,
  height_cm: false,
  back_length_cm: false,
};

function parseValues(raw: FieldValues): Partial<Measurements> {
  const result: Partial<Measurements> = {};
  for (const key of FIELD_ORDER) {
    const n = parseFloat(raw[key]);
    result[key] = isNaN(n) ? undefined : n;
  }
  return result as Partial<Measurements>;
}

export function MeasurementForm({
  onSubmit,
  isLoading = false,
  serverErrors,
}: MeasurementFormProps) {
  const [values, setValues] = useState<FieldValues>(EMPTY_VALUES);
  const [touched, setTouched] = useState<Touched>(UNTOUCHED);
  const [clientErrors, setClientErrors] = useState<FieldErrors>(
    {} as FieldErrors,
  );
  // Per-field server error overrides; cleared when user edits that field
  const [dismissedServerErrors, setDismissedServerErrors] = useState<
    Set<keyof Measurements>
  >(new Set());

  function getDisplayError(field: keyof Measurements): string | undefined {
    if (
      serverErrors?.[field] &&
      !dismissedServerErrors.has(field)
    ) {
      return serverErrors[field];
    }
    return touched[field] ? clientErrors[field] : undefined;
  }

  function handleChange(field: keyof Measurements, raw: string) {
    const next = { ...values, [field]: raw };
    setValues(next);
    // Dismiss any server error for this field on first edit
    if (serverErrors?.[field] && !dismissedServerErrors.has(field)) {
      setDismissedServerErrors((prev) => new Set(prev).add(field));
    }
    // Live re-validate only if field has been touched
    if (touched[field]) {
      const parsed = parseFloat(raw);
      const errs = validateMeasurements({
        ...parseValues(next),
        [field]: isNaN(parsed) ? undefined : parsed,
      } as Partial<Measurements>);
      setClientErrors((prev) => ({ ...prev, [field]: errs[field] }));
    }
  }

  function handleBlur(field: keyof Measurements) {
    if (!touched[field]) {
      setTouched((prev) => ({ ...prev, [field]: true }));
    }
    const errs = validateMeasurements(parseValues(values));
    setClientErrors((prev) => ({ ...prev, [field]: errs[field] }));
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const parsed = parseValues(values);
    const errs = validateMeasurements(parsed);
    if (FIELD_ORDER.some((k) => errs[k] !== undefined)) return;
    onSubmit(parsed as Measurements);
  }

  const isFormValid = FIELD_ORDER.every(
    (k) => validateMeasurements(parseValues(values))[k] === undefined,
  );

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-5">
      {FIELD_ORDER.map((field) => {
        const meta = FIELD_META[field];
        const error = getDisplayError(field);
        const inputId = `field-${field}`;
        return (
          <div key={field} className="flex flex-col gap-1">
            <label
              htmlFor={inputId}
              className="text-sm font-medium text-gray-700"
            >
              {meta.label}
              <span className="text-gray-400 font-normal"> (cm)</span>
            </label>
            <input
              id={inputId}
              type="number"
              inputMode="decimal"
              min={meta.min}
              max={meta.max}
              step="0.1"
              value={values[field]}
              disabled={isLoading}
              onChange={(e) => handleChange(field, e.target.value)}
              onBlur={() => handleBlur(field)}
              aria-describedby={`${inputId}-helper ${error ? `${inputId}-error` : ""}`}
              aria-invalid={!!error}
              className={`w-full rounded border px-3 py-2 text-sm focus:outline-none focus:ring-2 ${
                error
                  ? "border-red-400 focus:ring-red-300"
                  : "border-gray-300 focus:ring-indigo-300"
              } disabled:bg-gray-50 disabled:text-gray-400`}
            />
            <p id={`${inputId}-helper`} className="text-xs text-gray-500">
              {meta.helper}
            </p>
            {error && (
              <p
                id={`${inputId}-error`}
                className="text-xs text-red-600"
                role="alert"
              >
                {error}
              </p>
            )}
          </div>
        );
      })}
      <button
        type="submit"
        disabled={isLoading || !isFormValid}
        aria-label="Calculate my fit"
        className="w-full rounded bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-indigo-300"
      >
        {isLoading ? "Calculating…" : "Calculate my fit"}
      </button>
    </form>
  );
}
