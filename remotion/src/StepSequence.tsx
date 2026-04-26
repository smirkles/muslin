import React from "react";
import { useCurrentFrame, useVideoConfig, spring, interpolate } from "remotion";
import type { CascadeStep, TransformStep } from "@cascade/CascadeScript";

interface StepSequenceProps {
  step: CascadeStep;
  svgContent: string;
}

/**
 * Renders a single CascadeStep's animation within its Sequence window.
 * Uses spring() to drive the transform, applied as an SVG transform attribute.
 */
export const StepSequence: React.FC<StepSequenceProps> = ({
  step,
  svgContent,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const springValue = spring({
    frame,
    fps,
    config: {
      damping: 18,
      mass: 0.8,
      stiffness: 90,
    },
  });

  const transform = step.transform;
  const svgTransform = buildSvgTransform(transform, springValue);

  // Apply transform to the target element by replacing/injecting the transform attribute
  const animatedSvg = injectTransform(svgContent, transform.elementId, svgTransform);

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
      dangerouslySetInnerHTML={{ __html: animatedSvg }}
    />
  );
};

/**
 * Builds an SVG transform string for the given step at the given spring progress.
 */
function buildSvgTransform(transform: TransformStep, progress: number): string {
  switch (transform.type) {
    case "translate":
      return `translate(${interpolateValue(0, transform.dx, progress)}, ${interpolateValue(0, transform.dy, progress)})`;
    case "rotate":
      return `rotate(${interpolateValue(0, transform.angleDeg, progress)}, ${transform.pivotX}, ${transform.pivotY})`;
    case "scale":
      return `scale(${interpolateValue(1, transform.sx, progress)}, ${interpolateValue(1, transform.sy, progress)})`;
  }
}

function interpolateValue(from: number, to: number, progress: number): number {
  return from + (to - from) * progress;
}

/**
 * Injects a transform attribute on the SVG element with the given ID.
 * Uses a simple string replacement to apply the transform.
 * Throws if the elementId is not found.
 */
function injectTransform(svgContent: string, elementId: string, transform: string): string {
  const pattern = new RegExp(`(<[^>]+\\sid="${elementId}"[^>]*)`, "s");
  if (!pattern.test(svgContent)) {
    throw new Error(
      `[cascade] elementId "${elementId}" not found in SVG. ` +
        `Ensure bodice-front.svg has an element with id="${elementId}".`
    );
  }
  return svgContent.replace(pattern, `$1 transform="${transform}"`);
}
