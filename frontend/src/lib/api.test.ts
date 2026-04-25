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

// ── gradePattern tests ────────────────────────────────────────────────────────

const GRADED_PATTERN_RESPONSE = {
  graded_pattern_id: "graded-456",
  pattern_id: "bodice-classic",
  measurement_id: "abc-123",
  svg: "<svg>...</svg>",
  adjustments_cm: { bust: 2.5 },
};

describe("gradePattern", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
  });

  it("returns a GradedPatternResponse on 200", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        status: 200,
        ok: true,
        json: () => Promise.resolve(GRADED_PATTERN_RESPONSE),
      }),
    );

    const { gradePattern } = await import("./api");
    const result = await gradePattern("bodice-classic", "abc-123");

    expect(result).toEqual(GRADED_PATTERN_RESPONSE);
    expect(result.graded_pattern_id).toBe("graded-456");
  });

  it("calls POST /patterns/{patternId}/grade with correct URL", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      status: 200,
      ok: true,
      json: () => Promise.resolve(GRADED_PATTERN_RESPONSE),
    });
    vi.stubGlobal("fetch", mockFetch);

    const { gradePattern } = await import("./api");
    await gradePattern("bodice-classic", "abc-123");

    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/patterns/bodice-classic/grade",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("throws on non-ok response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        status: 500,
        ok: false,
        json: () => Promise.resolve({ detail: "Server error" }),
      }),
    );

    const { gradePattern } = await import("./api");
    await expect(gradePattern("bodice-classic", "abc-123")).rejects.toThrow(
      "API error 500",
    );
  });

  it("uses NEXT_PUBLIC_API_URL env var", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "http://custom.test:9000");
    const mockFetch = vi.fn().mockResolvedValue({
      status: 200,
      ok: true,
      json: () => Promise.resolve(GRADED_PATTERN_RESPONSE),
    });
    vi.stubGlobal("fetch", mockFetch);

    const { gradePattern } = await import("./api");
    await gradePattern("bodice-classic", "abc-123");

    expect(mockFetch).toHaveBeenCalledWith(
      "http://custom.test:9000/patterns/bodice-classic/grade",
      expect.objectContaining({ method: "POST" }),
    );
  });
});

// ── segmentPhoto tests ────────────────────────────────────────────────────────

const SEGMENT_RESPONSE = {
  photo_id: "photo-789",
  mask_path: "/tmp/mask.png",
  cropped_path: "/tmp/cropped.jpg",
  confidence: 0.92,
};

describe("segmentPhoto", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
  });

  it("returns a SegmentationResponse on 200", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        status: 200,
        ok: true,
        json: () => Promise.resolve(SEGMENT_RESPONSE),
      }),
    );

    const { segmentPhoto } = await import("./api");
    const result = await segmentPhoto("photo-789");

    expect(result).toEqual(SEGMENT_RESPONSE);
    expect(result.cropped_path).toBe("/tmp/cropped.jpg");
  });

  it("calls POST /photos/{photoId}/segment with correct URL", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      status: 200,
      ok: true,
      json: () => Promise.resolve(SEGMENT_RESPONSE),
    });
    vi.stubGlobal("fetch", mockFetch);

    const { segmentPhoto } = await import("./api");
    await segmentPhoto("photo-789");

    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/photos/photo-789/segment",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("throws on non-ok response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        status: 502,
        ok: false,
        json: () => Promise.resolve({ detail: "Segmentation service error" }),
      }),
    );

    const { segmentPhoto } = await import("./api");
    await expect(segmentPhoto("photo-789")).rejects.toThrow("API error 502");
  });

  it("uses NEXT_PUBLIC_API_URL env var", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "http://custom.test:9000");
    const mockFetch = vi.fn().mockResolvedValue({
      status: 200,
      ok: true,
      json: () => Promise.resolve(SEGMENT_RESPONSE),
    });
    vi.stubGlobal("fetch", mockFetch);

    const { segmentPhoto } = await import("./api");
    await segmentPhoto("photo-789");

    expect(mockFetch).toHaveBeenCalledWith(
      "http://custom.test:9000/photos/photo-789/segment",
      expect.objectContaining({ method: "POST" }),
    );
  });
});

// ── runDiagnosis tests ────────────────────────────────────────────────────────

const DIAGNOSIS_RESPONSE = {
  issues: [
    {
      issue_type: "fba",
      confidence: 0.88,
      description: "Bust dart too small",
      recommended_adjustment: "Full bust adjustment of 2.5 cm",
    },
  ],
  primary_recommendation: "Full bust adjustment",
  cascade_type: "fba" as const,
};

describe("runDiagnosis", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
  });

  it("returns a DiagnosisResponse on 200", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        status: 200,
        ok: true,
        json: () => Promise.resolve(DIAGNOSIS_RESPONSE),
      }),
    );

    const { runDiagnosis } = await import("./api");
    const result = await runDiagnosis("abc-123", ["photo-789"]);

    expect(result).toEqual(DIAGNOSIS_RESPONSE);
    expect(result.cascade_type).toBe("fba");
  });

  it("calls POST /diagnosis/run with measurement_id and photo_ids", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      status: 200,
      ok: true,
      json: () => Promise.resolve(DIAGNOSIS_RESPONSE),
    });
    vi.stubGlobal("fetch", mockFetch);

    const { runDiagnosis } = await import("./api");
    await runDiagnosis("abc-123", ["photo-789", "photo-000"]);

    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/diagnosis/run",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ measurement_id: "abc-123", photo_ids: ["photo-789", "photo-000"] }),
      }),
    );
  });

  it("throws on non-ok response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        status: 502,
        ok: false,
        json: () => Promise.resolve({ detail: "Upstream error" }),
      }),
    );

    const { runDiagnosis } = await import("./api");
    await expect(runDiagnosis("abc-123", ["photo-789"])).rejects.toThrow("API error 502");
  });

  it("uses NEXT_PUBLIC_API_URL env var", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "http://custom.test:9000");
    const mockFetch = vi.fn().mockResolvedValue({
      status: 200,
      ok: true,
      json: () => Promise.resolve(DIAGNOSIS_RESPONSE),
    });
    vi.stubGlobal("fetch", mockFetch);

    const { runDiagnosis } = await import("./api");
    await runDiagnosis("abc-123", ["photo-789"]);

    expect(mockFetch).toHaveBeenCalledWith(
      "http://custom.test:9000/diagnosis/run",
      expect.objectContaining({ method: "POST" }),
    );
  });
});

// ── downloadPattern tests ─────────────────────────────────────────────────────

describe("downloadPattern", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
  });

  it("returns a Blob on 200", async () => {
    const fakeBlob = new Blob(["<svg>...</svg>"], { type: "image/svg+xml" });
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        status: 200,
        ok: true,
        blob: () => Promise.resolve(fakeBlob),
      }),
    );

    const { downloadPattern } = await import("./api");
    const result = await downloadPattern("graded-456", "svg");

    expect(result).toBe(fakeBlob);
    expect(result).toBeInstanceOf(Blob);
  });

  it("calls GET /patterns/download/{id}?format=svg with correct URL", async () => {
    const fakeBlob = new Blob(["<svg/>"], { type: "image/svg+xml" });
    const mockFetch = vi.fn().mockResolvedValue({
      status: 200,
      ok: true,
      blob: () => Promise.resolve(fakeBlob),
    });
    vi.stubGlobal("fetch", mockFetch);

    const { downloadPattern } = await import("./api");
    await downloadPattern("graded-456", "svg");

    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/patterns/download/graded-456?format=svg",
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("calls GET /patterns/download/{id}?format=pdf with correct URL", async () => {
    const fakeBlob = new Blob(["%PDF-1.4"], { type: "application/pdf" });
    const mockFetch = vi.fn().mockResolvedValue({
      status: 200,
      ok: true,
      blob: () => Promise.resolve(fakeBlob),
    });
    vi.stubGlobal("fetch", mockFetch);

    const { downloadPattern } = await import("./api");
    await downloadPattern("graded-456", "pdf");

    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/patterns/download/graded-456?format=pdf",
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("throws on non-ok response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        status: 404,
        ok: false,
        blob: () => Promise.resolve(new Blob()),
      }),
    );

    const { downloadPattern } = await import("./api");
    await expect(downloadPattern("graded-456", "svg")).rejects.toThrow("API error 404");
  });

  it("uses NEXT_PUBLIC_API_URL env var", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "http://custom.test:9000");
    const fakeBlob = new Blob(["<svg/>"], { type: "image/svg+xml" });
    const mockFetch = vi.fn().mockResolvedValue({
      status: 200,
      ok: true,
      blob: () => Promise.resolve(fakeBlob),
    });
    vi.stubGlobal("fetch", mockFetch);

    const { downloadPattern } = await import("./api");
    await downloadPattern("graded-456", "svg");

    expect(mockFetch).toHaveBeenCalledWith(
      "http://custom.test:9000/patterns/download/graded-456?format=svg",
      expect.objectContaining({ method: "GET" }),
    );
  });
});
