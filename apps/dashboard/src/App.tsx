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

type World = {
  id: "overdrive" | "hybrid" | "foundry" | "atlas" | "cathedral";
  name: string;
  tabLabel: string;
  title: string;
  thesis: string;
  verb: string;
  readout: string;
};

const arsenal = loadouts as Loadout[];

const worlds: World[] = [
  {
    id: "overdrive",
    name: "Atlas Foundry Overdrive",
    tabLabel: "Overdrive",
    title: "Command the full prompt arsenal.",
    thesis: "A denser evidence atlas with Foundry reactor energy, colored loadout classes, live route telemetry, and FULL BLITZ staged like the final launch gate.",
    verb: "Launch",
    readout: "Legendary prompt arsenal online",
  },
  {
    id: "hybrid",
    name: "Atlas Foundry",
    tabLabel: "Atlas Foundry",
    title: "Forge prompt architecture on a living atlas.",
    thesis: "Portfolio-style signal mapping, Foundry-grade execution energy, and Cathedral blueprint structure merged into one prompt operations command surface.",
    verb: "Execute",
    readout: "Prompt evidence and capability constellation live",
  },
  {
    id: "foundry",
    name: "The Foundry",
    tabLabel: "Foundry",
    title: "Forge prompts as executable artifacts.",
    thesis: "A black-glass semantic forge for assembling modes, modules, evals, and exports into production prompt weapons-grade infrastructure.",
    verb: "Ignite",
    readout: "Molten context stream stable",
  },
  {
    id: "atlas",
    name: "Signal Atlas",
    tabLabel: "Signal Atlas",
    title: "Navigate the prompt system like a living map.",
    thesis: "A cartographic cockpit where loadouts become routes through safety boundaries, eval ranges, missing context, and export destinations.",
    verb: "Route",
    readout: "All prompt vectors triangulated",
  },
  {
    id: "cathedral",
    name: "Cathedral Engine",
    tabLabel: "Cathedral",
    title: "Architect prompt systems as luminous structures.",
    thesis: "A high-ceremony blueprint engine for turning rough intent into pillars of behavior, verification, safety, and reusable context.",
    verb: "Consecrate",
    readout: "Architecture lock established",
  },
];

const buildPrompts = [
  {
    label: "Intent",
    question: "What are we building this loadout to survive?",
    answers: ["Repo work", "Custom GPT launch", "Agent workflow", "Eval regression"],
  },
  {
    label: "Boundary",
    question: "Which constraint is sacred?",
    answers: ["No invented facts", "Safety intact", "Tool limits", "Format locked"],
  },
  {
    label: "Proof",
    question: "What proves the system deserves trust?",
    answers: ["JSONL cases", "Rubric pass", "Report skeleton", "Manual review"],
  },
];

const blitzStages = ["Scan", "Build", "Harden", "Eval", "Report", "Export"];

function App() {
  const [selectedId, setSelectedId] = useState(arsenal[0].id);
  const [worldId, setWorldId] = useState<World["id"]>(() => readInitialWorld());
  const [blitzActive, setBlitzActive] = useState(false);
  const [answerIndex, setAnswerIndex] = useState(0);

  const selected = arsenal.find((item) => item.id === selectedId) ?? arsenal[0];
  const world = worlds.find((item) => item.id === worldId) ?? worlds[0];

  const compiledPreview = useMemo(
    () => [
      `LOADOUT ${selected.name.toUpperCase()}`,
      `WORLD ${world.name.toUpperCase()}`,
      `MODE ${selected.mode}`,
      `MODULES ${selected.modules.length}`,
      `EVAL PACKS ${selected.eval_packs.length}`,
      `EXPORTS ${selected.exports.length}`,
      blitzActive ? "FULL BLITZ LIVE" : "FULL BLITZ ARMED",
    ],
    [blitzActive, selected, world],
  );

  return (
    <main className={`arsenal-shell world-${world.id}`}>
      <section className="top-command" aria-label="PromptRig design command">
        <div>
          <span className="brand-glyph">PR</span>
          <div>
            <p>PromptRig Arsenal</p>
            <h1>{world.name}</h1>
          </div>
        </div>
        <nav aria-label="Design worlds">
          {worlds.map((item) => (
            <button
              className={item.id === world.id ? "world-tab active" : "world-tab"}
              key={item.id}
              onClick={() => {
                setWorldId(item.id);
                window.history.replaceState(null, "", `?world=${item.id}`);
              }}
            >
              {item.tabLabel}
            </button>
          ))}
        </nav>
      </section>

      <section className="legendary-rail">
        <div className="panel-heading">
          <p>Legendary Loadouts</p>
          <h2>Choose Your Architecture</h2>
        </div>
        <div className="loadout-stack">
          {arsenal.map((loadout, index) => (
            <button
              className={loadout.id === selected.id ? "loadout-card selected" : "loadout-card"}
              key={loadout.id}
              onClick={() => setSelectedId(loadout.id)}
            >
              <span>{String(index + 1).padStart(2, "0")}</span>
              <strong>{loadout.name}</strong>
              <small>{loadout.role}</small>
            </button>
          ))}
        </div>
      </section>

      <section className="main-stage">
        <div className="stage-copy">
          <p>{world.readout}</p>
          <h2>{world.title}</h2>
          <span>{world.thesis}</span>
        </div>

        <WorldStage world={world.id} selected={selected} />

        <div className="slot-dock">
          <Slot label="Primary" value={selected.primary} />
          <Slot label="Mode" value={selected.mode} />
          <Slot label="Modules" value={`${selected.modules.length} armed`} />
          <Slot label="Eval Pack" value={`${selected.eval_packs.length} linked`} />
        </div>
      </section>

      <aside className="inspector">
        <div className="active-loadout">
          <p>Active Loadout</p>
          <h2>{selected.name}</h2>
          <span>{selected.tagline}</span>
        </div>

        <div className="preview-console">
          <p>Compiled Preview</p>
          {compiledPreview.map((line) => (
            <code key={line}>{line}</code>
          ))}
        </div>

        <button className={blitzActive ? "full-blitz live" : "full-blitz"} onClick={() => setBlitzActive(!blitzActive)}>
          <span>{world.verb}</span>
          FULL BLITZ
        </button>

        <div className="stage-list">
          {blitzStages.map((stage, index) => (
            <div className={blitzActive || index < 2 ? "stage-item active" : "stage-item"} key={stage}>
              <span>{String(index + 1).padStart(2, "0")}</span>
              {stage}
            </div>
          ))}
        </div>
      </aside>

      <section className="build-room">
        <div>
          <p>Build Room</p>
          <h2>Q&A Assembly Flow</h2>
        </div>
        <article className="question-card">
          <span>{buildPrompts[answerIndex].label}</span>
          <h3>{buildPrompts[answerIndex].question}</h3>
          <div>
            {buildPrompts[answerIndex].answers.map((answer) => (
              <button key={answer} onClick={() => setAnswerIndex((answerIndex + 1) % buildPrompts.length)}>
                {answer}
              </button>
            ))}
          </div>
        </article>
        <article className="operation-card">
          <span>Full Blitz Output</span>
          {selected.full_blitz.map((step, index) => (
            <p key={step}>
              <strong>{index + 1}</strong>
              {step}
            </p>
          ))}
        </article>
      </section>
    </main>
  );
}

function Slot({ label, value }: { label: string; value: string }) {
  return (
    <article className="slot">
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}

function WorldStage({ world, selected }: { world: World["id"]; selected: Loadout }) {
  if (world === "overdrive") {
    return (
      <div className="world-stage overdrive-stage" aria-label="Atlas Foundry Overdrive visualization">
        <svg className="overdrive-map" viewBox="0 0 900 500" role="img">
          <defs>
            <radialGradient id="overdrive-core" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#56ff9b" stopOpacity="0.42" />
              <stop offset="48%" stopColor="#ffd35f" stopOpacity="0.16" />
              <stop offset="100%" stopColor="#020706" stopOpacity="0" />
            </radialGradient>
          </defs>
          <rect className="overdrive-grid-frame" x="36" y="34" width="828" height="408" />
          <circle className="overdrive-core-glow" cx="450" cy="246" r="164" fill="url(#overdrive-core)" />
          <path className="overdrive-arch arch-a" d="M92 408 C128 122 284 46 450 46 S772 122 808 408" />
          <path className="overdrive-arch arch-b" d="M178 408 C204 178 318 104 450 104 S696 178 722 408" />
          <path className="overdrive-link core-link" d="M92 250 H232 L322 184 L450 246 L578 168 L804 168" />
          <path className="overdrive-link capability-link" d="M128 112 L260 154 L344 102 L520 126 L774 306" />
          <path className="overdrive-link evidence-link" d="M104 366 L246 324 L374 354 L536 310 L802 360" />
          <path className="overdrive-link framework-link" d="M240 72 L340 154 L450 246 L630 116" />
          <path className="overdrive-link future-link" d="M708 88 L780 162 L742 260 L820 348" />
          <circle className="overdrive-orbit orbit-a" cx="450" cy="246" r="142" />
          <ellipse className="overdrive-orbit orbit-b" cx="450" cy="246" rx="286" ry="94" />
          <ellipse className="overdrive-orbit orbit-c" cx="450" cy="246" rx="192" ry="232" />
          {[
            [92, 250, "core", "CORE"],
            [232, 250, "capability", "MODE"],
            [322, 184, "evidence", "EVAL"],
            [578, 168, "core", "SAFE"],
            [804, 168, "future", "NEXT"],
            [128, 112, "capability", "API"],
            [260, 154, "core", "CTX"],
            [344, 102, "capability", "GPT"],
            [520, 126, "framework", "RULE"],
            [774, 306, "evidence", "REP"],
            [104, 366, "evidence", "CASE"],
            [246, 324, "capability", "TOOL"],
            [374, 354, "evidence", "JSONL"],
            [536, 310, "framework", "STOP"],
            [802, 360, "future", "SHIP"],
            [708, 88, "future", "V2"],
            [780, 162, "framework", "RED"],
            [742, 260, "capability", "RUN"],
            [820, 348, "future", "LAB"],
          ].map(([x, y, tone, label]) => (
            <g className={`overdrive-node ${tone}`} key={`${x}-${y}-${label}`}>
              <rect x={Number(x) - 25} y={Number(y) - 17} width="50" height="34" />
              <text x={Number(x)} y={Number(y) + 4}>
                {label}
              </text>
            </g>
          ))}
        </svg>
        <div className="overdrive-core-card">
          <span>Atlas Reactor</span>
          <strong>{selected.name}</strong>
          <small>FULL BLITZ routes core, mode, modules, evals, reports, and exports.</small>
        </div>
        <div className="overdrive-control-strip">
          {["Core", "Capability", "Evidence", "Framework", "Future"].map((item) => (
            <span key={item}>{item}</span>
          ))}
        </div>
      </div>
    );
  }

  if (world === "hybrid") {
    return (
      <div className="world-stage hybrid-stage" aria-label="Atlas Foundry merged visualization">
        <svg className="hybrid-map" viewBox="0 0 820 460" role="img">
          <path className="cathedral-arch arch-a" d="M118 380 C146 120 278 42 410 42 S674 120 702 380" />
          <path className="cathedral-arch arch-b" d="M190 380 C208 192 304 112 410 112 S612 192 630 380" />
          <path className="signal-line green-line" d="M118 258 L252 258 L332 214 L410 238 L502 186 L692 186" />
          <path className="signal-line cyan-line" d="M156 142 L284 172 L372 120 L482 142 L640 288" />
          <path className="signal-line amber-line" d="M180 338 L292 310 L410 338 L546 308 L694 338" />
          <path className="signal-line red-line" d="M246 92 L326 168 L410 238 L570 142" />
          <circle className="forge-orbit orbit-a" cx="410" cy="238" r="132" />
          <ellipse className="forge-orbit orbit-b" cx="410" cy="238" rx="220" ry="86" />
          {[
            [118, 258, "core"],
            [252, 258, "capability"],
            [332, 214, "evidence"],
            [502, 186, "core"],
            [692, 186, "future"],
            [156, 142, "capability"],
            [284, 172, "core"],
            [372, 120, "capability"],
            [482, 142, "framework"],
            [640, 288, "evidence"],
            [180, 338, "evidence"],
            [292, 310, "capability"],
            [546, 308, "framework"],
            [694, 338, "future"],
          ].map(([x, y, tone]) => (
            <g className={`hybrid-node ${tone}`} key={`${x}-${y}`}>
              <rect x={Number(x) - 20} y={Number(y) - 20} width="40" height="40" />
              <circle cx={Number(x)} cy={Number(y)} r="5" />
            </g>
          ))}
        </svg>
        <div className="hybrid-core">
          <span>Atlas Forge Core</span>
          <strong>{selected.name}</strong>
          <small>Core + Mode + Modules + Evals + Exports</small>
        </div>
        <div className="atlas-legend" aria-label="Atlas legend">
          <span className="core-dot">Core</span>
          <span className="capability-dot">Capability</span>
          <span className="evidence-dot">Evidence</span>
          <span className="framework-dot">Framework</span>
          <span className="future-dot">Future</span>
        </div>
      </div>
    );
  }

  if (world === "atlas") {
    return (
      <div className="world-stage atlas-stage" aria-label="Signal atlas visualization">
        <svg viewBox="0 0 720 420" role="img">
          <path className="route route-a" d="M92 324 C180 220 252 296 332 190 S504 100 628 168" />
          <path className="route route-b" d="M96 122 C210 176 256 78 374 138 S522 292 640 238" />
          <path className="route route-c" d="M138 372 C260 348 300 268 384 250 S532 330 634 340" />
          {[92, 194, 332, 484, 628].map((x, index) => (
            <circle className="map-node" cx={x} cy={[324, 178, 190, 116, 168][index]} r={index === 2 ? 24 : 12} key={x} />
          ))}
          {[96, 246, 374, 510, 640].map((x, index) => (
            <rect className="map-tile" x={x - 18} y={[122, 96, 138, 256, 238][index] - 18} width="36" height="36" key={x} />
          ))}
        </svg>
        <div className="stage-label">
          <span>Route Locked</span>
          <strong>{selected.name}</strong>
        </div>
      </div>
    );
  }

  if (world === "cathedral") {
    return (
      <div className="world-stage cathedral-stage" aria-label="Cathedral engine blueprint">
        <div className="vault-line" />
        <div className="pillar-set">
          {["Context", "Mode", "Safety", "Eval", "Export"].map((item) => (
            <div className="pillar" key={item}>
              <span>{item}</span>
            </div>
          ))}
        </div>
        <div className="blueprint-core">
          <span>Prompt Architecture</span>
          <strong>{selected.name}</strong>
        </div>
      </div>
    );
  }

  return (
    <div className="world-stage foundry-stage" aria-label="Foundry forge visualization">
      <div className="forge-ring ring-one" />
      <div className="forge-ring ring-two" />
      <div className="forge-core">
        <span>Active Artifact</span>
        <strong>{selected.name}</strong>
      </div>
      <div className="heat-lane lane-a" />
      <div className="heat-lane lane-b" />
      <div className="heat-lane lane-c" />
    </div>
  );
}

function readInitialWorld(): World["id"] {
  const requested = new URLSearchParams(window.location.search).get("world");
  return worlds.some((world) => world.id === requested) ? (requested as World["id"]) : "overdrive";
}

export default App;
