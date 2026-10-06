"""`numpty` command line."""

import argparse
import os
import sys

from numpty.policy import Policy
from numpty.run import run


class _Once(argparse.Action):
    """Store an option value. A second occurrence is an error: an option added after an
    approved command prefix cannot change it."""

    def __call__(self, parser, namespace, values, option_string=None):
        if getattr(self, "seen", False):
            parser.error(f"{'/'.join(self.option_strings)} can be given only once")
        self.seen = True
        setattr(namespace, self.dest, values)


def _names(value: str) -> list[str]:
    return [name.strip() for name in value.split(",") if name.strip()]


def _dimension(name: str) -> tuple[str, str]:
    """Slot prefix and verb of a policy name: `FS_WRITE_LOCATION` -> `("FS_", "WRITE")`."""
    prefix, _, flag = name.partition("_")
    return prefix + "_", flag.removesuffix("_STRICT").removesuffix("_LOCATION")


def _fill(names: list[str]) -> list[str]:
    """Add the `Policy()` names for each dimension that `names` does not set.

    A dimension is a verb in a slot, for example filesystem WRITE. `UNRESTRICTED` sets every
    dimension of its slot, or of every slot without a prefix. `Policy()` is the strictest policy
    that can be enforced, so a dimension that is not given gets its strictest enforceable value.
    """
    if "UNRESTRICTED" in names:
        return names
    given = {_dimension(name) for name in names}
    return names + [name for name in Policy().names() if _dimension(name) not in given
                    and (_dimension(name)[0], "UNRESTRICTED") not in given]


def _parsers() -> tuple[argparse.ArgumentParser, argparse.ArgumentParser]:
    """`numpty` parser and its `run` subparser."""
    parser = argparse.ArgumentParser(prog="numpty", description="numpty agent library tools.")
    commands = parser.add_subparsers(dest="command", required=True)
    run_command = commands.add_parser(
        "run", help="run Python from stdin under a permissions policy",
        description="Run Python code from stdin in a new process under a permissions policy, and pass through "
                    "its stdout, stderr, and exit code. Exit 124: timeout. Exit 126: the policy denied an action. "
                    "The policy is a guardrail, not a sandbox.")
    run_command.add_argument(
        "-p", "--permission", action=_Once, type=_names, default=[], metavar="NAMES",
        help="comma-separated Policy names, for example FS_WRITE_LOCATION,NET_UNRESTRICTED. A permission that "
             "is not given takes its Policy() default: read files, no writes, no network, no processes.")
    run_command.add_argument("-l", "--location", action=_Once, metavar="DIR",
                             help="current directory of the code. Default: this current directory")
    run_command.add_argument("-t", "--timeout", action=_Once, type=float, default=30, metavar="SECONDS",
                             help="maximum run time. Default: 30")
    return parser, run_command


def main(argv: list[str] | None = None) -> int:
    """Run the `numpty` command line.

    `numpty run [-p NAMES] [-l DIR] [-t SECONDS]` runs Python from stdin with `numpty.run.run`.
    Each option can be given only once.

    Args:
        argv: Arguments without the program name. Default: `sys.argv[1:]`.

    Returns:
        Exit code of the code. 124: timeout. 126: denied.

    Raises:
        SystemExit: Exit 2 for a usage error: unknown or unenforceable policy name, an option given
            twice, or a location that is not a directory.
    """
    parser, run_command = _parsers()
    args = parser.parse_args(argv)

    names = _fill(args.permission)
    try:
        policy = Policy.from_names(names)
    except (ValueError, ImportError) as e:
        run_command.error(str(e))
    if args.location is not None and not os.path.isdir(os.path.expanduser(args.location)):
        run_command.error(f"location {args.location!r} is not a directory")
    if args.location is not None and not any("_LOCATION" in name for name in names):
        print(f"numpty run: warning: no _LOCATION permission in {names}, so --location changes only the "
              "current directory", file=sys.stderr)

    p = run(sys.stdin.read(), policy, args.location, args.timeout)
    sys.stdout.write(p.stdout)
    sys.stderr.write(p.stderr)
    return p.returncode
