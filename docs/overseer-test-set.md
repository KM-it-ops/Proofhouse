# Overseer test set (labels for Boss to confirm)

`proofhouse "<objective>"` reads a plain goal and decides what kind of thing to make. This file is the
answer key for that decision: 32 realistic goals, each with the kind of artifact (artifact class) it
should become and a one-line reason.

**Status:** draft labels. Boss confirms or corrects them. Nothing here builds or changes the router.

How to read a row:

- **Should be:** the proposed kind, one of the 13 artifact classes in
  `src/proofhouse/compiler/orchestration/route.py` (prompt, loop, workflow, subagent, skill, tool, MCP,
  API, hook, harness, site, media, plain_code).
- **Also fair:** other answers that a good router could defend. A router that gives one of these is not
  wrong, but it should say why.
- **Today's router:** what the current keyword router answers, from running `route()` offline on the
  objective (no model calls). "same" means it agrees. A **bold** answer means it disagrees.

Today's keyword router agrees on **7 of 32**. It sends most goals to `prompt`, because it only reacts to
fixed words such as "away", "website" or "video". Row 1 is the known case: a weekly CVE summary should
be a loop, and the router says prompt.

## The set

| # | Objective | Should be | Also fair | Today's router | Reason |
|---|---|---|---|---|---|
| 1 | a weekly agent that summarizes new CVEs for my stack and emails me | loop | - | **prompt** | Runs on its own every week with nobody watching; the known case the keyword router sent to prompt. |
| 2 | write a system prompt for a customer support bot for my bakery | prompt | - | same | One set of instructions for one model to follow. |
| 3 | make my prompt for summarizing contracts better | prompt | - | same | Improve an existing prompt: write, try, judge, revise. |
| 4 | every night, check my GitHub repos for failing CI and open an issue with the cause | loop | - | **prompt** | Repeats on a schedule and acts without an operator. |
| 5 | keep fixing the failing tests in this repo until they pass, but stop at $5 | loop | - | **prompt** | Repeats until a goal is met, inside a spending limit. |
| 6 | I'm away next week, answer routine questions in our support inbox | loop | - | same | Works unattended for a stretch of time. |
| 7 | build a website scraper that pulls competitor prices every morning | loop | plain_code | **site** | Runs every morning on its own; 'website' is a trap, nothing here is a site. |
| 8 | a code reviewer agent for Claude Code that only looks at security | subagent | - | **prompt** | A specialist with its own context that a host tool hands work to. |
| 9 | a skill that teaches any agent our commit message style and changelog rules | skill | - | **prompt** | Reusable instructions any agent loads across projects. |
| 10 | block any git commit that contains an API key | hook | plain_code | **prompt** | Reacts to an event (a commit) and can stop it. |
| 11 | when Claude Code finishes a task, post a summary to my Slack | hook | - | **prompt** | Reacts to a host tool's event. |
| 12 | let my agents read and update tickets in our Jira | MCP | tool | **prompt** | Gives agents ongoing access to an outside system with credentials. |
| 13 | connect Claude to my Postgres database, read-only | MCP | - | **prompt** | A tool server agents can query; the database is the external system. |
| 14 | a function my agent can call to look up today's weather for a city | tool | - | **prompt** | One callable action against an outside service. |
| 15 | let my agent send emails through my Resend account | tool | MCP | **prompt** | One action with a key; becomes MCP if it needs inbox state. |
| 16 | an endpoint my app can call to classify support emails by urgency | API | - | **prompt** | Another program calls it over HTTP. |
| 17 | a command-line tool that renames my photos by the date they were taken | plain_code | - | **prompt** | Fully deterministic; no model needed. |
| 18 | convert this CSV of invoices into QuickBooks import format | plain_code | prompt | **prompt** | A fixed mapping; a model would add cost and risk. |
| 19 | a landing page for my launch with a waitlist form | site | - | same | A web page people visit. |
| 20 | a 30-second hype video for the README with voice-over and music | media | - | same | Generated video, voice and music, edited and rendered. |
| 21 | take a product brief, write the spec, then the code, then the tests, then the docs | workflow | - | **prompt** | A fixed chain of stages, each feeding the next. |
| 22 | research three competitors, compare their pricing, and write a one-page brief | workflow | prompt | **prompt** | Several steps (gather, compare, write) in a set order. |
| 23 | an agent that remembers what it learned about my codebase between sessions | harness | skill | **prompt** | State must survive across runs. |
| 24 | a research assistant that keeps a notebook and picks up where it left off each day | harness | loop | **prompt** | Persistent memory is the core; the daily schedule is secondary. |
| 25 | write a hook for my blog post intro | prompt | - | same | 'Hook' means an opening line here, not an event handler; a keyword trap. |
| 26 | write alt text for every image in this folder | workflow | loop | **media** | The same model step over many files; 'image' is a trap, nothing is generated. |
| 27 | help me with my resume | prompt | - | same | Ambiguous: could be one answer now (one_prompt) rather than a reusable artifact. |
| 28 | an assistant for my team's onboarding | skill | subagent, site | **prompt** | Ambiguous: reusable know-how is the core, but it could be a chat page or a specialist agent. |
| 29 | automate my weekly report | loop | workflow, plain_code | **prompt** | Ambiguous: 'weekly' and 'automate' mean unattended; the content may need only fixed code. |
| 30 | something that watches our logs and tells me when something weird happens | loop | hook | **prompt** | Ambiguous: polling the logs is a loop; reacting to a log event is a hook. |
| 31 | turn our docs into something people can ask questions to | site | MCP, prompt | **prompt** | Ambiguous: for people it is a page; for agents it is an MCP server. |
| 32 | translate our app's strings into 12 languages | workflow | prompt, plain_code | **prompt** | Ambiguous: one model step per language, then a fixed merge. |

Rows 7, 25 and 26 are keyword traps: they use a word ("website", "hook", "image") that means something
else in context. Rows 27 to 32 are ambiguous on purpose. A good router asks one short question or picks
the safer kind and says so.

## What Boss needs to decide

1. **Confirm or correct each "Should be" label.** Mark any row where the label is wrong.
2. **Newer kinds.** The 13 classes are older than some of what Proofhouse makes today: the `make` kinds
   agent, app, copy, rule, video and launch, and the separate `train` command. Several goals
   above fit those better. For example, row 9 could be a rule, row 20 a video, and row 31 an app. Decide whether the overseer should answer
   with the newer kinds, or keep the 13 classes and map them onward.
3. **Ambiguous goals.** Decide whether the overseer should ask a question (rows 27 to 32) or pick and
   explain.

Once the labels are confirmed, this table becomes the test the new router must pass. The router is not
built yet.
