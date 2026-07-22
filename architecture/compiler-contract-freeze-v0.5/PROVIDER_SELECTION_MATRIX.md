# Provider selection matrix

**Status:** Recommended adapter order; no provider calls are authorized by this document.  
**Assessed:** 2026-07-21

| Criterion | OpenAI | Anthropic | Gemini |
|---|---|---|---|
| Capability breadth | Broad model, tool, multimodal, agent, and eval surfaces | Broad reasoning and client/server tool surfaces | Broad multimodal, tool, grounding, and code-execution surfaces |
| Structured outputs | Strict JSON Schema mode, with a supported subset | JSON outputs and strict tool use, with schema limits | Structured output with a supported schema subset |
| Tool support | Function tools, built-in tools, remote MCP | Typed client tools plus server-executed tools | Function calling plus built-in tools |
| Reasoning controls | Model-specific reasoning effort | Adaptive/extended thinking with preservation rules | Thinking levels/signatures with model-specific continuation rules |
| Evaluation suitability | Native eval API plus structured outputs | Strong rubric/reasoning candidate; application owns eval harness | Strong multimodal and grounded evaluation candidate |
| Repair suitability | Strong structured repair target | Strong reasoning and strict tools | Strong structured/multimodal repair target |
| Adapter complexity | Medium; strict-schema subset and response/tool event model | Medium-high; thinking blocks and client/server tool loops | High; schema subset and thought-signature continuity |
| Strategic value | Best first target for validating structured compiler artifacts and evaluation integration | Best second target for proving provider neutrality and reasoning/tool semantics | Best third target for exposing multimodal and signature/state assumptions |

Official documentation confirms that OpenAI supports strict JSON Schema response formats and function tools ([OpenAI API reference](https://platform.openai.com/docs/api-reference/evals)); Anthropic supports JSON outputs, strict tool use, and distinct client/server tool contracts ([structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs), [tool use](https://platform.claude.com/docs/en/agents-and-tools/tool-use/how-tool-use-works)); Gemini supports structured outputs and function calling but documents schema-subset constraints ([structured output](https://ai.google.dev/gemini-api/docs/structured-output), [function calling](https://ai.google.dev/gemini-api/docs/function-calling)).

## Recommendation

1. **Deterministic fake adapter first** — mandatory reference for offline conformance.
2. **OpenAI first live adapter** — maximizes progress toward strict artifact generation plus future evaluation integration.
3. **Anthropic second mandatory adapter** — proves the IR and adapter contract do not encode OpenAI-specific tool or reasoning semantics.
4. **Gemini third adapter** — deliberately stress-tests schema subsets, multimodal capability modeling, and reasoning-signature provenance.

No provider may be silently substituted. Exact models and API versions are runtime configuration and provenance, never frozen brand aliases. Provider documentation snapshots and capability manifests must be versioned before live implementation.
