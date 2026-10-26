# train data, no model trained

`tickets.jsonl` has 20 invented support tickets plus one deliberate duplicate. `proofhouse train data` turns them into `data/train.jsonl` (18) and `data/valid.jsonl` (2) with `system-prompt.md` as the system message. `prove.py` runs it, checks the files, and shows `train start` refusing without a key. `proof-output.txt` is a saved run; `../train-record/` records the system prompt (two rounds).

```bash
uv run --no-sync python examples/host-mode/train/prove.py
```

No model is trained and nothing is paid for. Twenty examples is a demonstration, not enough for a useful fine-tune.

## What this does not prove

- The refusal shown is the missing-key one only. The spending-limit refusal is not exercised here.
- No fine-tune job was started, so nothing shows that training works or that the result would be any good.
- The 20 tickets are invented, so the data says nothing about real support traffic.
