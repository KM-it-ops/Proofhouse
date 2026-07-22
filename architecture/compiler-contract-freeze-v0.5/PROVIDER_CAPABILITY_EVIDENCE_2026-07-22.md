# Provider capability evidence refresh — 2026-07-22

This record refreshes provenance only. It authorizes no provider execution, credentials, new IR fields, or universal model claims.

| Provider | API surface and applicability | Continuation-state evidence | Source |
|---|---|---|---|
| OpenAI | Responses API; reasoning support and configuration vary by model family. | Manually managed context must include prior reasoning items; encrypted reasoning content is available when requested. | https://platform.openai.com/docs/api-reference/responses-streaming/response/refusal/delta?lang=curl |
| Anthropic | Messages API; extended thinking and tool use are model/configuration dependent. | Signature-verified thinking blocks must be preserved unmodified for continuation where required. | https://docs.anthropic.com/en/docs/build-with-claude/extended-thinking |
| Gemini | GenerateContent/Interactions APIs; thought-signature requirements differ by model/API and stateful versus stateless use. | In stateless flows, thought blocks/signatures must be returned exactly as received; function-calling requirements are model-specific. | https://ai.google.dev/gemini-api/docs/generate-content/thought-signatures |

**Retrieval date:** 2026-07-22. Capability manifests remain conservative: a provider capability is conditional unless its required model/runtime conditions are concrete compile inputs. No claim in this record applies to every model from a provider.
