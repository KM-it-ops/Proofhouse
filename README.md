# Proofhouse

[![CI](https://github.com/KM-it-ops/Proofhouse/actions/workflows/ci.yml/badge.svg)](https://github.com/KM-it-ops/Proofhouse/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-3776ab)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/framework-v1.3-7c3aed)](proofhouse-framework.json)
[![PromptOps](https://img.shields.io/badge/promptops-clarify%20%E2%86%92%20compile%20%E2%86%92%20heal-0f766e)](#how-it-works)
[![License](https://img.shields.io/badge/license-MIT-111827)](LICENSE)

**A local workspace for revising prompts with evidence you can trace: every PASS names the exact prompt, outputs, checks and judgements it came from.**

I built Proofhouse because I kept rewriting the same prompt for different models and never had a good answer for which version was better, or whether a revision had quietly dropped a requirement. You give it an objective and a target model; it asks its clarifying questions in one batch and turns your answers into constraints that every later revision must keep. You record each prompt revision and the outputs a model actually produced, declare the checks that matter, and Proofhouse tells you which revision passes, which constraint lacks evidence, and what changed between revisions.

It runs on your machine with no API key. Proofhouse writes the prompts it needs as packets; you run them in the agent or model you already use and paste the results back. It is a local tool, not a hosted service, and I make no benchmark or quality claims for it.

https://github.com/user-attachments/assets/17ec6d22-1ba7-4952-bec0-d3f24c9b29ce

*44-second demo of the standalone app. You type one sentence, pick a model, answer seven questions, and get a compiled prompt where each rule is traced back to the answer that produced it. The scene is an authored example, not a recorded run. Remotion draws it; the source is in `videos/readme-hype/studio`.*

Portfolio: [km-it-ops.github.io](https://km-it-ops.github.io/)

---

## Try it in two minutes

```bash
uv tool install proofhouse
proofhouse demo
```

That runs the [reference workflow](https://github.com/KM-it-ops/Proofhouse/blob/main/docs/reference-workflow.md) end to end, offline, from files shipped in the package. It replays recorded outputs: a security-advisory summary whose first revision invents an exploitation claim and fails its checks, and whose second revision passes without losing a constraint. It does not call a model. On Windows, set `$env:PYTHONUTF8='1'` first for reliable console output.

With pip: `python -m pip install proofhouse`, then `proofhouse demo`.

From a clone, the same check is `uv run python scripts/reference_workflow.py` (or `python -m pip install -e ".[test]"` without [uv](https://docs.astral.sh/uv/)). The by-hand steps later on this page copy `examples/reference-advisory`, which is in the repository, not in the wheel.

---

## How it works

`proofhouse case` renders the framework's clarify / compile / self-heal prompts as packets you run in the agent or model of your choice, and checks what you paste back against the criteria you declare. It does not call a model and it does not rate quality.

These are the [reference workflow](docs/reference-workflow.md)'s steps, and they run as written. `pc` below is `proofhouse` (`uv run proofhouse` from a clone). Work in a scratch folder holding copies of the example inputs:

```bash
mkdir -p build/try && cp examples/reference-advisory/* build/try && cd build/try
```

**1. Start a case and answer one batch of questions.** Proofhouse writes a clarify packet, `advisory-case/01-clarify.md`. You run it in your own agent and save the answers as `advisory-case/answers.json` (for this example, copy `answers.json` there). Compile turns each answer into an accepted constraint (K1-K3) that every later revision receives.

```bash
pc case new --case advisory-case --objective-file objective.txt --model "Claude Sonnet 5" --preset efficient
pc case compile --case advisory-case
```

**2. Say how each constraint will be checked.** Checks can look at the prompt text or at what a model returned (`--target output`), and some can be a human judgement (`--manual`).

```bash
pc case constraints add --case advisory-case --text "Cite the advisory section for each claim"      # K4
pc case criteria add --case advisory-case --id AUD --must-contain "SOC analysts"
pc case criteria add --case advisory-case --id UNK --target output --must-contain UNKNOWN
pc case criteria add --case advisory-case --id NOGUESS --target output --must-not-contain "exploited in the wild"
pc case criteria add --case advisory-case --id LEN --target output --max-words 120
pc case criteria add --case advisory-case --id CITE --target output --regex "\(s\d\)"
pc case criteria add --case advisory-case --id ACC --target output --manual "Every claim matches the advisory"
pc case constraints link --case advisory-case --id K1 --criterion AUD
pc case constraints link --case advisory-case --id K2 --criterion UNK
pc case constraints link --case advisory-case --id K2 --criterion NOGUESS
pc case constraints link --case advisory-case --id K3 --criterion LEN
pc case constraints link --case advisory-case --id K4 --criterion CITE
pc case constraints link --case advisory-case --id K4 --criterion ACC
```

**3. Record a revision and what it produced, judge the manual check, then check it.**

```bash
pc case record --case advisory-case --prompt-file prompt-v1.txt
pc case output add --case advisory-case --revision 1 --output-file output-v1.txt --input-id EC-2026-017 --input-file advisory.txt --model "Claude Sonnet 5" --source "pasted from host agent"
pc case verdict --case advisory-case --revision 1 --criterion ACC --run R1 --result fail --note "claims active exploitation; the advisory does not say that"
pc case check --case advisory-case        # exit 3: v1 FAIL  UNK NOGUESS CITE ACC fail
```

**4. Revise without losing anything.** The revise packet carries your feedback, the original answers and every accepted constraint. Run it in your agent, save the new prompt, and record revision 2 the same way.

```bash
pc case revise --case advisory-case --feedback "It claimed active exploitation, which the advisory never states."
pc case record --case advisory-case --prompt-file prompt-v2.txt
pc case output add --case advisory-case --revision 2 --output-file output-v2.txt --input-id EC-2026-017 --input-file advisory.txt --model "Claude Sonnet 5" --source "pasted from host agent"
pc case verdict --case advisory-case --revision 2 --criterion ACC --run R2 --result pass
pc case check --case advisory-case        # exit 0: v2 PASS, K1-K4 satisfied
```

**5. Compare, report and hand it on.** `compare` shows what newly passes or regresses between revisions, `report` writes the evidence as Markdown, and `export` / `import` move a case to another workspace, refusing any file that does not match the bundle's manifest (the manifest is not signed).

### What a PASS proves, and what it does not

| A PASS from `case check` means | It does not mean |
|---|---|
| Every check you declared passed on this exact revision (and, for output checks, on the outputs you recorded) | That the prompt is good in general, or better than one you did not test |
| Every accepted constraint is linked to a check that passed | That a model will reproduce the recorded outputs |
| Each human verdict applies to the exact text and check definition you judged | That model notes are correct: shipped profiles cite no sources yet and are labeled `unverified` |
| Nothing was edited after it was recorded (digests are re-checked) | That the files are tamper-proof against someone who controls your machine |

Details: [docs/architecture.md](docs/architecture.md), [decision 0002](docs/decisions/0002-what-pass-means.md), [evidence format](docs/evidence-format.md).

---

## Two ways in

| Entry | Use it when | Status | Network |
|---|---|---|---|
| **Command line**: `proofhouse case` | You want the evidence trail above: constraints, recorded outputs, checks, compare, report | supported | none |
| **Any provider, any model**: `proofhouse run --provider P --model M --prompt "..."` | You want a prompt run on OpenAI, Anthropic, Google, Mistral, Groq, Together, Fireworks, OpenRouter, DeepSeek, xAI, a model on your own machine (Ollama, LM Studio, vLLM, llama.cpp), or any other provider you add with one command | new | only that call, through your spending limit |
| **Cursor or Claude Code skill**: `proofhouse install-skill` asks which agent (Cursor, Claude Code, or another one you name with its skills folder); `--host cursor` or `--host claude` skips the question. Then say "Proofhouse" in a new chat or session | You want the same clarify → compile → self-heal loop as a conversation | supported entry point | the host agent's tools |

Proofhouse is two products in one repo, at different levels of maturity. The **PromptOps skill and framework (v1.3)**, the conversational meta-optimizer with current frontier model profiles, is the most mature part of the project. The headless compiler's maturity is listed under [Experimental and prototype parts](#experimental-and-prototype-parts).

Both entries use the same framework ([`proofhouse-framework.json`](proofhouse-framework.json)) and the same model notes. The framework also covers Efficient / Balanced / Thorough token presets, loops for recurring agents (trigger, body, exit, escalation), prompt audits with missing-context labels, and agent design (permission maps, tool boundaries, stop conditions). The skill is installed to `~/.cursor/skills/proofhouse` (or `~/.claude/skills/proofhouse` with `--host claude`) and the installer checks it (the bundle ships inside the package; `tests/test_skill_bundle.py` keeps it identical to `skills/proofhouse/`); without the console script, `python -m zipfile -e skills/proofhouse/proofhouse.skill ~/.cursor/skills` (or `~/.claude/skills`) does the same. The skill can research an unfamiliar model with the host agent's tools; the command line goes online only when you ask it to run a model (`proofhouse run`, `execute-openai`), and otherwise uses your own notes (`models remember`) or a generic profile labeled `fallback`.

### Run on any provider

```bash
proofhouse providers list                     # shipped providers, and whether each key is set
proofhouse run --provider ollama --model llama3 --prompt "Say hi"          # on your machine: free, no key
export MISTRAL_API_KEY=...                                                 # your key stays in your environment
proofhouse providers price mistral mistral-large --input 2 --output 6      # USD per million tokens, if none ships
proofhouse run --provider mistral --model mistral-large --prompt "Say hi" --max-cost-usd 0.05
proofhouse providers add myhost --base-url https://api.myhost.ai/v1 --key-env MYHOST_KEY   # any other provider
```

### Same job, many models

```bash
proofhouse compare "Summarise this contract in five bullet points." --input-file contract.txt \
  --on anthropic:<model> --on openai:<model> --on groq:<model> --on ollama:llama3 \
  --judge anthropic:<model> --max-cost-usd 1.00
```

Every model runs the same job at the same time. You get a table (score, cost, time, why) and a side-by-side page, `side-by-side.html`, with every output in full. With `--judge`, one more model scores the outputs without seeing which model wrote which, and the best is named; that score is advice, not proof. One spending limit covers every call, the judge's included. Each call gets an equal share of it, so the total never passes it.

### Make it

```bash
proofhouse make "a prompt that answers refund emails warmly" --provider ollama --model llama3
proofhouse make "a skill that reviews pull requests for security issues" --kind skill \
  --provider anthropic --model <model> --max-cost-usd 1.00
```

`make` writes version 1 with your model and tries it (a prompt runs on a test input, yours or one it writes). A judge model scores it against what you asked for, and `make` revises until the score reaches `--target` (default 9), the rounds run out (`--rounds`, default 3), or the next call would cross your spending limit, which covers the whole command. Every version, test output, score and cost is kept in one folder. The best version is `final.md`, or for a skill an installable folder (`proofhouse install-skill --bundle <folder>`). The judge is a model, so its score is advice, not proof.

Put it online when you say so, with the hosting service's own tool (signed in your usual way):

```bash
proofhouse deploy make-landing-page-* --to netlify --dry-run    # shows the exact command first
proofhouse deploy make-landing-page-* --to netlify               # or vercel, cloudflare, surge, or any target you add
```

### Launch something: every part from one goal

```bash
proofhouse make "launch Brew, a one-tap coffee ordering app, to busy commuters" --kind launch \
  --provider anthropic --model <model> --max-cost-usd 15 \
  --visual-provider fal --visual-model <image-model> --voice-provider elevenlabs --voice-model eleven_multilingual_v2 --voice <voice-id>
```

A model plans the launch: which parts it needs (site, video, support agent, skill, prompt, announcement copy) and a full brief for each, with the same names, facts and tone throughout. Then each part is made by its own engine, the same one its own command uses, and judged and improved the same way. `--parts site,copy,video` picks the parts yourself. One spending limit covers the plan and every part; a part that would not fit is skipped and says so. Each part gets its own numbered folder, and `README.md` and `launch.json` sum it all up. The video part needs the video options above and FFmpeg.

`--kind copy` makes announcement copy on its own: headline, body, call to action and ready-to-post versions.

### Make a website

```bash
proofhouse make "a landing page for my bakery, with menu and opening hours" --kind site \
  --provider anthropic --model <model> --max-cost-usd 2.00
```

The model writes the whole site (HTML, CSS, JavaScript, as many pages as it needs). Proofhouse writes it to disk and checks it the way a visitor would: every page has a title, a language and a phone viewport, every image has alt text, and every link and file inside the site exists. With Chrome or Chromium on your machine (or `PROOFHOUSE_BROWSER` pointing at one), the home page is opened headless, screenshots are taken at desktop and phone width, and JavaScript errors are reported. The judge scores the pages and those results, and `make` revises until it is good enough or the limit is reached. The best version is in `site/`; open `site/index.html`.

### Images, video, voice and music

```bash
proofhouse media list                                   # OpenAI images and speech, ElevenLabs, Replicate, fal.ai, and yours
proofhouse media price fal "*" --usd 0.40               # your price per request, image, second or 1k characters
proofhouse generate image --provider openai-images --model gpt-image-1 --prompt "a red fox, studio light" --max-cost-usd 0.10
proofhouse generate video --provider fal --model <video-model> --prompt "drone shot over a neon city" --seconds 5 --max-cost-usd 1
proofhouse media add --from my-service.json             # any other service (or a local GPU server) as a template
```

### Make a video

```bash
proofhouse make "a 30-second hype video for my app" --kind video \
  --provider anthropic --model <text-model> \
  --visual-provider fal --visual-model <image-or-video-model> --visual-kind video \
  --voice-provider elevenlabs --voice-model eleven_multilingual_v2 --voice <voice-id> \
  --music-provider replicate --music-model <music-model> \
  --seconds 30 --max-cost-usd 10
```

A text model writes the script and shot list. Each shot is generated by any image or video service (stills get a slow push-in). A speech service reads the voice-over, and a music service makes the bed (or bring your own with `--music-file`). FFmpeg then cuts and frames every shot, mixes voice over music, burns in captions, and renders landscape 16:9, vertical 9:16 and square 1:1.

Each render is checked for length, frame size and sound, and the captions must match the script word for word. One spending limit covers the whole video. Everything is kept in one folder (`script.json`, `shots/`, audio, renders, `studio.json`). Needs FFmpeg installed.

### Let an agent run on its own

```bash
proofhouse loop "make the tests pass" --in ./my-app --check "pytest -q" --allow-commands \
  --provider anthropic --model <model> --rounds 30 --max-cost-usd 5
proofhouse loop "when the build breaks, find out why and write it up in BUILD-NOTES.md" --in . \
  --watch "gh run list --limit 1" --every 10m --for 8h --allow-commands --provider ollama --model llama3
```

Each round, the agent sees the goal, the files in its folder, what happened in recent rounds, and the output of your check and watch commands. It reads files, writes files, and (only with `--allow-commands`) runs commands in that folder. It cannot touch anything outside the folder.

The loop stops when your `--check` command passes, or when the agent says it is done. It also stops when `--rounds` or `--for` runs out, when the next call would cross the one spending limit, or when you press Ctrl-C. With `--watch` and `--every`, a look that finds nothing changed sends nothing and costs nothing. Every round is kept in `rounds.jsonl`, with `loop.json` for the totals. Provider keys are blanked out of command output before it goes anywhere.

### Train a model on your data

```bash
proofhouse train data examples.jsonl --out brew-data --system "You are Brew's support agent."   # or a .csv of input,output
proofhouse train price openai <base-model> --usd-per-million <price>      # your price per million training tokens
proofhouse train start --service openai --model <base-model> --data brew-data --epochs 3 --suffix brew --max-cost-usd 20
proofhouse train start --service mlx-lm --model <hf-model> --data brew-data                      # LoRA on your own Mac, free
proofhouse train services                                                 # OpenAI, Together, MLX, and any you add
```

`train data` cleans your examples into `train.jsonl` and a held-out `valid.jsonl` (chat format; duplicates dropped; it warns under 10 examples). `train start` uploads them, starts the job and waits for it (`--no-wait` returns at once; `train status` checks later). It then prints the exact `proofhouse run` line for your trained model.

Before anything is uploaded, the most the job could bill is worked out: every byte of the data times the epochs, as training tokens, at the price you declared. If that is over `--max-cost-usd`, or there is no price, nothing is uploaded or started. Training on your own machine runs your command (MLX LoRA ships) and costs nothing. Any other service, online or local, is one template: `proofhouse train add --from service.json`.

### Add-ons

```bash
proofhouse addons install ./acme-pack        # a folder with addon.json: providers, media and training services, tools, make kinds
proofhouse addons list                       # every add-on, what it adds, and any that failed to load
proofhouse make "a launch thread for Brew" --kind tweet-thread --provider ollama --model llama3   # a kind the pack added
```

Other people's providers, media services, training services, tools to install into, and new `make` kinds plug in without changing Proofhouse. A pack is data only (`addon.json`, schema `proofhouse.addon/v1`), and nothing in it runs. A Python package can also provide an add-on through the `proofhouse.addons` entry point. Its function returns the same contents, and it is code you chose to install, running as you. Shipped entries load first, then add-ons, then your own, so your entry with the same id always wins. Every request an add-on adds still goes through the spending limit. A broken add-on is skipped and reported, never fatal.

### Put it where you work

```bash
proofhouse make "an agent that reviews pull requests for security issues" --kind agent --provider ollama --model llama3
proofhouse install agent make-*/review-bot.md --into claude                     # ~/.claude/agents/
proofhouse install rule house-style.md --into cursor --project .               # .cursor/rules/house-style.mdc
proofhouse install mcp files --into cursor --command npx --arg=-y --arg server-files   # ~/.cursor/mcp.json
proofhouse uninstall mcp files --from cursor                                     # removes only what Proofhouse wrote
proofhouse hosts list                                                            # Claude Code, Cursor, Codex, and any tool you add
```

Agents, rules and MCP servers go into Claude Code, Cursor and Codex. Any other tool is one entry in `PROOFHOUSE_HOME/hosts.json`. Proofhouse writes marked blocks into shared files (`CLAUDE.md`, `AGENTS.md`, `config.toml`) and single entries into `mcp.json`, and keeps a record and a copy of every file it changes. Installing twice changes nothing; uninstalling removes only what it wrote, and refuses if you edited it since unless you pass `--force`.

Every provider that speaks the OpenAI chat format works, known or not, cloud or local. Each run goes through the spending limit: it is refused before sending if its worst-case estimate is over `--max-cost-usd`, or if the model has no price (shipped, or declared by you). A model on your own machine costs nothing. Dollar figures are estimates, not your bill. See [docs/providers.md](docs/providers.md).

---

## Supported models (framework v1.3)

Built-in `modelNotes` cover prompting quirks, API ids, and cost and caching levers for each model:

<!-- supported-models:begin -->
| Tier | Models |
|---|---|
| **Anthropic** | Claude Fable 5.1 · Mythos 5.1 · Opus 5 · Sonnet 5 · Haiku 4.5 |
| **OpenAI** | GPT-5.6 Sol · Terra · Luna |
| **Google** | Gemini 3.8 Flash |
| **xAI** | Grok 4.6 |
| **Meta** | Muse Spark 1.3 |
| **Moonshot** | Kimi K3 |
| **Legacy** | GPT-5.5 · Gemini (generic) · Fable 5 · Mythos 5 · Opus 4.8 |
| **Other** | Skill and artifact: the host agent or the artifact web-researches the model and caches the paragraph. CLI (`proofhouse`): offline; `models remember` stores your own notes, otherwise the generic profile is used and labeled `fallback`. |

Profiles last reviewed 2026-09-03; a profile older than 90 days is flagged stale. None of the 18 profiles cites sources yet, so every profile is labeled unverified. They are prompting guidance, not vendor specifications. `proofhouse models list` shows per-model ids, aliases, and dates.

Full profiles: [`proofhouse-framework.json`](proofhouse-framework.json) · human-readable [`proofhouse-framework.md`](proofhouse-framework.md)
<!-- supported-models:end -->

---

## Install and verify

One Python package, version 0.6.0, ships one command, `proofhouse`. Every interface reaches the same command tree (`proofhouse-compiler` still works as an alias and prints a one-line notice on stderr; `proofhouse optimize` likewise forwards to `proofhouse case`):

| Command group | What it is | Commands |
|---|---|---|
| Cases | The prompt or skill workspace above (`case new --kind prompt` or `--kind skill`), the skill installer, the model-notes cache, the packaged reference demo, and the part registry | `case` `install-skill` `uninstall-skill` `models` `demo` `parts` `scan` |
| Compiler | Offline compiler: requirements → IR → request builder artifact → evidence | `doctor` `validate` `inspect` `compile` `closed-loop` `adapters` |
| Eval harness | JSONL datasets, YAML rubrics, report skeletons | `eval validate` `eval report` `eval loadouts` `eval compile-loadout` `eval generate` |

Supported: the `case` workflow, `models`, `install-skill`, `demo`, and `validate` / `compile` / `closed-loop`. The experimental commands are listed under [Experimental and prototype parts](#experimental-and-prototype-parts).

```bash
uv sync --extra test                                    # package + pytest into .venv
uv run proofhouse doctor                                # doctor: success
uv run proofhouse closed-loop tests/compiler/fixtures/closed_loop_requirements_minimal.json --repair-budget 1
                                                        # closed-loop: PASS (structural)
uv run proofhouse eval validate --dataset evals/datasets/prompt_audit_cases.jsonl
                                                        # Dataset validation passed: ...
uv run pytest -q                                        # all passed, 1 deselected (live tests are opt-in)
uv run proofhouse demo --quiet                          # reference workflow: OK
uv run python scripts/reference_workflow.py --quiet     # same run via the script wrapper
```

CI runs the test suite on Linux, macOS and Windows with Python 3.11 to 3.14, runs the reference workflow against the built wheel, and runs `proofhouse demo` from that wheel outside the checkout. Everything above is offline: no network, no API key. Nothing here is a benchmark.

The compiler's `closed-loop` PASS is structural: the prompt compiles offline with the fake adapter and passes security gates, and its evidence lists what it did not measure. Its approved headless profiles are `structured_minimal_v0` and `structured_developer_v0`.

---

## Experimental and prototype parts

These ship in the repository but are not the supported path. Treat them as previews.

| Part | Status | Network |
|---|---|---|
| `proofhouse execute-openai`: a fail-closed live OpenAI call that refuses to send unless every mandatory requirement is in the request, and refuses before sending when the worst-case estimate of its cost is over your ceiling or the model has no price. The shipped price table has no entries yet, so today it refuses every model. Its dollar figures are estimates from that table, not your bill | experimental, opt-in | yes, only when opted in |
| `evaluate-product`, the requirements-contract commands, `route` / `assay` / `proof` | experimental | none |
| [`apps/proofhouse.jsx`](apps/proofhouse.jsx): a Claude artifact with a model picker, efficiency modes and a live compile loop; for an unknown model it web-researches, caches the result in artifact storage and labels it `researched` / `cached` / `fallback` | experimental | calls `api.anthropic.com` |
| The `hosted-*` and `missionrig-*` modules: experimental library slices, not a hosted service (their tenant label is not isolation) | experimental | none |
| `apps/dashboard/` | prototype | none |

The headless requirements compiler's maturity is still `PARTIAL`. Full map with versions and diagnostic codes: [docs/surfaces.md](docs/surfaces.md).

---

## Design rules

- Stay lightweight by default. Tighten only for safety, agentic execution, or missing context.
- Never invent repository or project facts.
- Use exact missing-context labels: `UNKNOWN`, `NOT SPECIFIED`, `NOT FOUND IN PROVIDED MATERIAL`.
- Keep cybersecurity and sensitive-data work defensive, authorized, and privacy-preserving.
- No private chain-of-thought dumps. Concise rationales only.

It was designed for coding agents, Custom GPTs, Cursor skills, and security-adjacent AI work, where inventing facts or skipping a safety boundary is not acceptable.

---

## Repository map

```text
proofhouse-framework.*   Portable meta-optimizer spec (v1.3 model profiles)
skills/proofhouse/       Cursor / Claude Code skill bundle + artifact JSX
src/proofhouse/          Eval harness, headless compiler, optimize (cases, constraints, runs, checks, export)
examples/                Demo inputs, including reference-advisory/ for the reference workflow
scripts/                 Generators (model surfaces, skill bundle, contracts) and reference_workflow.py
docs/                    Scope, architecture, surfaces, evidence format, decisions, assurance statements
prompts/                 Core prompt, modes, modules, templates, Custom GPT pack
evals/                   JSONL datasets, YAML rubrics
apps/                    Experimental artifact and dashboard prototypes
tests/                   Test suite, contract schemas and fixtures
```

Internal mission reports and review corpora are not published in this repository. Public decisions are summarized in [docs/decisions/](docs/decisions/), and each assurance statement in [docs/assurance/](docs/assurance/) lists the exact revision, commands, results and exclusions.

---

## Start here

- [Reference workflow](https://github.com/KM-it-ops/Proofhouse/blob/main/docs/reference-workflow.md): one failed check to a verified fix, offline
- [Product scope](https://github.com/KM-it-ops/Proofhouse/blob/main/docs/product-scope.md) · [Architecture](https://github.com/KM-it-ops/Proofhouse/blob/main/docs/architecture.md) · [Surfaces and contracts](https://github.com/KM-it-ops/Proofhouse/blob/main/docs/surfaces.md) · [Evidence format](https://github.com/KM-it-ops/Proofhouse/blob/main/docs/evidence-format.md)
- [Decision records](https://github.com/KM-it-ops/Proofhouse/blob/main/docs/decisions/) · [Assurance statements](https://github.com/KM-it-ops/Proofhouse/blob/main/docs/assurance/) · [Troubleshooting](https://github.com/KM-it-ops/Proofhouse/blob/main/docs/troubleshooting.md)
- [Quickstart](https://github.com/KM-it-ops/Proofhouse/blob/main/docs/quickstart.md) · [Showcase](https://github.com/KM-it-ops/Proofhouse/blob/main/docs/showcase.md) · [Custom GPT setup](https://github.com/KM-it-ops/Proofhouse/blob/main/docs/custom-gpt-setup.md)
- [Changelog](https://github.com/KM-it-ops/Proofhouse/blob/main/CHANGELOG.md) · [Contributing](https://github.com/KM-it-ops/Proofhouse/blob/main/CONTRIBUTING.md) · [Security policy](https://github.com/KM-it-ops/Proofhouse/blob/main/SECURITY.md)

---

<sub>Custom GPT surface: <strong>PromptOps Architect powered by Proofhouse</strong> · MIT License</sub>
