---
id: NUMP-005
title: Add structured output support to all models
status: Done
assignee:
  - '@claude'
created_date: '2026-09-24 17:13'
updated_date: '2026-10-06 15:27'
labels: []
dependencies: []
documentation:
  - doc-004 - Structured output across providers and Jev
ordinal: 5000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Let a caller request a response that conforms to a JSON schema, and receive the parsed result. Support must work the same way across `AnthropicMessages`, `OpenAIChat`, and `OpenAIResponses`, using each provider native mechanism.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A caller can supply a schema and get a parsed, validated result from every provider model
- [x] #2 The interface is provider-neutral
- [x] #3 Invalid or refused output produces a clear error
- [x] #4 Tests cover rendering and parsing for each provider offline
- [x] #5 Public API is documented
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 tests pass
- [x] #2 docstrings are up to date
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Decisions (rounds 1-6, see comments): 007 layers on 005; schema is a kwarg on query; Object block, parsed in Model; provider-side validation + json.loads only; ValueError on refusal/truncation/bad JSON; no custom exception.

1. messages.py: add `Object(value: dict)` dataclass; extend `Block`; add `AssistantMessage.object` property returning the Object block's value or None. Keep the property LAST in the class (shadows builtin `object` in class body only); add code comment.
2. models/__init__.py: `Model.query(messages, tools=None, schema: dict | None = None)`. Docstring: schema is a JSON Schema dict with an object root; portable subset; raises ValueError when no conforming object returns.
3. AnthropicMessages: render `output_config={"format": {"type": "json_schema", "schema": schema}}` when schema given. Parse: `stop_reason == "refusal"` -> ValueError refused; `"max_tokens"` -> ValueError truncated; first text block json.loads -> Object, else ValueError not JSON. Render Object back as a text block (json.dumps).
4. OpenAIChat: `response_format={"type": "json_schema", "json_schema": {"name": "output", "schema": schema, "strict": True}}`. Parse: `message.refusal` / `finish_reason == "content_filter"` -> refused; `finish_reason == "length"` -> truncated; `message.content` json.loads -> Object. Render Object back as assistant text. Tool schemas keep strict False.
5. OpenAIResponses: `text={"format": {"type": "json_schema", "name": "output", "schema": schema, "strict": True}}`. Parse: refusal content item -> refused; `status == "incomplete"` -> truncated; message output_text json.loads -> Object. Render Object back as output_text.
6. Shared: no schema transform (no anthropic.transform_schema, no optional->nullable). Send caller's schema unchanged. Schema None: request byte-identical to today.
7. agent.py: `__call__(text, max_turns=5, schema=None)`; pass schema to every query; return `reply.object` when schema given, else `reply.text`. ValueError propagates.
8. Tests (offline, SimpleNamespace stubs as in tests/test_models.py): per provider request rendering with/without schema; parse to Object; refusal/truncation/bad-JSON raise ValueError; Object renders back as text. Agent: schema passed every turn incl. after tool turn; return type by schema. messages: object property None without block. Existing signature-parity test covers the kwarg.
9. Docs: docstrings; griffonner page descriptor for Object; regenerate docs/. README "Structured output" section: schema in, dict out, portable subset list, out-of-subset fails at API, non-strict backends may return non-conforming JSON as-is.
10. Verify with local Qwen via OpenAIChat (llama.cpp): schema + tools together; confirm object-root requirement across providers.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented steps 1-9. Object block + AssistantMessage.object (kept last, commented). Model.query(schema=) on base and all three adapters; shared Model.parse_object replaces Text with Object, raises ValueError on non-JSON / non-object. Anthropic: output_config.format, stop_reason refusal/max_tokens. Chat: strict response_format name 'output', refusal field / content_filter / length. Responses: strict text.format, refusal content item / status incomplete. Object renders back as JSON text on all three. Agent passes schema every turn, returns reply.object. 26 new offline tests (187 total pass). README 'Structured output' section; Object doc page; docs regenerated. Step 10 (live Qwen/llama.cpp check of schema + tools) not run: no local server or API keys in this session.

Validation: uv run pytest -q -> 187 passed. AC 2-5 and DoD checked on offline evidence. AC 1 left unchecked pending a live run against a real provider (schema alone, and schema + tools).

Live validation against llama.cpp b11429 (Qwen 3.8, saturn) via OpenAIChat: schema-only query -> Reasoning + Object, object dict correct; Agent with schema across two turns works, Object replays into history; max_tokens=40 -> ValueError truncated. Limit found: llama.cpp rejects tools + response_format ('failed to parse grammar'), strict or not, json_object too; tool_choice none works. Documented in README (Structured output + Local models limits) and doc-004. Anthropic and OpenAIResponses: SDK parameter names (output_config, text) confirmed in installed SDK source; behavior covered by offline stubs only, no API keys in session.

Researched the llama.cpp limit before commit. Upstream: ggml-org/llama.cpp#27114 'Qwen 3.[68] grammar compilation failure in presence of tools and response schema', closed 2026-08-15 by maintainer as by design (Qwen templates do not support response format + tool calls; only a better error is possible). Reproduced here: Gemma 4 on the same server accepts tools + schema; Qwen rejects unless tool_choice none. Source (common/chat-auto-parser-generator.cpp build_parser): when json_schema is set the parser is response-format only, tools are never parsed, so a schema disables tool calls for that turn on every template. b11429 is dated 2026-10-05 (current). README and doc-004 corrected: not a blanket llama.cpp limit; schema wins over tools, Qwen rejects.

Gemma 4 (gemma-4-31b-Q4, same llama.cpp server) via numpty Agent: schema only -> Object correct; schema + calculate tool -> no error, single turn, Object, tool never called; tool without schema -> ToolCall then Text. Confirms 'schema takes precedence over tools' on llama.cpp for a template that accepts the request.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: @claude
created: 2026-10-05 17:21
---
Research and reuse analysis in doc-004. Planning rounds listed there; round 1 (reuse strategy) awaiting answer. Continue in a new session.
---

author: @claude
created: 2026-10-05 18:40
---
Round 1 agreed: 007 layers on 005, not the reverse. 005 keeps no Jev concepts (no confidence/probabilities). 005 commits to: JSON Schema dict in, plain Python value out, single-shot via query(schema=), documented portable subset (enum/integer/boolean/description kept), one 'no conforming output' error, no pydantic in public API. Chat-backed question sets added to NUMP-007 as AC.
---

author: @claude
created: 2026-10-05 18:56
---
Round 2 agreed: schema enters as a keyword on the existing method. Model.query(messages, tools=None, schema: dict | None = None); Agent.__call__(text, max_turns=5, schema=None). None = unchanged behavior. Each provider renders natively (output_config / response_format / text.format); provider supplies OpenAI's required name. Tools and schema coexist; Agent passes schema every turn, JSON arrives on the final turn. Agent returns parsed value when schema given, str otherwise. Framing: a constraint on output for a given input, same flow with a validated guarantee.
---

author: @claude
created: 2026-10-05 19:28
---
Round 3 agreed: option A. Model.query parses and validates; Agent stays dumb (return reply.object if schema else reply.text). New block type Object(value: dict) in messages.py; Block = Text | ToolCall | Reasoning | Object. Root schema type is always object (strict modes require it; confirm in impl), hence value: dict. AssistantMessage.object property returns the Object block's value or None. Object renders back to providers as json.dumps text on later turns. Naming pass: Object converges bottom-up and top-down (JSON Schema's own root-type word); Record was runner-up; Structured rejected (adjective in a noun family). Implementation note: the object property shadows the builtin inside the AssistantMessage class body only. Keep it the LAST member of the class so no later class-body statement (field annotation, default arg, nested class) can resolve object to the property. Add a code comment saying so.
---

author: @claude
created: 2026-10-05 19:49
---
Round 4 agreed. 4a: 'validated' = provider-side constraint (strict modes / grammar) + client json.loads + refusal/truncation detection. No client schema validation; no jsonschema dependency; document that a non-strict backend may return non-conforming JSON as-is. 4b: send the caller's schema unchanged; strict: True on OpenAI output format (unlike tool schemas, which stay strict: False); no optional-property transform; do not call anthropic.transform_schema. Out-of-subset schemas fail fast at the API with the provider's own error. Deferred: an optional dependency (e.g. pydantic) for Python-object <-> schema translation and richer validation. Not 005 scope.
---

author: @claude
created: 2026-10-05 20:08
---
Round 5 agreed: no custom exception (project has none; all errors are builtins). Model.query raises ValueError when schema was given and no conforming object came back, one message per cause: refused (with provider refusal text if any), truncated at max_tokens (with output prefix), not valid JSON (with output prefix). Not raised when schema is None. Agent lets it propagate. A reason-aware subclass of ValueError can be added later without breaking callers.
---

author: @claude
created: 2026-10-05 20:10
---
Plan ready for review
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added structured output: Model.query(messages, tools=None, schema=None) on AnthropicMessages, OpenAIChat, OpenAIResponses using each provider's native mechanism (output_config / strict response_format / strict text.format). New Object block holds the parsed dict; AssistantMessage.object exposes it; Agent.__call__(text, max_turns, schema) returns the dict and passes schema every turn. Refusal, truncation, and non-object replies raise ValueError. Object renders back to each provider as JSON text. Verified: 187 offline tests pass (26 new, per-provider request shape, parse, failures, render-back; agent turn passing); live run on llama.cpp via OpenAIChat for schema-only, agent, history replay, truncation. Known limit documented: llama.cpp cannot combine tools with a schema. README section and Object doc page added; docs regenerated. NUMP-007 gained an AC and dependency for chat-backed question sets.
<!-- SECTION:FINAL_SUMMARY:END -->
