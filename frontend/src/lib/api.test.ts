import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// We need to dynamically import api.ts to pick up env var changes.
// We use vi.resetModules() + dynamic import() to re-evaluate the module.

const VALID_MEASUREMENTS = {
  bust_cm: 96,
  high_bust_cm: 85,
  apex_to_apex_cm: 18,
  waist_cm: 78,
  hip_cm: 104,
  height_cm: 168,
  back_length_cm: 39.5,
};

const VALID_RESPONSE = {
  ...VALID_MEASUREMENTS,
  measurement_id: "abc-123",
  size_label: "14",
};

describe("postMeasurements", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
  });

  it("returns a typed MeasurementsResponse on 200", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        status: 200,
        ok: true,
        json: () => Promise.resolve(VALID_RESPONSE),
      }),
    );

    const { postMeasurements } = await import("./api");
    const result = await postMeasurements(VALID_MEASUREMENTS);

    expect(result).toEqual(VALID_RESPONSE);
    expect(result.measurement_id).toBe("abc-123");
    expect(result.size_label).toBe("14");
  });

  it("throws ApiValidationError with detail array on 422", async () => {
    const detail = [
      { loc: ["body", "bust_cm"], msg: "value too small", type: "value_error" },
    ];
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        status: 422,
        ok: false,
        json: () => Promise.resolve({ detail }),
      }),
    );

    const { postMeasurements, ApiValidationError } = await import("./api");

    await expect(postMeasurements(VALID_MEASUREMENTS)).rejects.toBeInstanceOf(
      ApiValidationError,
    );

    try {
      await postMeasurements(VALID_MEASUREMENTS);
    } catch (err) {
      expect(err).toBeInstanceOf(ApiValidationError);
      expect((err as InstanceType<typeof ApiValidationError>).detail).toEqual(
        detail,
      );
    }
  });

  it("throws a plain Error on non-2xx non-422 response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        status: 500,
        ok: false,
        json: () => Promise.resolve({ detail: "Internal server error" }),
      }),
    );

    const { postMeasurements, ApiValidationError } = await import("./api");

    await expect(postMeasurements(VALID_MEASUREMENTS)).rejects.toThrow(
      "API error 500",
    );
    await expect(postMeasurements(VALID_MEASUREMENTS)).rejects.not.toBeInstanceOf(
      ApiValidationError,
    );
  });

  it("uses NEXT_PUBLIC_API_URL env var to build the request URL", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "http://example-api.test:9000");

    const mockFetch = vi.fn().mockResolvedValue({
      status: 200,
      ok: true,
      json: () => Promise.resolve(VALID_RESPONSE),
    });
    vi.stubGlobal("fetch", mockFetch);

    const { postMeasurements } = await import("./api");
    await postMeasurements(VALID_MEASUREMENTS);

    expect(mockFetch).toHaveBeenCalledWith(
      "http://example-api.test:9000/measurements",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("falls back to http://localhost:8000 when NEXT_PUBLIC_API_URL is not set", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "");

    const mockFetch = vi.fn().mockResolvedValue({
      status: 200,
      ok: true,
      json: () => Promise.resolve(VALID_RESPONSE),
    });
    vi.stubGlobal("fetch", mockFetch);

    const { postMeasurements } = await import("./api");
    await postMeasurements(VALID_MEASUREMENTS);

    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/measurements",
      expect.objectContaining({ method: "POST" }),
    );
  });
});
