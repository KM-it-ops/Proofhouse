import { spawnSync } from "node:child_process";
import { buildAll, root } from "./build.mjs";
import { expectedTexts, hyperframesTexts, remotionTexts } from "./scene-text.mjs";

const scene = buildAll();
const expected = expectedTexts(scene);
const shown = { "remotion/Hype.tsx": remotionTexts(scene), hyperframes: hyperframesTexts() };

const missing = [];
// The one name that is written twice in the scene (model field, output header) must agree.
if (!scene.copy.output.head.toLowerCase().includes(scene.copy.input.modelAfter.toLowerCase())) {
  missing.push(`scene: output header "${scene.copy.output.head}" does not name the model "${scene.copy.input.modelAfter}"`);
}
for (const [name, texts] of Object.entries(shown)) {
  const blob = [...texts].join("\n");
  // The recorded run must be on screen in full.
  if (!blob.includes(scene.run.objective)) missing.push(`${name} missing objective`);
  for (const line of scene.run.promptLines.map((l) => l.trim()).filter(Boolean)) {
    if (!blob.includes(line)) missing.push(`${name} missing prompt line: ${line.slice(0, 72)}`);
  }
  for (const { question, answer } of scene.run.answers) {
    if (!blob.includes(question)) missing.push(`${name} missing question: ${question}`);
    if (!blob.includes(answer)) missing.push(`${name} missing answer: ${answer}`);
  }
  for (const banned of ["unverified", "not verified", "Not specified", "NOT SPECIFIED"]) {
    if (blob.toLowerCase().includes(banned.toLowerCase())) missing.push(`${name} contains ${banned}`);
  }
  // Both versions must show exactly the text the scene declares: nothing dropped, nothing hard-coded on the side.
  for (const text of expected) if (!texts.has(text)) missing.push(`${name} does not show: ${text.slice(0, 72)}`);
  for (const text of texts) if (!expected.has(text)) missing.push(`${name} shows text the scene does not declare: ${text.slice(0, 72)}`);
}
if (missing.length > 0) {
  console.error(missing.join("\n"));
  process.exit(1);
}

const bed = spawnSync(process.execPath, ["generate-bed.mjs"], { cwd: root, stdio: "inherit" });
if (bed.status !== 0) process.exit(bed.status ?? 1);

console.log(`orchestrate: both versions show the same ${expected.size} strings as the scene; bed.wav written`);
console.log("next: npm run still -- --frame=90");
console.log("      npm run render:remotion -- ../../docs/assets/proofhouse-demo.mp4");
console.log("      npm run check && npm run render:hyperframes -- -o ../../docs/assets/proofhouse-demo.mp4");
