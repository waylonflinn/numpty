import pytest

from numpty import (Agent, AssistantMessage, Model, Policy, PythonTool, ShellTool, SystemMessage, Text, ToolCall,
                    ToolResultMessage, UserMessage)
from numpty.functions import write_file


def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


def fail() -> str:
    """Always fails."""
    raise ValueError("boom")


class ScriptedModel(Model):
    """Returns canned replies in order and records what it was sent."""

    def __init__(self, *replies):
        self.replies = list(replies)
        self.calls = []

    def query(self, messages, tools=None):
        self.calls.append((list(messages), tools))
        return self.replies.pop(0)


def reply(*blocks):
    return AssistantMessage(list(blocks), origin=("scripted", "test"))


def test_text_reply_returns_immediately():
    model = ScriptedModel(reply(Text("hello")))
    agent = Agent(model, [], system="sys")
    assert agent("hi") == "hello"
    assert agent.messages[:2] == [SystemMessage("sys"), UserMessage("hi")]
    assert len(agent.messages) == 3


def test_no_system_prompt_adds_no_system_message():
    agent = Agent(ScriptedModel(reply(Text("hello"))), [])
    assert agent.messages == []


def test_tool_call_loop():
    model = ScriptedModel(reply(ToolCall("c1", "add", {"a": 2, "b": 3})), reply(Text("5")))
    agent = Agent(model, [PythonTool(add)])
    assert agent("2+3?") == "5"
    results = next(m for m in agent.messages if isinstance(m, ToolResultMessage))
    assert isinstance(results, ToolResultMessage)
    assert results.tool_results[0].call_id == "c1"
    assert results.tool_results[0].content == "5"
    assert not results.tool_results[0].is_error


def test_tools_passed_to_model():
    tool = PythonTool(add)
    model = ScriptedModel(reply(Text("ok")))
    Agent(model, [tool])("x")
    assert model.calls[0][1] == [tool]


def test_tool_exception_becomes_error_result():
    agent = Agent(ScriptedModel(), [PythonTool(fail)])
    result = agent.run(ToolCall("c1", "fail", {}))
    assert result.is_error
    assert result.content == "ValueError: boom"


def test_unknown_tool_becomes_error_result():
    result = Agent(ScriptedModel(), []).run(ToolCall("c1", "missing", {}))
    assert result.is_error
    assert result.content.startswith("KeyError")


def test_max_turns_exceeded():
    call = reply(ToolCall("c", "add", {"a": 1, "b": 1}))
    agent = Agent(ScriptedModel(call, call), [PythonTool(add)])
    try:
        agent("loop", max_turns=2)
    except RuntimeError as e:
        assert "max_turns" in str(e)
    else:
        raise AssertionError("expected RuntimeError")


def test_assistant_message_accessors():
    message = reply(Text("a"), ToolCall("c", "t", {}), Text("b"))
    assert message.text == "ab"
    assert message.tool_calls == [ToolCall("c", "t", {})]


def test_policy_denial_becomes_error_result(tmp_path, monkeypatch):
    pytest.importorskip("fastaudit")
    monkeypatch.chdir(tmp_path)
    agent = Agent(ScriptedModel(), [PythonTool(write_file)], policy=Policy())
    result = agent.run(ToolCall("c1", "write_file", {"path": "a.txt", "content": "x"}))
    assert result.is_error
    assert result.content.startswith("PermissionError")
    assert not (tmp_path / "a.txt").exists()


def test_policy_allows_permitted_tool_call(tmp_path, monkeypatch):
    pytest.importorskip("fastaudit")
    monkeypatch.chdir(tmp_path)
    policy = Policy(Policy.Filesystem.READ | Policy.Filesystem.WRITE_LOCATION_TREE)
    agent = Agent(ScriptedModel(), [PythonTool(write_file)], policy=policy)
    result = agent.run(ToolCall("c1", "write_file", {"path": "a.txt", "content": "x"}))
    assert not result.is_error
    assert (tmp_path / "a.txt").read_text() == "x"


def test_shell_tool_with_restricted_policy_raises():
    pytest.importorskip("fastaudit")
    with pytest.raises(ValueError, match="Process.UNRESTRICTED"):
        Agent(ScriptedModel(), [ShellTool()], policy=Policy(Policy.Filesystem.UNRESTRICTED))


def test_shell_tool_with_process_policy_runs():
    pytest.importorskip("fastaudit")
    agent = Agent(ScriptedModel(), [ShellTool()], policy=Policy(process=Policy.Process.UNRESTRICTED))
    assert agent.run(ToolCall("c1", "shell", {"command": "echo hi"})).content == "hi\n"


def test_no_policy_checks_nothing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    agent = Agent(ScriptedModel(), [PythonTool(write_file), ShellTool()])
    assert agent.policy is None
    assert not agent.run(ToolCall("c1", "write_file", {"path": "a.txt", "content": "x"})).is_error
