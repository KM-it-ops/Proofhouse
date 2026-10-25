# The evidence trail: `proofhouse case`

One feature of the record: you declare the checks, and a PASS names the exact prompt, outputs, checks and judgements it came from. It is not the main product, which is making things with any model ([usage guide](usage.md)).

https://github.com/user-attachments/assets/17ec6d22-1ba7-4952-bec0-d3f24c9b29ce

*44-second clip of the older evidence walk, not the product. You type one sentence, pick a model, answer seven questions, and get a compiled prompt where each rule is traced back to the answer that produced it. The scene is an authored example, not a recorded run.*

## How it works

`proofhouse case` renders the framework's clarify / compile / self-heal prompts as packets you run in the agent or model of your choice, and checks what you paste back against the criteria you declare. It does not call a model and it does not rate quality.

These are the [reference workflow](reference-workflow.md)'s steps, and they run as written. `pc` below is `proofhouse` (`uv run proofhouse` from a clone). Work in a scratch folder holding copies of the example inputs:

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

Details: [architecture](architecture.md)(architecture.md), [decision 0002](decisions/0002-what-pass-means.md), [evidence format](evidence-format.md).
