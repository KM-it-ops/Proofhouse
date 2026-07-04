import { useState } from "react";
import { Terminal, Copy, RefreshCw, Check, AlertTriangle, Loader2, ChevronRight, ArrowLeft, History } from "lucide-react";

// ---------------------------------------------------------------------------
// Model-specific prompting knowledge injected into every API call so the
// optimizer respects real behavioral differences between targets.
// ---------------------------------------------------------------------------
const MODEL_NOTES = {
  "Claude Fable 5":
    "Fable 5 (Mythos-tier) is built for long, autonomous, self-verifying runs, not rapid back-and-forth. State goals and success criteria rather than prescriptive steps -- over-specifying degrades it. Default effort: high (xhigh only for the hardest work). It delegates to subagents on its own when useful, and benefits from a persistent lessons file across sessions. It runs safety classifiers on offensive-cybersecurity and bio/life-science content that can occasionally flag legitimate defensive or detection-engineering work -- frame technique descriptions defensively. Never ask it to echo, transcribe, or explain its internal reasoning as response text -- this risks a refusal fallback to Opus 4.8. For long or autonomous tasks, define explicit checkpoints for where it should pause vs. keep going, since it will otherwise define them itself.",
  "Claude Mythos 5":
    "Same underlying model as Fable 5, without the added cyber/bio safety layers, used only in restricted trusted-org contexts. Apply identical prompting patterns to Fable 5.",
  "Claude Opus 4.8":
    "Strong general-purpose reasoning model. Benefits from clear step structure, explicit success criteria, and worked examples for style-sensitive tasks. Handles moderate agentic tasks well but is less suited to fully autonomous multi-hour runs than Fable 5.",
  "Claude Sonnet 5":
    "Fast, capable default model for most tasks. Responds well to concise, direct instructions and doesn't need heavy scaffolding. Well suited to genuine iterative back-and-forth.",
  "Claude Haiku 4.5":
    "Optimized for speed and cost. Keep prompts tight and narrow; break multi-stage work into smaller discrete requests rather than one open-ended instruction.",
  "GPT-5.5":
    "Apply general best practice: explicit system/developer instructions, clear output-format specification, few-shot examples for style-sensitive output. Vendor specifics may have shifted since this tool's knowledge was last verified -- flag that in the rationale.",
  "Gemini":
    "Apply general best practice: explicit structure, clear formatting instructions, and grounding context provided up front. Vendor specifics may have shifted since this tool's knowledge was last verified -- flag that in the rationale.",
  "Other":
    "No verified vendor-specific behavior available. Apply general best practice: be explicit about goal, constraints, format, and audience, and note in the rationale that this is generic guidance.",
};

const MODEL_OPTIONS = Object.keys(MODEL_NOTES);

// Universal token-discipline directive, applied to every call this tool makes AND
// baked into every prompt it produces. Two separate concerns: (1) keep PromptRig's
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

function estimateTokens(text) {
  return Math.ceil((text || "").length / 4);
}

async function researchModel(name) {
  const response = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model: "claude-sonnet-4-6",
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

async function callClaude(system, user) {
  const response = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model: "claude-sonnet-4-6",
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

function extractJSON(text) {
  const cleaned = text.replace(/```json/gi, "").replace(/```/g, "").trim();
  return JSON.parse(cleaned);
}

function isVisible(q, answers) {
  if (!q.dependsOn) return true;
  const parentVal = answers[q.dependsOn.questionId];
  if (parentVal === undefined || parentVal === null) return false;
  const values = q.dependsOn.values || [];
  if (Array.isArray(parentVal)) return values.some((v) => parentVal.includes(v));
  return values.includes(parentVal);
}

export default function PromptRig() {
  const [screen, setScreen] = useState("input"); // input | clarify | output
  const [rawRequest, setRawRequest] = useState("");
  const [targetModel, setTargetModel] = useState("Claude Fable 5");
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
      const notes = await researchModel(raw);
      window.storage.set(`model-notes:${key}`, notes, true).catch(() => {});
      return { notes, source: "researched" };
    } catch (e) {
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
      const text = await callClaude(system, user);
      const parsed = extractJSON(text);
      setQuestionGroups(parsed);
      setAnswers({});
      setScreen("clarify");
    } catch (e) {
      setError("Couldn't generate questions. " + e.message);
    } finally {
      setLoading(false);
    }
  }

  async function compilePrompt(previousVersion, feedback) {
    setLoading(true);
    setError("");
    try {
      const answeredEntries = Object.entries(answers)
        .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(", ") : v}`)
        .join("\n");

      const preset = EFFICIENCY_PRESETS[efficiencyMode];
      const system = `You are an expert prompt engineer. Synthesize a fully optimized prompt for the target model below, using the user's raw request and their clarifying answers.

Target model: ${resolvedModel}
Known behavior of this target: ${resolvedModelNotes}

${TOKEN_DISCIPLINE}
${loopMode ? "\n" + LOOP_ENGINEERING : ""}

Optimize for: user satisfaction, feasibility, usability, and top-tier performance on this specific model. If the request involves building software, systems, or handling sensitive data, include a short "Security & Reliability" section in the prompt capturing relevant constraints -- omit it entirely if not applicable.

User's efficiency preference: ${preset.label} (${preset.note}). Keep the compiled prompt itself under ${preset.promptWordCap} words -- trim aggressively rather than covering every edge case when the mode is efficient. Keep your whole response (including rationale) under 550 words total.

Return ONLY valid JSON (no markdown fences, no prose) matching exactly this schema:
{"prompt":"the full optimized prompt text, ready to paste as-is","rationale":"2-4 sentences on key choices made for this model","settings":"one line of suggested settings for this model (effort level, temperature, etc.) or empty string if not applicable","efficiency":"one sentence naming the concrete token-saving choices made in this specific prompt (e.g. merged constraints, cacheable block split out, cut N words of redundant framing)"}`;

      let user;
      if (previousVersion && feedback) {
        user = `Original request: "${rawRequest}"\n\nPrevious optimized prompt (~${estimateTokens(previousVersion.prompt)} tokens):\n${previousVersion.prompt}\n\nUser feedback on that version: "${feedback}"\n\nDiagnose what's wrong (scope mismatch, wrong tone, missing constraint, too rigid, too vague, model mismatch, security gap, token bloat/too verbose, or other) and produce a revised version that fixes it. Reflect the diagnosis briefly in the rationale.`;
      } else {
        user = `Raw request: "${rawRequest}"\n\nClarifying answers:\n${answeredEntries || "(none provided)"}\n\nCompile the optimized prompt now.`;
      }

      const text = await callClaude(system, user);
      const parsed = extractJSON(text);
      const newVersion = { ...parsed, feedback: feedback || null };
      setVersions((prev) => [...prev, newVersion]);
      setActiveVersion(versions.length); // index of the new version
      setScreen("output");
      setShowFeedback(false);
      setFeedbackText("");
    } catch (e) {
      setError("Couldn't compile the prompt. " + e.message);
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

  function visibleQuestions() {
    return questionGroups.flatMap((g) => g.questions.filter((q) => isVisible(q, answers)));
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
          <h1 className="text-xl tracking-widest text-[#3ddc84] font-bold">PROMPTRIG</h1>
          <span className="w-2 h-4 bg-[#3ddc84] animate-pulse ml-1" />
        </div>
        <p className="text-xs text-[#5a8a6a] mb-6">
          natural language in &gt; model-optimized prompt out &gt; refine until it's right
        </p>

        {/* SCREEN: INPUT */}
        {screen === "input" && (
          <div className="border border-[#1e3a2a] rounded-md bg-[#0d1410] p-5 space-y-4">
            <div>
              <label className="text-xs uppercase tracking-wide text-[#5a8a6a]">Objective</label>
              <textarea
                value={rawRequest}
                onChange={(e) => setRawRequest(e.target.value)}
                placeholder="What do you want the prompt to accomplish?"
                rows={4}
                className="w-full mt-1 bg-[#0a0f0c] border border-[#1e3a2a] rounded px-3 py-2 text-sm text-[#c8f5d8] placeholder-[#3a5a48] focus:outline-none focus:border-[#3ddc84] resize-none"
              />
            </div>

            <div>
              <label className="text-xs uppercase tracking-wide text-[#5a8a6a]">Target model / provider</label>
              <select
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
                  value={customModel}
                  onChange={(e) => setCustomModel(e.target.value)}
                  placeholder="Name the model/provider"
                  className="w-full mt-2 bg-[#0a0f0c] border border-[#1e3a2a] rounded px-3 py-2 text-sm text-[#c8f5d8] placeholder-[#3a5a48] focus:outline-none focus:border-[#3ddc84]"
                />
              )}
              {targetModel === "Other" && customModel.trim() && (
                <p className="text-[10px] text-[#5a8a6a] mt-1">
                  Unfamiliar model -- I'll research it via web search and index it for next time.
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
              <div className="flex items-start gap-2 text-xs text-[#ffb454] bg-[#241a0c] border border-[#4a3418] rounded px-3 py-2">
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
                model notes: {modelSource === "cached" ? "loaded from a prior session" : modelSource === "researched" ? "freshly researched and indexed for next time" : "research failed, using generic fallback"}
              </p>
            )}

            {questionGroups.map((group) => {
              const visibleQs = group.questions.filter((q) => isVisible(q, answers));
              if (visibleQs.length === 0) return null;
              return (
                <div key={group.group} className="border border-[#1e3a2a] rounded-md bg-[#0d1410] p-4">
                  <h2 className="text-xs uppercase tracking-widest text-[#3ddc84] mb-3">{group.group}</h2>
                  <div className="space-y-3">
                    {visibleQs.map((q) => (
                      <div key={q.id}>
                        <p className="text-sm text-[#c8f5d8] mb-1.5">{q.text}</p>
                        {q.type === "text" && (
                          <input
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
              <div className="flex items-start gap-2 text-xs text-[#ffb454] bg-[#241a0c] border border-[#4a3418] rounded px-3 py-2">
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
              <div className="flex items-start gap-2 text-xs text-[#ffb454] bg-[#241a0c] border border-[#4a3418] rounded px-3 py-2">
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
                    onClick={() => setShowFeedback(false)}
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
