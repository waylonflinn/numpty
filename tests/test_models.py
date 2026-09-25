"""Offline tests of provider rendering and parsing. No API calls."""

import inspect
import subprocess
import sys
from types import SimpleNamespace

import pytest

from numpty import (AssistantMessage, Model, PythonTool, Reasoning, SystemMessage, Text, ToolCall, ToolResult,
                    ToolResultMessage, UserMessage)


def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


TOOL = PythonTool(add)


def test_core_import_does_not_load_provider_sdks():
    code = "import sys, numpty; print('openai' in sys.modules, 'anthropic' in sys.modules, 'simpleeval' in sys.modules)"
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True).stdout
    assert out.split() == ["False", "False", "False"]


def test_unknown_attribute():
    import numpty
    with pytest.raises(AttributeError):
        numpty.Nope


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

    def test_query_without_tools(self, model):
        def create(**kwargs):
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="hi", tool_calls=None))])
        model.client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        assert model.query([UserMessage("u")]).text == "hi"

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
