# Providers: any model, from any service or your own machine

`proofhouse run` sends a prompt to any provider that speaks the OpenAI chat format (`POST <base_url>/chat/completions`). That covers almost every hosted service and every common local server.

## Shipped providers

| Id | Where | Key variable |
|---|---|---|
| `openai` | cloud | `OPENAI_API_KEY` |
| `anthropic` | cloud (OpenAI-compatible endpoint) | `ANTHROPIC_API_KEY` |
| `google` | cloud (Gemini, OpenAI-compatible endpoint) | `GEMINI_API_KEY` |
| `mistral`, `groq`, `together`, `fireworks`, `openrouter`, `deepseek`, `xai` | cloud | `<NAME>_API_KEY` (see `providers list`) |
| `ollama`, `lmstudio`, `vllm`, `llamacpp` | this machine | none |

The addresses are the ones each provider publishes. If one changes, override it: `proofhouse providers add openai --base-url ... --key-env ...`.

## Add any provider

```bash
proofhouse providers add myhost --base-url https://api.myhost.ai/v1 --key-env MYHOST_KEY
proofhouse providers add gpu-box --base-url http://localhost:9000/v1          # a server on this machine, no key
```

Rules:
- Addresses must use https. Plain http is allowed only for `localhost`, `127.0.0.1` and `::1`.
- An address cannot carry a user, password, query or fragment.
- Your providers live in `PROOFHOUSE_HOME/providers.json` (default `~/.proofhouse/providers.json`). One of yours with a shipped id replaces the shipped one. A broken file is refused as a whole.

## Prices and your spending limit

Every run goes through the spend gate. It works out the most the run could cost from the exact request, and refuses before sending when that is over `--max-cost-usd`. It also refuses when the model has no price.

- A price comes from the shipped price table first. If the table has none, it comes from a price you declare: `proofhouse providers price PROVIDER MODEL --input 2.50 --output 10` (USD per million tokens). Results label it "declared by you". A declared price never changes a shipped one.
- A provider on this machine costs nothing unless you declare a price. A paid run needs `--max-cost-usd`.
- Dollar figures are estimates from those prices, not your bill.

## Results

`proofhouse run --json` returns:
- `output_text`;
- `admission` (the gate's decision, worst case, bounds and the price used, with its source);
- `cost` (tokens the provider reported, labelled measured; `usd`, labelled estimated);
- `cost_warning` when the provider reported more tokens than the bound.

Refusal codes: `PHC-COST-0001` to `0003`, and `PHC-RUN-0001` to `0006` (see [troubleshooting](troubleshooting.md)).
