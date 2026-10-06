"""Offline tests of decision questions, schema, Agent.decide, DecisionTool, and TypeSafe."""

import json
from types import SimpleNamespace

import pytest

from numpty import (Agent, Answer, Choice, DecisionModel, DecisionTool, Noul, Object, Score, Text, ToolCall,
                    ToolResultMessage, UserMessage)
from numpty.decisions import schema
from test_agent import ScriptedModel, reply

QUESTIONS = {
    "mood": Choice("Classify the mood.", {"angry": "Upset or hostile", "calm": None}),
    "urgency": Score("How urgent?", ["Can wait", "This week", "Today"]),
    "spam": Noul("Is it spam?", {"true": "Unsolicited advertising", "false": "A real message"}),
}
ANSWERS = {"mood": Answer("calm", 0.8, {"angry": 0.1, "calm": 0.9}),
           "urgency": Answer(1.2, 0.6, {0: 0.1, 1: 0.6, 2: 0.3}),
           "spam": Answer(False, 0.9, {True: 0.05, False: 0.95})}


class ScriptedDecider(DecisionModel):
    """Returns canned answers and records what it was sent."""
    name = "scripted"

    def __init__(self, answers):
        self.answers = answers
        self.calls = []

    def decision(self, state, questions):
        self.calls.append((state, questions))
        return self.answers


def test_schema():
    assert schema(QUESTIONS) == {
        "type": "object",
        "properties": {
            "mood": {"type": "string", "enum": ["angry", "calm"],
                     "description": "Classify the mood.\nangry: Upset or hostile\ncalm"},
            "urgency": {"type": "integer", "enum": [0, 1, 2],
                        "description": "How urgent?\n0: Can wait\n1: This week\n2: Today"},
            "spam": {"type": "boolean",
                     "description": "Is it spam?\ntrue: Unsolicited advertising\nfalse: A real message"},
        },
        "required": ["mood", "urgency", "spam"],
        "additionalProperties": False,
    }


def test_schema_noul_without_criteria():
    assert schema({"q": Noul("Yes?")})["properties"]["q"] == {"type": "boolean", "description": "Yes?"}


def test_decide_with_chat_model():
    model = ScriptedModel(reply(Object({"mood": "angry", "urgency": 2, "spam": True})))
    agent = Agent(model, [], system="sys")
    before = list(agent.messages)
    assert agent.decide("hi", QUESTIONS) == {"mood": Answer("angry"), "urgency": Answer(2), "spam": Answer(True)}
    messages, tools, sent = model.calls[0]
    assert messages[1:] == [UserMessage("hi")]
    assert messages[0].content.endswith(json.dumps(schema(QUESTIONS)))
    assert not tools
    assert sent == schema(QUESTIONS)
    assert agent.messages == before


def test_decide_dumps_non_text_state():
    model = ScriptedModel(reply(Object({"spam": False})))
    Agent(model, []).decide({"a": 1}, {"spam": QUESTIONS["spam"]})
    assert model.calls[0][0][1] == UserMessage('{"a": 1}')

    decider = ScriptedDecider({})
    Agent(decider, []).decide([1, 2], {})
    assert decider.calls[0][0] == "[1, 2]"


def test_decide_with_decision_model():
    decider = ScriptedDecider(ANSWERS)
    assert Agent(decider, []).decide("hi", QUESTIONS) == ANSWERS
    assert decider.calls == [("hi", QUESTIONS)]


def test_decision_model_cannot_answer():
    agent = Agent(ScriptedDecider(ANSWERS), [])
    with pytest.raises(TypeError, match="decide"):
        agent.answer("hi")
    with pytest.raises(TypeError):
        agent("hi")


def test_decision_tool_defaults():
    tool = DecisionTool(ScriptedDecider(ANSWERS), QUESTIONS)
    assert tool.name == "decision-model-mood-urgency-spam"
    assert tool.parameters["required"] == ["state"]
    assert tool.description == DecisionTool.describe(QUESTIONS)
    assert DecisionTool.describe(QUESTIONS) == (
        "Ask a decision model these questions about a text:\n"
        "- mood (choice of angry, calm): Classify the mood.\n"
        "- urgency (score, levels 0 to 2): How urgent?\n"
        "- spam (yes/no): Is it spam?\n"
        'Call with {"state": <text to judge>}. '
        "Returns per question: value, confidence (0 to 1), probabilities of each option.")


def test_decision_tool_name_cut_and_overrides():
    long = {"q" * 40: QUESTIONS["spam"], "r" * 40: QUESTIONS["spam"]}
    assert len(DecisionTool(ScriptedDecider({}), long).name) == 64
    tool = DecisionTool(ScriptedDecider({}), QUESTIONS, name="triage", description="d")
    assert (tool.name, tool.description) == ("triage", "d")


def test_decision_tool_run():
    decider = ScriptedDecider(ANSWERS)
    result = DecisionTool(decider, QUESTIONS).run({"state": "hi"})
    assert result["mood"] == {"value": "calm", "confidence": 0.8, "probabilities": {"angry": 0.1, "calm": 0.9}}
    assert set(result) == set(QUESTIONS)
    assert decider.calls == [("hi", QUESTIONS)]


def test_decision_tool_through_agent():
    tool = DecisionTool(ScriptedDecider(ANSWERS), QUESTIONS, name="triage")
    model = ScriptedModel(reply(ToolCall("c1", "triage", {"state": "buy now"})), reply(Text("spam: no")))
    agent = Agent(model, [tool])
    assert agent("triage this") == "spam: no"
    result = next(m for m in agent.messages if isinstance(m, ToolResultMessage)).tool_results[0]
    assert not result.is_error
    assert "'confidence': 0.8" in result.content


class TestTypeSafe:
    @pytest.fixture
    def model(self):
        pytest.importorskip("typesafe_sdk")
        from numpty import TypeSafe
        return TypeSafe("lev-4b-Q8", base_url="http://localhost:1", api_key="none", timeout=5)

    def test_render_question(self, model):
        assert model.render_question(QUESTIONS["mood"]) == {
            "type": "choice", "instructions": "Classify the mood.",
            "criteria": {"angry": "Upset or hostile", "calm": None}}
        assert model.render_question(QUESTIONS["urgency"]) == {
            "type": "score", "instructions": "How urgent?", "criteria": ["Can wait", "This week", "Today"]}
        assert model.render_question(Noul("Yes?")) == {"type": "noul", "instructions": "Yes?"}

    def test_parse_answer(self, model):
        choice = SimpleNamespace(type="choice", choice="calm", confidence=0.8, probabilities={"angry": 0.1, "calm": 0.9})
        score = SimpleNamespace(type="score", score=1.2, confidence=0.6, probabilities={0: 0.1, 1: 0.6, 2: 0.3},
                                legend={0: "Can wait"})
        assert model.parse_answer(choice) == ANSWERS["mood"]
        assert model.parse_answer(score) == ANSWERS["urgency"]

        noul = model.parse_answer(SimpleNamespace(type="noul", noul=0.25))
        assert noul == Answer(False, 0.5, {True: 0.25, False: 0.75})
        assert model.parse_answer(SimpleNamespace(type="noul", noul=0.5)).value is True

    def test_parse_unknown_answer(self, model):
        with pytest.raises(ValueError, match="unknown"):
            model.parse_answer(SimpleNamespace(type="ranking"))

    def test_decision(self, model, monkeypatch):
        calls = []

        def system_one(state, questions, **kwargs):
            calls.append((state, questions, kwargs))
            return SimpleNamespace(answers={"spam": SimpleNamespace(type="noul", noul=0.9)})

        monkeypatch.setattr(model.client, "system_one", system_one)
        assert model.decision("hi", {"spam": Noul("Spam?")}) == {"spam": Answer(True, pytest.approx(0.8), pytest.approx(
            {True: 0.9, False: 0.1}))}
        assert calls == [("hi", {"spam": {"type": "noul", "instructions": "Spam?"}},
                          {"model": "lev-4b-Q8", "timeout": 5})]
