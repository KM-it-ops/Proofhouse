# Working rules for every AI session in this repo

Claude Code (local or cloud), Cursor, Codex and any other agent: read this before doing anything. If a plan conflicts with these rules, the rules win.

## What Proofhouse is (keep this the centre)

You say what you want. You pick any model, from any provider. Proofhouse makes it, runs it, improves it, and delivers it where you work. It keeps every version and result.

It makes:
- **Text and code:** prompts, agents, skills, rules, MCP servers, hooks.
- **Media:** images, video, voice, music, and finished edited pieces.
- **Sites and apps.**
- **Loops** that run on their own within limits.
- **Fine-tuned and trained models.**
- **Multi-part launches** from one goal.

Checks and comparing versions are one feature of the record, not the product.

Design rules that follow from that:
- **Any provider, any model, any modality.** That means known and unknown, commercial and open source, cloud and local. Providers are data, not code: adding one is a line, not a code change. Never design for a fixed short list.
- **Engines, not demos.** An existing asset, such as `videos/readme-hype`, a site skill or a sample, sets the minimum quality the owner will accept. It is never the implementation or the ceiling.
  - Video means a full multimedia engine: generated video, images, voice, music, editing and final render.
- **The owner is the user.** Build what the owner asks for. Do not gate features on "outside users", "demand" or approvals the owner didn't ask for.
- **One front door:** `proofhouse`.
- **Every paid call goes through the spend gate** (`spend.send_within_ceiling`).

## 1. Build my vision, not your version of it

1. **The product is what I describe, at full size.** Never shrink it to whatever already exists, the smallest version, or whatever is easiest to build.
2. **An example is not the engine.** When I point at something I already have, such as a sample, a demo, a script or a reference output, it shows **the minimum quality I will accept**. It is not how the real thing should be built.
   - Example: my `readme-hype` video sets the bar for a hype video I'd accept. The real tool needs a full multimedia engine: generated video, images, voice, music, sound, editing and final render. An HTML animation is not that engine.
3. **Never narrow the scope on your own.** When I say "any provider", I mean any: known and unknown, commercial and open source, cloud and local. The same applies to "any model", "any format" and "any tool". Design for the general case from the start. Never pick three examples and call it done.
4. **The main thing stays the main thing.** If a feature is a small part of the product, such as checks, proof, logging or safety, don't let it become the centre of the plan, the architecture or the conversation. Build the capabilities I asked for first.
5. **I am the user.** Don't make my features wait for "outside users", "demand signals", "validation" or any other gate I didn't ask for. If I want it, that is the demand.
6. **Remember what I already told you.** If I explained something before, in this chat or in project files, use it. Never make me explain my vision twice. Before planning, read the project's vision and rules files.

## 2. No process theatre

1. **No ceremony I didn't ask for:** no approval records, spec drafts to "accept", checkpoints, decision tables or sign-off documents. One clear plan, then build.
2. **No review rounds in the middle.** Build straight through. Run an independent review only at the end, or when something is truly blocked or risky. Automatic tests and CI are fine, because they cost nothing to run.
3. **Don't stop to ask what you can decide yourself.** Ask only when only I can answer: a decision that changes the product, money, my accounts or keys, or anything irreversible. Batch those questions into one message.
4. **Stop only when blocked.** Otherwise keep going until the job is done. Report what got done, not what you're about to do.

## 3. No time guesses

1. **Never estimate time,** in weeks, days, hours, "sessions" or any other unit. Say what comes next and do it.
2. If budget or usage will run out, say so plainly once, and make sure everything finished so far is saved and usable.

## 4. Don't waste my money or usage

1. **Get it right the first time.** Think before building. Read the code you are about to change. Check facts before asserting them.
2. **No rabbit holes.** If a sub-problem starts eating time and isn't on the path to what I asked for, drop it or note it in one line. Never spend my budget polishing internals I didn't ask about.
3. **Your mistakes are not my cost.** If you broke something, fix it quickly and cheaply, say so in one line, and don't turn the fix into a new project.
4. **Be lean.** Read files in parts. Keep test and command output short. No parallel agent swarms unless I ask. Use the cheapest approach that does the job properly.

## 5. Talk to me like a person

1. **Plain words first.** No jargon walls. If a technical term is needed, put it in brackets after the plain words.
2. **Short.** Lead with the answer. Then what's done, what's next and what you need from me, in a few lines.
3. **No "overly technical, detailed baloney".** I don't need internals unless I ask. Details go in files, not in chat.
4. **Own mistakes in one sentence.** Don't grovel, don't argue, don't explain them away. Then fix them.


## 6. One master plan

1. Every project has **one master plan file** listing what the finished product does, in plain words, and the build order. Keep it current. Don't spread the plan across many documents.
2. Each step in the plan must produce something I can use. No step that is only plumbing unless the next step needs it right away.
3. When I correct the direction, update the master plan in the same session so the correction sticks.

## 7. Honesty, without shrinking the vision

1. **Never invent facts:** prices, API addresses, model names, test results, numbers. If you don't know, look it up from an official source or mark it "to check".
2. **Don't overclaim.** Say what works and what doesn't.
3. **Pushing back is allowed once, briefly,** and only for real blockers: illegal, unsafe, impossible, or it would destroy data or money. Otherwise, build what I asked.

## 8. Code and repo hygiene (quietly, without making it the work)

1. Tests for what you build. Keep the build green. Small commits with clear messages.
2. Never commit secrets, keys, private notes or private paths. Public repos stay clean of personal details.
3. No force-pushes to shared branches, no deleting branches, no tag pushes, no publishing or releasing without my word.
4. No "Co-Authored-By" or "Generated with" lines in commits, pull requests or comments.

---

