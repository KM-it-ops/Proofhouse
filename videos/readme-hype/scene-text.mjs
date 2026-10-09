// What text does each version actually put on screen? Read it out of each renderer, never out of a copy of it.
//   Hyperframes: the text nodes of the generated html.
//   Remotion:    the real remotion/Hype.tsx rendered to static markup at the frames where each state is settled
//                (typing finished, model switched, each answer counted, button busy, copied...).
import { createElement, createContext, useContext } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import * as real from "remotion";
import ts from "typescript";
import { createRequire } from "node:module";
import { readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { root } from "./build.mjs";

const require = createRequire(import.meta.url);

const decode = (text) =>
  text
    .replace(/&#x([0-9a-f]+);/gi, (_, hex) => String.fromCodePoint(parseInt(hex, 16)))
    .replace(/&#(\d+);/g, (_, dec) => String.fromCodePoint(Number(dec)))
    .replaceAll("&lt;", "<")
    .replaceAll("&gt;", ">")
    .replaceAll("&quot;", '"')
    .replaceAll("&amp;", "&");

// Text nodes, in document order. Spans marked data-inline are one run of text (the typed objective is one span per character).
export function textNodes(markup) {
  const flat = markup
    .replace(/<!--[\s\S]*?-->/g, "")
    .replace(/<(script|style|title)\b[\s\S]*?<\/\1>/g, "")
    .replace(/<span\b[^>]*\bdata-inline\b[^>]*>([\s\S]*?)<\/span>/g, "$1");
  return flat
    .split(/<[^>]+>/)
    .map((piece) => decode(piece).trim())
    .filter(Boolean);
}

export function hyperframesTexts() {
  const files = ["index.html", "compositions/input.html", "compositions/clarify.html", "compositions/output.html"];
  return new Set(files.flatMap((file) => textNodes(readFileSync(join(root, file), "utf8"))));
}

const FrameContext = createContext(0);

function remotionShim(scene) {
  return {
    interpolate: real.interpolate,
    Easing: real.Easing,
    spring: real.spring,
    staticFile: (name) => name,
    Audio: () => null,
    AbsoluteFill: ({ children, style }) => createElement("div", { style }, children),
    useCurrentFrame: () => useContext(FrameContext),
    useVideoConfig: () => ({ fps: scene.fps, width: scene.width, height: scene.height, durationInFrames: scene.durationFrames }),
    Sequence: ({ from = 0, durationInFrames = Infinity, children }) => {
      const frame = useContext(FrameContext);
      if (frame < from || frame >= from + durationInFrames) return null;
      return createElement(FrameContext.Provider, { value: frame - from }, children);
    },
  };
}

function loadHype(scene) {
  const file = join(root, "remotion", "Hype.tsx");
  const { outputText } = ts.transpileModule(readFileSync(file, "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2020, esModuleInterop: true },
  });
  const shim = remotionShim(scene);
  const requireFor = (id) => {
    if (id === "remotion") return shim;
    if (id.endsWith(".json")) return JSON.parse(readFileSync(resolve(dirname(file), id), "utf8"));
    return require(id);
  };
  const mod = { exports: {} };
  new Function("exports", "require", "module", outputText)(mod.exports, requireFor, mod);
  return mod.exports.Hype;
}

// Frames at which every piece of on-screen text has settled into one of its states.
export function probeFrames(scene) {
  const { input, clarify, output } = scene.screens;
  const bi = scene.beats.input;
  const bc = scene.beats.clarify;
  const bo = scene.beats.output;
  const answered = scene.run.answers.map((_, i) => clarify + bc.answerAt + i * bc.step + 2);
  return [
    input + 1,
    input + bi.typeTo,
    input + bi.modelSwitchAfter,
    input + bi.modelSwitchAfter + 2,
    input + bi.busyAt - 1,
    input + bi.busyAt + 1,
    clarify + 1,
    ...answered,
    output + bo.copiedAfter - 1,
    output + bo.copiedAfter + 2,
    output + bo.copiedBefore + 2,
    scene.durationFrames - 1,
  ];
}

export function remotionTexts(scene) {
  const Hype = loadHype(scene);
  const found = new Set();
  for (const frame of probeFrames(scene)) {
    const html = renderToStaticMarkup(createElement(FrameContext.Provider, { value: frame }, createElement(Hype)));
    for (const text of textNodes(html)) found.add(text);
  }
  return found;
}

// Every string the scene says should be seen, once.
export function expectedTexts(scene) {
  const strings = [];
  const walk = (value) => {
    if (typeof value === "string") strings.push(value);
    else if (Array.isArray(value)) value.forEach(walk);
    else if (value && typeof value === "object") Object.values(value).forEach(walk);
  };
  const { counter, ...clarifyCopy } = scene.copy.clarify;
  walk({ ...scene.copy, clarify: clarifyCopy });
  walk(scene.derived.counts);
  walk(scene.run.objective);
  scene.run.answers.forEach(({ question, answer }) => walk([question, answer]));
  walk(scene.run.promptLines.map((line) => line.trim()).filter(Boolean));
  return new Set(strings);
}
