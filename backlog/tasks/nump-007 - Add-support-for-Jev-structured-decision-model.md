---
id: NUMP-007
title: Add support for Jev structured decision model
status: Done
assignee:
  - '@claude'
created_date: '2026-09-24 17:34'
updated_date: '2026-10-06 21:26'
labels: []
dependencies:
  - NUMP-005
  - NUMP-016
references:
  - 'https://docs.typesafe.ai/introduction/quickstart'
documentation:
  - doc-004 - Structured output across providers and Jev
ordinal: 7000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Jev (TypeSafe, `typesafe-sdk`) is a structured decision model: likely an LLM tuned and served for zero-shot classification and regression. Its creators call it a "System One" model. It does not fit the chat-style `Model` interface: `TypeSafeClient.system_one(state, questions)` takes input text and typed questions (`Choice`, `Score`, `Noul`) and returns answers with a predicted value, confidence, and probability distribution per question. It has no chat or tool use. Support may need a new abstraction for decision models, and may also be offered to agents as a tool. The SDK must be an optional extra, loaded only when used, and listed in the README.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A caller can ask Jev classification, score, and yes/no questions through numpty and get answers with confidences
- [x] #2 An agent can use Jev decisions (for example through a tool)
- [x] #3 `typesafe-sdk` is an optional extra listed in the README; importing numpty does not load it
- [x] #4 Tests run offline
- [x] #5 Public API is documented
- [x] #6 A chat model with structured output (NUMP-005) can answer the same Choice/Score/Noul question set, without probabilities or confidence; the question set compiles to the portable JSON Schema subset
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 tests pass
- [x] #2 docstrings are up to date
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
# Plan (agreed 2026-10-06; basis doc-004, doc-005, decision-001)

## Architecture
- One new core module numpty/decisions.py, no dependencies at import: question types, Answer, DecisionModel ABC, schema(), DecisionTool, TypeSafe.
- Agent is the single top-level entry point. Agent.decide answers a question set with either a DecisionModel (System One wire protocol) or a chat Model (NUMP-005 schema, labels only, no probabilities).
- TypeSafe is the one DecisionModel: typesafe-sdk client, base_url + model + key. Serves TypeSafe, llama-server /v1/systemone, llmman unchanged. SDK import inside __init__ (extra typesafe), so numpty.TypeSafe is a plain export and import numpty loads no SDK.
- No client-side limit checks (option count, 2-10 levels, state length are per backend; the server rejects). SDK exceptions propagate, as openai/anthropic exceptions do from Model.query. Docstring records the llama-server mapping (400 bad request, 501 not a decision model).

## Types and signatures (numpty/decisions.py)
- @dataclass Choice(instructions: str, criteria: dict[str, str | None])  # label -> description
- @dataclass Score(instructions: str, criteria: list[str])               # levels, lowest first
- @dataclass Noul(instructions: str, criteria: dict[str, str] | None = None)  # {true, false}
- Question = Choice | Score | Noul
- @dataclass Answer(value: str | int | float | bool, confidence: float | None = None, probabilities: dict | None = None). Choice: label, {label: p}. Score: level index (int from chat, float expected level from System One), {int: p}. Noul: bool, {True: p, False: 1-p}. Chat backend: confidence and probabilities None, never fabricated.
- class DecisionModel(ABC): name: str; decision(state: str | dict | list, questions: dict[str, Question]) -> dict[str, Answer]
- def schema(questions) -> dict: portable subset. Choice -> string enum of labels; Score -> integer enum 0..n-1; Noul -> boolean; instructions + criteria text -> description; one root object, all required, additionalProperties false.
- class DecisionTool(Tool): __init__(decider: DecisionModel, questions, name=None, description=None). parameters fixed {state: string}. Default name 'decision-model-' + '-'.join(keys), cut to 64 chars. Default description from DecisionTool.describe(questions): one line per question (key, kind and labels or level count or yes/no, instructions), plus how to call and what returns. run(arguments) -> {name: asdict(answer)}.
- class TypeSafe(DecisionModel): name = 'typesafe'. __init__(model: str, base_url=None, api_key=None, **kwargs); kwargs go to every client.system_one call (timeout, extra_body). decision(): render_question per question, client.system_one(state, questions, model=self.model), parse_answer per answer. render_question(question) -> wire dict. parse_answer(answer) -> Answer. Score legend dropped. Noul: value=p>=0.5, probabilities={True: p, False: 1-p}, confidence=2*max(p,1-p)-1 (Choice formula at n=2, documented as derived). api_key default TYPESAFE_API_KEY (SDK); local hosts pass any non-empty string.

## Agent (numpty/agent.py)
- __init__(model: Model | DecisionModel, tools, system='', policy=None): unchanged otherwise.
- answer(text, max_turns=5, schema=None): today's __call__ body. TypeError if model is a DecisionModel.
- __call__ delegates to answer.
- decide(state, questions) -> dict[str, Answer]: DecisionModel -> model.decision(state, questions). Model -> one model.query([UserMessage(state)], schema=schema(questions)) with no tools and no system prompt, Answer(value) per key. Stateless: messages not read or appended. Non-string state JSON-dumped in both paths.

## Exports and packaging
- numpty/__init__.py: export Answer, Choice, DecisionModel, DecisionTool, Noul, Score, TypeSafe. schema stays in numpty.decisions.
- pyproject: typesafe = ['typesafe-sdk'], added to all.
- README: extra listed; Decisions section (question set, Agent.decide with a chat model and with TypeSafe, DecisionTool, local llama-server via base_url, no-probabilities caveat for chat models).

## Tests (offline)
- schema(): each question kind, description text, root object shape.
- Agent.decide with ScriptedModel: sent schema and messages, Answer mapping, messages untouched, no tools sent.
- Agent(DecisionModel): decide dispatches, answer raises TypeError.
- DecisionTool: parameters, default name (and 64-char cut), describe() text, run returns asdict answers; through Agent with ScriptedModel tool call.
- TypeSafe (importorskip typesafe_sdk): render_question for all three kinds, parse_answer for all three (SimpleNamespace answers), decision() with stubbed client.system_one records model and questions.
- Extend test_core_import_does_not_load_provider_sdks with typesafe_sdk.
- Manual check against saturn lev-4b-Q8 (one request at a time), not in the suite.

## Steps
1. decisions.py: types, DecisionModel, schema, tests.
2. Agent.answer/decide, tests.
3. DecisionTool with defaults, tests.
4. TypeSafe, pyproject extra, import test.
5. README, docstrings, manual saturn check, uv.lock.
6. Finalization guide, AC evidence, commit.

Revision (2026-10-06, approved in session): chat-path decide sends [SystemMessage(questions + schema JSON), UserMessage(state)]. Reason: llama-server compiles json_schema to a grammar only, so the model never saw the questions (gemma-4-31b answered calm/1 for an angry outage; with the schema in the prompt, angry/2). Agent system prompt is still not sent.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Validation: uv run pytest -q, 201 passed offline (tests/test_decisions.py: schema, Agent.decide both paths, DecisionTool, TypeSafe render/parse/decision with stubbed client; import test covers typesafe_sdk). Manual on saturn: TypeSafe lev-4b-Q8 returned Choice/Score/Noul with confidence and probabilities; OpenAIChat gemma-4-31b-Q4 decide returned angry/2/False after the system-message fix. API docs generate (griffonner pages added for 7 classes).
Policy finding: DecisionTool under Policy() is denied (socket.connect blocked); works with Policy.Network.UNRESTRICTED. Documented in README and DecisionTool docstring. Exempting decision-model requests from the policy, as model queries are, is a policy design question, not done here.

Jev check (2026-10-06, TYPESAFE_API_KEY from .env, jev-latest): Agent.decide over text and dict state and DecisionTool.run returned Choice/Score/Noul answers with confidence and probabilities. Outage text: angry 1.0, urgency 2.0, spam False 0.94. Spam text: spam True 0.92. Follow-up: NUMP-017 (Policy exemption for DecisionTool).
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: @claude
created: 2026-10-06 20:26
---
Plan ready for review
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added numpty/decisions.py: Choice, Score, Noul, Answer, DecisionModel, schema(), DecisionTool, and TypeSafe (System One protocol via typesafe-sdk, extra typesafe, imported on construction). Agent gains answer() (old __call__) and decide(): DecisionModel path calls decision(); chat path sends one structured query with questions in a system message (llama-server does not show the schema to the model). README Decisions section, extra listed. Verified: 201 offline tests pass; manual runs on saturn with lev-4b-Q8 (TypeSafe) and gemma-4-31b-Q4 (OpenAIChat).
<!-- SECTION:FINAL_SUMMARY:END -->
