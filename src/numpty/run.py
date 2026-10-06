"""Run Python code in a new process under a policy."""

import linecache
import os
import platform
import signal
import subprocess
import sys
import traceback

from numpty.policy import Policy
from numpty.tools import Tool, _report

TIMEOUT, DENIED = 124, 126


def run(code: str, policy: Policy | None = None, location: str | None = None,
        timeout: float = 30) -> subprocess.CompletedProcess:
    """Run Python code in a new process under a policy. A guardrail, not a sandbox.

    The process gets the policy names, makes the policy again, and runs the code inside its
    enforcement. It uses this interpreter and inherits the environment. Its stdin is the code,
    so the code reads no input. No state is kept between calls.

    | Exit  | Meaning                                                  |
    |-------|----------------------------------------------------------|
    | 0     | Code finished.                                           |
    | 1     | Code raised. stderr: traceback of the code frames only.  |
    | 124   | Timeout. stderr ends with `[timed out after <timeout>s]` |
    | 126   | Policy denied. stderr: `PermissionError: <reason>`       |
    | other | Exit code from the code, for example `sys.exit(3)`.      |

    The code can itself exit 124 or 126, or catch a denial and exit 0.

    Args:
        code: Python source.
        policy: Policy for the code. Default: `Policy()`.
        location: Current directory of the process. `~` is expanded. Default: this current directory.
        timeout: Maximum run time, in seconds. On timeout the process and all its children are killed.

    Returns:
        Finished process with text `stdout` and `stderr`. Output written before a timeout is kept.

    Raises:
        ValueError: `policy` cannot be enforced (from `Policy()`).
        ImportError: Default `policy` and fastaudit is not installed.
    """
    policy = Policy() if policy is None else policy
    # -P: location is not on sys.path while the bootstrap imports. -u: output before a kill is kept.
    args = [sys.executable, "-P", "-u", "-c", "from numpty.run import _child; _child()", *policy.names()]
    with subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                          cwd=os.path.expanduser(location) if location else None, start_new_session=True) as p:
        try:
            out, err = p.communicate(code, timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL)   # the process is a session leader: kill its children too
            out, err = p.communicate()
            return subprocess.CompletedProcess(args, TIMEOUT, out, err + f"[timed out after {timeout}s]\n")
    return subprocess.CompletedProcess(args, p.returncode, out, err)


def _child():
    """Entry point of the process `run` starts. Policy names in argv, code on stdin."""
    policy = Policy.from_names(sys.argv[1:])
    code = sys.stdin.read()
    linecache.cache["<run>"] = (len(code), None, code.splitlines(True), "<run>")   # source lines in tracebacks
    sys.path.insert(0, "")   # location, after the bootstrap imports
    try:
        with policy.enforcement():
            exec(compile(code, "<run>", "exec"), {"__name__": "__main__"})
    except PermissionError as e:
        if e.errno is not None:   # from the OS, not a policy denial
            _exit_traceback(e)
        print(f"PermissionError: {e}", file=sys.stderr)
        sys.exit(DENIED)
    except Exception as e:
        _exit_traceback(e)


def _exit_traceback(e):
    """Print the traceback of `e` from the first code frame, and exit 1. A SyntaxError has no code frame."""
    tb = traceback.TracebackException.from_exception(e)
    frames = list(tb.stack)
    first = next((i for i, f in enumerate(frames) if f.filename == "<run>"), len(frames))
    tb.stack = traceback.StackSummary.from_list(frames[first:])
    print("".join(tb.format()), end="", file=sys.stderr)
    sys.exit(1)


class RunTool(Tool):
    """Tool that runs Python code in a new process under a policy. See `run`.

    `Agent` passes its policy, or `Policy.UNRESTRICTED` when it has none. The process starts in the
    current directory.
    """
    name = "run"
    parameters = {
        "type": "object",
        "properties": {"code": {"type": "string", "description": "Python source to run"}},
        "required": ["code"],
        "additionalProperties": False,
    }

    def __init__(self, timeout: float = 30, max_output: int = 10_000):
        """Make a run tool.

        Args:
            timeout: Maximum run time per call, in seconds.
            max_output: Maximum output length, in characters. Longer output is truncated.
        """
        self.timeout = timeout
        self.max_output = max_output
        self.description = (
            f"Run Python {platform.python_version()} code in a new process and return stdout. "
            "Non-zero exit returns stderr and the exit code. Exit 126: a permissions policy denied an action. "
            f"Time limit: {timeout}s. No stdin. No state is kept between calls. Print what you need to see.")

    def run(self, arguments: dict, policy: Policy | None = None) -> str:
        """Run code.

        Args:
            arguments: `{"code": <Python source>}`.
            policy: Policy for the code. Default: `Policy()`.

        Returns:
            - Exit 0: stdout. stderr is dropped.
            - Nonzero exit: stdout, then `[exit <code>]` and stderr. Exit codes as for `run`.
            - Output of `max_output` characters or more: truncated to `max_output`
              characters, with a truncation notice at the end.
        """
        return _report(run(arguments["code"], policy, timeout=self.timeout), self.max_output)
