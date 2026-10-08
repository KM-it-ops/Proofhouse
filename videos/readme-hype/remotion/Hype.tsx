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

export const FPS = 30;
export const WIDTH = 1920;
export const HEIGHT = 1080;
export const DURATION = 42 * FPS;

const INPUT_AT = 0;
const CLARIFY_AT = 420;
const OUTPUT_AT = 840;

const INK = "#0a0f0c";
const CARD = "#0d1410";
const LINE = "#1e3a2a";
const MINT = "#c8f5d8";
const GREEN = "#3ddc84";
const DIM = "#5a8a6a";
const SOFT = "#8ab89a";

const OBJECTIVE = "I want to create an app like Facebook";

const ANSWERS: ReadonlyArray<readonly [string, string]> = [
  [
    "What should this prompt produce?",
    "A full goal with nonidempotent loops and instructions for production of a fully working Facebook clone.",
  ],
  ["Which pieces should it include?", "Let Grok decide."],
  ["Who is it for?", "Social media users."],
  ["Phone, web, or both?", "Both."],
  ["What must it avoid?", "Trademarked or registered copyrights and names."],
  ["Who chooses the stack?", "The agent chooses the stack."],
  ["Do people sign in?", "People sign in."],
];

const PROMPT = `Goal
Produce a fully working social app for social media users, on phone and on web, where people sign in. It must do what Facebook does. You choose the pieces. You choose the stack. Do not use trademarked or registered names, or copyrighted material, in the product.

Loop Structure
Trigger: start the next pass when the last build is saved and the app is still not finished.
Loop body: plan one slice, build it, and prove that slice runs. The loop is nonidempotent: each pass must change the product. Do not repeat a slice that already works.
Exit: stop only when a person can sign in on the phone and on the web and use the finished app. Finishing one slice does not end the loop.
Checkpoint: stop and ask before any name that could be trademarked or registered, and before a step that cannot be undone.
Memory: keep one notes file, one lesson per entry. When a slice fails or is confirmed, update that entry. Do not add a duplicate.

Security & Reliability
People sign in. Keep passwords out of this prompt and out of the notes file.`;

const mono = '"Cascadia Mono", Consolas, ui-monospace, monospace';

const clamp = { extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const };

const Field: React.FC<{ frame: number }> = ({ frame }) => {
  const dots = Array.from({ length: 56 }, (_, i) => {
    const x = ((i * 173) % 1920) + Math.sin(frame / 17 + i * 0.65) * 42;
    const y = ((i * 89) % 1080) + Math.cos(frame / 21 + i * 0.4) * 34;
    const bright = 0.25 + (Math.sin(frame / 11 + i) + 1) * 0.2;
    return { x, y, bright, size: 1.4 + (i % 4) * 0.7 };
  });
  const ripples = [340, 780];
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
      {ripples.map((at) => {
        const age = frame - at;
        if (age < 0 || age > 36) return null;
        const scale = interpolate(age, [0, 36], [0.15, 2.8]);
        return (
          <div
            key={at}
            style={{
              position: "absolute",
              left: at === 340 ? 960 : 960,
              top: at === 340 ? 760 : 820,
              width: 220,
              height: 220,
              marginLeft: -110,
              marginTop: -110,
              borderRadius: "50%",
              border: `2px solid ${GREEN}`,
              opacity: interpolate(age, [0, 36], [0.8, 0]),
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
        <div style={{ color: GREEN, fontWeight: 800, letterSpacing: 6, fontSize: 26 }}>PROOFHOUSE</div>
        <div style={{ width: 10, height: 18, background: GREEN, opacity: frame % 20 < 10 ? 1 : 0.2 }} />
      </div>
      <div style={{ color: DIM, fontSize: 14, marginTop: 6 }}>
        natural language in &gt; model-optimized prompt out &gt; refine until it's right
      </div>
    </div>
  );
};

const Shell: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const frame = useCurrentFrame();
  const spin = frame * 3;
  return (
    <div style={{ width: 1080, margin: "64px auto 0", position: "relative" }}>
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
  const typedCount = Math.floor(interpolate(frame, [24, 150], [0, OBJECTIVE.length], clamp));
  const modelOn = frame > 175;
  const loop = spring({ frame: frame - 210, fps: 30, config: { damping: 12, stiffness: 180 } });
  const pressed = frame > 300 && frame < 318;
  const loading = frame >= 318;
  return (
    <div style={{ border: `1px solid ${LINE}`, background: CARD, borderRadius: 8, padding: 22 }}>
      <div style={{ color: DIM, fontSize: 13, letterSpacing: 1.5, textTransform: "uppercase" }}>Objective</div>
      <div
        style={{
          marginTop: 8,
          minHeight: 92,
          border: `1px solid ${frame < 160 ? GREEN : LINE}`,
          borderRadius: 6,
          background: INK,
          color: MINT,
          fontSize: 20,
          padding: "12px 14px",
        }}
      >
        {OBJECTIVE.slice(0, typedCount)}
        {frame < 160 ? <Caret /> : null}
      </div>
      <div style={{ color: DIM, fontSize: 13, letterSpacing: 1.5, textTransform: "uppercase", marginTop: 16 }}>
        Target model / provider
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
        {modelOn ? "Grok 4.7" : "Claude Sonnet 5"}
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
          <span style={{ color: DIM, letterSpacing: 1 }}>LOOP / RECURRING TASK</span> — trigger, verify, exit, checkpoints
        </div>
      </div>
      <div style={{ color: DIM, fontSize: 13, letterSpacing: 1.5, textTransform: "uppercase", marginTop: 16 }}>
        Token efficiency
      </div>
      <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
        {["Efficient", "Balanced", "Thorough"].map((label) => {
          const on = label === "Efficient";
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
        {loading ? "Analyzing..." : "Initialize >"}
      </div>
    </div>
  );
};

const ClarifyScreen: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", color: DIM, fontSize: 13, marginBottom: 10 }}>
        <span>← back</span>
        <span>{Math.min(7, ANSWERS.filter((_, index) => frame > 18 + index * 16).length)}/7 answered</span>
      </div>
      {ANSWERS.map(([question, answer], index) => {
        const enter = spring({
          frame: frame - 10 - index * 16,
          fps,
          config: { damping: 14, stiffness: 140, mass: 0.6 },
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
  const lines = PROMPT.split("\n");
  const copied = frame > 300 && frame < 340;
  return (
    <div style={{ border: `1px solid ${LINE}`, background: CARD, borderRadius: 8, padding: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
        <div style={{ color: GREEN, letterSpacing: 2, fontSize: 13, fontWeight: 700 }}>OPTIMIZED PROMPT · GROK 4.7</div>
        <div style={{ color: copied ? GREEN : SOFT, fontSize: 13 }}>{copied ? "copied" : "copy"}</div>
      </div>
      <div style={{ color: MINT, fontSize: 15, lineHeight: 1.35 }}>
        {lines.map((line, index) => {
          const reveal = interpolate(frame, [12 + index * 2, 22 + index * 2], [100, 0], {
            ...clamp,
            easing: Easing.out(Easing.cubic),
          });
          const title = line === "Goal" || line === "Loop Structure" || line === "Security & Reliability";
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
      <div style={{ color: DIM, fontSize: 12, marginTop: 8 }}>~260 tokens (est.) · efficient mode · loop-structured</div>
    </div>
  );
};

const Cursor: React.FC = () => {
  const frame = useCurrentFrame();
  const stops = [
    { f: 0, x: 240, y: 180 },
    { f: 30, x: 760, y: 300 },
    { f: 170, x: 760, y: 430 },
    { f: 210, x: 250, y: 500 },
    { f: 300, x: 960, y: 700 },
    { f: 420, x: 700, y: 240 },
    { f: 760, x: 960, y: 860 },
    { f: 860, x: 1500, y: 220 },
  ];
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
  const click = [300, 760].some((at) => frame >= at && frame < at + 8);
  return (
    <div style={{ position: "absolute", left: x, top: y, zIndex: 8, transform: `scale(${click ? 0.85 : 1})` }}>
      <svg width="28" height="28" viewBox="0 0 24 24">
        <path d="M4 2 L4 18 L9 14 L13 22 L16 20 L12 12 L19 12 Z" fill={MINT} stroke={INK} strokeWidth="1" />
      </svg>
    </div>
  );
};

export const Hype: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const enter = spring({ frame, fps, config: { damping: 16, stiffness: 70, mass: 0.8 } });
  return (
    <AbsoluteFill style={{ background: INK, overflow: "hidden" }}>
      <Audio src={staticFile("bed.wav")} volume={0.45} />
      <Field frame={frame} />
      <AbsoluteFill style={{ opacity: enter, transform: `translateY(${interpolate(enter, [0, 1], [30, 0])}px)` }}>
        <Shell>
          <div style={{ position: "relative", minHeight: 640 }}>
            <Sequence from={INPUT_AT} durationInFrames={CLARIFY_AT}>
              <InputScreen />
            </Sequence>
            <Sequence from={CLARIFY_AT} durationInFrames={OUTPUT_AT - CLARIFY_AT}>
              <ClarifyScreen />
            </Sequence>
            <Sequence from={OUTPUT_AT} durationInFrames={DURATION - OUTPUT_AT}>
              <OutputScreen />
            </Sequence>
          </div>
        </Shell>
      </AbsoluteFill>
      <Cursor />
    </AbsoluteFill>
  );
};
