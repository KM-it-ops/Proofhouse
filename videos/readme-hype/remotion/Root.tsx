import React from "react";
import { Composition } from "remotion";
import { DURATION, FPS, HEIGHT, Hype, WIDTH } from "./Hype";

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="Hype"
      component={Hype}
      durationInFrames={DURATION}
      fps={FPS}
      width={WIDTH}
      height={HEIGHT}
    />
  );
};
