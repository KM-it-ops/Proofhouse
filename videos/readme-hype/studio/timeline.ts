// One timeline for the picture (Studio.tsx) and the sound (gen-audio.mjs). Frames at 30 fps.
// Erasable TypeScript only, so node can import it directly.

export const FPS = 30;
export const W = 1920;
export const H = 1080;
export const DURATION = 1320;

export type Pt = [number, number];
export type Sections = { title: string; paras: string[] }[];
export type Data = { objective: string; qa: { q: string; a: string }[]; sections: Sections };

export const hash = (n: number): number => {
  const x = Math.sin(n * 127.1 + 311.7) * 43758.5453;
  return x - Math.floor(x);
};

// Frame offset at which each character lands. Uneven on purpose: people do not type on a metronome.
export const charTimes = (text: string, cps: number, seed = 0): number[] => {
  const out: number[] = [];
  let t = 0;
  for (let i = 0; i < text.length; i++) {
    out.push(t);
    let gap = (30 / cps) * (0.5 + hash(i * 7.3 + seed));
    if (text[i] === " ") gap *= 1.25;
    if (text[i] === "," || text[i] === ".") gap += 3;
    t += gap;
  }
  out.push(t);
  return out;
};

export const typedCount = (times: number[], local: number): number => {
  let n = 0;
  for (let i = 0; i < times.length - 1; i++) {
    if (local >= times[i]) n = i + 1;
    else break;
  }
  return n;
};

// ---- stage geometry (stage = the 1920x1080 frame; local = inside the panel) ----
export const PANEL = { x: 320, y: 120, w: 1280, h: 840, xOut: 140, wOut: 1640, bar: 64 };
export const MODEL_RECT = { x: 64, y: 292, w: 620, h: 76 };
export const MENU = { x: 64, y: 376, w: 620, pad: 8, item: 58 };
export const BTN_RECT = { x: 64, y: 660, w: 340, h: 84 };
export const CHECK = { x: 64, y: 408, s: 34 };
export const PILL = { x: 64, y: 530, w: 190, h: 60, pad: 6 };
export const MODELS = ["Claude Opus 5", "Claude Sonnet 5", "GPT-5.6 Sol", "Gemini 3.8 Flash", "Grok 4.6", "Kimi K3"];
export const MODEL_FROM = 1;
export const MODEL_TO = 3;
export const rowTop = (i: number) => 168 + (i === 0 ? 0 : 130 + 80 * (i - 1));
export const rowH = (i: number) => (i === 0 ? 130 : 80);
export const CHIP = { x: 1008, y: 150, w: 568, h: 74, gap: 8 };
export const COPY_AT: Pt = [PANEL.xOut + 1500, PANEL.y + 108];

// ---- prompt column ----
export const CW = 12.89;
export const LH = 34;
export const COLS = 68;
export const PROMPT = { x: 64, y: 150, w: 900, h: 628 };

export type PLine = { kind: "title" | "text"; text: string; y: number; sec: number; para: number; from: number };

const wrap = (text: string, cols: number): { text: string; from: number }[] => {
  const out: { text: string; from: number }[] = [];
  let cur = "";
  let from = 0;
  let idx = 0;
  for (const word of text.split(" ")) {
    const next = cur ? cur + " " + word : word;
    if (next.length > cols && cur) {
      out.push({ text: cur, from });
      cur = word;
      from = idx;
    } else {
      if (!cur) from = idx;
      cur = next;
    }
    idx += word.length + 1;
  }
  if (cur) out.push({ text: cur, from });
  return out;
};

export const layoutPrompt = (sections: Sections) => {
  const lines: PLine[] = [];
  let y = 0;
  sections.forEach((s, si) => {
    if (si > 0) y += LH * 0.7;
    lines.push({ kind: "title", text: s.title, y, sec: si, para: -1, from: 0 });
    y += LH * 1.25;
    s.paras.forEach((p, pi) => {
      for (const w of wrap(p, COLS)) {
        lines.push({ kind: "text", text: w.text, y, sec: si, para: pi, from: w.from });
        y += LH;
      }
      y += LH * 0.35;
    });
  });
  return { lines, height: y };
};

export const findPhrase = (lines: PLine[], sec: number, para: number, phrase: string, text: string) => {
  const a = text.indexOf(phrase);
  if (a < 0) throw new Error("phrase not in prompt: " + phrase);
  const b = a + phrase.length;
  const rects: { x: number; y: number; w: number }[] = [];
  for (const l of lines) {
    if (l.sec !== sec || l.para !== para) continue;
    const s = Math.max(a, l.from);
    const e = Math.min(b, l.from + l.text.length);
    if (e > s) rects.push({ x: (s - l.from) * CW, y: l.y, w: (e - s) * CW });
  }
  return rects;
};

// ---- phases ----
export const HOOK = { kickerAt: 6, typeAt: 16, cps: 15, subAt: 104, morphAt: 132, morphLen: 40 };
export const PANEL_IN = { at: 128, len: 48 };
export const INPUT_AT = 172;
export const THINK = { pressAt: 392, busyAt: 394 };
export const CLARIFY_AT = 470;
export const SWITCH_LEN = 26;
export const OUTPUT_AT = 790;
export const OUTRO_AT = 1078;

export const OUTPUT = {
  gridAt: OUTPUT_AT + 4,
  revealAt: OUTPUT_AT + 30,
  traceAt: OUTPUT_AT + 62,
  traceLen: 26,
  cascadeStep: 8,
  copyClick: 1048,
  copiedLen: 22,
};

export const TRACES = [
  { q: 2, sec: 0, para: 0, phrase: 'plain, calm language with no hype', wire: true },
  { q: 4, sec: 2, para: 0, phrase: "Leave out the names of people outside the writer's team.", wire: true },
  { q: 5, sec: 2, para: 1, phrase: 'Never guess a number.', wire: true },
  { q: 0, sec: 0, para: 0, phrase: 'under 200 words', wire: false },
  { q: 1, sec: 0, para: 0, phrase: 'a director who reads on her phone', wire: false },
  { q: 3, sec: 0, para: 0, phrase: 'wins, blockers, and what the writer needs from her', wire: false },
  { q: 6, sec: 0, para: 0, phrase: 'End with one line saying what happens next.', wire: false },
];

export const makeTimeline = (d: Data) => {
  const P = (x: number, y: number): Pt => [PANEL.x + x, PANEL.y + y];
  const modelC = P(MODEL_RECT.x + 330, MODEL_RECT.y + 38);
  const item = (i: number): Pt => [PANEL.x + MENU.x + 260, PANEL.y + MENU.y + MENU.pad + MENU.item * (i + 0.5)];
  const chk = P(CHECK.x + 17, CHECK.y + 17);
  const pill = (i: number): Pt => P(PILL.x + PILL.pad + PILL.w * (i + 0.5), PILL.y + PILL.pad + 30);
  const btn = P(BTN_RECT.x + 190, BTN_RECT.y + 42);

  const objTimes = charTimes(d.objective, HOOK.cps, 3);

  // clarify rows: click into the row, type, move on
  const rows: { clickAt: number; typeAt: number; times: number[]; endAt: number; at: Pt }[] = [];
  let t = CLARIFY_AT + 28;
  d.qa.forEach((qa, i) => {
    const times = charTimes(qa.a, i === 0 ? 72 : 56, 11 + i);
    const at: Pt = [PANEL.x + 1060 + hash(i) * 70, PANEL.y + rowTop(i) + (i === 0 ? 62 : 46)];
    const typeAt = t + 5;
    const endAt = Math.round(typeAt + times[times.length - 1]);
    rows.push({ clickAt: t, typeAt, times, endAt, at });
    t = endAt + 8;
  });
  const clarifyEnd = rows[rows.length - 1].endAt;

  const stops: { f: number; p: Pt }[] = [
    { f: 168, p: [1790, 1060] },
    { f: 208, p: modelC },
    { f: 220, p: modelC },
    { f: 230, p: item(0) },
    { f: 238, p: item(1) },
    { f: 246, p: item(2) },
    { f: 254, p: item(4) },
    { f: 264, p: item(5) },
    { f: 278, p: item(3) },
    { f: 288, p: item(3) },
    { f: 316, p: chk },
    { f: 326, p: chk },
    { f: 352, p: pill(0) },
    { f: 362, p: pill(0) },
    { f: 388, p: btn },
    { f: 402, p: btn },
    { f: 440, p: [btn[0] + 300, btn[1] - 120] },
  ];
  rows.forEach((r, i) => {
    stops.push({ f: r.clickAt, p: r.at });
    stops.push({ f: Math.max(r.endAt, r.clickAt + 8), p: [r.at[0] + 8 + hash(i + 40) * 20, r.at[1] + 4] });
  });
  stops.push({ f: clarifyEnd + 26, p: [1500, 640] });
  // second visit: copy button
  stops.push({ f: OUTPUT_AT + 210, p: [1500, 980] });
  stops.push({ f: OUTPUT.copyClick - 8, p: COPY_AT });
  stops.push({ f: OUTPUT.copyClick + 10, p: COPY_AT });
  stops.push({ f: OUTPUT.copyClick + 40, p: [COPY_AT[0] + 120, COPY_AT[1] + 90] });

  const clicks = [
    214, 280, 318, 354, THINK.pressAt, ...rows.map((r) => r.clickAt), OUTPUT.copyClick,
  ];
  const visible: [number, number][] = [
    [172, clarifyEnd + 34],
    [OUTPUT_AT + 204, OUTPUT.copyClick + 44],
  ];

  const prompt = layoutPrompt(d.sections);
    const traces = TRACES.map((tr, i) => {
    const rects = findPhrase(prompt.lines, tr.sec, tr.para, tr.phrase, d.sections[tr.sec].paras[tr.para]);
    const last = rects[rects.length - 1];
    const at = i < 3 ? OUTPUT.traceAt + i * (OUTPUT.traceLen + 4) : OUTPUT.traceAt + 3 * (OUTPUT.traceLen + 4) + (i - 3) * OUTPUT.cascadeStep;
    const len = i < 3 ? OUTPUT.traceLen : 10;
    return {
      ...tr,
      at,
      len,
      rects,
      end: [PROMPT.x + last.x + last.w, PROMPT.y + last.y + LH / 2] as Pt,
      chip: [CHIP.x, CHIP.y + (CHIP.h + CHIP.gap) * tr.q + CHIP.h / 2] as Pt,
    };
  });

  // typing ticks for the sound track
  const ticks: number[] = [];
  objTimes.slice(0, -1).forEach((c) => ticks.push(HOOK.typeAt + c));
  rows.forEach((r) => r.times.slice(0, -1).forEach((c) => ticks.push(r.typeAt + c)));

  return { objTimes, rows, clarifyEnd, stops, clicks, visible, prompt, traces, ticks, modelC, item, chk, pill, btn };
};

export type Timeline = ReturnType<typeof makeTimeline>;
