# 0006: Refuse before sending when the worst-case cost is over the ceiling

Accepted 2026-10-12.

## Decision

In the Python package, nothing that can cost money is sent except through one function, `spend.send_within_ceiling`; `execute-openai` is the package's only live path. (The browser artifact `apps/proofhouse.jsx` runs inside its host and calls that host's model itself; it is not covered.) The function makes the exact request bytes, reads the model and the output cap from them rather than taking the caller's word, refuses a request with any field or content its estimate does not cover (more choices, another processing tier, image or audio parts, tools other than functions), works out the most the request could cost, and calls the one send step with exactly those bytes only when that worst case is at or under the caller's ceiling (`--max-cost-usd`). Otherwise nothing is sent:

| Code | When | Exit |
|---|---|---|
| `PHC-COST-0001` | the worst case is over the ceiling | 7 |
| `PHC-COST-0002` | the model has no entry in the price table | 7 |
| `PHC-COST-0003` | no worst case could be made (table unreadable, an amount that would need rounding, a request above the size its price applies to, a request field or content the estimate does not cover, a ceiling outside 0.000000000001 to under 10000000000000) | 7 |

Every earlier refusal (opt-in, credential, model, ceilings, allowed hosts, compilation, unsupported fields) still runs first.

**The worst case.** Input tokens are at most the UTF-8 bytes of the request body as sent, plus 1024. Output tokens are taken to be at most `--max-output-tokens`, which is sent as `max_completion_tokens`. Dollars are input tokens times the input price plus output tokens times the output price, per million tokens, in exact decimals; an amount that would need rounding is refused, never rounded.

**The price table** is data shipped in the package (`data/price_table.json`), with a `price_table_version` pinned by a test to the table's content. Each entry names the provider, the exact model id, the input and output price in US dollars per million tokens, the provider's official pricing page and the date it was read. A model matches only by its exact id. There is no flag, setting, file or environment variable that replaces the table or skips the check. The table ships with no entries: until a price is read from the provider's official page and cited, every model is refused.

**After a call**, the result carries `cost`: the token counts the provider reports and the wall time around the one send are `measured`; the dollar figure worked out from the reported tokens at table prices is `estimated`. If the provider reports more tokens than the bound used before sending, the result adds `PHC-COST-0004` and one line on stderr.

An architecture test fails the build if a module other than the live path can reach the network, if anything outside the one send step touches the raw sender or a transport's `send`, or if that step is used other than by handing it to the gate. The mutation check confirms that removing the gate or its comparison is caught. The test reads the package's code; it is not a proof about code outside it.

## Why

A ceiling that is only recorded does not stop spending. One opt-in request that a person starts can live with that; anything that sends more than once without a person watching cannot, so the check comes first. Deciding in one function, not in each sender, gives one place to review and test. Working the estimate out from the exact bytes about to be sent means a sender cannot under-report it.

## What it does not promise

- **It is not your bill.** The dollar figures come from the price table, which can be out of date. Cached-input discounts are not applied. Prices are for the provider's standard processing; a project set to a different processing tier can be billed differently.
- **The output bound rests on an assumption**: that `max_completion_tokens` caps every output token the provider bills, reasoning tokens included. This has not been confirmed against the provider's API reference. `PHC-COST-0004` reports any call where it did not hold.
- **The input bound rests on an assumption**: that the provider's tokenizer makes at most one token per byte, and that what the provider adds around a request fits in the 1024 margin. The provider does not publish that wrapping; the margin is ours. `PHC-COST-0004` reports any call where the bound did not hold.
- Runs recorded by hand into a case are imported: nothing was sent through Proofhouse, so the gate does not apply and their cost stays `unknown`.

## Consequences

`execute-openai` refuses every model until the table has a cited price for it, and changing a price takes a release. Run records and case files do not change. The envelope's `admission` now states the gate's decision, where it used to say the ceiling was only declared.
