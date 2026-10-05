---
id: NUMP-004
title: Support a local Qwen model
status: Done
assignee:
  - '@claude'
created_date: '2026-09-24 17:13'
updated_date: '2026-10-05 15:56'
labels: []
dependencies: []
ordinal: 4000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Test, develop, and document compatibility with a Qwen model served locally (for example through an OpenAI-compatible server). `OpenAIChat` already accepts `base_url` and `api_key` for this purpose, but this path has not been tested against a real local model. Tool calling, reasoning output, and message rendering may differ from the hosted OpenAI API.

Considerations:
- `OpenAIChat` does not read or send `Reasoning`. Newer OpenAI models do not expose reasoning through the Chat Completions API, so it was left out. Local reasoning models (Qwen) may return reasoning in this API (for example a `reasoning_content` field or `<think>` tags in the text). Decide whether to parse it and send it back between turns.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 An agent with tools completes a multi-turn tool-calling conversation against a local Qwen model
- [x] #2 Differences from the hosted APIs are fixed or documented
- [x] #3 README documents how to connect to a local Qwen model
- [x] #4 Tests cover any Qwen-specific rendering or parsing, and run offline
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 tests pass
- [x] #2 docstrings are up to date
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
Findings (live, 2026-10-05, saturn.wayforwardlabs.com, llama-server, Qwen 3.8 27B Q4, --jinja, preserve_thinking=true):
- Current OpenAIChat completes a 2-step dependent tool-calling run unchanged (AC #1 already holds).
- Replies carry `message.reasoning_content` (str) regardless of `preserve_thinking`. `content` is "" on tool-call replies. `<think>` tags do not appear in content (server parses them when run with --jinja).
- Server accepts `reasoning_content` on assistant input messages. `preserve_thinking=true` renders prior reasoning into `<think>` blocks (verified via /apply-template); `false` strips it server-side, so sending it is harmless. Per-request override: `chat_template_kwargs` in the body, reachable via `OpenAIChat(..., extra_body={"chat_template_kwargs": {...}})`.
- DeepSeek thinking mode (api-docs.deepseek.com/guides/thinking_mode): with tools, reasoning_content of all prior turns MUST be passed back (400 if missing); without tools it is ignored. Sending it back by default satisfies this.
- openai SDK (3.x) exposes the extra field as `message.reasoning_content` (pydantic extra=allow).
- Qwen 3.8 template takes `reasoning_effort`: `xhigh` (default) and `low` inject a system instruction, `medium` injects nothing, `high` maps to `xhigh`, other values raise. Default xhigh is very slow (ref: simonwillison.net/2026/Aug/16/qwen-38-27b/). llama-server b9584 ignored the OpenAI top-level `reasoning_effort` param; b11429 (current master) forwards it to the template. Verified: bogus value -> template error, low/medium/default -> 41/11/53 prompt tokens.

Plan:
1. OpenAIChat.query: if reply has non-empty `reasoning_content`, prepend `Reasoning({"reasoning_content": <str>})` to blocks.
2. OpenAIChat.render_message (AssistantMessage): if origin == (self.name, self.model) and a Reasoning block exists, add `reasoning_content` to the rendered dict. Different origin: dropped, as in other adapters. No new classes, no new flags, signatures unchanged.
3. Docstrings: drop the "Reasoning not supported" NOTE; state the rule in `query` and `render_message`.
4. Tests (offline, tests/test_models.py TestOpenAIChat): parse reasoning_content; render with same-origin Reasoning includes key; other origin omits; no Reasoning -> no key (hosted OpenAI unchanged).
5. README: "Local models" section. llama-server flags (--jinja), `OpenAIChat(model, base_url=..., api_key="none")`, reasoning round-trip, server-side toggle via `extra_body={"chat_template_kwargs": {"preserve_thinking": ...}}`, limit: `<think>` tags inside text are not parsed.
6. Live run against saturn after implementing; record in notes. Not part of the test suite.
7. README Qwen example passes `reasoning_effort="medium"` (standard OpenAI param, flows through **kwargs). Note allowed values, the xhigh default, and that it needs llama.cpp >= b11429; older builds ignore it silently (use `extra_body={"chat_template_kwargs": {"reasoning_effort": "medium"}}` there).
8. README: short example of `OpenAIChat` against hosted OpenAI (model + `OPENAI_API_KEY`), next to the existing Anthropic example. Existing defect: README shows no OpenAI usage.

Decision (resolved 2026-10-05): send reasoning_content back whenever present, origin-gated, no flag. Server template decides whether to use it. Implementation deferred to a new session.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Implemented: OpenAIChat.query parses reasoning_content into Reasoning; render_message merges it back into the assistant message when origin matches. Tests: 2 new in TestOpenAIChat. README: hosted OpenAI example, Local models section (llama-server --jinja, reasoning_effort, preserve_thinking toggle, limits). Validation: uv run pytest -q -> 161 passed. Live run vs saturn (llama-server b11429, qwen-38-27b-Q4, reasoning_effort=medium): 2 dependent tool calls, reasoning_content present on every assistant turn and rendered back; final reply 15. docs/ is gitignored, not regenerated.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: @claude
created: 2026-10-05 14:47
---
Plan ready for review
---

author: @claude
created: 2026-10-05 15:27
---
Plan reviewed in session 2026-10-05: direction agreed (no flag). Items 7-8 added. Implement in a new session.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
OpenAIChat now reads reasoning_content from replies into Reasoning blocks and sends them back to the same origin model. README documents hosted OpenAI use and local Qwen via llama-server, with reasoning_effort and preserve_thinking. Verified: 161 offline tests pass; live multi-turn tool-calling run against Qwen 3.8 on llama-server b11429 succeeded with reasoning round-tripped.
<!-- SECTION:FINAL_SUMMARY:END -->
