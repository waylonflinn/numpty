"""Offline tests of provider rendering and parsing. No API calls."""

import inspect
import subprocess
import sys
from types import SimpleNamespace

import pytest

from numpty import (AssistantMessage, Model, Object, PythonTool, Reasoning, SystemMessage, Text, ToolCall, ToolResult,
                    ToolResultMessage, UserMessage)


def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


TOOL = PythonTool(add)
SCHEMA = {"type": "object", "properties": {"n": {"type": "integer"}}, "required": ["n"], "additionalProperties": False}


def test_core_import_does_not_load_provider_sdks():
    sdks = ["openai", "anthropic", "simpleeval", "typesafe_sdk"]
    code = f"import sys, numpty; print(*(s in sys.modules for s in {sdks!r}))"
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True).stdout
    assert out.split() == ["False"] * len(sdks)


def test_unknown_attribute():
    import numpty
    with pytest.raises(AttributeError):
        numpty.Nope


def test_parse_object_replaces_text_keeps_other_blocks():
    reasoning = Reasoning({"r": 1})
    reply = AssistantMessage([reasoning, Text('{"n": '), Text("5}")], ("p", "m"))
    assert Model.parse_object(reply) == AssistantMessage([reasoning, Object({"n": 5})], ("p", "m"))


@pytest.mark.parametrize("text, message", [("nope", "not valid JSON"), ("[1]", "not a JSON object")])
def test_parse_object_rejects_bad_text(text, message):
    with pytest.raises(ValueError, match=message):
        Model.parse_object(AssistantMessage([Text(text)], ("p", "m")))


@pytest.mark.parametrize("sdk, cls", [("anthropic", "AnthropicMessages"), ("openai", "OpenAIChat"),
                                      ("openai", "OpenAIResponses")])
def test_adapter_query_signature_matches_model(sdk, cls):
    pytest.importorskip(sdk)
    import numpty
    assert inspect.signature(getattr(numpty, cls).query) == inspect.signature(Model.query)


class TestAnthropic:
    @pytest.fixture
    def model(self, monkeypatch):
        pytest.importorskip("anthropic")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
        from numpty import AnthropicMessages
        return AnthropicMessages("claude-test")

    def test_render_messages(self, model):
        call = ToolCall("c1", "add", {"a": 1, "b": 2})
        assert model.render_message(SystemMessage("s")) == []
        assert model.render_message(UserMessage("u")) == [{"role": "user", "content": "u"}]
        assert model.render_message(AssistantMessage([Text("t"), call], ("anthropic", "claude-test"))) == [
            {"role": "assistant", "content": [
                {"type": "text", "text": "t"},
                {"type": "tool_use", "id": "c1", "name": "add", "input": {"a": 1, "b": 2}},
            ]}]
        assert model.render_message(ToolResultMessage([ToolResult("c1", "3")])) == [
            {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": "c1", "content": "3", "is_error": False}]}]

    def test_reasoning_only_replayed_to_origin(self, model):
        block = Reasoning({"type": "thinking", "thinking": "hm"})
        assert model.render_block(block, ("anthropic", "claude-test")) == block.data
        assert model.render_block(block, ("openai-chat", "gpt")) is None

    def test_parse_blocks(self, model):
        assert model.parse_block(SimpleNamespace(type="text", text="t")) == Text("t")
        assert model.parse_block(SimpleNamespace(type="tool_use", id="c", name="n", input={})) == ToolCall("c", "n", {})
        assert model.parse_block(SimpleNamespace(type="other")) is None

    def test_query_without_system_omits_it(self, model):
        sent = {}
        def create(**kwargs):
            sent.update(kwargs)
            return SimpleNamespace(content=[SimpleNamespace(type="text", text="hi")])
        model.client = SimpleNamespace(messages=SimpleNamespace(create=create))
        assert model.query([UserMessage("u")]).text == "hi"
        assert sent["system"] is not None

    def test_render_tool(self, model):
        assert model.render_tool(TOOL) == {"name": "add", "description": "Add two numbers.",
                                           "input_schema": TOOL.parameters}

    def test_render_object_as_text(self, model):
        assert model.render_block(Object({"n": 5}), ("anthropic", "claude-test")) == {"type": "text", "text": '{"n": 5}'}

    @staticmethod
    def stub(model, text, stop_reason="end_turn"):
        sent = {}
        def create(**kwargs):
            sent.update(kwargs)
            return SimpleNamespace(content=[SimpleNamespace(type="text", text=text)], stop_reason=stop_reason)
        model.client = SimpleNamespace(messages=SimpleNamespace(create=create))
        return sent

    def test_schema_renders_and_parses(self, model):
        sent = self.stub(model, '{"n": 5}')
        reply = model.query([UserMessage("u")], schema=SCHEMA)
        assert sent["output_config"] == {"format": {"type": "json_schema", "schema": SCHEMA}}
        assert reply.blocks == [Object({"n": 5})]
        assert reply.object == {"n": 5}

    def test_no_schema_omits_output_config(self, model):
        from anthropic import omit
        sent = self.stub(model, "hi")
        assert model.query([UserMessage("u")]).text == "hi"
        assert sent["output_config"] is omit

    def test_schema_with_tool_call_leaves_turn_alone(self, model):
        def create(**kwargs):
            return SimpleNamespace(content=[SimpleNamespace(type="tool_use", id="c", name="add", input={})],
                                   stop_reason="tool_use")
        model.client = SimpleNamespace(messages=SimpleNamespace(create=create))
        assert model.query([UserMessage("u")], [TOOL], SCHEMA).tool_calls == [ToolCall("c", "add", {})]

    @pytest.mark.parametrize("stop_reason, text, message", [
        ("refusal", "", "refused"), ("max_tokens", '{"n"', "truncated"), ("end_turn", "oops", "not valid JSON")])
    def test_schema_failures_raise(self, model, stop_reason, text, message):
        self.stub(model, text, stop_reason)
        with pytest.raises(ValueError, match=message):
            model.query([UserMessage("u")], schema=SCHEMA)


class TestOpenAIChat:
    @pytest.fixture
    def model(self):
        pytest.importorskip("openai")
        from numpty import OpenAIChat
        return OpenAIChat("gpt-test", api_key="test")

    def test_render_messages(self, model):
        call = ToolCall("c1", "add", {"a": 1})
        assert model.render_message(SystemMessage("s")) == [{"role": "system", "content": "s"}]
        assert model.render_message(AssistantMessage([Text("t"), call], ("openai-chat", "gpt-test"))) == [
            {"role": "assistant", "content": "t", "tool_calls": [
                {"id": "c1", "type": "function", "function": {"name": "add", "arguments": '{"a": 1}'}}]}]
        assert model.render_message(ToolResultMessage([ToolResult("c1", "3"), ToolResult("c2", "4")])) == [
            {"role": "tool", "tool_call_id": "c1", "content": "3"},
            {"role": "tool", "tool_call_id": "c2", "content": "4"}]

    def test_reasoning_only_replayed_to_origin(self, model):
        reasoning = Reasoning({"reasoning_content": "hm"})
        assert model.render_message(AssistantMessage([reasoning, Text("t")], ("openai-chat", "gpt-test"))) == [
            {"role": "assistant", "content": "t", "reasoning_content": "hm"}]
        assert model.render_message(AssistantMessage([reasoning, Text("t")], ("openai-chat", "other"))) == [
            {"role": "assistant", "content": "t"}]

    def test_query_without_tools(self, model):
        def create(**kwargs):
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="hi", tool_calls=None))])
        model.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        assert model.query([UserMessage("u")]).text == "hi"

    def test_query_parses_reasoning_content(self, model):
        def create(**kwargs):
            message = SimpleNamespace(content="hi", reasoning_content="hm", tool_calls=None)
            return SimpleNamespace(choices=[SimpleNamespace(message=message)])
        model.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        assert model.query([UserMessage("u")]).blocks == [Reasoning({"reasoning_content": "hm"}), Text("hi")]

    def test_render_object_as_content(self, model):
        assert model.render_message(AssistantMessage([Object({"n": 5})], ("openai-chat", "gpt-test"))) == [
            {"role": "assistant", "content": '{"n": 5}'}]

    @staticmethod
    def stub(model, content, finish_reason="stop", refusal=None):
        sent = {}
        def create(**kwargs):
            sent.update(kwargs)
            message = SimpleNamespace(content=content, tool_calls=None, refusal=refusal)
            return SimpleNamespace(choices=[SimpleNamespace(message=message, finish_reason=finish_reason)])
        model.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        return sent

    def test_schema_renders_and_parses(self, model):
        sent = self.stub(model, '{"n": 5}')
        reply = model.query([UserMessage("u")], schema=SCHEMA)
        assert sent["response_format"] == {"type": "json_schema",
                                           "json_schema": {"name": "output", "schema": SCHEMA, "strict": True}}
        assert reply.blocks == [Object({"n": 5})]

    def test_no_schema_omits_response_format(self, model):
        sent = self.stub(model, "hi")
        assert model.query([UserMessage("u")]).text == "hi"
        assert "response_format" not in sent

    @pytest.mark.parametrize("finish_reason, content, refusal, message", [
        ("stop", None, "no", "refused structured output: no"), ("content_filter", None, None, "refused"),
        ("length", '{"n"', None, "truncated"), ("stop", "oops", None, "not valid JSON")])
    def test_schema_failures_raise(self, model, finish_reason, content, refusal, message):
        self.stub(model, content, finish_reason, refusal)
        with pytest.raises(ValueError, match=message):
            model.query([UserMessage("u")], schema=SCHEMA)

    def test_render_tool(self, model):
        assert model.render_tool(TOOL) == {"type": "function", "function": {
            "name": "add", "description": "Add two numbers.", "parameters": TOOL.parameters}}


class TestOpenAIResponses:
    @pytest.fixture
    def model(self, monkeypatch):
        pytest.importorskip("openai")
        monkeypatch.setenv("OPENAI_API_KEY", "test")
        from numpty import OpenAIResponses
        return OpenAIResponses("gpt-test")

    def test_render_messages(self, model):
        call = ToolCall("c1", "add", {"a": 1})
        reasoning = Reasoning({"type": "reasoning", "id": "r"})
        assert model.render_message(SystemMessage("s")) == []
        assert model.render_message(AssistantMessage([reasoning, Text("t"), call], ("openai-responses", "gpt-test"))) == [
            reasoning.data,
            {"role": "assistant", "content": "t"},
            {"type": "function_call", "call_id": "c1", "name": "add", "arguments": '{"a": 1}'}]
        assert model.render_message(ToolResultMessage([ToolResult("c1", "3")])) == [
            {"type": "function_call_output", "call_id": "c1", "output": "3"}]

    def test_parse_items(self, model):
        message = SimpleNamespace(type="message", content=[SimpleNamespace(type="output_text", text="t")])
        call = SimpleNamespace(type="function_call", call_id="c", name="n", arguments='{"a": 1}')
        assert model.parse_item(message) == Text("t")
        assert model.parse_item(call) == ToolCall("c", "n", {"a": 1})
        assert model.parse_item(SimpleNamespace(type="other")) is None

    def test_render_tool(self, model):
        assert model.render_tool(TOOL) == {"type": "function", "name": "add", "description": "Add two numbers.",
                                           "parameters": TOOL.parameters, "strict": False}

    def test_render_object_as_assistant_message(self, model):
        assert model.render_block(Object({"n": 5}), ("openai-responses", "gpt-test")) == {
            "role": "assistant", "content": '{"n": 5}'}

    @staticmethod
    def stub(model, content, status="completed"):
        sent = {}
        def create(**kwargs):
            sent.update(kwargs)
            return SimpleNamespace(output=[SimpleNamespace(type="message", content=content)], status=status)
        model.client = SimpleNamespace(responses=SimpleNamespace(create=create))
        return sent

    def test_schema_renders_and_parses(self, model):
        sent = self.stub(model, [SimpleNamespace(type="output_text", text='{"n": 5}')])
        reply = model.query([UserMessage("u")], schema=SCHEMA)
        assert sent["text"] == {"format": {"type": "json_schema", "name": "output", "schema": SCHEMA, "strict": True}}
        assert reply.blocks == [Object({"n": 5})]

    def test_no_schema_omits_text_format(self, model):
        sent = self.stub(model, [SimpleNamespace(type="output_text", text="hi")])
        assert model.query([UserMessage("u")]).text == "hi"
        assert "text" not in sent

    @pytest.mark.parametrize("content, status, message", [
        ([SimpleNamespace(type="refusal", refusal="no")], "completed", "refused structured output: no"),
        ([SimpleNamespace(type="output_text", text='{"n"')], "incomplete", "truncated"),
        ([SimpleNamespace(type="output_text", text="oops")], "completed", "not valid JSON")])
    def test_schema_failures_raise(self, model, content, status, message):
        self.stub(model, content, status)
        with pytest.raises(ValueError, match=message):
            model.query([UserMessage("u")], schema=SCHEMA)
