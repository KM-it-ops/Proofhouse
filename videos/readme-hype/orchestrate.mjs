import { readFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const root = dirname(fileURLToPath(import.meta.url));
const repo = join(root, "..", "..");
const demo = join(repo, "examples", "readme-demo");
const objective = readFileSync(join(demo, "objective.txt"), "utf8").trim();
const prompt = readFileSync(join(demo, "prompt.txt"), "utf8").trim();
const answers = JSON.parse(readFileSync(join(demo, "answers.json"), "utf8"));
const hype = readFileSync(join(root, "remotion", "Hype.tsx"), "utf8");
const htmlFiles = ["index.html", "compositions/input.html", "compositions/clarify.html", "compositions/output.html"];
const html = htmlFiles
  .map((file) => readFileSync(join(root, file), "utf8"))
  .join("\n")
  .replaceAll("&amp;", "&");
const promptLines = prompt.split("\n").map((line) => line.trim()).filter(Boolean);

const missing = [];
for (const [file, text] of [
  ["remotion/Hype.tsx", hype],
  ["hyperframes", html],
]) {
  if (!text.includes(objective)) missing.push(`${file} missing objective`);
  for (const line of promptLines) {
    if (!text.includes(line)) missing.push(`${file} missing prompt line: ${line.slice(0, 72)}`);
  }
  for (const [question, answer] of Object.entries(answers)) {
    if (!text.includes(question)) missing.push(`${file} missing question: ${question}`);
    if (!text.includes(answer)) missing.push(`${file} missing answer: ${answer}`);
  }
  for (const banned of ["unverified", "not verified", "Not specified", "NOT SPECIFIED"]) {
    if (text.toLowerCase().includes(banned.toLowerCase())) missing.push(`${file} contains ${banned}`);
  }
}
if (missing.length > 0) {
  console.error(missing.join("\n"));
  process.exit(1);
}

const bed = spawnSync(process.execPath, ["generate-bed.mjs"], { cwd: root, stdio: "inherit" });
if (bed.status !== 0) process.exit(bed.status ?? 1);

console.log("orchestrate: copy matches the recorded run, bed.wav written");
console.log("next: npm run still -- --frame=90");
console.log("      npm run render:remotion -- ../../docs/assets/proofhouse-demo.mp4");
console.log("      npm run check && npm run render:hyperframes -- -o ../../docs/assets/proofhouse-demo.mp4");
