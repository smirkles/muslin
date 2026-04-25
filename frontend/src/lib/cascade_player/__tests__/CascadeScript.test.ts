import { describe, it, expect } from "vitest";
import { parseCascadeScript, ScriptValidationError } from "../CascadeScript";

const validScript = {
  version: "1" as const,
  steps: [
    {
      id: "step-1",
      transform: { type: "translate", elementId: "front-bodice", dx: 10, dy: 5 },
      narration: "Moving the front piece",
      durationMs: 500,
    },
  ],
};

describe("parseCascadeScript", () => {
  it("parses a valid v1 script with a translate step", () => {
    const result = parseCascadeScript(validScript);
    expect(result.version).toBe("1");
    expect(result.steps).toHaveLength(1);
    expect(result.steps[0].transform.type).toBe("translate");
  });

  it("parses a rotate step", () => {
    const script = {
      ...validScript,
      steps: [
        {
          id: "step-1",
          transform: {
            type: "rotate",
            elementId: "piece",
            angleDeg: 45,
            pivotX: 100,
            pivotY: 200,
          },
          narration: "Rotating",
          durationMs: 300,
        },
      ],
    };
    const result = parseCascadeScript(script);
    expect(result.steps[0].transform.type).toBe("rotate");
  });

  it("parses a scale step", () => {
    const script = {
      ...validScript,
      steps: [
        {
          id: "step-1",
          transform: {
            type: "scale",
            elementId: "piece",
            sx: 1.2,
            sy: 0.9,
            originX: 50,
            originY: 100,
          },
          narration: "Scaling",
          durationMs: 300,
        },
      ],
    };
    const result = parseCascadeScript(script);
    expect(result.steps[0].transform.type).toBe("scale");
  });

  it("throws ScriptValidationError for unknown transform type 'shear'", () => {
    const bad = {
      ...validScript,
      steps: [
        {
          id: "s1",
          transform: { type: "shear", elementId: "x", kx: 1 },
          narration: "bad",
          durationMs: 100,
        },
      ],
    };
    expect(() => parseCascadeScript(bad)).toThrow(ScriptValidationError);
  });

  it("throws ScriptValidationError for version '2'", () => {
    expect(() => parseCascadeScript({ ...validScript, version: "2" })).toThrow(
      ScriptValidationError
    );
  });

  it("throws ScriptValidationError for step missing narration", () => {
    const bad = {
      version: "1",
      steps: [
        {
          id: "s1",
          transform: { type: "translate", elementId: "x", dx: 0, dy: 0 },
          durationMs: 100,
          // narration missing
        },
      ],
    };
    expect(() => parseCascadeScript(bad)).toThrow(ScriptValidationError);
  });

  it("throws ScriptValidationError for missing steps array", () => {
    expect(() => parseCascadeScript({ version: "1" })).toThrow(ScriptValidationError);
  });
});
