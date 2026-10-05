---
id: doc-004
title: Structured output across providers and Jev
type: other
created_date: '2026-10-05 16:08'
updated_date: '2026-10-05 20:30'
---
# Structured output across providers and Jev

Research for NUMP-005 (structured output) and NUMP-007 (Jev). Facts from SDK source and provider docs, 2026-10-05. Versions probed: openai 3.19.2, anthropic 1.8.0, typesafe-sdk 0.7.2.

## Provider-native structured output (NUMP-005)

| | Anthropic Messages | OpenAI Chat | OpenAI Responses | llama.cpp via OpenAIChat |
|---|---|---|---|---|
| Request | `output_config={"format": {"type": "json_schema", "schema": S}}` | `response_format={"type": "json_schema", "json_schema": {"name": N, "schema": S, "strict": True}}` | `text={"format": {"type": "json_schema", "name": N, "schema": S, "strict": True}}` | Same as Chat. Grammar-constrained. |
| Reply | First `text` block is JSON | `message.content` is JSON | `message` item, `output_text` content is JSON | `content` is JSON |
| Refusal | `stop_reason == "refusal"` | `message.refusal` (str), `finish_reason == "content_filter"` | content item `type == "refusal"` | none |
| Truncated | `stop_reason == "max_tokens"` | `finish_reason == "length"` | `status == "incomplete"`, `incomplete_details.reason` | `finish_reason == "length"` |
| Schema limits | Objects need `additionalProperties: false`. No `minimum`/`maximum`, `minLength`, recursion. SDK `anthropic.transform_schema(dict)` strips unsupported keywords into `description`. | Strict mode: every property in `required`, `additionalProperties: false`, subset of JSON Schema. Optional field idiom: `"type": ["string", "null"]`. | Same as Chat | Full JSON Schema (grammar) |
| With tools | Yes. JSON arrives on the final turn, tool turns unchanged. | Yes | Yes | No. Schema takes precedence: the auto-parser builds a response-format parser and ignores tools, so no tool calls on that turn (any template). Qwen 3.6/3.8 templates reject the request: `failed to parse grammar` (ggml-org/llama.cpp#27114, closed by design 2026-08-15; Gemma 4 accepts). b11429, 2026-10-05. |

- All three SDKs have `.parse()` helpers, but they take pydantic classes. numpty core has no dependencies, so the public contract must be a plain JSON Schema dict in and a plain Python value (`json.loads`) out.
- "Validated" in AC #1: provider strict modes and llama.cpp grammars constrain output server-side. Client-side validation beyond `json.loads` would need `jsonschema` or pydantic (an extra), or a small checker for the portable subset.
- Portable schema subset that every strict mode accepts: `object` with `properties`, `required` (all), `additionalProperties: false`; `string`, `integer`, `number`, `boolean`, `null`; `enum`; `array` with `items`; `description`. No numeric or length constraints, no recursion.
- `PythonTool.function_schema` makes parameters with defaults optional. Under OpenAI strict mode that schema is rejected. A schema transform (optional -> required with `null` type) or `strict: False` is needed if tool schemas are reused as output schemas.
- OpenAI name field: Chat and Responses require a `name` for the schema. Anthropic has none.

## Jev / TypeSafe (NUMP-007)

- Package `typesafe-sdk` (pydantic, httpx2, tenacity). Python >= 3.10. Env `TYPESAFE_API_KEY`. Default model `jev-latest` -> `jev-1.13.0`.
- `TypeSafeClient(api_key=None, model=None, retry=None, timeout=None, headers=None, base_url=None)`. `client.system_one(state, questions, *, model=None, ...) -> SystemOneResponse`. Async client `AsyncTypeSafeClient`. `client.models.list()`.
- State: `str | object | array` (JSON). Text only. 64k tokens per request, 32k for state plus the longest question.
- Questions, keyed by name. Plain dicts (`{"type": "choice", ...}`) are accepted, so numpty can render its own types without importing SDK classes:
  - `Choice(instructions, criteria: {label: description})` -> `ChoiceAnswer(choice, confidence, probabilities)`
  - `Score(instructions, criteria: [level descriptions], 2-10 levels)` -> `ScoreAnswer(score: float, confidence, probabilities: {int: float}, legend)`
  - `Noul(instructions, criteria={"true": ..., "false": ...})` -> `NoulAnswer(noul: float)`. Probability of yes. No separate confidence.
  - `instructions` and every criteria value accept `str | object | array`.
- Confidence: Choice `(p_max - 1/n) / (1 - 1/n)`. Score: distance-weighted. Docs suggest act > 0.9, confirm 0.5-0.9, escalate < 0.5.
- Response: `.answers: dict[str, Answer]`, `.choices`, `.scores`, `.nouls`, `.model`, `.usage(input_tokens, output_tokens)`.
- Errors: `TypeSafeError` base; `TypeSafeAuthenticationError`, `TypeSafeRateLimitError`, `TypeSafeUnprocessableEntityError` (422 bad question), `TypeSafeAPIResponseValidationError`, and others. SDK retries 429/529.
- No chat, no tools, no generation. REST: `POST https://api.typesafe.ai/v1/systemone`, bearer auth.
- Intended agent uses (docs): intent routing, guardrails, confidence-gated routing, and a "function calling" cookbook where Jev picks a function and each `Literal` argument becomes a Choice question. Many questions per call is the recommended shape (cheap, parallel).
- Pricing: $0.042 per million input tokens, output free.

## Overlap

- A Choice/Score/Noul question set compiles to the portable JSON Schema subset: Choice -> `{"type": "string", "enum": labels}`, Score -> `{"type": "integer", "enum": [0..n-1]}`, Noul -> `{"type": "boolean"}`, instructions -> `description`, the set -> one `object`. So a chat model with NUMP-005 can answer NUMP-007 questions, without probabilities.
- The reverse does not hold: Jev cannot take an arbitrary schema.
- Confidence and probabilities are Jev-only. They must not enter the NUMP-005 contract.

## Reuse verdict (session 2026-10-05)

Directional, not symmetric. NUMP-007 can be layered on NUMP-005 (questions compile to a schema, chat model answers without probabilities). NUMP-005 cannot be built on NUMP-007. Confidence and probabilities stay out of the NUMP-005 contract.

## Constraints NUMP-005 carries for NUMP-007

1. Schema: JSON Schema dict. No pydantic in the public API.
2. Result: plain Python value, not a provider object.
3. Single-shot path: `Model.query([UserMessage(state)], schema=...)` is enough. No new method for 007 to reuse.
4. Document the portable schema subset. Choice/Score/Noul live inside it.
5. One error type for "no conforming output" (refusal, truncation, unparsable). 007 can reuse it.
6. Open: "validated" in AC #1. Provider strict modes constrain server-side. Client validation beyond `json.loads` needs an extra or a tiny subset checker. OpenAI strict rejects optional properties, which `PythonTool.function_schema` produces.
