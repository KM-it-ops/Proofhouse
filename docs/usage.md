# Using Proofhouse

Every way to make, run and deliver things. For a short tour, see the [README](../README.md); for the evidence trail, see [the evidence trail](evidence-trail.md). `<model>` stands for a model id from your provider.

## First run: what do I have, and what is missing?

```bash
proofhouse setup                 # finds your agents, local model servers, keys (set / not set), ffmpeg, a browser, a hosting tool
proofhouse setup --json
proofhouse setup add grok-imagine --name "Grok Imagine" --how web --url https://grok.com/imagine --makes image,video --step "Open the page" --step "Paste the brief" --step "Download the clip"
proofhouse setup add my-gen --name "My generator" --how cli --command my-gen --makes image
proofhouse setup remove grok-imagine
```

It only looks: it never starts a program, never shows a key's value, and talks only to ports on your own machine. For each missing piece it says what that piece would unlock and how to get it, and ends with a "You can do now / Not yet" list. A tool it cannot find, such as a website-only app, is saved as data in `PROOFHOUSE_HOME/tools.json`; a website tool is listed as used by hand, with your steps, and the file it makes comes back through `record` or `render video`. For a hosting tool it cannot tell whether you are signed in.

## Host mode (no API key)

If you already work in Cursor, Codex, Gemini CLI, Grok CLI or Claude Code, **host mode** lets that agent write and judge with its own model while Proofhouse only checks, records and assembles—no API key, and Proofhouse itself makes no network calls on these commands. (With `--allow-commands`, Proofhouse runs the code the model wrote, and that code may use the network.)

```bash
proofhouse check site ./my-site --allow-commands    # opens the site in your browser
proofhouse check mcp ./server --allow-commands    # starts model-written servers only when you opt in
proofhouse record site ./my-site --out ./out --request "bakery landing" --agent cursor --score 8
proofhouse render video ./my-video --formats 16x9,9x16,1x1
```

Install the teaching skill with `proofhouse install-skill --skill proofhouse-host` (or copy `skills/proofhouse-host/` into your agent's skills folder). Scores on `record` are the agent's own advice; a second agent as judge is better when you have one.

A check that did not run (no `--allow-commands`, no browser, a browser that got stuck) shows as `NOT MEASURED` and never counts as passed. `check` and `record` exit 0 when every check ran and passed, 1 when something failed, and 3 when nothing failed but something was not measured; `record` saves that version as "not measured" and delivers it only while no version has passed.

### What the quality checks catch

Host mode still checks that files exist, links work and manifests run; these extra rows catch thin or repetitive writing and weak static sites.

| Check | Applies to | Passes when |
| --- | --- | --- |
| **length** | copy, prompt, skill/agent body, site text (from HTML) | copy has at least 25 words; prompt at least 40; skill or agent body at least 60 |
| **filler** | same text targets | fewer than two distinct vague phrases from the built-in list; one hit is a warning in `detail` |
| **specifics** | copy and site text | at least one digit, money amount, or capitalised name not at the start of a sentence |
| **parts differ** | launch only | no pair of text parts (15+ words each) shares 3-word shingles with Jaccard overlap 50% or higher |
| **contrast** | site and app | body or `:root` text/background hex pair has WCAG contrast ratio at least 4.5, or no plain pair is found |
| **text size** | site and app | body `font-size` in px or rem is at least 16px (1rem = 16px), or no size is set |
| **headings** | site and app | exactly one `h1` in `index.html` |
| **image alt** | site and app | every `img` has non-empty `alt` |
| **title** | site and app | non-empty `<title>` between 10 and 70 characters |

### A second agent as judge

When the same agent writes and scores, the score is only its own advice. If you have another coding agent installed (Codex, Gemini CLI, Grok CLI, Claude Code, or another), use it as an independent judge:

1. Save each candidate version without agent names in the paths (blind judging).
2. Ask the second agent to read the rubric and the files and reply with one number from 0 to 10, for example:
   - `codex exec --skip-git-repo-check -s read-only -C <tmpdir> --output-last-message score.txt "<rubric + list of files>"`
   - `grok -p "<rubric + list of files>" --output-format plain`
3. Record the writer's round with `--score` (optional) and the judge's result with `--judge <name> --judge-score <0-10>` and optionally `--judge-note "one sentence"`. The judge name must differ from `--agent` (labels like `cursor` and `cursor:composer` count as the same agent).

For comparing saved files, add `--judge <name>` to `proofhouse compare` with `--entry` so the side-by-side page says who gave the scores.

## Ways in

| Entry | Use it when | Status | Network |
|---|---|---|---|
| **Command line**: `proofhouse case` | You want the evidence trail above: constraints, recorded outputs, checks, compare, report | supported | none |
| **Any provider, any model**: `proofhouse run --provider P --model M --prompt "..."` | You want a prompt run on OpenAI, Anthropic, Google, Mistral, Groq, Together, Fireworks, OpenRouter, DeepSeek, xAI, a model on your own machine (Ollama, LM Studio, vLLM, llama.cpp), or any other provider you add with one command | new | only that call, through your spending limit |
| **Cursor or Claude Code skill**: `proofhouse install-skill` asks which agent (Cursor, Claude Code, or another one you name with its skills folder); `--host cursor` or `--host claude` skips the question. Then say "Proofhouse" in a new chat or session | You want the same clarify → compile → self-heal loop as a conversation | supported entry point | the host agent's tools |

One command, `proofhouse`, makes the thing and can keep the evidence trail. The PromptOps skill (v1.3) is the conversation entry: say "Proofhouse" after `install-skill`. The headless compiler's maturity is listed under [Experimental and prototype parts](development.md#experimental-and-prototype-parts).

Both entries use the same framework ([`proofhouse-framework.json`](../proofhouse-framework.json)) and the same model notes. The framework also covers Efficient / Balanced / Thorough token presets, loops for recurring agents (trigger, body, exit, escalation), prompt audits with missing-context labels, and agent design (permission maps, tool boundaries, stop conditions). The skill is installed to `~/.cursor/skills/proofhouse` (or `~/.claude/skills/proofhouse` with `--host claude`) and the installer checks it (the bundle ships inside the package); without the console script, `python -m zipfile -e skills/proofhouse/proofhouse.skill ~/.cursor/skills` (or `~/.claude/skills`) does the same. The skill can research an unfamiliar model with the host agent's tools; the command line goes online only when you ask it to run a model (`proofhouse run`, `execute-openai`), and otherwise uses your own notes (`models remember`) or a generic profile labeled `fallback`.

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

If your coding agent already ran the job and saved each answer to a file, you can compare without calling any model:

```bash
proofhouse compare "Summarise this contract in five bullet points." \
  --entry cursor:composer-2.5=outputs/cursor.md --entry codex=outputs/codex.md \
  --score cursor:composer-2.5=8 --score codex=9 --note codex="shorter and clearer"
```

Give at least two `--entry LABEL=path` pairs (label is free text, for example an agent name or `provider:model`). Optional `--score` and `--note` use the same label; optional `--judge NAME` marks scores as coming from a different agent than the writers. Proofhouse copies the files, writes `side-by-side.html` and `compare.json`, and prints a small table. Scores are advice, not proof, and Proofhouse spends nothing on this path.

### Make it

```bash
proofhouse make "a prompt that answers refund emails warmly" --provider ollama --model llama3
proofhouse make "a skill that reviews pull requests for security issues" --kind skill \
  --provider anthropic --model <model> --max-cost-usd 1.00
```

`make` writes version 1 with your model and tries it (a prompt runs on a test input, yours or one it writes). A judge model scores it against what you asked for, and `make` revises until the score reaches `--target` (default 9), the rounds run out (`--rounds`, default 3), or the next call would cross your spending limit, which covers the whole command. Every version, test output, score and cost is kept in one folder. The best version is `final.md`, or for a skill an installable folder (`proofhouse install-skill --bundle <folder>`). The judge is a model, so its score is advice, not proof.

`--kind rule` makes a Markdown instruction and checks installation and clean removal in every rule-capable host using throwaway settings. `--kind mcp` makes a stdio server and checks its `initialize` and `tools/list` replies; the best folder includes an exact install line. `--kind hook` makes a command hook, runs it on a sample event, and includes a Claude Code settings snippet. Each version keeps `checks.json`; generated commands run with a limited environment and a timeout.

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

In **host mode**, you can also check and record a launch your agent wrote into one folder (no API key): put `launch.json` plus each part at the paths it names, run `proofhouse check launch ./LAUNCH`, then `proofhouse record launch ./LAUNCH --out ./out --request "..." --agent cursor --score 8`. Proofhouse checks every part the same way as that kind on its own, checks shared names and facts across parts, and on record delivers each part under `--out/<part-id>/`, copies `launch.json`, and writes `README.md` with a parts table and which part carried each fact.

`--kind app` makes a shared web app and a separate package for every selected platform. Use repeatable `--platform` (for example `--platform pwa --platform android`); without it, every target in `app_platforms.json` is selected. The catalog ships PWA, Windows, macOS, Linux, iOS and Android targets and can be extended or overridden in `PROOFHOUSE_HOME/app_platforms.json`. Each version keeps static and build results in `checks.json`; platform builds run only with `--allow-commands`, after their setup steps (such as `npm install` and `npx cap add android`). The delivered `README.md` lists files, where the build output is, and how to build by hand. The native builds are proven on all six platforms with a fixed sample app and no model; a build of a model-written app that has not been run is marked "to check" with what is left to confirm. Signed store builds are not covered.

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
  --facts product-facts.json --allow-commands \
  --voice-provider elevenlabs --voice-model eleven_multilingual_v2 --voice <voice-id> \
  --music-provider replicate --music-model <music-model> \
  --seconds 30 --max-cost-usd 10
```

A text model writes the script and shot list. Each shot is generated by any image or video service (stills get a slow push-in), or captured from real command output and pages when you pass `--facts` (command captures need `--allow-commands`). A speech service reads the voice-over, and a music service makes the bed (or bring your own with `--music-file`). FFmpeg then cuts and frames every shot, mixes voice over music, burns in captions, and renders landscape 16:9, vertical 9:16 and square 1:1.

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

### Your agent runs the loop; Proofhouse referees

When Cursor, Codex or another tool already writes and runs the work, Proofhouse does not call a model. It runs your check after each round, keeps the record, and tells you whether to stop.

```bash
proofhouse referee start "make the tests pass" --check "pytest -q" --folder ./my-app --out ./referee-run --allow-commands
proofhouse referee round ./referee-run --summary "fixed the failing test" --allow-commands
proofhouse referee status ./referee-run
```

`referee round` exits `0` when the check passes, `10` when you should keep going, and `11` when the round or time limit is up without a pass. The check needs `--allow-commands` on `start` and every `round`. The record folder must be new or empty and separate from the work folder. The check sees only a short list of basic system variables (such as PATH, TEMP and HOME), never one whose name looks like a key, token, secret or password, and its whole process tree is stopped on timeout. The record is a plain-file log, not tamper-proof: it refuses a changed check command, but the agent being refereed can still edit the folder, so treat it as a record to read, not a signed proof.

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

Every provider that speaks the OpenAI chat format works, known or not, cloud or local. Each run goes through the spending limit: it is refused before sending if its worst-case estimate is over `--max-cost-usd`, or if the model has no price (shipped, or declared by you). A model on your own machine costs nothing. Dollar figures are estimates, not your bill. See [providers](providers.md)(providers.md).
