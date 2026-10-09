// Sound bed for the Studio cut, built from the same timeline as the picture.
// node --no-warnings studio/gen-audio.mjs  ->  public/studio-bed.wav
import fs from "node:fs";
import { makeTimeline, DURATION, FPS, HOOK, PANEL_IN, OUTPUT_AT, OUTRO_AT, OUTPUT, CLARIFY_AT, hash } from "./timeline.ts";
import { story } from "./story.ts";

const SR = 44100;
const tl = makeTimeline(story);
const n = Math.round((DURATION / FPS) * SR);
const L = new Float32Array(n);
const R = new Float32Array(n);
const T = (f) => f / FPS;

const add = (t, fn, dur, pan = 0) => {
  const s0 = Math.floor(t * SR);
  const len = Math.floor(dur * SR);
  for (let i = 0; i < len && s0 + i < n; i++) {
    const v = fn(i / SR, i / len);
    L[s0 + i] += v * (1 - Math.max(0, pan));
    R[s0 + i] += v * (1 + Math.min(0, pan));
  }
};
const TAU = Math.PI * 2;

// pad: slow A-minor chord that swells with the story
const notes = [110, 164.81, 220, 261.63, 329.63];
for (let i = 0; i < n; i++) {
  const t = i / SR;
  const f = t * FPS;
  const swell = 0.5 + 0.5 * Math.min(1, f / 150) * (f > OUTRO_AT ? 1 + 0.4 * Math.min(1, (f - OUTRO_AT) / 60) : 1);
  const fade = Math.min(1, (DURATION - f) / 40);
  let v = 0;
  notes.forEach((hz, k) => {
    v += Math.sin(TAU * hz * t + Math.sin(t * 0.3 + k) * 0.6) * (0.5 / (k + 1.4));
    v += Math.sin(TAU * hz * 1.004 * t) * (0.25 / (k + 1.4));
  });
  v *= 0.045 * swell * fade * (0.8 + 0.2 * Math.sin(t * 0.7));
  L[i] += v;
  R[i] += v;
}

const click = (f, hz = 900, vol = 0.22) =>
  add(T(f), (t, p) => Math.sin(TAU * hz * t) * Math.exp(-t * 60) * vol + (hash(t * 9000) - 0.5) * Math.exp(-t * 180) * vol, 0.09);
const tick = (f, k) => add(T(f), (t) => (hash(t * 7000 + k) - 0.5) * Math.exp(-t * 420) * 0.09 + Math.sin(TAU * (1900 + hash(k) * 700) * t) * Math.exp(-t * 300) * 0.025, 0.04, (hash(k + 5) - 0.5) * 0.4);
const whoosh = (f, dur = 0.7, vol = 0.14, up = true) => {
  let lp = 0;
  add(T(f), (t, p) => {
    const env = Math.sin(Math.PI * p) ** 2;
    const k = up ? 0.04 + 0.5 * p : 0.5 - 0.46 * p;
    lp += k * ((hash(t * 20000) - 0.5) * 2 - lp);
    return lp * env * vol * 2.5;
  }, dur);
};
const chime = (f, hz, vol = 0.12, dur = 1.6) =>
  add(T(f), (t) => (Math.sin(TAU * hz * t) + 0.35 * Math.sin(TAU * hz * 2.01 * t)) * Math.exp(-t * 3.2) * vol, dur);

tl.ticks.forEach((f, k) => tick(f, k));
tl.clicks.forEach((f) => click(f));
whoosh(PANEL_IN.at - 4, 0.9, 0.16, true);
whoosh(CLARIFY_AT - 14, 0.6, 0.11, true);
whoosh(OUTPUT_AT - 8, 0.8, 0.14, true);
whoosh(OUTRO_AT, 1.1, 0.16, false);
tl.rows.forEach((r) => chime(r.endAt + 3, 880, 0.05, 0.5));
chime(PANEL_IN.at + 10, 220, 0.14, 2);
tl.traces.forEach((t, i) => (t.wire ? chime(t.at + 6 + t.len * 0.8, 660 + 110 * i, 0.07, 0.9) : chime(t.at + 3, 988 + 40 * (i - 3), 0.035, 0.4)));
chime(OUTPUT.copyClick + 2, 784, 0.12, 1.2);
[523.25, 659.25, 783.99].forEach((hz, k) => chime(OUTRO_AT + 40 + k * 4, hz, 0.1, 2.4));

// normalise to -3 dB, soft limit
let pk = 0;
for (let i = 0; i < n; i++) pk = Math.max(pk, Math.abs(L[i]), Math.abs(R[i]));
const g = 0.7 / (pk || 1);
const buf = Buffer.alloc(44 + n * 4);
buf.write("RIFF", 0);
buf.writeUInt32LE(36 + n * 4, 4);
buf.write("WAVEfmt ", 8);
buf.writeUInt32LE(16, 16);
buf.writeUInt16LE(1, 20);
buf.writeUInt16LE(2, 22);
buf.writeUInt32LE(SR, 24);
buf.writeUInt32LE(SR * 4, 28);
buf.writeUInt16LE(4, 32);
buf.writeUInt16LE(16, 34);
buf.write("data", 36);
buf.writeUInt32LE(n * 4, 40);
for (let i = 0; i < n; i++) {
  buf.writeInt16LE(Math.round(Math.tanh(L[i] * g) * 32000), 44 + i * 4);
  buf.writeInt16LE(Math.round(Math.tanh(R[i] * g) * 32000), 46 + i * 4);
}
fs.mkdirSync("public", { recursive: true });
fs.writeFileSync("public/studio-bed.wav", buf);
console.log("wrote public/studio-bed.wav", (n / SR).toFixed(1) + "s", "peak", pk.toFixed(3));
