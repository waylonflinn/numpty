import builtins
import importlib

import pytest

from numpty import PythonTool
from numpty.functions import append_file, calculate, read_binary, read_file, write_file

calculate_module = importlib.import_module("numpty.functions.calculate")


def test_file_round_trip(tmp_path):
    path = str(tmp_path / "f.txt")
    write_file(path, "one")
    append_file(path, " two")
    assert read_file(path) == "one two"
    assert read_binary(path) == b"one two"


def test_write_functions_return_characters_written(tmp_path):
    path = str(tmp_path / "f.txt")
    assert write_file(path, "one") == 3
    assert append_file(path, " two") == 4


def test_append_file_encoding(tmp_path):
    path = str(tmp_path / "f.txt")
    write_file(path, "é", encoding="latin-1")
    append_file(path, "è", encoding="latin-1")
    assert read_file(path, encoding="latin-1") == "éè"


def test_file_functions_wrap_as_tools():
    for fn in (read_file, write_file, append_file):
        PythonTool(fn)


def test_calculate():
    pytest.importorskip("simpleeval")
    assert calculate("3 * sqrt(9) + 4") == 13.0


@pytest.mark.parametrize("expression, error", [("3 +", SyntaxError), ("1/0", ZeroDivisionError)])
def test_calculate_invalid_expression_raises(expression, error):
    pytest.importorskip("simpleeval")
    with pytest.raises(error):
        calculate(expression)


def test_calculate_tool_schema_does_not_need_simpleeval():
    schema = PythonTool(calculate).parameters
    assert "sqrt" in schema["properties"]["expression"]["description"]


def test_calculate_without_simpleeval(monkeypatch):
    real_import = builtins.__import__

    def no_simpleeval(name, *args, **kwargs):
        if name == "simpleeval":
            raise ImportError(name)
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_simpleeval)
    calculate_module._evaluator.cache_clear()
    try:
        with pytest.raises(ImportError, match=r"numpty\[calc\]"):
            calculate("1 + 1")
    finally:
        calculate_module._evaluator.cache_clear()
