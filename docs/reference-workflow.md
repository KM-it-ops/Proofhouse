# Reference workflow: an advisory summary that keeps its constraints

This walks one real failure to a verified fix, offline. The inputs are in [`examples/reference-advisory/`](../examples/reference-advisory/): a synthetic advisory, clarification answers, two prompt revisions and the output each produced. [`scripts/reference_workflow.py`](../scripts/reference_workflow.py) runs exactly these steps and fails if any result differs; CI runs it against the installed wheel.

Run it in one go:

```bash
python scripts/reference_workflow.py                # prints each command and its output
```

Measured on the maintainer's Windows machine: about 13 seconds for the script. How long a person takes to follow it by hand has not been measured.

The rest of this page is the same journey by hand. Commands assume you are in a scratch directory holding copies of the example files; `pc` stands for `proofhouse-compiler` (`uv run proofhouse-compiler` from a clone).

## 1. Start a case and answer the clarify packet

```bash
pc optimize new --case advisory-case --objective-file objective.txt --model "Claude Sonnet 5" --preset efficient
```

`advisory-case/01-clarify.md` is a packet you run in your own agent or model. Put the answers in `advisory-case/answers.json` (the example has them), then:

```bash
pc optimize compile --case advisory-case
pc optimize constraints list --case advisory-case
```

Compile snapshots your answers and turns each into an **accepted constraint** (K1–K3). They stay in `case.json`, outside any generated prompt, and every later revise packet receives them.

## 2. Say how each constraint will be checked

```bash
pc optimize constraints add --case advisory-case --text "Cite the advisory section for each claim"      # K4
pc optimize criteria add --case advisory-case --id AUD --must-contain "SOC analysts"                     # prompt text
pc optimize criteria add --case advisory-case --id UNK --target output --must-contain UNKNOWN
pc optimize criteria add --case advisory-case --id NOGUESS --target output --must-not-contain "exploited in the wild"
pc optimize criteria add --case advisory-case --id LEN --target output --max-words 120
pc optimize criteria add --case advisory-case --id CITE --target output --regex "\(s\d\)"
pc optimize criteria add --case advisory-case --id ACC --target output --manual "Every claim matches the advisory"
pc optimize constraints link --case advisory-case --id K1 --criterion AUD
pc optimize constraints link --case advisory-case --id K2 --criterion UNK
pc optimize constraints link --case advisory-case --id K2 --criterion NOGUESS
pc optimize constraints link --case advisory-case --id K3 --criterion LEN
pc optimize constraints link --case advisory-case --id K4 --criterion CITE
pc optimize constraints link --case advisory-case --id K4 --criterion ACC
```

`--target output` checks what a model returned, not the prompt. `ACC` is a human judgement.

## 3. Record revision 1 and what it produced

```bash
pc optimize record --case advisory-case --prompt-file prompt-v1.txt
pc optimize output add --case advisory-case --revision 1 --output-file output-v1.txt \
    --input-id EC-2026-017 --input-file advisory.txt --model "Claude Sonnet 5" --source "pasted from host agent"
pc optimize verdict --case advisory-case --revision 1 --criterion ACC --run R1 --result fail \
    --note "claims active exploitation; the advisory does not say that"
pc optimize check --case advisory-case        # exit 3: v1 FAIL  UNK NOGUESS CITE ACC fail
```

The output said the issue was "actively exploited in the wild". The advisory says the vendor has not published that. That is the failure this case exists to catch.

## 4. Revise without losing anything

```bash
pc optimize revise --case advisory-case --feedback "It claimed active exploitation, which the advisory never states, and cited nothing."
```

Open `advisory-case/03-revise-v1.md`: next to your feedback it carries the original clarification answers and every accepted constraint, marked authoritative. Run it, save the result, then:

```bash
pc optimize record --case advisory-case --prompt-file prompt-v2.txt
pc optimize output add --case advisory-case --revision 2 --output-file output-v2.txt \
    --input-id EC-2026-017 --input-file advisory.txt --model "Claude Sonnet 5" --source "pasted from host agent"
pc optimize verdict --case advisory-case --revision 2 --criterion ACC --run R2 --result pass
pc optimize check --case advisory-case        # exit 0: v2 PASS, K1-K4 satisfied
```

## 5. Compare, report, export

```bash
pc optimize compare --case advisory-case --from 1 --to 2      # UNK, NOGUESS, CITE, ACC newly_passing
pc optimize compare --case advisory-case --from 2 --to 1      # exit 3: regressions
pc optimize report --case advisory-case --out report.md
pc optimize export --case advisory-case --out advisory-case.zip --preview
pc optimize export --case advisory-case --out advisory-case.zip
pc optimize import --bundle advisory-case.zip --case elsewhere/advisory-case
pc optimize check --case elsewhere/advisory-case              # same result
```

`report.md` lists lineage, the constraint ledger with status, every check with its evidence class, the exact outputs tested, and what the report does not show. The export leaves out the `.md` packets because they embed local paths; import refuses any altered byte.

## What this demonstrates, and what it does not

It demonstrates that a real check failure on recorded output is caught, that a revision keeps every accepted constraint, that the fix is shown against the same criteria, and that the evidence survives a round trip to another workspace.

It does not demonstrate that revision 2 is a good prompt in general, that a model would produce `output-v2.txt` reliably, or anything about other advisories. The outputs are synthetic text written for the example.
