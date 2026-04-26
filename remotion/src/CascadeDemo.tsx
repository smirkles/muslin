import type { CascadeScript, TransformStep } from "@cascade/CascadeScript";
import React from "react";
import {
  Sequence,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { NarrationCaption } from "./NarrationCaption";
import { StepSequence } from "./StepSequence";
import { BODICE_FRONT_SVG } from "./data/bodiceSvg";
import { SAMPLE_CASCADE_SCRIPT } from "./data/sampleScript";

const HOLD_FRAMES = 15;
const FADE_OUT_FRAMES = 30;

/**
 * Top-level composition component for the Cascade Demo.
 * Lays out each CascadeStep as a Sequence and shows narration text.
 * Uses inline SVG to avoid static file serving issues.
 */
export const CascadeDemo: React.FC = () => {
  const frame = useCurrentFrame();
  const { durationInFrames, fps } = useVideoConfig();
  const script: CascadeScript = SAMPLE_CASCADE_SCRIPT;
  const svgContent = BODICE_FRONT_SVG;

  // Compute per-step frame durations
  const stepFrames = script.steps.map((step) =>
    Math.round((step.durationMs / 1000) * fps)
  );

  // Compute sequential start offsets for each step
  const stepOffsets: number[] = [];
  let offset = 0;
  for (const frames of stepFrames) {
    stepOffsets.push(offset);
    offset += frames + HOLD_FRAMES;
  }

  const activeFrames = offset;

  // Fade-out near the end
  const fadeOpacity = interpolate(
    frame,
    [durationInFrames - FADE_OUT_FRAMES, durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // Find which step is currently active
  let currentStepIndex = -1;
  for (let i = 0; i < stepOffsets.length; i++) {
    const stepEnd =
      i < stepOffsets.length - 1 ? stepOffsets[i + 1] : activeFrames;
    if (frame >= stepOffsets[i] && frame < stepEnd) {
      currentStepIndex = i;
      break;
    }
  }

  // Build cumulative SVG with all completed steps' final transforms baked in
  let cumulativeSvg = svgContent;
  for (let i = 0; i < currentStepIndex; i++) {
    const t = script.steps[i].transform;
    const finalTransform = buildFinalTransform(t);
    cumulativeSvg = injectTransformIntoSvg(cumulativeSvg, t.elementId, finalTransform);
  }

  // After all steps complete, show final state with all transforms baked in
  const isInFinalHold = frame >= activeFrames;
  let finalStateSvg = svgContent;
  if (isInFinalHold) {
    for (const step of script.steps) {
      const t = step.transform;
      finalStateSvg = injectTransformIntoSvg(finalStateSvg, t.elementId, buildFinalTransform(t));
    }
  }

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        backgroundColor: "#faf9f7",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        position: "relative",
        opacity: fadeOpacity,
      }}
    >
      {/* Title */}
      <div
        style={{
          position: "absolute",
          top: 60,
          left: 0,
          right: 0,
          textAlign: "center",
        }}
      >
        <h1
          style={{
            fontFamily: "Georgia, serif",
            fontSize: 36,
            color: "#2d2d2d",
            margin: 0,
            letterSpacing: 2,
            fontWeight: "normal",
          }}
        >
          Full Bust Adjustment
        </h1>
      </div>

      {/* SVG Container */}
      <div
        style={{
          width: 500,
          height: 660,
          position: "relative",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        {isInFinalHold ? (
          /* Final hold: show all transforms baked in */
          <div
            style={{
              width: "100%",
              height: "100%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
            dangerouslySetInnerHTML={{ __html: finalStateSvg }}
          />
        ) : currentStepIndex >= 0 ? (
          /* Active step: animate via StepSequence */
          <Sequence
            key={`step-${currentStepIndex}`}
            from={stepOffsets[currentStepIndex]}
            durationInFrames={stepFrames[currentStepIndex] + HOLD_FRAMES}
          >
            <div
              style={{
                width: 500,
                height: 660,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <StepSequence
                step={script.steps[currentStepIndex]}
                svgContent={cumulativeSvg}
              />
            </div>
          </Sequence>
        ) : (
          /* Frame 0 and before first step: bodice at rest, no narration */
          <div
            style={{ display: "flex", alignItems: "center", justifyContent: "center" }}
            dangerouslySetInnerHTML={{ __html: svgContent }}
          />
        )}
      </div>

      {/* Narration captions — each step's text fades in at step start */}
      {script.steps.map((step, i) => (
        <Sequence
          key={`narration-${step.id}`}
          from={stepOffsets[i]}
          durationInFrames={stepFrames[i] + HOLD_FRAMES}
        >
          <NarrationCaption text={step.narration} />
        </Sequence>
      ))}
    </div>
  );
};

function buildFinalTransform(t: TransformStep): string {
  switch (t.type) {
    case "translate":
      return `translate(${t.dx}, ${t.dy})`;
    case "rotate":
      return `rotate(${t.angleDeg}, ${t.pivotX}, ${t.pivotY})`;
    case "scale":
      return `scale(${t.sx}, ${t.sy})`;
  }
}

function injectTransformIntoSvg(
  svg: string,
  elementId: string,
  transform: string
): string {
  const pattern = new RegExp(`(<[^>]+\\sid="${elementId}"[^>]*)`, "s");
  if (!pattern.test(svg)) {
    throw new Error(`[cascade] elementId "${elementId}" not found in SVG.`);
  }
  return svg.replace(pattern, `$1 transform="${transform}"`);
}
