const S = {{json *}};
const T = S.theme;
const sec = (frame) => frame / S.fps;
// Replays a sampled Remotion spring: curve[k] is the value at frame k after `atFrame`.
function playCurve(tl, target, curve, atFrame, make) {
  tl.set(target, make(curve[0]), 0);
  const steps = curve.slice(1).map((v) => ({ ...make(v), duration: 1 / S.fps, ease: "none" }));
  tl.to(target, { keyframes: steps }, sec(atFrame));
}
// Toggles between two states every `half` frames until `untilFrame` (frame % (2*half) < half is "on").
function blink(tl, target, untilFrame, half, on, off) {
  for (let f = 0; f < untilFrame; f += half) tl.set(target, (f / half) % 2 === 0 ? on : off, sec(f));
}
