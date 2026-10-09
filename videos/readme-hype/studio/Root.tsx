import React from "react";
import { Composition } from "remotion";
import { DURATION, FPS, H, Studio, W } from "./Studio";

export const Root: React.FC = () => (
  <Composition id="Studio" component={Studio} durationInFrames={DURATION} fps={FPS} width={W} height={H} />
);
