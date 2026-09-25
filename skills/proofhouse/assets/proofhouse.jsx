import { useRef, useState } from "react";
import { Terminal, Copy, RefreshCw, Check, AlertTriangle, Loader2, ChevronRight, ArrowLeft, History } from "lucide-react";

// ---------------------------------------------------------------------------
// Model-specific prompting knowledge injected into every API call so the
// optimizer respects real behavioral differences between targets.
// ---------------------------------------------------------------------------
// model-notes:begin
const MODEL_NOTES = {
  "Claude Fable 5.1":
    "Long-horizon / science / unattended runs. 1M context, 128k output (`claude-fable-5-1`), thinking always on (disabled returns 400), default effort high, $10/$50, slower than Opus 5. State goals and success criteria, not steps -- over-specifying degrades it. Cyber + bio classifiers remain; life-sciences R&D is redirected to Opus 5 or Mythos 5.1 trusted access. Never ask it to echo/explain hidden reasoning as response text. Define explicit pause-vs-continue checkpoints for long tasks. Reach for it when Opus 5 at higher effort still fails evals.",
  "Claude Mythos 5.1":
    "Same model as Fable 5.1, with looser cyber/bio safeguards, restricted to trusted-org programs (CVP / LSVP). Same prompting patterns as Fable 5.1.",
  "Claude Opus 5":
    "Anthropic's default for complex agentic coding. 1M context, 128k output (`claude-opus-5`), thinking on by default (disable only at effort high or below), default effort high, $5/$25. Give the full task spec and let it run -- it finishes rather than stubbing. Drop redundant generic 'double-check your work' wording (it causes over-verification); keep every user-required test, acceptance check and approval gate. Cap subagent spawns; it delegates eagerly. Ask for concise progress explicitly; default replies run long. Constrain scope on large jobs or it will expand them. Step up to Fable 5.1 only when Opus 5 at higher effort still fails evals.",
  "Claude Sonnet 5":
    "Fast, capable default. Concise, direct instructions; doesn't need heavy scaffolding. Good for genuine iteration.",
  "Claude Haiku 4.5":
    "Optimized for speed/cost. Keep prompts narrow; break multi-stage work into smaller discrete requests.",
  "GPT-5.6 Sol":
    "Flagship GPT-5.6 (`gpt-5.6-sol`; the `gpt-5.6` alias routes here). Outcome, constraints, evidence, and completion bar -- not step lists. Lean system prompts; strip repeated rules and unused examples. More concise than 5.5 by default -- skip blanket 'be concise'; control length with `text.verbosity`. Define autonomy/approval bounds (it is proactive on multi-step work). `reasoning.effort` default medium; high/xhigh only when evals gain; reserve max. Personality vs collaboration as separate short blocks. Programmatic Tool Calling only for bounded reduction of large tool results, not every tool loop. Keep reusable prefixes stable for prompt caching.",
  "GPT-5.6 Terra":
    "Balanced GPT-5.6 default for most apps (`gpt-5.6-terra`). Same prompting contract as Sol: outcome-first, lean prompts, `text.verbosity`, explicit autonomy bounds. Prefer Terra over Sol unless hard reasoning, coding, or tool coordination fails evals. Same 1M context / 128k output family. Start `reasoning.effort` at medium and test one step lower before stepping up.",
  "GPT-5.6 Luna":
    "Fast/cheap GPT-5.6 (`gpt-5.6-luna`). Same family prompting patterns, but keep the task narrow. Best for classification, extraction, transformation, and batch work with automated validation -- not high-error-cost agentic coding unless evals hold. Same verbosity/effort/caching levers as Sol/Terra; default effort medium and prefer `none`/`low` when quality holds.",
  "GPT-5.5":
    "Legacy. Explicit system/developer instructions, clear output format, few-shot examples for style-sensitive output. Prefer the GPT-5.6 family unless a workload is pinned here.",
  "Gemini 3.8 Flash":
    "Google workhorse (`gemini-3.8-flash`), 1M context, 65k output, intro $0.75/$3.75. Reasoning model -- concise direct instructions; legacy CoT scaffolding hurts. Control depth with `thinking_level` (low/medium/high), not temperature/top_p (ignored on 3.x). Put instructions after large context; anchor with 'Based on the preceding information...'. Higher effort uses more tokens by design. Separate stable system instructions from per-call variable content for caching. Add 2026 date + Jan 2025 knowledge-cutoff clauses for time-sensitive or strictly grounded tasks per Google docs.",
  "Grok 4.6":
    "xAI frontier (`grok-4.6`), 500K context, image+text in, reasoning low/medium/high (default)/xhigh, $2/$6 per MTok below 200K prompt tokens (entire request doubles above 200K). Agentic coding and long-horizon work -- outcome-first with explicit stop/approval bounds. Set `prompt_cache_key` or `x-grok-conv-id` for cache affinity on multi-turn loops. Compact context before the 200K cliff on long agent runs. Available via xAI API, Cursor, OpenRouter.",
  "Muse Spark 1.3":
    "Meta frontier (`muse-spark-1.3`, xhigh GA; max after safety testing), 1M context, text/image/video in, Meta Model API + Muse Code. Self-corrects, asks clarifying questions, confirms before consequential actions. Do not over-script tool loops (~20% fewer vs 1.2). Standard endpoint keeps data private; Contributor is cheaper but may train Meta products. Lean outcome prompts with explicit autonomy and escalation bounds.",
  "Kimi K3":
    "Moonshot open frontier (`kimi-k3`), 2.8T MoE, 1M context, native vision, $0.30 cache-hit / $3 input / $15 output per MTok. Long-horizon coding and agentic work -- best with Kimi Code harness. Default max thinking at launch; use low/high effort when available. Outcome and evidence bar, not micromanaged steps. Structure a stable prefix for Mooncake cache hits.",
  "Gemini":
    "Legacy/generic Google. Prefer Gemini 3.8 Flash for current Flash work. Explicit structure, clear formatting, grounding context up front. Verify against current Google docs for anything critical.",
  "Claude Fable 5":
    "Legacy. Mythos-tier, built for long autonomous self-verifying runs, not rapid back-and-forth. State goals/success criteria, not steps -- over-specifying degrades it. Default effort: high (xhigh for the hardest work). Delegates to subagents on its own. Benefits from a persistent lessons file across sessions. Runs safety classifiers on offensive-cybersecurity and bio/life-science content that can flag legitimate defensive/detection work -- frame technique descriptions defensively. Never ask it to echo/explain its internal reasoning as response text (risks refusal fallback to Opus 4.8). Define explicit pause-vs-continue checkpoints for long tasks.",
  "Claude Mythos 5":
    "Legacy. Same model as Fable 5, without the added cyber/bio safety layer, restricted to trusted orgs. Same prompting patterns as Fable 5.",
  "Claude Opus 4.8":
    "Legacy. Strong general reasoning. Benefits from clear step structure, explicit success criteria, worked examples for style-sensitive tasks. Less suited to fully autonomous multi-hour runs than Fable 5.",
  "Other":
    "No verified vendor-specific behavior available. General best practice: explicit goal, constraints, format, audience. Note in rationale that this is generic guidance.",
};
// model-notes:end

const MODEL_OPTIONS = Object.keys(MODEL_NOTES);

// Model this artifact calls. Must be a real Anthropic Messages API model id the host
// accepts, not a marketing name. A host can override it with window.PROOFHOUSE_MODEL.
const ARTIFACT_MODEL =
  (typeof window !== "undefined" && window.PROOFHOUSE_MODEL) || "claude-sonnet-4-6";

// Universal token-discipline directive, applied to every call this tool makes AND
// baked into every prompt it produces. Two separate concerns: (1) keep Proofhouse's
// own API usage lean, (2) make the compiled prompt itself token-efficient to run.
const TOKEN_DISCIPLINE = `Apply strict token discipline, in your own output and in the prompt you produce: eliminate redundant framing, merge overlapping constraints into single directives, never restate information already established, and default to the shortest phrasing that fully preserves meaning. Where the target model supports prompt caching (e.g., Claude models via cache_control), structure the compiled prompt so stable/reusable instructions are clearly separated from per-call variable content, and say so explicitly in settings. Do not pad with filler transitions, meta-commentary about your own process, hedging, or restated instructions.`;

const EFFICIENCY_PRESETS = {
  efficient: { label: "Efficient", questionCount: "6-10", promptWordCap: 250, note: "tightest possible prompt, minimum viable questions" },
  balanced: { label: "Balanced", questionCount: "10-16", promptWordCap: 500, note: "standard coverage" },
  thorough: { label: "Thorough", questionCount: "14-22", promptWordCap: 800, note: "maximum coverage, more explicit guardrails" },
};

// Loop-engineering directive: only injected when the task is recurring/autonomous
// rather than a one-shot request. Structures the compiled prompt as trigger ->
// loop body -> exit condition -> checkpoint, with a compounding-memory mechanism.
const LOOP_ENGINEERING = `This is a recurring or autonomous loop task, not a one-shot request. Structure the compiled prompt with an explicit loop shape: (1) Trigger/cadence -- what starts each iteration (schedule, event, or manual invocation), (2) Loop body -- plan, act, verify each iteration against evidence rather than assuming success, (3) Exit/stop condition -- what ends the loop entirely, distinct from what ends one iteration, (4) Checkpoint/escalation -- what's severe or ambiguous enough to interrupt the loop and involve the human. Include a compounding-memory mechanism (a running notes file: one lesson per entry, corrections and confirmed approaches alike, update rather than duplicate) so later iterations benefit from earlier ones. Label this section "Loop Structure" in the compiled prompt.`;

// validators:begin
// Pure helpers: no React, no network. tests/test_artifact_validators.py runs
// this block under node. Model responses are untrusted input (review F10):
// every response is parsed and schema-checked before it reaches state, and
// only answers to questions that are currently visible reach compilation.
const QUESTION_TYPES = ["single_select", "multi_select", "text"];
const MAX_QUESTIONS = 40;
const REQUEST_TIMEOUT_MS = 90000;
const POLICY_PRECEDENCE =
  "Precedence: never remove or weaken the user's mandatory requirements, acceptance checks, tests, permission or approval gates, or verification steps they asked for. Model-specific notes and token discipline may only trim redundant wording, never a required gate.";

function invalid(error) {
  return { ok: false, error };
}

function parseModelJSON(text) {
  if (typeof text !== "string" || !text.trim()) return invalid("the model returned an empty response");
  const cleaned = text.replace(/```json/gi, "").replace(/```/g, "").trim();
  try {
    return { ok: true, value: JSON.parse(cleaned) };
  } catch (_) {
    return invalid("the model's response was not complete JSON (it may have been cut off)");
  }
}

function validateQuestionGroups(value) {
  if (!Array.isArray(value) || value.length === 0) return invalid("expected a non-empty list of question groups");
  const byId = new Map();
  const groups = [];
  for (let gi = 0; gi < value.length; gi += 1) {
    const group = value[gi];
    if (!group || typeof group !== "object" || typeof group.group !== "string" || !group.group.trim()) {
      return invalid(`question group ${gi + 1} has no name`);
    }
    if (!Array.isArray(group.questions) || group.questions.length === 0) {
      return invalid(`question group "${group.group}" has no questions`);
    }
    const questions = [];
    for (const q of group.questions) {
      if (!q || typeof q !== "object") return invalid(`group "${group.group}" contains a non-object question`);
      if (typeof q.id !== "string" || !/^[a-z][a-z0-9_]{0,63}$/.test(q.id)) {
        return invalid(`question id ${JSON.stringify(q.id)} is not short_snake_case`);
      }
      if (byId.has(q.id)) return invalid(`duplicate question id ${q.id}`);
      if (typeof q.text !== "string" || !q.text.trim()) return invalid(`question ${q.id} has no text`);
      if (!QUESTION_TYPES.includes(q.type)) return invalid(`question ${q.id} has unknown type ${JSON.stringify(q.type)}`);
      const options = q.options === undefined || q.options === null ? [] : q.options;
      if (!Array.isArray(options) || !options.every((o) => typeof o === "string" && o.trim())) {
        return invalid(`question ${q.id} options must be non-empty strings`);
      }
      if (new Set(options).size !== options.length) return invalid(`question ${q.id} repeats an option`);
      if (q.type === "text" && options.length > 0) return invalid(`text question ${q.id} must not have options`);
      if (q.type !== "text" && options.length < 2) return invalid(`question ${q.id} needs at least two options`);
      const normalized = { id: q.id, text: q.text, type: q.type, options, dependsOn: q.dependsOn ?? null };
      byId.set(q.id, normalized);
      questions.push(normalized);
    }
    groups.push({ group: group.group, questions });
  }
  if (byId.size > MAX_QUESTIONS) return invalid(`too many questions (${byId.size}; limit ${MAX_QUESTIONS})`);
  for (const q of byId.values()) {
    const dep = q.dependsOn;
    if (dep === null) continue;
    if (typeof dep !== "object" || typeof dep.questionId !== "string" || !Array.isArray(dep.values) || dep.values.length === 0) {
      return invalid(`question ${q.id} has a malformed dependsOn`);
    }
    const parent = byId.get(dep.questionId);
    if (!parent) return invalid(`question ${q.id} depends on unknown question ${dep.questionId}`);
    if (parent.id === q.id) return invalid(`question ${q.id} depends on itself`);
    if (parent.type === "text") return invalid(`question ${q.id} branches on free-text question ${parent.id}`);
    if (!dep.values.every((v) => parent.options.includes(v))) {
      return invalid(`question ${q.id} depends on values that ${parent.id} does not offer`);
    }
  }
  for (const start of byId.values()) {
    const seen = new Set();
    let cur = start;
    while (cur && cur.dependsOn) {
      if (seen.has(cur.id)) return invalid(`question dependencies form a cycle at ${cur.id}`);
      seen.add(cur.id);
      cur = byId.get(cur.dependsOn.questionId);
    }
  }
  return { ok: true, value: groups };
}

function questionIndex(groups) {
  const byId = {};
  for (const g of groups || []) for (const q of g.questions || []) byId[q.id] = q;
  return byId;
}

function isVisible(q, answers, byId, depth = 0) {
  if (!q.dependsOn) return true;
  if (depth > MAX_QUESTIONS) return false;
  const parent = byId[q.dependsOn.questionId];
  if (!parent || !isVisible(parent, answers, byId, depth + 1)) return false;
  const parentVal = answers[q.dependsOn.questionId];
  if (parentVal === undefined || parentVal === null) return false;
  const values = q.dependsOn.values || [];
  if (Array.isArray(parentVal)) return values.some((v) => parentVal.includes(v));
  return values.includes(parentVal);
}

function hasAnswer(v) {
  return v !== undefined && v !== null && v !== "" && !(Array.isArray(v) && v.length === 0);
}

// Answers the user can currently see. A hidden branch's stale answer never reaches compilation.
function visibleAnswers(groups, answers) {
  const byId = questionIndex(groups);
  const out = {};
  for (const q of Object.values(byId)) {
    if (isVisible(q, answers, byId) && hasAnswer(answers[q.id])) out[q.id] = answers[q.id];
  }
  return out;
}

function formatAnswers(answers) {
  return Object.entries(answers)
    .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(", ") : v}`)
    .join("\n");
}

function validateCompiledVersion(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return invalid("expected a JSON object with a prompt");
  if (typeof value.prompt !== "string" || !value.prompt.trim()) return invalid("the response has no prompt text");
  const out = { prompt: value.prompt };
  for (const key of ["rationale", "settings", "efficiency"]) {
    if (value[key] === undefined || value[key] === null) out[key] = "";
    else if (typeof value[key] === "string") out[key] = value[key];
    else return invalid(`${key} must be text`);
  }
  return { ok: true, value: out };
}

// Revision context (review F11): the clarifying answers ride along with every self-heal request.
function buildRevisionUser({ rawRequest, answeredText, previousPrompt, feedback, estimate }) {
  return (
    `Original request: "${rawRequest}"\n\n` +
    `Clarifying answers from the original compile (still in force unless the feedback below changes one; name any conflict in the rationale):\n${answeredText || "(none provided)"}\n\n` +
    `Previous optimized prompt (~${estimate} tokens):\n${previousPrompt}\n\n` +
    `User feedback on that version: "${feedback}"\n\n` +
    "Diagnose what's wrong (scope mismatch, wrong tone, missing constraint, too rigid, too vague, model mismatch, security gap, token bloat/too verbose, or other) and produce a revised version that fixes it. Reflect the diagnosis briefly in the rationale."
  );
}
// validators:end

function estimateTokens(text) {
  return Math.ceil((text || "").length / 4);
}

async function researchModel(name, signal) {
  const response = await fetch("https://api.anthropic.com/v1/messages", {
    signal,
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model: ARTIFACT_MODEL,
      max_tokens: 1000,
      tools: [{ type: "web_search_20250305", name: "web_search" }],
      messages: [
        {
          role: "user",
          content: `Research the AI model/provider "${name}". Find its known prompting best practices, behavioral quirks, context window, and anything a prompt engineer should know to optimize prompts for it specifically. Write ONE dense paragraph under 120 words, in this style: "Fast, capable default model for most tasks. Responds well to concise, direct instructions and doesn't need heavy scaffolding." Return ONLY that paragraph -- no preamble, no markdown, no citations, no "based on my research."`,
        },
      ],
    }),
  });
  if (!response.ok) throw new Error(`Research API error: ${response.status}`);
  const data = await response.json();
  const text = (data.content || [])
    .filter((b) => b.type === "text")
    .map((b) => b.text)
    .join(" ")
    .trim();
  if (!text) throw new Error("No research result returned");
  return text;
}

async function callClaude(system, user, signal) {
  const response = await fetch("https://api.anthropic.com/v1/messages", {
    signal,
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model: ARTIFACT_MODEL,
      max_tokens: 1000,
      system,
      messages: [{ role: "user", content: user }],
    }),
  });
  if (!response.ok) throw new Error(`API error: ${response.status}`);
  const data = await response.json();
  const text = (data.content || [])
    .filter((b) => b.type === "text")
    .map((b) => b.text)
    .join("\n");
  if (!text) throw new Error("Empty response");
  return text;
}

function requestErrorMessage(e) {
  if (e && e.name === "AbortError") return "the request was cancelled or timed out; nothing was changed, try again";
  return e && e.message ? e.message : String(e);
}

export default function Proofhouse() {
  const [screen, setScreen] = useState("input"); // input | clarify | output
  const [rawRequest, setRawRequest] = useState("");
  const [targetModel, setTargetModel] = useState("Claude Opus 5");
  const [customModel, setCustomModel] = useState("");
  const [questionGroups, setQuestionGroups] = useState([]);
  const [answers, setAnswers] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [versions, setVersions] = useState([]); // {prompt, rationale, settings, feedback}
  const [activeVersion, setActiveVersion] = useState(0);
  const [feedbackText, setFeedbackText] = useState("");
  const [showFeedback, setShowFeedback] = useState(false);
  const [copied, setCopied] = useState(false);
  const [efficiencyMode, setEfficiencyMode] = useState("balanced"); // efficient | balanced | thorough
  const [loopMode, setLoopMode] = useState(false);
  const [resolvedModelNotes, setResolvedModelNotes] = useState("");
  const [modelSource, setModelSource] = useState("builtin"); // builtin | cached | researched | fallback
  const [researching, setResearching] = useState(false);
  const abortRef = useRef(null);

  // One in-flight request at a time, with a timeout and a user-visible cancel.
  async function guarded(run) {
    const controller = new AbortController();
    abortRef.current = controller;
    const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
    try {
      return await run(controller.signal);
    } finally {
      clearTimeout(timer);
      abortRef.current = null;
    }
  }

  function guardedCall(system, user) {
    return guarded((signal) => callClaude(system, user, signal));
  }

  function cancelRequest() {
    if (abortRef.current) abortRef.current.abort();
  }

  const resolvedModel = targetModel === "Other" ? (customModel || "an unspecified model") : targetModel;

  async function resolveModelNotes() {
    if (targetModel !== "Other") return { notes: MODEL_NOTES[targetModel], source: "builtin" };
    const raw = customModel.trim();
    if (!raw) return { notes: MODEL_NOTES["Other"], source: "builtin" };
    const key = raw.toLowerCase();

    try {
      const cached = await window.storage.get(`model-notes:${key}`, true);
      if (cached?.value) return { notes: cached.value, source: "cached" };
    } catch (_) {
      // not cached yet -- fall through to research
    }

    setResearching(true);
    try {
      const notes = await guarded((signal) => researchModel(raw, signal));
      window.storage.set(`model-notes:${key}`, notes, true).catch(() => {});
      return { notes, source: "researched" };
    } catch (e) {
      if (e && e.name === "AbortError") throw e; // cancelled or timed out: stop, don't fall back
      return { notes: `${MODEL_NOTES["Other"]} (research attempt failed: ${e.message})`, source: "fallback" };
    } finally {
      setResearching(false);
    }
  }

  async function generateQuestions() {
    if (!rawRequest.trim()) return;
    setLoading(true);
    setError("");
    try {
      const { notes, source } = await resolveModelNotes();
      setResolvedModelNotes(notes);
      setModelSource(source);

      const preset = EFFICIENCY_PRESETS[efficiencyMode];
      const system = `You are an expert prompt engineer. You generate a single batch of clarifying questions that will let you fully optimize a prompt for a specific target model, given a user's raw natural-language request.

Target model: ${resolvedModel}
Known behavior of this target: ${notes}

${TOKEN_DISCIPLINE}
${loopMode ? "\n" + LOOP_ENGINEERING : ""}

Because this target is not always well suited to rapid back-and-forth (especially long-horizon models), ask everything you'll need in ONE batch rather than iteratively. Group questions into 3-5 categories relevant to the request (choose from: Scope & Goal, Constraints & Format, Tone & Audience, Autonomy & Iteration Cadence, Security & Reliability, Technical Environment${loopMode ? ", Loop & Recurrence" : ""} -- only include categories relevant to this specific request). Within groups, include conditional follow-up questions that only make sense given a particular answer (a domino-effect branch), marked with dependsOn.

User's efficiency preference: ${preset.label} (${preset.note}). Keep every question under 15 words and every option under 5 words. Produce ${preset.questionCount} total questions including branches -- ask only what materially changes the compiled prompt, skip anything you can reasonably default.

Return ONLY valid JSON (no markdown fences, no prose) matching exactly this schema:
[{"group":"string","questions":[{"id":"short_snake_case","text":"string","type":"single_select|multi_select|text","options":["..."],"dependsOn":null}]}]

For conditional questions, dependsOn must be {"questionId":"parent_id","values":["option","that","triggers","it"]} -- otherwise null. For type "text", options must be an empty array.`;

      const user = `Raw request: "${rawRequest}"\n\nGenerate the question batch now.`;
      const text = await guardedCall(system, user);
      const parsed = parseModelJSON(text);
      const checked = parsed.ok ? validateQuestionGroups(parsed.value) : parsed;
      if (!checked.ok) throw new Error(`${checked.error}. Your objective is unchanged; try again.`);
      setQuestionGroups(checked.value);
      setAnswers({});
      setScreen("clarify");
    } catch (e) {
      setError("Couldn't generate questions. " + requestErrorMessage(e));
    } finally {
      setLoading(false);
    }
  }

  async function compilePrompt(previousVersion, feedback) {
    setLoading(true);
    setError("");
    try {
      const answeredEntries = formatAnswers(visibleAnswers(questionGroups, answers));

      const preset = EFFICIENCY_PRESETS[efficiencyMode];
      const system = `You are an expert prompt engineer. Synthesize a fully optimized prompt for the target model below, using the user's raw request and their clarifying answers.

Target model: ${resolvedModel}
Known behavior of this target: ${resolvedModelNotes}

${TOKEN_DISCIPLINE}
${loopMode ? "\n" + LOOP_ENGINEERING : ""}

${POLICY_PRECEDENCE}

Optimize for: user satisfaction, feasibility, usability, and top-tier performance on this specific model. If the request involves building software, systems, or handling sensitive data, include a short "Security & Reliability" section in the prompt capturing relevant constraints -- omit it entirely if not applicable.

User's efficiency preference: ${preset.label} (${preset.note}). Keep the compiled prompt itself under ${preset.promptWordCap} words -- trim aggressively rather than covering every edge case when the mode is efficient. Keep your whole response (including rationale) under 550 words total.

Return ONLY valid JSON (no markdown fences, no prose) matching exactly this schema:
{"prompt":"the full optimized prompt text, ready to paste as-is","rationale":"2-4 sentences on key choices made for this model","settings":"one line of suggested settings for this model (effort level, temperature, etc.) or empty string if not applicable","efficiency":"one sentence naming the concrete token-saving choices made in this specific prompt (e.g. merged constraints, cacheable block split out, cut N words of redundant framing)"}`;

      let user;
      if (previousVersion && feedback) {
        user = buildRevisionUser({
          rawRequest,
          answeredText: answeredEntries,
          previousPrompt: previousVersion.prompt,
          feedback,
          estimate: estimateTokens(previousVersion.prompt),
        });
      } else {
        user = `Raw request: "${rawRequest}"\n\nClarifying answers:\n${answeredEntries || "(none provided)"}\n\nCompile the optimized prompt now.`;
      }

      const text = await guardedCall(system, user);
      const parsed = parseModelJSON(text);
      const checked = parsed.ok ? validateCompiledVersion(parsed.value) : parsed;
      if (!checked.ok) throw new Error(`${checked.error}. Your answers and earlier versions are unchanged; try again.`);
      const newVersion = { ...checked.value, feedback: feedback || null };
      setVersions((prev) => [...prev, newVersion]);
      setActiveVersion(versions.length); // index of the new version
      setScreen("output");
      setShowFeedback(false);
      setFeedbackText("");
    } catch (e) {
      setError("Couldn't compile the prompt. " + requestErrorMessage(e));
    } finally {
      setLoading(false);
    }
  }

  function handleAnswer(q, value) {
    setAnswers((prev) => {
      if (q.type === "multi_select") {
        const current = prev[q.id] || [];
        const next = current.includes(value) ? current.filter((v) => v !== value) : [...current, value];
        return { ...prev, [q.id]: next };
      }
      return { ...prev, [q.id]: value };
    });
  }

  const questionById = questionIndex(questionGroups);

  function visibleQuestions() {
    return questionGroups.flatMap((g) => g.questions.filter((q) => isVisible(q, answers, questionById)));
  }

  const answeredCount = visibleQuestions().filter((q) => {
    const v = answers[q.id];
    return v !== undefined && v !== "" && !(Array.isArray(v) && v.length === 0);
  }).length;
  const totalVisible = visibleQuestions().length;

  function copyPrompt() {
    const text = versions[activeVersion]?.prompt || "";
    navigator.clipboard?.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  function reset() {
    setScreen("input");
    setRawRequest("");
    setQuestionGroups([]);
    setAnswers({});
    setVersions([]);
    setActiveVersion(0);
    setError("");
    setShowFeedback(false);
    setFeedbackText("");
    setResolvedModelNotes("");
    setModelSource("builtin");
  }

  const current = versions[activeVersion];

  return (
    <div className="min-h-screen bg-[#0a0f0c] text-[#c8f5d8] font-mono flex flex-col items-center px-4 py-8">
      <div className="w-full max-w-2xl">
        {/* Header */}
        <div className="flex items-center gap-2 mb-1">
          <Terminal size={20} className="text-[#3ddc84]" />
          <h1 className="text-xl tracking-widest text-[#3ddc84] font-bold">PROOFHOUSE</h1>
          <span className="w-2 h-4 bg-[#3ddc84] animate-pulse ml-1" />
        </div>
        <p className="text-xs text-[#5a8a6a] mb-6">
          natural language in &gt; model-optimized prompt out &gt; refine until it's right
        </p>

        {/* SCREEN: INPUT */}
        {screen === "input" && (
          <div className="border border-[#1e3a2a] rounded-md bg-[#0d1410] p-5 space-y-4">
            <div>
              <label htmlFor="objective" className="text-xs uppercase tracking-wide text-[#5a8a6a]">Objective</label>
              <textarea
                id="objective"
                value={rawRequest}
                onChange={(e) => setRawRequest(e.target.value)}
                placeholder="What do you want the prompt to accomplish?"
                rows={4}
                className="w-full mt-1 bg-[#0a0f0c] border border-[#1e3a2a] rounded px-3 py-2 text-sm text-[#c8f5d8] placeholder-[#3a5a48] focus:outline-none focus:border-[#3ddc84] resize-none"
              />
            </div>

            <div>
              <label htmlFor="targetModel" className="text-xs uppercase tracking-wide text-[#5a8a6a]">Target model / provider</label>
              <select
                id="targetModel"
                value={targetModel}
                onChange={(e) => setTargetModel(e.target.value)}
                className="w-full mt-1 bg-[#0a0f0c] border border-[#1e3a2a] rounded px-3 py-2 text-sm text-[#c8f5d8] focus:outline-none focus:border-[#3ddc84]"
              >
                {MODEL_OPTIONS.map((m) => (
                  <option key={m} value={m}>{m}</option>
                ))}
              </select>
              {targetModel === "Other" && (
                <input
                  aria-label="Model or provider name"
                  value={customModel}
                  onChange={(e) => setCustomModel(e.target.value)}
                  placeholder="Name the model/provider"
                  className="w-full mt-2 bg-[#0a0f0c] border border-[#1e3a2a] rounded px-3 py-2 text-sm text-[#c8f5d8] placeholder-[#3a5a48] focus:outline-none focus:border-[#3ddc84]"
                />
              )}
              {targetModel === "Other" && customModel.trim() && (
                <p className="text-[10px] text-[#5a8a6a] mt-1">
                  Unfamiliar model -- the model will web-search it; the notes are unverified and cached for next time.
                </p>
              )}
            </div>

            <div className="flex items-start gap-2">
              <input
                type="checkbox"
                id="loopMode"
                checked={loopMode}
                onChange={(e) => setLoopMode(e.target.checked)}
                className="mt-0.5 accent-[#3ddc84]"
              />
              <label htmlFor="loopMode" className="text-xs text-[#8ab89a]">
                <span className="uppercase tracking-wide text-[#5a8a6a]">Loop / recurring task</span> — the prompt should
                run as a repeated cycle (trigger, verify, exit condition, checkpoints) rather than a single pass.
              </label>
            </div>

            <div>
              <label className="text-xs uppercase tracking-wide text-[#5a8a6a]">Token efficiency</label>
              <div className="flex gap-2 mt-1">
                {Object.entries(EFFICIENCY_PRESETS).map(([key, p]) => (
                  <button
                    key={key}
                    onClick={() => setEfficiencyMode(key)}
                    className={`flex-1 text-xs rounded border px-2 py-1.5 transition-colors ${
                      efficiencyMode === key
                        ? "bg-[#3ddc84] text-[#0a0f0c] border-[#3ddc84] font-semibold"
                        : "border-[#1e3a2a] text-[#8ab89a] hover:border-[#3ddc84]"
                    }`}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
              <p className="text-[10px] text-[#5a8a6a] mt-1">{EFFICIENCY_PRESETS[efficiencyMode].note}</p>
            </div>

            {error && (
              <div role="alert" className="flex items-start gap-2 text-xs text-[#ffb454] bg-[#241a0c] border border-[#4a3418] rounded px-3 py-2">
                <AlertTriangle size={14} className="mt-0.5 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <button
              onClick={generateQuestions}
              disabled={loading || !rawRequest.trim()}
              className="w-full flex items-center justify-center gap-2 bg-[#3ddc84] text-[#0a0f0c] font-semibold text-sm rounded py-2.5 disabled:opacity-40 hover:bg-[#5aeea0] transition-colors"
            >
              {loading ? <Loader2 size={16} className="animate-spin" /> : <ChevronRight size={16} />}
              {loading ? (researching ? `Researching ${resolvedModel}...` : "Analyzing...") : "Initialize >"}
            </button>
            {loading && (
              <button
                onClick={cancelRequest}
                className="w-full text-xs text-[#8ab89a] border border-[#1e3a2a] rounded py-1.5 hover:border-[#ffb454] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#ffb454]"
              >
                cancel request
              </button>
            )}
          </div>
        )}

        {/* SCREEN: CLARIFY */}
        {screen === "clarify" && (
          <div className="space-y-4">
            <div className="flex items-center justify-between text-xs text-[#5a8a6a]">
              <button onClick={() => setScreen("input")} className="flex items-center gap-1 hover:text-[#3ddc84]">
                <ArrowLeft size={12} /> back
              </button>
              <span>{answeredCount}/{totalVisible} answered</span>
            </div>

            {modelSource !== "builtin" && (
              <p className="text-[10px] text-[#5a8a6a] -mt-2">
                model notes: {modelSource === "cached" ? "loaded from a prior session" : modelSource === "researched" ? "researched by the model via web search just now -- unverified, no sources recorded" : "research failed, using generic fallback"}
              </p>
            )}

            {questionGroups.map((group) => {
              const visibleQs = group.questions.filter((q) => isVisible(q, answers, questionById));
              if (visibleQs.length === 0) return null;
              return (
                <div key={group.group} className="border border-[#1e3a2a] rounded-md bg-[#0d1410] p-4">
                  <h2 className="text-xs uppercase tracking-widest text-[#3ddc84] mb-3">{group.group}</h2>
                  <div className="space-y-3">
                    {visibleQs.map((q) => (
                      <div key={q.id}>
                        <p id={`q-${q.id}`} className="text-sm text-[#c8f5d8] mb-1.5">{q.text}</p>
                        {q.type === "text" && (
                          <input
                            aria-labelledby={`q-${q.id}`}
                            value={answers[q.id] || ""}
                            onChange={(e) => handleAnswer(q, e.target.value)}
                            className="w-full bg-[#0a0f0c] border border-[#1e3a2a] rounded px-3 py-1.5 text-sm text-[#c8f5d8] focus:outline-none focus:border-[#3ddc84]"
                          />
                        )}
                        {(q.type === "single_select" || q.type === "multi_select") && (
                          <div className="flex flex-wrap gap-2">
                            {(q.options || []).map((opt) => {
                              const active =
                                q.type === "multi_select"
                                  ? (answers[q.id] || []).includes(opt)
                                  : answers[q.id] === opt;
                              return (
                                <button
                                  key={opt}
                                  aria-pressed={active}
                                  onClick={() => handleAnswer(q, opt)}
                                  className={`text-xs px-3 py-1.5 rounded border transition-colors ${
                                    active
                                      ? "bg-[#3ddc84] text-[#0a0f0c] border-[#3ddc84] font-semibold"
                                      : "border-[#1e3a2a] text-[#8ab89a] hover:border-[#3ddc84]"
                                  }`}
                                >
                                  {opt}
                                </button>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}

            {error && (
              <div role="alert" className="flex items-start gap-2 text-xs text-[#ffb454] bg-[#241a0c] border border-[#4a3418] rounded px-3 py-2">
                <AlertTriangle size={14} className="mt-0.5 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <button
              onClick={() => compilePrompt(null, null)}
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 bg-[#3ddc84] text-[#0a0f0c] font-semibold text-sm rounded py-2.5 disabled:opacity-40 hover:bg-[#5aeea0] transition-colors"
            >
              {loading ? <Loader2 size={16} className="animate-spin" /> : <ChevronRight size={16} />}
              {loading ? "Compiling..." : "Compile optimized prompt >"}
            </button>
            {loading && (
              <button
                onClick={cancelRequest}
                className="w-full text-xs text-[#8ab89a] border border-[#1e3a2a] rounded py-1.5 hover:border-[#ffb454] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#ffb454]"
              >
                cancel request
              </button>
            )}
          </div>
        )}

        {/* SCREEN: OUTPUT */}
        {screen === "output" && current && (
          <div className="space-y-4">
            {versions.length > 1 && (
              <div className="flex items-center gap-2 text-xs text-[#5a8a6a]">
                <History size={12} />
                {versions.map((_, i) => (
                  <button
                    key={i}
                    onClick={() => setActiveVersion(i)}
                    className={`px-2 py-0.5 rounded border ${
                      i === activeVersion
                        ? "border-[#3ddc84] text-[#3ddc84]"
                        : "border-[#1e3a2a] text-[#5a8a6a] hover:border-[#3ddc84]"
                    }`}
                  >
                    v{i + 1}
                  </button>
                ))}
              </div>
            )}

            <div className="border border-[#1e3a2a] rounded-md bg-[#0d1410] p-4">
              <div className="flex items-center justify-between mb-2">
                <h2 className="text-xs uppercase tracking-widest text-[#3ddc84]">Optimized prompt · {resolvedModel}</h2>
                <button onClick={copyPrompt} className="flex items-center gap-1 text-xs text-[#8ab89a] hover:text-[#3ddc84]">
                  {copied ? <Check size={12} /> : <Copy size={12} />}
                  {copied ? "copied" : "copy"}
                </button>
              </div>
              <pre className="whitespace-pre-wrap text-sm text-[#c8f5d8] leading-relaxed">{current.prompt}</pre>
              <p className="text-[10px] text-[#5a8a6a] mt-2">
                ~{estimateTokens(current.prompt)} tokens (est.) · {efficiencyMode} mode{loopMode ? " · loop-structured" : ""}
              </p>
            </div>

            <div className="border border-[#1e3a2a] rounded-md bg-[#0d1410] p-4 text-xs text-[#8ab89a] space-y-1">
              <p><span className="text-[#5a8a6a]">rationale — </span>{current.rationale}</p>
              {current.settings && <p><span className="text-[#5a8a6a]">suggested settings — </span>{current.settings}</p>}
              {current.efficiency && <p><span className="text-[#5a8a6a]">token savings — </span>{current.efficiency}</p>}
              {current.feedback && <p><span className="text-[#5a8a6a]">revised because — </span>{current.feedback}</p>}
            </div>

            {error && (
              <div role="alert" className="flex items-start gap-2 text-xs text-[#ffb454] bg-[#241a0c] border border-[#4a3418] rounded px-3 py-2">
                <AlertTriangle size={14} className="mt-0.5 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {!showFeedback ? (
              <div className="flex gap-2">
                <button
                  onClick={() => setShowFeedback(true)}
                  className="flex-1 flex items-center justify-center gap-2 border border-[#4a3418] text-[#ffb454] text-sm rounded py-2 hover:bg-[#1a1408] transition-colors"
                >
                  <RefreshCw size={14} /> This isn't quite right
                </button>
                <button
                  onClick={reset}
                  className="flex-1 flex items-center justify-center gap-2 border border-[#1e3a2a] text-[#8ab89a] text-sm rounded py-2 hover:border-[#3ddc84] transition-colors"
                >
                  Start over
                </button>
              </div>
            ) : (
              <div className="border border-[#4a3418] rounded-md bg-[#0d1410] p-4 space-y-3">
                <p className="text-xs text-[#ffb454]">What's off about it?</p>
                <textarea
                  aria-label="What is off about this version"
                  value={feedbackText}
                  onChange={(e) => setFeedbackText(e.target.value)}
                  rows={3}
                  placeholder="e.g. too rigid, wrong tone, too long/wasteful, missed the security requirement..."
                  className="w-full bg-[#0a0f0c] border border-[#1e3a2a] rounded px-3 py-2 text-sm text-[#c8f5d8] placeholder-[#3a5a48] focus:outline-none focus:border-[#3ddc84] resize-none"
                />
                <div className="flex gap-2">
                  <button
                    onClick={() => compilePrompt(current, feedbackText)}
                    disabled={loading || !feedbackText.trim()}
                    className="flex-1 flex items-center justify-center gap-2 bg-[#ffb454] text-[#0a0f0c] font-semibold text-sm rounded py-2 disabled:opacity-40 hover:bg-[#ffc575] transition-colors"
                  >
                    {loading ? <Loader2 size={16} className="animate-spin" /> : null}
                    {loading ? "Self-healing..." : "Self-heal prompt"}
                  </button>
                  <button
                    onClick={() => (loading ? cancelRequest() : setShowFeedback(false))}
                    className="px-4 border border-[#1e3a2a] text-[#8ab89a] text-sm rounded hover:border-[#3ddc84] transition-colors"
                  >
                    cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
