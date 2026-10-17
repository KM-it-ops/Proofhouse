#!/usr/bin/env node
// Acceptance check for the dashboard browser tests (completion criterion C9).
//
// A browser test that always passes is worse than no test. This script proves the
// tests in e2e/*.spec.ts both pass and can fail:
//   1. They must pass on the real dashboard.
//   2. They must fail on copies of the dashboard broken on purpose, each one caught
//      by the test group that is meant to catch it:
//        focus      focus outline removed          -> [keyboard]
//        width      fixed 1200 px width            -> [phone-width]
//        motion     animation ignores reduced motion -> [reduced-motion]
//        error      unknown ?world= value crashes  -> [error-state]
//
// Every test title must start with one of those four tags. Run from apps/dashboard:
//   node e2e/check-tests-have-teeth.mjs            (everything)
//   node e2e/check-tests-have-teeth.mjs --only=real|focus|width|motion|error
// Exit 0 = all checks passed, 1 = something failed. Servers bind to 127.0.0.1 only.

import { spawnSync } from "node:child_process";
import {
  appendFileSync,
  cpSync,
  existsSync,
  lstatSync,
  mkdirSync,
  mkdtempSync,
  readdirSync,
  readFileSync,
  rmSync,
  symlinkSync,
  unlinkSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";

const appDir = path.resolve(import.meta.dirname, "..");
const repoRoot = path.resolve(appDir, "..", "..");
const e2eDir = path.join(appDir, "e2e");
const playwrightCli = path.join(appDir, "node_modules", "@playwright", "test", "cli.js");
const tscCli = path.join(appDir, "node_modules", "typescript", "bin", "tsc");
const basePort = Number(process.env.E2E_BASE_PORT ?? 4180);

const MIN_TESTS = { "[keyboard]": 1, "[phone-width]": 5, "[reduced-motion]": 5, "[error-state]": 1 };
const TAGS = Object.keys(MIN_TESTS);

const VARIANTS = [
  {
    key: "focus",
    name: "focus outline removed",
    tag: "[keyboard]",
    edits: [{ file: "src/styles.css", append: "\n*, *:focus, *:focus-visible { outline: none !important; }\n" }],
  },
  {
    key: "width",
    name: "fixed 1200 px width",
    tag: "[phone-width]",
    edits: [{ file: "src/styles.css", append: "\n.arsenal-shell { width: 1200px !important; }\n" }],
  },
  {
    key: "motion",
    name: "animation ignores reduced motion",
    tag: "[reduced-motion]",
    edits: [{ file: "src/styles.css", append: "\n.brand-glyph { animation: spin 2s linear infinite !important; }\n" }],
  },
  {
    key: "error",
    name: "unknown ?world= value crashes the page",
    tag: "[error-state]",
    edits: [
      {
        file: "src/App.tsx",
        from: ': "overdrive";\n}',
        to: ': requested === null ? "overdrive" : (() => { throw new Error("unknown world"); })();\n}',
      },
    ],
  },
];

const only = process.argv.find((a) => a.startsWith("--only="))?.slice("--only=".length);
const failures = [];
const fail = (message) => {
  failures.push(message);
  console.log(`  FAIL: ${message}`);
};

function staticChecks() {
  console.log("static checks");
  const specs = existsSync(e2eDir) ? readdirSync(e2eDir).filter((f) => f.endsWith(".spec.ts")) : [];
  if (specs.length === 0) {
    fail("no e2e/*.spec.ts files");
    return;
  }
  for (const file of specs) {
    const text = readFileSync(path.join(e2eDir, file), "utf8");
    if (/(:|\bas|<)\s*any\b/.test(text)) fail(`${file} uses the type "any"`);
  }
  const tsc = spawnSync(process.execPath, [tscCli, "-p", "e2e/tsconfig.json"], { cwd: appDir, encoding: "utf8" });
  if (tsc.status !== 0) fail(`tsc -p e2e/tsconfig.json failed:\n${(tsc.stdout + tsc.stderr).trim().split("\n").slice(0, 15).join("\n")}`);
  else console.log(`  ok: ${specs.length} spec file(s), strict TypeScript, no "any"`);
}

function specsOf(suite, out = []) {
  out.push(...(suite.specs ?? []));
  for (const child of suite.suites ?? []) specsOf(child, out);
  return out;
}

const stripAnsi = (s) => s.replace(/\u001b\[[0-9;]*m/g, "");

// Runs the whole Playwright suite against the app in `dir` and returns a plain summary.
function runSuite(dir, port, reportFile) {
  rmSync(reportFile, { force: true });
  const run = spawnSync(process.execPath, [playwrightCli, "test", "--reporter=json"], {
    cwd: appDir,
    env: { ...process.env, E2E_APP_DIR: dir, E2E_PORT: String(port), PLAYWRIGHT_JSON_OUTPUT_NAME: reportFile },
    encoding: "utf8",
    timeout: 300_000,
    maxBuffer: 64 * 1024 * 1024,
  });
  let report = null;
  if (existsSync(reportFile)) {
    try {
      report = JSON.parse(readFileSync(reportFile, "utf8"));
    } catch {
      report = null;
    }
  }
  const specs = (report?.suites ?? []).flatMap((s) => specsOf(s)).map((spec) => {
    const passed = spec.tests.length > 0 && spec.tests.every((t) => t.status === "expected" && t.results.at(-1)?.status === "passed");
    const message = stripAnsi(spec.tests[0]?.results?.[0]?.error?.message ?? "").split("\n")[0].slice(0, 160);
    return { title: spec.title, passed, message };
  });
  const tail = stripAnsi(`${run.stderr ?? ""}\n${run.stdout ?? ""}`).trim().split("\n").slice(-12).join("\n");
  return { exit: run.status, specs, globalErrors: report?.errors?.length ?? (report ? 0 : 1), tail };
}

function countByTag(specs) {
  const counts = Object.fromEntries(TAGS.map((t) => [t, 0]));
  for (const s of specs) {
    const tag = TAGS.find((t) => s.title.startsWith(t));
    if (tag) counts[tag] += 1;
  }
  return counts;
}

function makeBrokenCopy(variant, tmpRoot) {
  const root = path.join(tmpRoot, variant.key);
  const dest = path.join(root, "apps", "dashboard");
  mkdirSync(path.join(root, "loadouts"), { recursive: true });
  cpSync(path.join(repoRoot, "loadouts", "legendary_loadouts.json"), path.join(root, "loadouts", "legendary_loadouts.json"));
  const skip = new Set(["node_modules", "dist", "test-results", "playwright-report", "backups", "e2e"]);
  cpSync(appDir, dest, { recursive: true, filter: (src) => !skip.has(path.basename(src)) });
  symlinkSync(path.join(appDir, "node_modules"), path.join(dest, "node_modules"), "junction");
  for (const edit of variant.edits) {
    const target = path.join(dest, edit.file);
    if (edit.append !== undefined) {
      appendFileSync(target, edit.append);
    } else {
      const before = readFileSync(target, "utf8").replace(/\r\n/g, "\n");
      if (!before.includes(edit.from)) throw new Error(`mutation target not found in ${edit.file}: the break would be a no-op`);
      writeFileSync(target, before.replace(edit.from, edit.to));
    }
  }
  return dest;
}

// The copy's node_modules is a link to the real one: remove the link first so the
// recursive delete can never reach the real folder.
function removeCopies(tmpRoot) {
  for (const entry of existsSync(tmpRoot) ? readdirSync(tmpRoot) : []) {
    const link = path.join(tmpRoot, entry, "apps", "dashboard", "node_modules");
    try {
      if (lstatSync(link).isSymbolicLink()) unlinkSync(link);
    } catch {
      // no link to remove
    }
  }
  rmSync(tmpRoot, { recursive: true, force: true });
}

staticChecks();
if (failures.length > 0) {
  console.log("\nRESULT: FAIL (fix the static checks first)");
  process.exit(1);
}

const tmpRoot = mkdtempSync(path.join(tmpdir(), "proofhouse-dashboard-teeth-"));
let realTotal = 0;
try {
  if (!only || only === "real") {
    console.log("real dashboard: every test must pass");
    const real = runSuite(appDir, basePort, path.join(tmpRoot, "real.json"));
    realTotal = real.specs.length;
    if (real.globalErrors > 0 || real.specs.length === 0) {
      fail(`no usable report (exit ${real.exit}):\n${real.tail}`);
    } else {
      for (const s of real.specs.filter((x) => !x.passed)) fail(`${s.title}: ${s.message}`);
      for (const s of real.specs.filter((x) => !TAGS.some((t) => x.title.startsWith(t)))) fail(`untagged test: ${s.title}`);
      const counts = countByTag(real.specs);
      for (const tag of TAGS) if (counts[tag] < MIN_TESTS[tag]) fail(`${tag} needs at least ${MIN_TESTS[tag]} test(s), found ${counts[tag]}`);
      if (real.exit !== 0 && failures.length === 0) fail(`playwright exited ${real.exit}`);
      if (failures.length === 0) console.log(`  ok: ${real.specs.length} tests passed ${JSON.stringify(counts)}`);
    }
  }

  let index = 0;
  for (const variant of VARIANTS) {
    index += 1;
    if (only && only !== variant.key) continue;
    console.log(`broken copy "${variant.name}": ${variant.tag} must fail`);
    let dir;
    try {
      dir = makeBrokenCopy(variant, tmpRoot);
    } catch (error) {
      fail(String(error.message ?? error));
      continue;
    }
    const broken = runSuite(dir, basePort + index, path.join(tmpRoot, `${variant.key}.json`));
    if (broken.globalErrors > 0 || broken.specs.length === 0) {
      fail(`copy did not run the tests (exit ${broken.exit}):\n${broken.tail}`);
      continue;
    }
    if (realTotal > 0 && broken.specs.length !== realTotal) {
      fail(`ran ${broken.specs.length} tests on the copy but ${realTotal} on the real dashboard`);
      continue;
    }
    const failed = broken.specs.filter((s) => !s.passed);
    const caught = failed.filter((s) => s.title.startsWith(variant.tag));
    const others = failed.filter((s) => !s.title.startsWith(variant.tag));
    if (caught.length === 0) fail(`no ${variant.tag} test noticed the break (${failed.length} other failure(s))`);
    else console.log(`  ok: caught by ${caught.length} ${variant.tag} test(s), e.g. "${caught[0].title}"`);
    if (others.length > 0) console.log(`  note: ${others.length} test(s) outside ${variant.tag} also failed on this copy`);
  }
} finally {
  removeCopies(tmpRoot);
}

if (!existsSync(path.join(appDir, "node_modules", "@playwright", "test", "cli.js"))) {
  fail("the real node_modules went missing during the run");
}
console.log(failures.length === 0 ? "\nRESULT: PASS" : `\nRESULT: FAIL (${failures.length} problem(s))`);
process.exit(failures.length === 0 ? 0 : 1);
