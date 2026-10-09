// Merge scene.json with the recorded-run copy and write everything generated from it:
//   scene.generated.json            read by remotion/Hype.tsx and by the Hyperframes templates
//   index.html, compositions/*.html filled in from hyperframes/*.tpl.html
// All of these are gitignored; scene.json and the recorded run are the only sources of truth.
import { mkdirSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { spring } from "remotion";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

export const root = dirname(fileURLToPath(import.meta.url));
const demo = join(root, "..", "..", "examples", "readme-demo");

export function loadScene() {
  const scene = JSON.parse(readFileSync(join(root, "scene.json"), "utf8"));
  const answers = JSON.parse(readFileSync(join(demo, "answers.json"), "utf8"));
  scene.run = {
    objective: readFileSync(join(demo, "objective.txt"), "utf8").trim(),
    answers: Object.entries(answers).map(([question, answer]) => ({ question, answer })),
    promptLines: readFileSync(join(demo, "prompt.txt"), "utf8").trim().split(/\r?\n/).map((line) => line.trimEnd()),
  };
  // Remotion's spring() is the canonical easing; Hyperframes replays its sampled values frame by frame.
  const curve = (config, frames) =>
    Array.from({ length: frames }, (_, f) => Number(spring({ frame: f, fps: scene.fps, config }).toFixed(5)));
  scene.curves = {
    shellEnter: curve(scene.shell.enter, 90),
    loop: curve(scene.beats.input.loopSpring, 60),
    clarifyEnter: curve(scene.beats.clarify.enterSpring, 60),
  };
  // Hyperframes wants seconds: the three screens become mounted sub-compositions.
  const starts = Object.entries(scene.screens);
  const { pills, pillOn } = scene.copy.input;
  const { titles } = scene.copy.output;
  scene.derived = {
    durationSec: scene.durationFrames / scene.fps,
    screenW: scene.shell.width - 2 - 52, // shell border (1px x2) and horizontal padding (26px x2)
    chars: [...scene.run.objective],
    pills: pills.map((label, index) => ({ label, cls: index === pillOn ? "on" : "off" })),
    counts: Array.from({ length: scene.run.answers.length + 1 }, (_, n) =>
      scene.copy.clarify.counter.replace("{n}", String(n)).replace("{total}", String(scene.run.answers.length)),
    ),
    outLines: scene.run.promptLines.map((text) => ({
      text,
      cls: text === "" ? "gap" : titles.includes(text) ? "title" : "line",
    })),
    hosts: starts.map(([name, at], index) => ({
      name,
      start: at / scene.fps,
      dur: ((starts[index + 1]?.[1] ?? scene.durationFrames) - at + (starts[index + 1] ? scene.transition.len : 0)) / scene.fps,
    })),
  };
  return scene;
}

const esc = (value) =>
  String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");

// Tiny template language: {{a.b}} (escaped), {{{a.b}}} (raw), {{json a.b}}, and
// <!--each a.b-->...<!--/each--> where {{.key}} reads the item and {{@i}} its index.
function render(template, scene, scope = {}) {
  const look = (path) => {
    if (path === "@i") return scope.index;
    if (path === "*") return scene;
    const local = path.startsWith(".");
    let value = local ? scope.item : scene;
    for (const key of (local ? path.slice(1) : path).split(".").filter(Boolean)) value = value?.[key];
    return value;
  };
  let out = template.replace(/<!--each ([\w.]+)-->([\s\S]*?)<!--\/each-->/g, (_, path, body) =>
    look(path).map((item, index) => render(body, scene, { item, index })).join(""),
  );
  out = out.replace(/\{\{\{([\w.@*]+)\}\}\}/g, (_, path) => String(look(path)));
  out = out.replace(/\{\{json ([\w.@*]+)\}\}/g, (_, path) => JSON.stringify(look(path)));
  return out.replace(/\{\{([\w.@*]+)\}\}/g, (_, path) => {
    const value = look(path);
    if (value === undefined) throw new Error(`template: no value for {{${path}}}`);
    return esc(value);
  });
}

export function buildAll() {
  const scene = loadScene();
  writeFileSync(join(root, "scene.generated.json"), JSON.stringify(scene, null, 2));
  const src = join(root, "hyperframes");
  const lib = readFileSync(join(src, "lib.js"), "utf8");
  mkdirSync(join(root, "compositions"), { recursive: true });
  for (const file of readdirSync(src).filter((name) => name.endsWith(".tpl.html"))) {
    const name = file.replace(".tpl.html", "");
    const html = render(readFileSync(join(src, file), "utf8").replaceAll("/*LIB*/", lib), scene);
    writeFileSync(join(root, name === "index" ? "index.html" : join("compositions", `${name}.html`)), html);
  }
  return scene;
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  buildAll();
  console.log("build: scene.generated.json + Hyperframes html written");
}
