import React, { useLayoutEffect, useRef, useState } from "react";
import { AbsoluteFill, Audio, Easing, interpolate, spring, staticFile } from "remotion";
import { MODEL_HEAD, story } from "./story";
import {
  BTN_RECT, CHECK, CHIP, CLARIFY_AT, COPY_AT, CW, DURATION, FPS, H, HOOK, INPUT_AT, LH, MENU, MODELS,
  MODEL_FROM, MODEL_RECT, MODEL_TO, OUTPUT, OUTPUT_AT, OUTRO_AT, PANEL, PANEL_IN, PILL, PROMPT, SWITCH_LEN,
  THINK, W, charTimes, hash, makeTimeline, typedCount, rowH, rowTop,
} from "./timeline";
import type { Pt } from "./timeline";

export { DURATION, FPS, H, W };

const tl = makeTimeline(story);

const G = "61, 220, 132";
const GREEN = "#3ddc84";
const MINT = "#c8f5d8";
const DIM = "#6f9a7e";
const SOFT = "#9cc7ab";
const INK = "#070b09";
const DISPLAY = 'Bahnschrift, "Segoe UI Variable Display", "Segoe UI", sans-serif';
const UI = '"Segoe UI Variable Text", "Segoe UI", system-ui, sans-serif';
const MONO = '"Cascadia Mono", Consolas, ui-monospace, monospace';

const clamp01 = (x: number) => Math.min(1, Math.max(0, x));
const ramp = (f: number, at: number, len: number) => clamp01((f - at) / len);
const eo = Easing.out(Easing.cubic);
const eio = Easing.inOut(Easing.cubic);
const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
const blur = (px: number) => (px > 0.05 ? `blur(${px}px)` : "none");
const pop = (f: number, at: number, len = 14) => spring({ frame: f - at, fps: FPS, config: { damping: 14, stiffness: 170, mass: 0.7 }, durationInFrames: len + 20 });

// ---------------------------------------------------------------- cursor path
const moveEase = Easing.bezier(0.4, 0, 0.2, 1.05);
const cursorAt = (f: number): Pt => {
  const s = tl.stops;
  if (f <= s[0].f) return s[0].p;
  const last = s[s.length - 1];
  if (f >= last.f) return last.p;
  let i = 0;
  while (s[i + 1].f < f) i++;
  const a = s[i];
  const b = s[i + 1];
  const dx = b.p[0] - a.p[0];
  const dy = b.p[1] - a.p[1];
  const dist = Math.hypot(dx, dy);
  if (dist < 1) return [a.p[0] + Math.sin(f / 9 + i) * 0.7, a.p[1] + Math.cos(f / 11 + i) * 0.7];
  const t = (f - a.f) / (b.f - a.f);
  const e = moveEase(t);
  const off = (hash(i * 3.1) - 0.5) * 2 * Math.min(110, dist * 0.2);
  const cx = (a.p[0] + b.p[0]) / 2 + (-dy / dist) * off;
  const cy = (a.p[1] + b.p[1]) / 2 + (dx / dist) * off;
  const u = 1 - e;
  const tremor = 1.4 * Math.sin(t * Math.PI);
  return [
    u * u * a.p[0] + 2 * u * e * cx + e * e * b.p[0] + Math.sin(f * 1.7 + i) * tremor,
    u * u * a.p[1] + 2 * u * e * cy + e * e * b.p[1] + Math.cos(f * 2.3 + i) * tremor,
  ];
};
const cursorAlpha = (f: number) =>
  Math.max(...tl.visible.map(([a, b]) => clamp01((f - a) / 8) * clamp01((b - f) / 8)));

type Rect = { x: number; y: number; w: number; h: number };
const hoverAmt = (f: number, r: Rect, ox = PANEL.x, oy = PANEL.y) => {
  let a = 0;
  let sum = 0;
  for (let k = 0; k < 7; k++) {
    const w = 1 - k / 7;
    const p = cursorAt(f - k);
    const inside = p[0] >= ox + r.x && p[0] <= ox + r.x + r.w && p[1] >= oy + r.y && p[1] <= oy + r.y + r.h;
    a += w * (inside ? 1 : 0);
    sum += w;
  }
  return (a / sum) * cursorAlpha(f);
};
const sinceClick = (f: number) => {
  for (const c of tl.clicks) if (f >= c && f < c + 9) return f - c;
  return -1;
};
const pressDepth = (f: number, c: number) => (f >= c && f < c + 9 ? Math.sin(((f - c) / 9) * Math.PI) : 0);

// ---------------------------------------------------------------- panel geometry over time
const panelProg = (f: number) => eio(ramp(f, OUTPUT_AT - 8, 34));
const panelX = (f: number) => lerp(PANEL.x, PANEL.xOut, panelProg(f));
const panelW = (f: number) => lerp(PANEL.w, PANEL.wOut, panelProg(f));

// ---------------------------------------------------------------- light that the backdrop follows
const bez = (p0: Pt, p1: Pt, p2: Pt, p3: Pt, t: number): Pt => {
  const u = 1 - t;
  return [
    u * u * u * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t * t * t * p3[0],
    u * u * u * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t * t * t * p3[1],
  ];
};
const wireGeom = (i: number) => {
  const tr = tl.traces[i];
  const ox = PANEL.xOut;
  const oy = PANEL.y;
  const last = tr.rects[tr.rects.length - 1];
  const p0: Pt = [ox + PROMPT.x + PROMPT.w + 12, oy + PROMPT.y + last.y + LH / 2 + 13];
  const p3: Pt = [ox + tr.chip[0] - 8, oy + tr.chip[1]];
  const dx = (p3[0] - p0[0]) * 0.55;
  const p1: Pt = [p0[0] + dx, p0[1]];
  const p2: Pt = [p3[0] - dx, p3[1]];
  return { p0, p1, p2, p3 };
};
const rawLight = (f: number): Pt => {
  const orbit: Pt = [960 + 560 * Math.sin(f / 52), 540 + 300 * Math.cos(f / 67)];
  if (f < HOOK.typeAt) return orbit;
  const hookEnd = HOOK.typeAt + tl.objTimes[tl.objTimes.length - 1];
  if (f < hookEnd + 6) {
    const frac = typedCount(tl.objTimes, f - HOOK.typeAt) / (tl.objTimes.length - 1);
    return [960 + (frac - 0.5) * 1400, 500];
  }
  if (f < tl.visible[0][0]) return orbit;
  if (f >= OUTPUT.traceAt && f < OUTPUT.traceAt + 150) {
    let idx = 0;
    tl.traces.forEach((t, i) => {
      if (f >= t.at) idx = i;
    });
    const t = tl.traces[idx];
    const g = wireGeom(idx);
    if (t.wire) return bez(g.p0, g.p1, g.p2, g.p3, eo(ramp(f, t.at + 6, t.len)));
    return [PANEL.xOut + t.chip[0], PANEL.y + t.chip[1]];
  }
  if (cursorAlpha(f) > 0.05) return cursorAt(f);
  return orbit;
};
const lightAt = (f: number): Pt => {
  let x = 0;
  let y = 0;
  for (let k = 0; k < 9; k++) {
    const p = rawLight(f - k * 1.5);
    x += p[0];
    y += p[1];
  }
  return [x / 9, y / 9];
};

const shocks: { at: number; p: Pt; power: number }[] = [
  { at: PANEL_IN.at + 6, p: [960, 560], power: 1.3 },
  { at: OUTPUT_AT, p: [960, 540], power: 1.1 },
  { at: OUTRO_AT, p: [960, 540], power: 1.5 },
  ...tl.clicks.map((c) => ({ at: c, p: cursorAt(c), power: 1 })),
];

// ---------------------------------------------------------------- backdrop
const COLS_N = 49;
const ROWS_N = 28;
const Backdrop: React.FC<{ f: number }> = ({ f }) => {
  const L = lightAt(f);
  const dots: React.ReactNode[] = [];
  const live = shocks.filter((s) => f >= s.at && f < s.at + 70);
  for (let gy = 0; gy < ROWS_N; gy++) {
    for (let gx = 0; gx < COLS_N; gx++) {
      let x = gx * 40;
      let y = gy * 40;
      const amb = Math.sin(f / 38 + gx * 0.33 + gy * 0.47);
      const ldx = x - L[0];
      const ldy = y - L[1];
      const d = Math.hypot(ldx, ldy) + 0.01;
      let glow = Math.exp(-(d * d) / (2 * 210 * 210));
      const push = 30 * Math.exp(-(d * d) / (2 * 120 * 120));
      x += (ldx / d) * push;
      y += (ldy / d) * push;
      for (const s of live) {
        const age = f - s.at;
        const cdx = x - s.p[0];
        const cdy = y - s.p[1];
        const r = Math.hypot(cdx, cdy) + 0.01;
        const w = Math.exp(-((r - age * 24) ** 2) / (2 * 60 * 60)) * Math.exp(-age / 30) * s.power;
        x += (cdx / r) * w * 26;
        y += (cdy / r) * w * 26;
        glow += w * 1.1;
      }
      const g = Math.min(glow, 1.6);
      const radius = 1.2 + g * 3 + (amb + 1) * 0.22;
      const alpha = Math.min(1, 0.13 + g * 0.8 + (amb + 1) * 0.035);
      dots.push(<circle key={gy * COLS_N + gx} cx={x} cy={y} r={radius} fill={g > 0.75 ? MINT : GREEN} opacity={alpha} />);
    }
  }
  return (
    <AbsoluteFill style={{ background: INK }}>
      <div style={{ position: "absolute", left: 1500 + Math.sin(f / 90) * 120, top: -260, width: 900, height: 900, borderRadius: "50%", background: "radial-gradient(circle, rgba(255,180,84,0.09), transparent 66%)" }} />
      <div style={{ position: "absolute", left: L[0] - 520, top: L[1] - 520, width: 1040, height: 1040, borderRadius: "50%", background: `radial-gradient(circle, rgba(${G},0.17), rgba(${G},0.04) 45%, transparent 68%)` }} />
      <svg width={W} height={H} style={{ position: "absolute", inset: 0 }}>{dots}</svg>
      <AbsoluteFill style={{ background: "radial-gradient(ellipse at center, transparent 55%, rgba(0,0,0,0.55))" }} />
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- small parts
const Caret: React.FC<{ f: number; solid?: boolean; h?: number; color?: string }> = ({ f, solid, h = 1, color = GREEN }) => (
  <span style={{ display: "inline-block", width: 3, height: `${h}em`, marginLeft: 3, marginRight: -6, verticalAlign: "-0.14em", background: color, opacity: solid || Math.floor(f / 15) % 2 === 0 ? 1 : 0 }} />
);

const Typed: React.FC<{ text: string; times: number[]; local: number; f: number; caret?: boolean }> = ({ text, times, local, f, caret }) => {
  const n = local < 0 ? 0 : typedCount(times, local);
  const typing = local >= 0 && local < times[times.length - 1] + 6;
  return (
    <span>
      <span>{text.slice(0, n)}</span>
      {caret && local >= 0 && <Caret f={f} solid={typing} />}
      <span style={{ opacity: 0 }}>{text.slice(n)}</span>
    </span>
  );
};

const Tick: React.FC<{ p: number; size: number; color?: string; width?: number }> = ({ p, size, color = INK, width = 3.2 }) => (
  <svg width={size} height={size} viewBox="0 0 34 34" style={{ display: "block" }}>
    <path d="M8 18 L15 25 L27 10" fill="none" stroke={color} strokeWidth={width} strokeLinecap="round" strokeLinejoin="round" pathLength={1} strokeDasharray="1" strokeDashoffset={1 - p} />
  </svg>
);

const Label: React.FC<{ children: React.ReactNode; x: number; y: number }> = ({ children, x, y }) => (
  <div style={{ position: "absolute", left: x, top: y, fontFamily: MONO, fontSize: 15, letterSpacing: 3, color: DIM, textTransform: "uppercase" }}>{children}</div>
);

const Chapter: React.FC<{ f: number; at: number; until: number; no: string; text: string; x: number }> = ({ f, at, until, no, text, x }) => {
  const out = ramp(f, until - 8, 8);
  if (f < at || out >= 1) return null;
  return (
    <div style={{ position: "absolute", left: x, top: 56, display: "flex", alignItems: "baseline", gap: 18, opacity: 1 - out, fontFamily: MONO, letterSpacing: 5, fontSize: 20 }}>
      <span style={{ color: GREEN, fontWeight: 700 }}>{no}</span>
      <span style={{ display: "flex" }}>
        {text.split("").map((c, i) => {
          const e = eo(ramp(f, at + i * 1.2, 10));
          return (
            <span key={i} style={{ whiteSpace: "pre", color: SOFT, opacity: e, transform: `translateY(${(1 - e) * 14}px)`, filter: blur((1 - e) * 5) }}>{c}</span>
          );
        })}
      </span>
    </div>
  );
};

// screen layers: enter and exit with depth, blur and a slide
const layer = (enter: number, exit: number, from: Pt, to: Pt): React.CSSProperties => {
  const e = 1 - enter;
  const op = enter * (1 - exit);
  return {
    position: "absolute",
    inset: 0,
    opacity: op,
    visibility: op < 0.002 ? "hidden" : "visible",
    transform: `translate(${from[0] * e + to[0] * exit}px, ${from[1] * e + to[1] * exit}px) scale(${1 - 0.04 * e - 0.05 * exit})`,
    filter: blur(e * 12 + exit * 12),
  };
};

// ---------------------------------------------------------------- input screen
const InputScreen: React.FC<{ f: number }> = ({ f }) => {
  const modelH = hoverAmt(f, MODEL_RECT);
  const openIn = eo(ramp(f, 214, 10));
  const open = openIn * (1 - eo(ramp(f, 282, 8)));
  const objFocus = 1 - ramp(f, 214, 8);
  const pickAt = 282;
  const swap = eio(ramp(f, pickAt, 14));
  const flash = 1 - ramp(f, pickAt, 40);
  const modelFocus = Math.max(open, flash * 0.8);
  const sel = f < pickAt ? MODEL_FROM : MODEL_TO;

  const menuTopStage = PANEL.y + MENU.y + MENU.pad;
  let snap = 0;
  for (let k = 0; k < 6; k++) snap += Math.max(0, Math.min(MODELS.length - 1, Math.floor((cursorAt(f - k)[1] - menuTopStage) / MENU.item)));
  snap /= 6;
  const menuHover = hoverAmt(f, { x: MENU.x, y: MENU.y, w: MENU.w, h: MENU.pad * 2 + MENU.item * MODELS.length });

  const chkP = eo(ramp(f, 318, 12));
  const chkPulse = ramp(f, 318, 22);
  const pillPos = lerp(1, 0, spring({ frame: f - 354, fps: FPS, config: { damping: 15, stiffness: 150, mass: 0.8 } }));
  const btnH = hoverAmt(f, BTN_RECT);
  const press = pressDepth(f, THINK.pressAt);
  const busy = eo(ramp(f, THINK.busyAt, 8));
  const clickPos = cursorAt(THINK.pressAt);
  const rip = ramp(f, THINK.pressAt, 22);

  return (
    <>
      <Label x={64} y={104}>Objective</Label>
      <div style={{ position: "absolute", left: 64, top: 132, width: 1152, height: 104, borderRadius: 18, border: `1.5px solid rgba(${G},${0.16 + 0.55 * objFocus})`, background: `rgba(${G},${0.035 + 0.03 * objFocus})`, boxShadow: `0 0 0 ${5 * objFocus}px rgba(${G},${0.1 * objFocus}), 0 0 50px rgba(${G},${0.2 * objFocus})` }} />
      <div style={{ position: "absolute", left: 92, top: 132, height: 104, display: "flex", alignItems: "center", fontFamily: DISPLAY, fontWeight: 600, fontSize: 36, color: MINT, whiteSpace: "nowrap", opacity: f >= INPUT_AT - 1 ? 1 : 0 }}>
        <span>{story.objective}</span>
        {f < 214 && <Caret f={f} />}
      </div>

      <Label x={64} y={264}>Target model / provider</Label>
      <div style={{ position: "absolute", left: MODEL_RECT.x, top: MODEL_RECT.y, width: MODEL_RECT.w, height: MODEL_RECT.h, borderRadius: 16, overflow: "hidden", border: `1.5px solid rgba(${G},${0.18 + 0.3 * modelH + 0.5 * modelFocus})`, background: `rgba(${G},${0.035 + 0.05 * modelH + 0.04 * modelFocus})`, boxShadow: `0 0 0 ${4 * modelFocus}px rgba(${G},${0.1 * modelFocus}), 0 0 ${40 * modelFocus}px rgba(${G},${0.22 * modelFocus})` }}>
        <div style={{ position: "absolute", left: 26, top: 0, height: "100%", display: "flex", alignItems: "center", fontFamily: UI, fontWeight: 600, fontSize: 28, color: MINT, transform: `translateY(${-swap * 34}px)`, opacity: 1 - swap }}>{MODELS[MODEL_FROM]}</div>
        <div style={{ position: "absolute", left: 26, top: 0, height: "100%", display: "flex", alignItems: "center", fontFamily: UI, fontWeight: 600, fontSize: 28, color: MINT, transform: `translateY(${(1 - swap) * 34}px)`, opacity: swap }}>{MODELS[MODEL_TO]}</div>
        <svg width={26} height={26} viewBox="0 0 26 26" style={{ position: "absolute", right: 22, top: 25, transform: `rotate(${open * 180}deg)` }}>
          <path d="M5 9 L13 17 L21 9" fill="none" stroke={SOFT} strokeWidth={2.6} strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </div>

      <div style={{ position: "absolute", left: CHECK.x, top: CHECK.y, display: "flex", alignItems: "center", gap: 20 }}>
        <div style={{ position: "relative", width: CHECK.s, height: CHECK.s, borderRadius: 9, border: `2px solid rgba(${G},${0.4 + 0.6 * chkP})`, background: `rgba(${G},${chkP})`, boxShadow: `0 0 ${24 * chkP}px rgba(${G},${0.45 * chkP})`, transform: `scale(${1 + 0.18 * Math.sin(chkPulse * Math.PI)})` }}>
          <div style={{ position: "absolute", inset: -2 }}><Tick p={chkP} size={CHECK.s} /></div>
        </div>
        <div style={{ fontFamily: MONO, fontSize: 19, letterSpacing: 1.5, whiteSpace: "nowrap" }}>
          <span style={{ color: GREEN, fontWeight: 700 }}>LOOP / RECURRING TASK</span>
          <span style={{ color: chkP > 0.5 ? SOFT : DIM }}> — trigger, verify, exit, checkpoints</span>
        </div>
      </div>

      <Label x={64} y={500}>Token efficiency</Label>
      <div style={{ position: "absolute", left: PILL.x, top: PILL.y, width: PILL.w * 3 + PILL.pad * 2, height: PILL.h + PILL.pad * 2, borderRadius: 18, border: `1.5px solid rgba(${G},0.16)`, background: "rgba(255,255,255,0.02)" }}>
        <div style={{ position: "absolute", left: PILL.pad + PILL.w * pillPos, top: PILL.pad, width: PILL.w, height: PILL.h, borderRadius: 13, background: `linear-gradient(180deg, rgba(${G},0.34), rgba(${G},0.2))`, border: `1.5px solid rgba(${G},0.7)`, boxShadow: `0 0 28px rgba(${G},0.25)` }} />
        {["Efficient", "Balanced", "Thorough"].map((t, i) => {
          const h = hoverAmt(f, { x: PILL.x + PILL.pad + PILL.w * i, y: PILL.y + PILL.pad, w: PILL.w, h: PILL.h });
          const near = 1 - Math.min(1, Math.abs(pillPos - i));
          return (
            <div key={t} style={{ position: "absolute", left: PILL.pad + PILL.w * i, top: PILL.pad, width: PILL.w, height: PILL.h, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: UI, fontWeight: 600, fontSize: 24, color: near > 0.5 ? MINT : lerp(0.55, 0.85, h) > 0 ? `rgba(156,199,171,${0.55 + 0.35 * h})` : SOFT }}>{t}</div>
          );
        })}
      </div>

      <div style={{ position: "absolute", left: BTN_RECT.x, top: BTN_RECT.y, width: BTN_RECT.w, height: BTN_RECT.h, borderRadius: 18, overflow: "hidden", transform: `translateY(${-3 * btnH}px) scale(${1 - 0.045 * press})`, background: `linear-gradient(180deg, #52e896, ${GREEN})`, boxShadow: `0 ${10 + 14 * btnH}px ${30 + 30 * btnH}px rgba(${G},${0.22 + 0.25 * btnH}), inset 0 1px 0 rgba(255,255,255,0.45)`, color: INK }}>
        <div style={{ position: "absolute", left: clickPos[0] - PANEL.x - BTN_RECT.x - 140 * rip, top: clickPos[1] - PANEL.y - BTN_RECT.y - 140 * rip, width: 280 * rip, height: 280 * rip, borderRadius: "50%", background: "rgba(255,255,255,0.5)", opacity: rip > 0 && rip < 1 ? 0.7 * (1 - rip) : 0 }} />
        <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: UI, fontWeight: 700, fontSize: 30, opacity: 1 - busy, transform: `translateY(${-busy * 18}px)` }}>Initialize &gt;</div>
        <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: UI, fontWeight: 700, fontSize: 30, opacity: busy, transform: `translateY(${(1 - busy) * 18}px)` }}>Analyzing...</div>
        {busy > 0 && (
          <div style={{ position: "absolute", top: 0, bottom: 0, width: 110, left: ((f - THINK.busyAt) * 9) % 460 - 110, background: "linear-gradient(100deg, transparent, rgba(255,255,255,0.55), transparent)" }} />
        )}
      </div>

      {open > 0.01 && (
        <div style={{ position: "absolute", left: MENU.x, top: MENU.y, width: MENU.w, height: MENU.pad * 2 + MENU.item * MODELS.length, borderRadius: 18, border: `1.5px solid rgba(${G},0.4)`, background: "linear-gradient(180deg, #101a14, #0b120e)", boxShadow: `0 30px 80px rgba(0,0,0,0.6), 0 0 50px rgba(${G},0.12)`, opacity: open, transform: `translateY(${(1 - open) * -14}px) scaleY(${0.94 + 0.06 * open})`, transformOrigin: "top", overflow: "hidden" }}>
          <div style={{ position: "absolute", left: 8, right: 8, top: MENU.pad + MENU.item * snap, height: MENU.item, borderRadius: 12, background: `rgba(${G},${0.2 * menuHover})`, border: `1px solid rgba(${G},${0.45 * menuHover})` }} />
          {MODELS.map((m, i) => {
            const e = eo(ramp(f, 216 + i * 2, 8));
            const isSel = i === sel;
            return (
              <div key={m} style={{ position: "absolute", left: 28, right: 24, top: MENU.pad + MENU.item * i, height: MENU.item, display: "flex", alignItems: "center", justifyContent: "space-between", fontFamily: UI, fontWeight: isSel ? 700 : 500, fontSize: 25, color: isSel ? MINT : SOFT, opacity: e, transform: `translateX(${(1 - e) * -16}px)` }}>
                <span>{m}</span>
                {isSel && <span style={{ color: GREEN }}><Tick p={1} size={28} color={GREEN} width={3} /></span>}
              </div>
            );
          })}
        </div>
      )}
    </>
  );
};

// ---------------------------------------------------------------- clarify screen
const ClarifyScreen: React.FC<{ f: number }> = ({ f }) => {
  const done = tl.rows.map((r) => f >= r.endAt + 3);
  const n = done.filter(Boolean).length;
  const lastDone = tl.rows.reduce((a, r) => (f >= r.endAt + 3 ? r.endAt + 3 : a), -99);
  const bump = Math.sin(clamp01((f - lastDone) / 12) * Math.PI);
  let frac = n;
  tl.rows.forEach((r, i) => {
    if (!done[i] && f >= r.typeAt) frac += clamp01((f - r.typeAt) / Math.max(1, r.endAt - r.typeAt));
  });
  return (
    <>
      <div style={{ position: "absolute", left: 64, top: 92, fontFamily: UI, fontSize: 22, color: DIM }}>← back</div>
      <div style={{ position: "absolute", right: 64, top: 84, fontFamily: MONO, fontSize: 24, letterSpacing: 1, color: MINT, transform: `scale(${1 + 0.14 * bump})`, transformOrigin: "right center", textShadow: `0 0 ${18 * bump}px rgba(${G},0.8)` }}>
        <span style={{ color: GREEN, fontWeight: 700 }}>{n}/7</span> answered
      </div>
      <div style={{ position: "absolute", left: 64, top: 136, width: 1152, height: 4, borderRadius: 2, background: `rgba(${G},0.12)` }}>
        <div style={{ width: `${(frac / 7) * 100}%`, height: "100%", borderRadius: 2, background: `linear-gradient(90deg, ${GREEN}, ${MINT})`, boxShadow: `0 0 16px rgba(${G},0.7)` }} />
      </div>
      {story.qa.map((qa, i) => {
        const r = tl.rows[i];
        const enter = eo(ramp(f, CLARIFY_AT - 6 + i * 3, 16));
        const active = f >= r.clickAt && !done[i];
        const act = eo(ramp(f, r.clickAt, 8)) * (done[i] ? 0 : 1);
        const chk = ramp(f, r.endAt + 3, 8);
        return (
          <div key={i} style={{ position: "absolute", left: 64, top: rowTop(i), width: 1152, height: rowH(i), opacity: enter, transform: `translateY(${(1 - enter) * 26}px)`, borderBottom: `1px solid rgba(${G},0.1)`, background: `linear-gradient(90deg, rgba(${G},${0.07 * act}), transparent 70%)` }}>
            <div style={{ position: "absolute", left: 0, top: 10, bottom: 12, width: 4, borderRadius: 2, background: GREEN, boxShadow: `0 0 18px ${GREEN}`, transform: `scaleY(${act})`, opacity: act }} />
            <div style={{ position: "absolute", left: 22, top: 16, width: 38, height: 38, borderRadius: "50%", border: `2px solid rgba(${G},${0.3 + 0.7 * Math.max(act, chk)})`, background: `rgba(${G},${chk})`, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: MONO, fontSize: 17, color: DIM }}>
              {chk < 0.05 ? i + 1 : null}
              <div style={{ position: "absolute", inset: 0, transform: "scale(1.12)" }}><Tick p={chk} size={38} /></div>
            </div>
            <div style={{ position: "absolute", left: 84, top: 8, fontFamily: UI, fontSize: 18, color: active ? SOFT : DIM, letterSpacing: 0.4 }}>{qa.q}</div>
            <div style={{ position: "absolute", left: 84, top: 34, width: 1020, fontFamily: UI, fontWeight: 500, fontSize: 28, lineHeight: "38px", color: MINT }}>
              <Typed text={qa.a} times={r.times} local={f - r.typeAt} f={f} caret={active} />
            </div>
          </div>
        );
      })}
    </>
  );
};

// ---------------------------------------------------------------- output screen
const promptChars = story.sections.reduce((a, s) => a + s.title.length + s.paras.join("").length, 0);
const OutputScreen: React.FC<{ f: number }> = ({ f }) => {
  const ox = PANEL.xOut;
  const copyRect = { x: 1432, y: 82, w: 136, h: 52 };
  const ch = hoverAmt(f, copyRect, ox);
  const copied = eo(ramp(f, OUTPUT.copyClick + 2, 8)) * (1 - ramp(f, OUTPUT.copyClick + OUTPUT.copiedLen + 20, 10));
  const press = pressDepth(f, OUTPUT.copyClick);
  const lastTrace = tl.traces[tl.traces.length - 1];
  const sweep = ramp(f, lastTrace.at + lastTrace.len + 6, 34);
  return (
    <>
      <div style={{ position: "absolute", left: 64, top: 90, fontFamily: MONO, fontWeight: 700, fontSize: 19, letterSpacing: 3.5, color: GREEN }}>{MODEL_HEAD}</div>
      <div style={{ position: "absolute", left: copyRect.x, top: copyRect.y, width: copyRect.w, height: copyRect.h, borderRadius: 14, overflow: "hidden", border: `1.5px solid rgba(${G},${0.3 + 0.4 * ch + 0.4 * copied})`, background: `rgba(${G},${0.05 + 0.1 * ch + 0.35 * copied})`, transform: `scale(${1 - 0.05 * press})`, boxShadow: `0 0 ${30 * copied}px rgba(${G},0.5)` }}>
        <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: MONO, fontSize: 21, color: SOFT, opacity: 1 - copied }}>copy</div>
        <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", gap: 6, fontFamily: MONO, fontSize: 21, color: MINT, opacity: copied }}>
          <Tick p={copied} size={24} color={MINT} width={3.4} />copied
        </div>
      </div>

      <svg width={PANEL.wOut} height={PANEL.h} style={{ position: "absolute", left: 0, top: 0, pointerEvents: "none", overflow: "visible" }}>
        {tl.traces.map((t, i) => {
          if (!t.wire) return null;
          const g = wireGeom(i);
          const d = `M ${g.p0[0] - ox} ${g.p0[1] - PANEL.y} C ${g.p1[0] - ox} ${g.p1[1] - PANEL.y}, ${g.p2[0] - ox} ${g.p2[1] - PANEL.y}, ${g.p3[0] - ox} ${g.p3[1] - PANEL.y}`;
          const p = eo(ramp(f, t.at + 6, t.len));
          const tip = bez(g.p0, g.p1, g.p2, g.p3, p);
          return (
            <g key={i} opacity={p > 0 ? 1 : 0}>
              <path d={d} fill="none" stroke={GREEN} strokeWidth={9} opacity={0.18} strokeLinecap="round" pathLength={1} strokeDasharray="1" strokeDashoffset={1 - p} />
              <path d={d} fill="none" stroke={MINT} strokeWidth={2.6} strokeLinecap="round" pathLength={1} strokeDasharray="1" strokeDashoffset={1 - p} />
              <path d={`M ${PROMPT.x + tl.traces[i].rects[tl.traces[i].rects.length - 1].x + tl.traces[i].rects[tl.traces[i].rects.length - 1].w} ${g.p0[1] - PANEL.y} L ${g.p0[0] - ox} ${g.p0[1] - PANEL.y}`} fill="none" stroke={MINT} strokeWidth={2} opacity={0.6} strokeLinecap="round" pathLength={1} strokeDasharray="1" strokeDashoffset={1 - Math.min(1, p * 5)} />
              <circle cx={g.p0[0] - ox} cy={g.p0[1] - PANEL.y} r={5} fill={MINT} opacity={Math.min(1, p * 6)} />
              {p < 1 && <circle cx={tip[0] - ox} cy={tip[1] - PANEL.y} r={7} fill={MINT} />}
            </g>
          );
        })}
      </svg>
      <div style={{ position: "absolute", left: PROMPT.x, top: PROMPT.y, width: PROMPT.w, height: PROMPT.h, overflow: "hidden" }}>
        {tl.prompt.lines.map((l, i) => {
          const e = eo(ramp(f, OUTPUT.revealAt + i * 3, 12));
          return (
            <div key={i} style={{ position: "absolute", left: 0, top: l.y, height: LH, lineHeight: `${LH}px`, whiteSpace: "pre", fontFamily: MONO, fontSize: l.kind === "title" ? 24 : 22, fontWeight: l.kind === "title" ? 700 : 400, color: l.kind === "title" ? GREEN : "rgba(200,245,216,0.9)", letterSpacing: l.kind === "title" ? 1 : 0, textShadow: "0 0 7px #0b120e, 0 0 3px #0b120e", opacity: e, transform: `translateY(${(1 - e) * 12}px)`, filter: blur((1 - e) * 5) }}>{l.text}</div>
          );
        })}
        {tl.traces.map((t, i) => {
          const p = eo(ramp(f, t.at, Math.max(8, t.len * 0.6)));
          return t.rects.map((r, k) => (
            <div key={`${i}-${k}`} style={{ position: "absolute", left: r.x - 3, top: r.y + 3, width: (r.w + 6) * p, height: LH - 6, borderRadius: 5, background: `rgba(${G},${0.2 * p})`, borderBottom: `2px solid rgba(${G},${0.9 * p})`, boxShadow: `0 0 ${18 * p}px rgba(${G},0.25)` }} />
          ));
        })}
        {sweep > 0 && sweep < 1 && (
          <div style={{ position: "absolute", left: 0, right: 0, top: -80 + sweep * (PROMPT.h + 160), height: 80, background: `linear-gradient(180deg, transparent, rgba(${G},0.14), transparent)` }} />
        )}
      </div>

      <Label x={CHIP.x} y={112}>From your answers</Label>
      {story.qa.map((qa, i) => {
        const e = eo(ramp(f, OUTPUT.gridAt + i * 3, 14));
        const tr = tl.traces.find((t) => t.q === i)!;
        const lit = tr.wire ? eo(ramp(f, tr.at + tr.len * 0.8, 8)) : eo(ramp(f, tr.at + 3, 7));
        return (
          <div key={i} style={{ position: "absolute", left: CHIP.x, top: CHIP.y + (CHIP.h + CHIP.gap) * i, width: CHIP.w, height: CHIP.h, borderRadius: 14, padding: "10px 18px", boxSizing: "border-box", opacity: e, transform: `translateX(${(1 - e) * 40}px) scale(${1 + 0.03 * Math.sin(lit * Math.PI)})`, border: `1.5px solid rgba(${G},${0.14 + 0.7 * lit})`, background: `rgba(${G},${0.025 + 0.1 * lit})`, boxShadow: `0 0 ${26 * lit}px rgba(${G},0.28)` }}>
            <div style={{ fontFamily: UI, fontSize: 15, color: lit > 0.5 ? SOFT : DIM, marginBottom: 3 }}>{qa.q}</div>
            <div style={{ fontFamily: UI, fontWeight: 600, fontSize: 18, lineHeight: "21px", color: lit > 0.5 ? MINT : SOFT, display: "-webkit-box", WebkitLineClamp: 1, WebkitBoxOrient: "vertical", overflow: "hidden" }}>{qa.a}</div>
          </div>
        );
      })}


      <div style={{ position: "absolute", left: 64, bottom: 30, fontFamily: MONO, fontSize: 16, letterSpacing: 1, color: DIM }}>
        ~{Math.round(promptChars / 4)} tokens (est.) · efficient mode · loop-structured
      </div>
    </>
  );
};

// ---------------------------------------------------------------- panel
const PanelFrame: React.FC<{ f: number }> = ({ f }) => {
  const pe = spring({ frame: f - PANEL_IN.at, fps: FPS, config: { damping: 17, stiffness: 80, mass: 0.9 } });
  const out = eio(ramp(f, OUTRO_AT, 36));
  const x = panelX(f);
  const w = panelW(f);
  const sw1 = eio(ramp(f, CLARIFY_AT - 14, SWITCH_LEN));
  const sw2 = eio(ramp(f, OUTPUT_AT - 8, SWITCH_LEN + 6));
  const scan = (p: number) => (p > 0 && p < 1 ? Math.sin(p * Math.PI) : 0);
  const sweepX = ramp(f, PANEL_IN.at + 14, 34);
  const think = ramp(f, THINK.busyAt, CLARIFY_AT - 10 - THINK.busyAt);
  const opacity = ramp(f, PANEL_IN.at, 8) * (1 - 0.5 * out);
  if (f < PANEL_IN.at) return null;
  const tf = `perspective(1700px) translate(${out * 500}px, ${(1 - pe) * 150 - out * 30}px) rotateX(${(1 - pe) * -58}deg) rotateY(${out * -17}deg) scale(${lerp(0.88, 1, pe) - out * 0.55})`;
  return (
    <div style={{ position: "absolute", left: x, top: PANEL.y, width: w, height: PANEL.h, opacity, transform: tf, filter: blur((1 - Math.min(1, pe)) * 14 + out * 3), padding: 2, borderRadius: 28, background: `conic-gradient(from ${f * 2.2}deg, rgba(${G},0) 0%, rgba(${G},0.85) 9%, rgba(${G},0) 22%, rgba(${G},0) 52%, rgba(200,245,216,0.5) 62%, rgba(${G},0) 74%)`, boxShadow: `0 50px 140px rgba(0,0,0,0.65), 0 0 90px rgba(${G},0.09)`, boxSizing: "border-box" }}>
      <div style={{ position: "relative", width: "100%", height: "100%", borderRadius: 26, overflow: "hidden", background: "linear-gradient(165deg, rgba(19,31,24,0.97), rgba(8,14,11,0.98))" }}>
        <div style={{ position: "absolute", left: 0, right: 0, top: 0, height: PANEL.bar, borderBottom: `1px solid rgba(${G},0.12)`, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: MONO, fontSize: 15, letterSpacing: 6, color: DIM }}>
          <div style={{ position: "absolute", left: 28, display: "flex", gap: 10 }}>
            {[0, 1, 2].map((i) => (<div key={i} style={{ width: 12, height: 12, borderRadius: "50%", background: i === 0 ? GREEN : `rgba(${G},0.22)`, boxShadow: i === 0 ? `0 0 12px ${GREEN}` : "none" }} />))}
          </div>
          PROOFHOUSE
        </div>
        <div style={layer(1, sw1, [0, 0], [0, -64])}><InputScreen f={f} /></div>
        <div style={layer(sw1, sw2, [0, 70], [-110, 0])}><ClarifyScreen f={f} /></div>
        <div style={layer(sw2, 0, [110, 0], [0, 0])}><OutputScreen f={f} /></div>
        {[sw1, sw2].map((s, i) => (
          <div key={i} style={{ position: "absolute", left: 0, right: 0, top: PANEL.bar + s * (PANEL.h - PANEL.bar), height: 3, opacity: scan(s), background: `linear-gradient(90deg, transparent, ${MINT}, transparent)`, boxShadow: `0 0 34px 8px rgba(${G},0.55)` }} />
        ))}
        {sweepX > 0 && sweepX < 1 && (
          <div style={{ position: "absolute", top: 0, bottom: 0, width: 360, left: -360 + sweepX * (w + 720), background: "linear-gradient(105deg, transparent 30%, rgba(255,255,255,0.16) 50%, transparent 70%)" }} />
        )}
        {think > 0 && think < 1 && (
          <div style={{ position: "absolute", left: 0, bottom: 0, height: 4, width: `${think * 100}%`, background: `linear-gradient(90deg, transparent, ${GREEN})`, boxShadow: `0 0 20px ${GREEN}` }} />
        )}
      </div>
    </div>
  );
};

// ---------------------------------------------------------------- hook (cold open)
const HOOK_FONT = 72;
const Hook: React.FC<{ f: number }> = ({ f }) => {
  const meas = useRef<HTMLSpanElement>(null);
  const [w, setW] = useState(1500);
  useLayoutEffect(() => {
    if (meas.current) setW(meas.current.getBoundingClientRect().width);
  }, []);
  const text = story.objective;
  const times = tl.objTimes;
  const local = f - HOOK.typeAt;
  const m = eio(ramp(f, HOOK.morphAt, HOOK.morphLen));
  if (f >= INPUT_AT) return null;
  const x0 = 960 - w / 2;
  const y0 = 500;
  const tx = (PANEL.x + 92 - x0) * m;
  const ty = (PANEL.y + 132 + 52 - y0) * m;
  const sc = lerp(1, 36 / HOOK_FONT, m);
  const kick = eo(ramp(f, HOOK.kickerAt, 14)) * (1 - ramp(f, HOOK.morphAt - 6, 10));
  const sub = eo(ramp(f, HOOK.subAt, 16)) * (1 - ramp(f, HOOK.morphAt - 4, 8));
  const hookEnd = HOOK.typeAt + times[times.length - 1];
  const n = local < 0 ? 0 : typedCount(times, local);
  return (
    <>
      <span ref={meas} style={{ position: "absolute", visibility: "hidden", whiteSpace: "nowrap", fontFamily: DISPLAY, fontWeight: 600, fontSize: HOOK_FONT }}>{text}</span>
      <div style={{ position: "absolute", left: 0, right: 0, top: 380, textAlign: "center", fontFamily: MONO, fontSize: 19, letterSpacing: 8, color: DIM, opacity: kick, transform: `translateY(${(1 - kick) * 12}px)` }}>THE WHOLE BRIEF</div>
      <div style={{ position: "absolute", left: x0, top: y0 - 50, height: 100, display: "flex", alignItems: "center", whiteSpace: "nowrap", fontFamily: DISPLAY, fontWeight: 600, fontSize: HOOK_FONT, color: MINT, transformOrigin: "0 50%", transform: `translate(${tx}px, ${ty}px) scale(${sc})`, textShadow: `0 0 ${40 * (1 - m)}px rgba(${G},0.35)` }}>
        {text.split("").map((c, i) => {
          const age = local - times[i];
          const e = i < n ? eo(clamp01(age / 7)) : 0;
          const caret = local >= 0 && m < 0.98 && i === n;
          return (
            <React.Fragment key={i}>
              {caret && <Caret f={f} solid={f < hookEnd + 6} h={0.95} />}
              <span style={{ whiteSpace: "pre", opacity: e, display: "inline-block", transform: `translateY(${(1 - e) * 18}px)`, filter: blur((1 - e) * 6) }}>{c}</span>
            </React.Fragment>
          );
        })}
        {local >= 0 && m < 0.98 && n >= text.length && <Caret f={f} solid={f < hookEnd + 6} h={0.95} />}
      </div>
      <div style={{ position: "absolute", left: 0, right: 0, top: 590, textAlign: "center", fontFamily: UI, fontSize: 34, color: SOFT, opacity: sub, transform: `translateY(${(1 - sub) * 16}px)`, letterSpacing: 0.5 }}>
        That is all you have to say.
      </div>
    </>
  );
};

// ---------------------------------------------------------------- outro
const OUTRO_LINES = ["Say it.", "Answer it.", "Trace it."];
const CMD1 = "uv tool install proofhouse";
const CMD2 = "proofhouse-compiler demo";
const Outro: React.FC<{ f: number }> = ({ f }) => {
  const l = f - OUTRO_AT;
  if (l < 0) return null;
  const t1 = charTimes(CMD1, 26, 5);
  const t2 = charTimes(CMD2, 26, 9);
  const c1 = 96;
  const c2 = c1 + t1[t1.length - 1] + 26;
  const foot = eo(ramp(l, c2 + t2[t2.length - 1] + 12, 18));
  const brand = eo(ramp(l, 4, 14));
  return (
    <>
      <div style={{ position: "absolute", left: 120, top: 92, fontFamily: MONO, fontWeight: 700, fontSize: 22, letterSpacing: 9, color: GREEN, opacity: brand, transform: `translateY(${(1 - brand) * -10}px)` }}>PROOFHOUSE</div>
      {OUTRO_LINES.map((t, i) => {
        const e = eo(ramp(l, 12 + i * 11, 20));
        return (
          <div key={t} style={{ position: "absolute", left: 120, top: 200 + i * 150, fontFamily: DISPLAY, fontWeight: 600, fontSize: 132, lineHeight: "140px", color: i === 2 ? GREEN : MINT, opacity: e, transform: `translateY(${(1 - e) * 60}px)`, filter: blur((1 - e) * 10), textShadow: i === 2 ? `0 0 60px rgba(${G},0.45)` : "none", whiteSpace: "nowrap" }}>{t}</div>
        );
      })}
      {[[CMD1, t1, c1, 690], [CMD2, t2, c2, 770]].map(([cmd, ts, at, y]) => {
        const lt = l - (at as number);
        const e = eo(ramp(l, (at as number) - 8, 12));
        const times = ts as number[];
        return (
          <div key={cmd as string} style={{ position: "absolute", left: 120, top: y as number, height: 64, padding: "0 28px", display: "flex", alignItems: "center", borderRadius: 16, border: `1.5px solid rgba(${G},0.3)`, background: "rgba(10,18,13,0.85)", fontFamily: MONO, fontSize: 30, color: MINT, opacity: e, transform: `translateY(${(1 - e) * 14}px)`, boxShadow: `0 0 40px rgba(${G},0.1)` }}>
            <span style={{ color: GREEN, marginRight: 16 }}>$</span>
            <Typed text={cmd as string} times={times} local={lt} f={f} caret={lt >= 0 && lt < times[times.length - 1] + 40} />
          </div>
        );
      })}
      <div style={{ position: "absolute", left: 120, top: 880, fontFamily: MONO, fontSize: 21, letterSpacing: 1.5, color: SOFT, opacity: foot, transform: `translateY(${(1 - foot) * 10}px)` }}>
        local · no API key · MIT · github.com/KM-it-ops/Proofhouse
      </div>
    </>
  );
};

// ---------------------------------------------------------------- cursor
const CursorLayer: React.FC<{ f: number }> = ({ f }) => {
  const a = cursorAlpha(f);
  if (a < 0.01) return null;
  const p = cursorAt(f);
  const sc = sinceClick(f);
  const press = sc >= 0 ? 1 - 0.18 * Math.sin((sc / 9) * Math.PI) : 1;
  const rings = tl.clicks.filter((c) => f >= c && f < c + 30);
  return (
    <>
      {[1, 2, 3, 4, 5, 6].map((k) => {
        const q = cursorAt(f - k * 1.6);
        return <div key={k} style={{ position: "absolute", left: q[0] - 11 + k, top: q[1] - 11 + k, width: 22 - k * 2.4, height: 22 - k * 2.4, borderRadius: "50%", background: `rgba(${G},${0.16 - k * 0.022})`, opacity: a, filter: "blur(3px)" }} />;
      })}
      {rings.map((c) => {
        const q = cursorAt(c);
        const r = (f - c) / 30;
        return <div key={c} style={{ position: "absolute", left: q[0] - 8 - r * 70, top: q[1] - 8 - r * 70, width: 16 + r * 140, height: 16 + r * 140, borderRadius: "50%", border: `2px solid rgba(${G},${0.8 * (1 - r)})`, boxShadow: `0 0 20px rgba(${G},${0.5 * (1 - r)})` }} />;
      })}
      <svg width={34} height={34} viewBox="0 0 34 34" style={{ position: "absolute", left: p[0] - 3, top: p[1] - 2, opacity: a, transform: `scale(${press})`, transformOrigin: "3px 2px", filter: "drop-shadow(0 4px 7px rgba(0,0,0,0.55))" }}>
        <path d="M3 2 L3 24 L8.8 18.6 L12.6 27.4 L16.6 25.6 L12.8 17 L21 17 Z" fill="#f4fff8" stroke="#06100a" strokeWidth={1.8} strokeLinejoin="round" />
      </svg>
    </>
  );
};

// ---------------------------------------------------------------- root
export const Studio: React.FC = () => {
  const f = useFrameSafe();
  let cx = 0;
  let cy = 0;
  for (let k = 0; k < 8; k++) {
    const p = cursorAt(f - k * 2);
    cx += p[0];
    cy += p[1];
  }
  cx /= 8;
  cy /= 8;
  const calm = 1 - ramp(f, OUTRO_AT - 6, 34);
  const act = ramp(f, PANEL_IN.at, 10);
  const rotY = ((cx - 960) / 960) * 2.2 * calm * act;
  const rotX = (-(cy - 540) / 540) * 1.5 * calm * act;
  const push = 1 + 0.05 * eio(ramp(f, 150, OUTPUT_AT + 200 - 150)) * calm + 0.012 * Math.sin(f / 70);
  const endFade = 1 - ramp(f, DURATION - 14, 14);
  const hookIn = eo(ramp(f, 0, 14));
  return (
    <AbsoluteFill style={{ background: INK, overflow: "hidden", opacity: endFade * hookIn + (1 - hookIn) * 0 }}>
      <Audio src={staticFile("studio-bed.wav")} volume={0.9} />
      <Backdrop f={f} />
      <AbsoluteFill style={{ transform: `perspective(2200px) rotateX(${rotX}deg) rotateY(${rotY}deg) scale(${push})`, transformOrigin: "50% 50%" }}>
        <Hook f={f} />
        <Chapter f={f} at={INPUT_AT} until={CLARIFY_AT} no="01" text="SAY IT" x={PANEL.x} />
        <Chapter f={f} at={CLARIFY_AT} until={OUTPUT_AT} no="02" text="ANSWER SEVEN QUESTIONS" x={PANEL.x} />
        <Chapter f={f} at={OUTPUT_AT} until={OUTRO_AT - 4} no="03" text="FROM YOUR ANSWERS" x={PANEL.xOut} />
        <PanelFrame f={f} />
        <Outro f={f} />
        <CursorLayer f={f} />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

import { useCurrentFrame } from "remotion";
function useFrameSafe(): number {
  return useCurrentFrame();
}
void interpolate;
void pop;
void lerp;
