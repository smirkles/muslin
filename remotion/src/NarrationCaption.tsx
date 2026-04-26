import React from "react";
import { useCurrentFrame, interpolate } from "remotion";

interface NarrationCaptionProps {
  text: string;
}

/**
 * Renders the narration text for a cascade step with a quick fade-in.
 * Designed to be mounted inside a <Sequence>, so frame 0 = step start.
 */
export const NarrationCaption: React.FC<NarrationCaptionProps> = ({ text }) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 8], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        position: "absolute",
        bottom: 80,
        left: 0,
        right: 0,
        textAlign: "center",
        opacity,
        padding: "0 60px",
      }}
    >
      <p
        style={{
          fontFamily: "Georgia, serif",
          fontSize: 32,
          color: "#2d2d2d",
          lineHeight: 1.5,
          margin: 0,
          fontStyle: "italic",
        }}
      >
        {text}
      </p>
    </div>
  );
};
