import type { CascadeScript } from "@cascade/CascadeScript";

/**
 * A 3-step Full Bust Adjustment (FBA) cascade script for the demo composition.
 * Steps: translate (spread), rotate (dart), translate (true seam).
 */
export const SAMPLE_CASCADE_SCRIPT: CascadeScript = {
  version: "1",
  steps: [
    {
      id: "step-1",
      transform: {
        type: "translate",
        elementId: "bodice-front-piece",
        dx: 30,
        dy: 0,
      },
      narration:
        "First, we slash from the bust point to the side seam and spread the pieces apart.",
      durationMs: 1500,
    },
    {
      id: "step-2",
      transform: {
        type: "rotate",
        elementId: "bust-dart",
        angleDeg: 15,
        pivotX: 120,
        pivotY: 200,
      },
      narration:
        "The bust dart rotates to absorb the extra ease at the fullest point.",
      durationMs: 1500,
    },
    {
      id: "step-3",
      transform: {
        type: "translate",
        elementId: "side-seam-line",
        dx: -15,
        dy: 0,
      },
      narration:
        "Finally, we true the side seams so front and back match.",
      durationMs: 1200,
    },
  ],
};
