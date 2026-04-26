import React from "react";
import { Composition } from "remotion";
import { CascadeDemo } from "./CascadeDemo";

/**
 * Remotion root — registers the CascadeDemo composition.
 * 1080×1080, 30fps, 600 frames (20 seconds).
 */
export const Root: React.FC = () => {
  return (
    <Composition
      id="CascadeDemo"
      component={CascadeDemo}
      durationInFrames={600}
      fps={30}
      width={1080}
      height={1080}
    />
  );
};
