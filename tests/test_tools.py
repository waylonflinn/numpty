from typing import Annotated

import pytest

from numpty import PythonTool, ShellTool, Tool


def greet(name: Annotated[str, "Who to greet"], times: int = 1) -> str:
    """Say hello."""
    return "hi " * times + name


def test_tool_constructor_sets_definition():
    class Echo(Tool):
        def run(self, arguments): return arguments
    tool = Echo("echo", "Echo back.", {"type": "object"})
    assert (tool.name, tool.description, tool.parameters) == ("echo", "Echo back.", {"type": "object"})


def test_function_schema_types_descriptions_and_required():
    assert PythonTool.function_schema(greet) == {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Who to greet"},
            "times": {"type": "integer"},
        },
        "required": ["name"],
        "additionalProperties": False,
    }


def test_python_tool_defaults_from_function():
    tool = PythonTool(greet)
    assert tool.name == "greet"
    assert tool.description == "Say hello."
    assert tool.parameters == PythonTool.function_schema(greet)


def test_python_tool_overrides():
    tool = PythonTool(greet, name="hello", description="d", parameters={"type": "object"})
    assert (tool.name, tool.description, tool.parameters) == ("hello", "d", {"type": "object"})


def test_python_tool_run_passes_arguments():
    assert PythonTool(greet).run({"name": "bob", "times": 2}) == "hi hi bob"


def test_function_schema_requires_type_hints():
    def untyped(x): pass
    try:
        PythonTool.function_schema(untyped)
    except TypeError as e:
        assert "'x'" in str(e)
    else:
        raise AssertionError("expected TypeError")


def test_function_schema_unsupported_type_names_parameter():
    def listy(x: list[str]): pass
    with pytest.raises(TypeError, match=r"listy.*'x'"):
        PythonTool.function_schema(listy)


def test_shell_tool_is_a_tool():
    assert isinstance(ShellTool(), Tool)


def test_shell_tool_runs_command():
    assert ShellTool().run({"command": "echo hello"}) == "hello\n"


def test_shell_tool_reports_nonzero_exit():
    out = ShellTool().run({"command": "echo oops >&2; exit 3"})
    assert "[exit 3]" in out and "oops" in out


def test_shell_tool_timeout():
    assert ShellTool(timeout=0.1).run({"command": "sleep 1"}) == "[timed out after 0.1s]"


def test_shell_tool_truncates_to_max_output():
    out = ShellTool(max_output=100).run({"command": "printf 'x%.0s' $(seq 500)"})
    assert len(out) == 100
    assert "TRUNCATED" in out
