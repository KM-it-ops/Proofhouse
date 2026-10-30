# Reference workflow: an advisory summary that keeps its constraints

This walks one real failure to a verified fix, offline. The inputs are in [`examples/reference-advisory/`](../examples/reference-advisory/): a synthetic advisory, clarification answers, two prompt revisions and the output each produced. The same files ship inside the package. `proofhouse demo` runs the case from that copy. [`scripts/reference_workflow.py`](../scripts/reference_workflow.py) is the clone wrapper and fails if any result differs; CI runs it against the installed wheel, and also runs `demo` from the wheel outside the checkout.

Run it in one go after install:

```bash
proofhouse demo                # recorded outputs, no model call
```

It ends by printing the workspace folder, the path to `report.md`, and two commands that reopen the case later: `proofhouse case status --case <folder>/advisory-case` shows where the case stands, and `proofhouse case check --case <folder>/advisory-case` checks it again.

From a clone:

```bash
python scripts/reference_workflow.py    # prints each command and its output
```

Measured on the maintainer's Windows machine on 2026-10-27: about 70 seconds for `proofhouse demo` or the script, and about 100 seconds for the first run from a clean install. It prints nothing while it works with `--quiet`, so let it finish. How long a person takes to follow it by hand has not been measured.

The rest of this page is the same journey by hand. Commands assume you are in a scratch directory holding copies of the example files; `pc` stands for `proofhouse` (`uv run proofhouse` from a clone).

## 1. Start a case and answer the clarify packet

```bash
mkdir -p build/ref && cp examples/reference-advisory/* build/ref && cd build/ref    # from a clone: the scratch directory
pc case new --case advisory-case --objective-file objective.txt --model "Claude Sonnet 5" --preset efficient
```

`advisory-case/01-clarify.md` is a packet you run in your own agent or model. Put the answers in `advisory-case/answers.json` (the example has them: `cp answers.json advisory-case/answers.json`), then:

```bash
cp answers.json advisory-case/answers.json
pc case compile --case advisory-case
pc case constraints list --case advisory-case
```

Compile snapshots your answers and turns each into an **accepted constraint** (K1–K3). They stay in `case.json`, outside any generated prompt, and every later revise packet receives them.

## 2. Say how each constraint will be checked

```bash
pc case constraints add --case advisory-case --text "Cite the advisory section for each claim"      # K4
pc case criteria add --case advisory-case --id AUD --must-contain "SOC analysts"                     # prompt text
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

`--target output` checks what a model returned, not the prompt. `ACC` is a human judgement.

## 3. Record revision 1 and what it produced

```bash
pc case record --case advisory-case --prompt-file prompt-v1.txt
pc case output add --case advisory-case --revision 1 --output-file output-v1.txt \
    --input-id EC-2026-017 --input-file advisory.txt --model "Claude Sonnet 5" --source "pasted from host agent"
pc case verdict --case advisory-case --revision 1 --criterion ACC --run R1 --result fail \
    --note "claims active exploitation; the advisory does not say that"
pc case check --case advisory-case        # exit 3: v1 FAIL  UNK NOGUESS CITE ACC fail
```

The output said the issue was "actively exploited in the wild". The advisory says the vendor has not published that. That is the failure this case exists to catch.

## 4. Revise without losing anything

```bash
pc case revise --case advisory-case --feedback "It claimed active exploitation, which the advisory never states, and cited nothing."
```

Open `advisory-case/03-revise-v1.md`: next to your feedback it carries the original clarification answers and every accepted constraint, marked authoritative. Run it, save the result, then:

```bash
pc case record --case advisory-case --prompt-file prompt-v2.txt
pc case output add --case advisory-case --revision 2 --output-file output-v2.txt \
    --input-id EC-2026-017 --input-file advisory.txt --model "Claude Sonnet 5" --source "pasted from host agent"
pc case verdict --case advisory-case --revision 2 --criterion ACC --run R2 --result pass
pc case check --case advisory-case        # exit 0: v2 PASS, K1-K4 satisfied
```

## 5. Compare, report, export

```bash
pc case compare --case advisory-case --from 1 --to 2      # UNK, NOGUESS, CITE, ACC newly_passing
pc case compare --case advisory-case --from 2 --to 1      # exit 3: regressions
pc case report --case advisory-case --out report.md
pc case export --case advisory-case --out advisory-case.zip --preview
pc case export --case advisory-case --out advisory-case.zip
pc case import --bundle advisory-case.zip --case elsewhere/advisory-case
pc case check --case elsewhere/advisory-case              # same result
```

`report.md` lists lineage, the constraint ledger with status, every check with its evidence class, the exact outputs tested, and what the report does not show. The export leaves out the `.md` packets because they embed local paths; import refuses any file that does not match the bundle's manifest (the manifest is not signed).

## What this demonstrates, and what it does not

It demonstrates that a real check failure on recorded output is caught, that a revision keeps every accepted constraint, that the fix is shown against the same criteria, and that the evidence survives a round trip to another workspace.

It does not demonstrate that revision 2 is a good prompt in general, that a model would produce `output-v2.txt` reliably, or anything about other advisories. The outputs are synthetic text written for the example.
