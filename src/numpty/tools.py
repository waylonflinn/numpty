"""Tools a model can call."""

import inspect
import os
import platform
import shutil
import subprocess
from abc import ABC, abstractmethod
from typing import Annotated, Callable, get_args, get_origin, get_type_hints


class Tool(ABC):
    """Action a model can call by name.

    Subclass: implement run. Set the attributes below, or pass them to Tool.__init__
    Models send `name`, `description`, and `parameters` to the provider as the tool definition.

    Attributes:
        name: Tool name the model calls. Unique among the tools of one agent.
        description: What the tool does and when to use it. The model reads it.
        parameters: JSON Schema of type `object` for the `run` arguments.
    """

    name: str
    description: str
    parameters: dict

    def __init__(self, name: str, description: str, parameters: dict):
        self.name = name
        self.description = description
        self.parameters = parameters

    @abstractmethod
    def run(self, arguments: dict):
        """Run the tool.

        Args:
            arguments: Argument values by parameter name. Should match
                `parameters`. Not checked.

        Returns:
            Tool output, any type. Converted to text for the model.

        Raises:
            Exception: Any exception means failure. Type and message go to the
                model as an error result.
        """
        pass


class PythonTool(Tool):
    """Tool that calls a Python function in-process."""

    def __init__(self, function: Callable, name: str | None = None, description: str | None = None,
                 parameters: dict | None = None):
        """Wrap a function as a tool.

        Args:
            function: Function to call. Gets call arguments as keyword arguments.
            name: Tool name. Default: `function.__name__`.
            description: Tool description. Default: full docstring of `function`,
                or `""`. The model reads it.
            parameters: JSON Schema of the arguments. Default:
                `function_schema(function)`.

        Raises:
            TypeError: Default `parameters` only. A parameter has no type hint or the type is not supported.
        """
        self.function = function
        self.name = name or function.__name__
        self.description = description or inspect.getdoc(function) or ""
        self.parameters = parameters or PythonTool.function_schema(function)

    def run(self, arguments: dict):
        """Call the function with `arguments` as keyword arguments.

        Args:
            arguments: Argument values by parameter name.

        Returns:
            Return value of the function, unchanged.
        """
        result = self.function(**arguments)

        return result

    @staticmethod
    def function_schema(fn) -> dict:
        """Make a JSON Schema for the parameters of a function, from its type hints.

        | Python  | JSON Schema |
        |---------|-------------|
        | `str`   | `string`    |
        | `int`   | `integer`   |
        | `float` | `number`    |
        | `bool`  | `boolean`   |

        - Description: annotate as `Annotated[<type>, "<description>"]`.
        - Parameter with no default: required.
        - Other properties: not allowed.

        Args:
            fn: Function to describe.

        Returns:
            JSON Schema of type `object`, one property per parameter.

        Raises:
            TypeError: A parameter has no type hint or the type is not supported.
        """
        JSON_TYPES = {str: "string", int: "integer", float: "number", bool: "boolean"}

        hints = get_type_hints(fn, include_extras=True)   # include_extras keeps Annotated
        props, required = {}, []
        for name, param in inspect.signature(fn).parameters.items():
            if name not in hints:
                raise TypeError(f"{fn.__name__}: parameter '{name}' needs a type hint")
            hint, desc = hints[name], None
            if get_origin(hint) is Annotated:
                hint, desc = get_args(hint)[0], get_args(hint)[1]

            # raise TypeError when type is not supported
            if hint not in JSON_TYPES:
                raise TypeError(f"{fn.__name__}: parameter '{name}' has unsupported type {hint!r}")

            prop = {"type": JSON_TYPES[hint]}
            if desc:
                prop["description"] = desc
            props[name] = prop
            if param.default is inspect.Parameter.empty:
                required.append(name)
        return {
            "type": "object",
            "properties": props,
            "required": required,
            "additionalProperties": False,
        }


class ShellTool(Tool):
    """Tool that runs shell commands on the local machine. No sandbox. Runs with the permissions of the current user.

        This tool is generally outside of the intended permissions architecture. It is intended as a temporary escape hatch
        for when the python based tools are inadequate.
    """
    name = "shell"
    parameters = {
        "type": "object",
        "properties": {"command": {"type": "string", "description": "The full command line to run"}},
        "required": ["command"],
        "additionalProperties": False,
    }

    def __init__(self, max_output=10_000, timeout=30):
        """Make a shell tool.

        Shell: `$SHELL`, else `/bin/sh`. The description tells the model the shell,
        the OS, and which common commands are on `PATH` (`ls`, `grep`, `git`, and others).

        Args:
            max_output: Maximum output length, in characters. Longer output is truncated.
            timeout: Maximum run time per command, in seconds.
        """
        self.max_output = max_output
        self.timeout = timeout
        # get the OS and shell
        self.operating_system = ShellTool._describe_os()
        self.shell = os.environ.get("SHELL", "/bin/sh")

        # search for common commands
        common_commands = [c.strip() for c in "ls, wc, cat, grep, sed, find, curl, awk, jq, git".split(',')]
        self.commands = [c for c in common_commands if shutil.which(c)]

        self.description = (
        f"Run a shell command on the local machine ({self.shell}, {self.operating_system}) and return stdout. "
        "Non-zero exit returns stderr and the exit code. "
        f"Available: {", ".join(self.commands)}. ")

    @staticmethod
    def _describe_os() -> str:
        if platform.system() == "Darwin":
            return f"macOS {platform.mac_ver()[0]}"
        return f"{platform.system()} {platform.release()}"

    def run(self, arguments: dict) -> str:
        """Run a command.

        Args:
            arguments: `{"command": <full command line>}`.

        Returns:
            - Exit 0: stdout. stderr is dropped.
            - Nonzero exit: stdout, then `[exit <code>]` and stderr.
            - Timeout: `[timed out after <timeout>s]`.
            - Output of `max_output` characters or more: truncated to `max_output`
              characters, with a truncation notice at the end.
        """
        try:
            p = subprocess.run(arguments["command"], shell=True, executable=self.shell, capture_output=True,
                               text=True, timeout=self.timeout)
            out = p.stdout
            if p.returncode != 0:
                out += f"\n[exit {p.returncode}]\n{p.stderr}"
        except subprocess.TimeoutExpired:
            out = f"[timed out after {self.timeout}s]"

        if(len(out) < self.max_output):
            return out
        else:
            truncation_warning = f"\n==========TRUNCATED===========\n(output beyond {self.max_output} characters has been truncated)"
            return out[:(self.max_output-len(truncation_warning))] + truncation_warning
