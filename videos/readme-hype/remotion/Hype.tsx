import React from "react";
import {
  AbsoluteFill,
  Audio,
  Easing,
  Sequence,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import scene from "../scene.generated.json";

const T = scene.theme;
export const FPS = scene.fps;
export const WIDTH = scene.width;
export const HEIGHT = scene.height;
export const DURATION = scene.durationFrames;

const { input: INPUT_AT, clarify: CLARIFY_AT, output: OUTPUT_AT } = scene.screens;

const INK = T.ink;
const CARD = T.card;
const LINE = T.line;
const MINT = T.mint;
const GREEN = T.green;
const DIM = T.dim;
const SOFT = T.soft;

const { copy, beats, run } = scene;
const OBJECTIVE = run.objective;
const ANSWERS = run.answers;
const PROMPT_LINES = run.promptLines;

const mono = T.mono;

const clamp = { extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const };

const Field: React.FC<{ frame: number }> = ({ frame }) => {
  const dots = Array.from({ length: 56 }, (_, i) => {
    const x = ((i * 173) % 1920) + Math.sin(frame / 17 + i * 0.65) * 42;
    const y = ((i * 89) % 1080) + Math.cos(frame / 21 + i * 0.4) * 34;
    const bright = 0.25 + (Math.sin(frame / 11 + i) + 1) * 0.2;
    return { x, y, bright, size: 1.4 + (i % 4) * 0.7 };
  });
  return (
    <AbsoluteFill>
      <AbsoluteFill
        style={{
          backgroundImage:
            "linear-gradient(rgba(61,220,132,0.07) 1px, transparent 1px), linear-gradient(90deg, rgba(61,220,132,0.07) 1px, transparent 1px)",
          backgroundSize: "72px 72px",
          backgroundPosition: `${frame * 0.45}px ${frame * 0.3}px`,
        }}
      />
      <div
        style={{
          position: "absolute",
          width: 820,
          height: 820,
          borderRadius: "50%",
          left: 180 + Math.sin(frame / 55) * 160,
          top: -80 + Math.cos(frame / 47) * 80,
          background: "radial-gradient(circle, rgba(61,220,132,0.22), transparent 68%)",
        }}
      />
      <div
        style={{
          position: "absolute",
          width: 640,
          height: 640,
          borderRadius: "50%",
          right: 40 + Math.cos(frame / 40) * 90,
          bottom: -120,
          background: "radial-gradient(circle, rgba(200,245,216,0.08), transparent 70%)",
        }}
      />
      {dots.map((dot, i) => (
        <div
          key={i}
          style={{
            position: "absolute",
            left: dot.x,
            top: dot.y,
            width: dot.size,
            height: dot.size,
            borderRadius: "50%",
            background: GREEN,
            opacity: dot.bright,
          }}
        />
      ))}
    </AbsoluteFill>
  );
};

const Ripples: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
        {scene.ripples.map(({ at, x, y }) => {
          const age = frame - at;
          if (age < 0 || age > scene.rippleLen) return null;
          const scale = interpolate(age, [0, scene.rippleLen], [0.15, 2.8]);
          return (
            <div
              key={at}
              style={{
                position: "absolute",
                left: x,
                top: y,
                width: 220,
                height: 220,
                marginLeft: -110,
                marginTop: -110,
                borderRadius: "50%",
                border: `2px solid ${GREEN}`,
                opacity: interpolate(age, [0, scene.rippleLen], [0.8, 0]),
                transform: `scale(${scale})`,
              }}
            />
          );
        })}
    </AbsoluteFill>
  );
};

const Caret: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <span
      style={{
        display: "inline-block",
        width: 8,
        height: 16,
        marginLeft: 2,
        background: GREEN,
        opacity: frame % 16 < 8 ? 1 : 0,
        verticalAlign: "text-bottom",
      }}
    />
  );
};

const Header: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <div style={{ marginBottom: 18 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={GREEN} strokeWidth="2">
          <path d="M4 6h16M4 12h16M4 18h10" />
        </svg>
        <div style={{ color: GREEN, fontWeight: 800, letterSpacing: 6, fontSize: 26 }}>{copy.brand}</div>
        <div style={{ width: 10, height: 18, background: GREEN, opacity: frame % 20 < 10 ? 1 : 0.2 }} />
      </div>
      <div style={{ color: DIM, fontSize: 14, marginTop: 6 }}>{copy.tagline}</div>
    </div>
  );
};

const Shell: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const frame = useCurrentFrame();
  const spin = frame * scene.shell.spinPerFrame;
  return (
    <div style={{
        width: scene.shell.width,
        margin: `${scene.shell.marginTop}px auto 0`,
        position: "relative",
        transform: `scale(${scene.shell.scale})`,
        transformOrigin: "top center",
      }}>
      <div
        style={{
          position: "absolute",
          inset: -10,
          borderRadius: 20,
          background: `conic-gradient(from ${spin}deg, transparent 0deg, ${GREEN} 36deg, transparent 80deg)`,
          filter: "blur(10px)",
          opacity: 0.9,
        }}
      />
      <div
        style={{
          position: "relative",
          background: INK,
          borderRadius: 12,
          border: `1px solid ${LINE}`,
          padding: "22px 26px 26px",
          fontFamily: mono,
        }}
      >
        <Header />
        {children}
      </div>
    </div>
  );
};

const InputScreen: React.FC = () => {
  const frame = useCurrentFrame();
  const b = beats.input;
  const ci = copy.input;
  const typedCount = Math.floor(interpolate(frame, [b.typeFrom, b.typeTo], [0, OBJECTIVE.length], clamp));
  const modelOn = frame > b.modelSwitchAfter;
  const loop = spring({ frame: frame - b.loopSpringAt, fps: FPS, config: b.loopSpring });
  const pressed = frame > b.pressAfter && frame < b.busyAt;
  const loading = frame >= b.busyAt;
  return (
    <div style={{ border: `1px solid ${LINE}`, background: CARD, borderRadius: 8, padding: 22 }}>
      <div style={{ color: DIM, fontSize: 13, letterSpacing: 1.5, textTransform: "uppercase" }}>{ci.objectiveLabel}</div>
      <div
        style={{
          marginTop: 8,
          minHeight: 92,
          border: `1px solid ${frame < b.caretUntil ? GREEN : LINE}`,
          borderRadius: 6,
          background: INK,
          color: MINT,
          fontSize: 20,
          padding: "12px 14px",
        }}
      >
        {OBJECTIVE.slice(0, typedCount)}
        {frame < b.caretUntil ? <Caret /> : null}
      </div>
      <div style={{ color: DIM, fontSize: 13, letterSpacing: 1.5, textTransform: "uppercase", marginTop: 16 }}>
        {ci.modelLabel}
      </div>
      <div
        style={{
          marginTop: 8,
          border: `1px solid ${modelOn ? GREEN : LINE}`,
          borderRadius: 6,
          background: INK,
          color: MINT,
          fontSize: 18,
          padding: "10px 14px",
        }}
      >
        {modelOn ? ci.modelAfter : ci.modelBefore}
      </div>
      <div style={{ display: "flex", gap: 10, alignItems: "center", marginTop: 16 }}>
        <div
          style={{
            width: 16,
            height: 16,
            border: `1px solid ${GREEN}`,
            borderRadius: 3,
            background: loop > 0.5 ? GREEN : "transparent",
            transform: `scale(${interpolate(loop, [0, 1], [0.8, 1])})`,
          }}
        />
        <div style={{ color: SOFT, fontSize: 14 }}>
          <span style={{ color: DIM, letterSpacing: 1 }}>{ci.loopLabel}</span> {ci.loopRest}
        </div>
      </div>
      <div style={{ color: DIM, fontSize: 13, letterSpacing: 1.5, textTransform: "uppercase", marginTop: 16 }}>
        {ci.efficiencyLabel}
      </div>
      <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
        {ci.pills.map((label, pillIndex) => {
          const on = pillIndex === ci.pillOn;
          return (
            <div
              key={label}
              style={{
                flex: 1,
                textAlign: "center",
                fontSize: 14,
                padding: "8px 0",
                borderRadius: 6,
                border: `1px solid ${on ? GREEN : LINE}`,
                background: on ? GREEN : "transparent",
                color: on ? INK : SOFT,
                fontWeight: on ? 700 : 500,
              }}
            >
              {label}
            </div>
          );
        })}
      </div>
      <div
        style={{
          marginTop: 18,
          background: GREEN,
          color: INK,
          fontWeight: 800,
          textAlign: "center",
          borderRadius: 6,
          padding: "12px 0",
          fontSize: 16,
          transform: `scale(${pressed ? 0.97 : 1})`,
        }}
      >
        {loading ? ci.buttonBusy : ci.button}
      </div>
    </div>
  );
};

const ClarifyScreen: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const b = beats.clarify;
  const answered = Math.min(
    ANSWERS.length,
    ANSWERS.filter((_, index) => frame > b.answerAt + index * b.step).length,
  );
  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", color: DIM, fontSize: 13, marginBottom: 10 }}>
        <span>{copy.clarify.back}</span>
        <span>{copy.clarify.counter.replace("{n}", String(answered)).replace("{total}", String(ANSWERS.length))}</span>
      </div>
      {ANSWERS.map(({ question, answer }, index) => {
        const enter = spring({
          frame: frame - b.enterAt - index * b.step,
          fps,
          config: b.enterSpring,
        });
        return (
          <div
            key={question}
            style={{
              border: `1px solid ${LINE}`,
              background: CARD,
              borderRadius: 8,
              padding: "10px 14px",
              marginBottom: 8,
              opacity: enter,
              transform: `translateY(${interpolate(enter, [0, 1], [22, 0])}px)`,
            }}
          >
            <div style={{ color: MINT, fontSize: 15 }}>{question}</div>
            <div style={{ color: GREEN, fontSize: 16, fontWeight: 700, marginTop: 3 }}>{answer}</div>
          </div>
        );
      })}
    </div>
  );
};

const OutputScreen: React.FC = () => {
  const frame = useCurrentFrame();
  const lines = PROMPT_LINES;
  const b = beats.output;
  const co = copy.output;
  const copied = frame > b.copiedAfter && frame < b.copiedBefore;
  return (
    <div style={{ border: `1px solid ${LINE}`, background: CARD, borderRadius: 8, padding: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
        <div style={{ color: GREEN, letterSpacing: 2, fontSize: 13, fontWeight: 700 }}>{co.head}</div>
        <div style={{ color: copied ? GREEN : SOFT, fontSize: 13 }}>{copied ? co.copied : co.copy}</div>
      </div>
      <div style={{ color: MINT, fontSize: 15, lineHeight: 1.35 }}>
        {lines.map((line, index) => {
          const from = b.revealAt + index * b.revealStep;
          const reveal = interpolate(frame, [from, from + b.revealLen], [100, 0], {
            ...clamp,
            easing: Easing.out(Easing.cubic),
          });
          const title = co.titles.includes(line);
          return (
            <div
              key={`${index}-${line}`}
              style={{
                clipPath: line === "" ? undefined : `inset(0 ${reveal}% 0 0)`,
                minHeight: line === "" ? 8 : 22,
                color: title ? GREEN : MINT,
                fontWeight: title ? 800 : 500,
              }}
            >
              {line}
            </div>
          );
        })}
      </div>
      <div style={{ color: DIM, fontSize: 12, marginTop: 8 }}>{co.footer}</div>
    </div>
  );
};

const Cursor: React.FC = () => {
  const frame = useCurrentFrame();
  const stops = scene.cursor.stops;
  let x = stops[0].x;
  let y = stops[0].y;
  for (let i = 0; i < stops.length - 1; i++) {
    const a = stops[i];
    const b = stops[i + 1];
    if (frame >= a.f && frame <= b.f) {
      const p = interpolate(frame, [a.f, b.f], [0, 1], { ...clamp, easing: Easing.inOut(Easing.cubic) });
      x = interpolate(p, [0, 1], [a.x, b.x]);
      y = interpolate(p, [0, 1], [a.y, b.y]);
      break;
    }
    if (frame > b.f) {
      x = b.x;
      y = b.y;
    }
  }
  const click = scene.cursor.clicks.some((at) => frame >= at && frame < at + scene.cursor.clickLen);
  return (
    <div style={{ position: "absolute", left: x - scene.cursor.tip.x, top: y - scene.cursor.tip.y, zIndex: 8, transform: `scale(${click ? 0.85 : 1})` }}>
      <svg width="28" height="28" viewBox="0 0 24 24">
        <path d="M4 2 L4 18 L9 14 L13 22 L16 20 L12 12 L19 12 Z" fill={MINT} stroke={INK} strokeWidth="1" />
      </svg>
    </div>
  );
};

const Screen: React.FC<{ length: number; fadeIn: boolean; fadeOut: boolean; children: React.ReactNode }> = ({
  length,
  fadeIn,
  fadeOut,
  children,
}) => {
  const frame = useCurrentFrame();
  const { len, rise } = scene.transition;
  const ease = { ...clamp, easing: Easing.inOut(Easing.quad) };
  const inP = fadeIn ? interpolate(frame, [0, len], [0, 1], ease) : 1;
  const outP = fadeOut ? interpolate(frame, [length, length + len], [1, 0], ease) : 1;
  return (
    <div
      style={{
        width: "100%",
        alignSelf: "flex-start",
        opacity: inP * outP,
        transform: `translateY(${rise * (1 - inP) - rise * (1 - outP)}px)`,
      }}
    >
      {children}
    </div>
  );
};

const SCREENS = [
  { name: "input", at: INPUT_AT, length: CLARIFY_AT - INPUT_AT, Component: InputScreen },
  { name: "clarify", at: CLARIFY_AT, length: OUTPUT_AT - CLARIFY_AT, Component: ClarifyScreen },
  { name: "output", at: OUTPUT_AT, length: DURATION - OUTPUT_AT, Component: OutputScreen },
];

export const Hype: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { enter: enterConfig, minHeight } = scene.shell;
  const enter = spring({ frame, fps, config: { damping: enterConfig.damping, stiffness: enterConfig.stiffness, mass: enterConfig.mass } });
  return (
    <AbsoluteFill style={{ background: INK, overflow: "hidden" }}>
      <Audio src={staticFile("bed.wav")} volume={scene.audio.volume} />
      <Field frame={frame} />
      <AbsoluteFill style={{ opacity: enter, transform: `translateY(${interpolate(enter, [0, 1], [enterConfig.rise, 0])}px)` }}>
        <Shell>
          <div style={{ position: "relative", minHeight }}>
            {SCREENS.map(({ name, at, length, Component }, index) => {
              const last = index === SCREENS.length - 1;
              return (
                <Sequence key={name} from={at} durationInFrames={length + (last ? 0 : scene.transition.len)}>
                  <Screen length={length} fadeIn={index > 0} fadeOut={!last}>
                    <Component />
                  </Screen>
                </Sequence>
              );
            })}
          </div>
        </Shell>
      </AbsoluteFill>
      <Ripples />
      <Cursor />
    </AbsoluteFill>
  );
};
