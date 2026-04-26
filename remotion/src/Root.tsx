// TODO: implement - this is a failing stub
import React from "react";
import { Composition } from "remotion";

export const Root: React.FC = () => {
  return (
    <Composition
      id="CascadeDemo"
      component={() => <></>}
      durationInFrames={600}
      fps={30}
      width={1080}
      height={1080}
    />
  );
};
