import { useMemo, useState } from "react";
import loadouts from "../../../loadouts/legendary_loadouts.json";

type Loadout = {
  id: string;
  name: string;
  role: string;
  tagline: string;
  rank: string;
  target_surfaces: string[];
  primary: string;
  mode: string;
  modules: string[];
  eval_packs: string[];
  rubrics: string[];
  full_blitz: string[];
  exports: string[];
};

const arsenal = loadouts as Loadout[];

const buildPrompts = [
  {
    label: "Intent",
    question: "What surface are we arming this loadout for?",
    answers: ["Codex repo work", "Custom GPT", "API agent", "Local LLM"],
  },
  {
    label: "Rules",
    question: "What must the prompt preserve under pressure?",
    answers: ["Safety boundaries", "Missing-context labels", "Repo conventions", "Output format"],
  },
  {
    label: "Proof",
    question: "How should this loadout prove it is working?",
    answers: ["JSONL evals", "Rubric scoring", "Report skeleton", "Manual checklist"],
  },
];

const blitzStages = ["Scan", "Build", "Harden", "Eval", "Report", "Export"];

function App() {
  const [selectedId, setSelectedId] = useState(arsenal[0].id);
  const [blitzActive, setBlitzActive] = useState(false);
  const [answerIndex, setAnswerIndex] = useState(0);
  const selected = arsenal.find((item) => item.id === selectedId) ?? arsenal[0];

  const moduleCount = selected.modules.length + selected.eval_packs.length + selected.rubrics.length;
  const compiledPreview = useMemo(
    () => [
      `LOADOUT ${selected.name.toUpperCase()}`,
      `ROLE ${selected.role}`,
      `PRIMARY ${selected.primary}`,
      `MODE ${selected.mode}`,
      `MODULES ${selected.modules.length}`,
      `EVAL PACKS ${selected.eval_packs.length}`,
      "FULL BLITZ ENABLED",
    ],
    [selected],
  );

  return (
    <main className="arsenal-shell">
      <aside className="command-rail" aria-label="PromptRig command rail">
        <div className="brand-mark">PR</div>
        {["Arsenal", "Builder", "Range", "Reports", "Exports"].map((item, index) => (
          <button className={index === 0 ? "rail-item active" : "rail-item"} key={item} title={item}>
            {item.slice(0, 1)}
          </button>
        ))}
      </aside>

      <section className="library-panel">
        <header>
          <p className="section-label">PromptRig Arsenal</p>
          <h1>Legendary Loadouts</h1>
          <p>Compose prompts like production systems: core, mode, modules, evals, reports, export.</p>
        </header>

        <div className="loadout-list">
          {arsenal.map((loadout) => (
            <button
              className={loadout.id === selected.id ? "loadout-card selected" : "loadout-card"}
              key={loadout.id}
              onClick={() => setSelectedId(loadout.id)}
            >
              <span>{loadout.rank}</span>
              <strong>{loadout.name}</strong>
              <small>{loadout.role}</small>
            </button>
          ))}
        </div>

        <div className="build-room">
          <div>
            <p className="section-label">Build Room</p>
            <h2>AI Q&A Assembly</h2>
          </div>
          <div className="qa-card">
            <span>{buildPrompts[answerIndex].label}</span>
            <p>{buildPrompts[answerIndex].question}</p>
            <div className="answer-grid">
              {buildPrompts[answerIndex].answers.map((answer) => (
                <button key={answer} onClick={() => setAnswerIndex((answerIndex + 1) % buildPrompts.length)}>
                  {answer}
                </button>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="loadout-panel" aria-live="polite">
        <div className="loadout-header">
          <div>
            <p className="section-label">Active Loadout</p>
            <h2>{selected.name}</h2>
            <p>{selected.tagline}</p>
          </div>
          <div className="rank-pill">{selected.rank}</div>
        </div>

        <div className="slot-grid">
          <Slot label="Primary" value={selected.primary} power="Core identity" />
          <Slot label="Mode" value={selected.mode} power="Behavior stance" />
          <Slot label="Attachments" value={`${selected.modules.length} modules armed`} power="Reusable controls" />
          <Slot label="Eval Pack" value={`${selected.eval_packs.length} datasets`} power="Regression proof" />
        </div>

        <div className="blitz-console">
          <div>
            <p className="section-label">Complete Operating Loop</p>
            <h2>FULL BLITZ</h2>
            <p>Scan, assemble, harden, evaluate, report, and export this preset as one guided pipeline.</p>
          </div>
          <button className={blitzActive ? "blitz-button live" : "blitz-button"} onClick={() => setBlitzActive(!blitzActive)}>
            FULL BLITZ
          </button>
        </div>

        <div className="stage-strip">
          {blitzStages.map((stage, index) => (
            <div className={blitzActive || index < 2 ? "stage active" : "stage"} key={stage}>
              <span>{String(index + 1).padStart(2, "0")}</span>
              {stage}
            </div>
          ))}
        </div>

        <div className="operation-grid">
          {selected.full_blitz.map((step, index) => (
            <article key={step}>
              <span>{index + 1}</span>
              <p>{step}</p>
            </article>
          ))}
        </div>
      </section>

      <aside className="inspector-panel">
        <div className="signal-card">
          <p className="section-label">Inspector</p>
          <h2>Compiled Preview</h2>
          <div className="code-preview">
            {compiledPreview.map((line) => (
              <code key={line}>{line}</code>
            ))}
          </div>
        </div>

        <div className="metric-grid">
          <Metric label="Modules" value={String(moduleCount)} />
          <Metric label="Surfaces" value={String(selected.target_surfaces.length)} />
          <Metric label="Exports" value={String(selected.exports.length)} />
        </div>

        <div className="checklist">
          <h3>Export Targets</h3>
          {selected.exports.map((item) => (
            <div className="check-row" key={item}>
              <span />
              {item}
            </div>
          ))}
        </div>

        <div className="safety-panel">
          <h3>Boundary Status</h3>
          <p>Missing context labels locked. Safety stance defensive. Eval validation ready.</p>
        </div>
      </aside>
    </main>
  );
}

function Slot({ label, value, power }: { label: string; value: string; power: string }) {
  return (
    <article className="slot">
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{power}</small>
    </article>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <strong>{value}</strong>
      <span>{label}</span>
    </div>
  );
}

export default App;
