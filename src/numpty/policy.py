"""Permissions policy for tool calls."""

from contextlib import AbstractContextManager, nullcontext
from enum import Flag, auto


class Policy:
    """What tool calls can do: filesystem, network, and processes. A guardrail, not a sandbox.

    Each subsystem has a slot of flags. Combine flags with `|`. Each flag name states a
    permission it enables. A slot with no flags enables nothing.

    Scopes, on the flags that have one:

    | Suffix           | Scope                                    |
    |------------------|------------------------------------------|
    | none             | everywhere                               |
    | `_LOCATION_TREE` | current directory and all its subfolders |
    | `_LOCATION`      | current directory only                   |

    Each check reads the current directory again. The policy does not store it.

    Enforcement uses fastaudit (Python audit hooks), which needs the `security` extra.
    It stops accidental overreach by a model. It does not stop code that tries to escape on
    purpose. Limits:

    - Reads are not checked. Tool output that goes to the model can leak any file the user can read.
    - New threads are denied unless `Process.UNRESTRICTED` is set.
    - C extensions that fastaudit does not know are denied, for example pyarrow
      (`DataFrame.to_parquet`). See `monitor_calls`.
    - Only one policy can be active at a time. Entering a different policy inside an active
      one is denied.

    Supported combinations. Redundant flags are allowed, for example `READ_LOCATION` with `READ`.

    - `filesystem`: `READ`, `READ | WRITE_LOCATION_TREE`, `READ | WRITE`, `UNRESTRICTED`
    - `network`: none, `UNRESTRICTED`
    - `process`: none, `UNRESTRICTED`

    Other combinations raise `ValueError`. They are never widened.

    Attributes:
        UNRESTRICTED: Policy with every slot `UNRESTRICTED`. Checks nothing. Does not need fastaudit.
    """

    class Filesystem(Flag):
        """Filesystem permissions. `WRITE` includes append."""
        READ = auto()
        READ_LOCATION = auto()
        READ_LOCATION_TREE = auto()
        APPEND = auto()
        APPEND_LOCATION = auto()
        APPEND_LOCATION_TREE = auto()
        WRITE = auto()
        WRITE_LOCATION = auto()
        WRITE_LOCATION_TREE = auto()
        UNRESTRICTED = auto()

    class Network(Flag):
        """Network permissions."""
        READ = auto()
        READ_LOCATION = auto()
        READ_LOCATION_TREE = auto()
        WRITE = auto()
        WRITE_LOCATION = auto()
        WRITE_LOCATION_TREE = auto()
        UNRESTRICTED = auto()

    class Process(Flag):
        """Process and thread permissions. The policy does not check a new process. Thus
        `UNRESTRICTED` also gives that process full filesystem and network access."""
        UNRESTRICTED = auto()

    UNRESTRICTED: "Policy"

    def __init__(self, filesystem: Filesystem = Filesystem.READ, network: Network = Network(0),
                 process: Process = Process(0), monitor_calls: bool = True):
        """Make a policy.

        Default: read files everywhere. No writes, no network, no processes, no threads.

        Make each policy outside an active policy. fastaudit denies setup inside one.

        Args:
            filesystem: Filesystem flags.
            network: Network flags.
            process: Process flags.
            monitor_calls: Check calls into C extensions. `False` lets unknown C extensions
                (for example pyarrow) run, but their file and network access is not checked.

        Raises:
            ValueError: fastaudit cannot enforce the combination of flags.
            ImportError: The policy restricts something and fastaudit is not installed.
            PermissionError: Made inside an active policy.
        """
        self.filesystem = filesystem
        self.network = network
        self.process = process
        self.monitor_calls = monitor_calls
        self._audit = None if self._unrestricted() else _fastaudit_enforcement(self)

    def _unrestricted(self):
        return (Policy.Filesystem.UNRESTRICTED in self.filesystem and Policy.Network.UNRESTRICTED in self.network
                and Policy.Process.UNRESTRICTED in self.process)

    def enforcement(self) -> AbstractContextManager:
        """Make a context manager that enforces this policy. Checks apply only inside it.

        Returns:
            New context manager. Denied actions inside it raise `PermissionError`.
        """
        return self._audit() if self._audit else nullcontext()

    def names(self) -> list[str]:
        """Names of the flags that are set, with a slot prefix: `FS_`, `NET_`, `PROC_`.

        Returns:
            Flag names, for example `["FS_READ", "FS_WRITE_LOCATION_TREE"]`.
        """
        slots = zip(_PREFIXES, (self.filesystem, self.network, self.process))
        return [prefix + flag.name for prefix, flags in slots for flag in flags]

    @classmethod
    def from_names(cls, names: list[str], monitor_calls: bool = True) -> "Policy":
        """Make a policy from flag names. Opposite of `names`.

        Args:
            names: Flag names with a slot prefix, for example `"FS_READ"`. `"UNRESTRICTED"`
                sets `UNRESTRICTED` in every slot.
            monitor_calls: Check calls into C extensions.

        Returns:
            New policy. A slot with no names gets no flags.

        Raises:
            ValueError: Unknown name, or a combination that `Policy` raises for.
        """
        slots = {prefix: kind(0) for prefix, kind in _PREFIXES.items()}
        for name in names:
            if name == "UNRESTRICTED":
                slots = {prefix: flags | kind.UNRESTRICTED for (prefix, flags), kind in
                         zip(slots.items(), _PREFIXES.values())}
                continue
            prefix = next((p for p in _PREFIXES if name.startswith(p)), None)
            try:
                slots[prefix] |= _PREFIXES[prefix][name.removeprefix(prefix)]
            except KeyError:
                raise ValueError(f"unknown policy name {name!r}") from None
        return cls(*slots.values(), monitor_calls=monitor_calls)

    def __repr__(self):
        return f"Policy.from_names({self.names()!r})"


_PREFIXES = {"FS_": Policy.Filesystem, "NET_": Policy.Network, "PROC_": Policy.Process}
Policy.UNRESTRICTED = Policy(Policy.Filesystem.UNRESTRICTED, Policy.Network.UNRESTRICTED, Policy.Process.UNRESTRICTED)

# Scopes, narrow to wide. fastaudit write roots for each write scope it can enforce.
_NONE, _LOCATION, _LOCATION_TREE, _EVERYWHERE = range(4)
_WRITE_ROOTS = {_NONE: (), _LOCATION_TREE: (".",), _EVERYWHERE: None}

# Audit event prefixes that each UNRESTRICTED slot allows. fastaudit denies them by default.
# See https://docs.python.org/3/library/audit_events.html
_NETWORK_EVENTS = ("socket.", "http.client.")
_PROCESS_EVENTS = ("subprocess.", "_posixsubprocess.", "os.system", "os.exec", "os.posix_spawn", "os.spawn",
                   "os.startfile", "os.kill", "_thread.")


def _scope(flags, kind, verb):
    """Widest scope that `flags` enables for `verb` (`"READ"`, `"APPEND"`, `"WRITE"`)."""
    for suffix, scope in (("", _EVERYWHERE), ("_LOCATION_TREE", _LOCATION_TREE), ("_LOCATION", _LOCATION)):
        if kind[verb + suffix] in flags:
            return scope
    return _NONE


def _fastaudit_enforcement(policy):
    """Make a fastaudit context factory for `policy`. The only place that imports fastaudit.

    Raises:
        ValueError: fastaudit cannot enforce the policy.
        ImportError: fastaudit not installed.
    """
    fs, net, proc = Policy.Filesystem, Policy.Network, Policy.Process

    if fs.UNRESTRICTED in policy.filesystem:
        roots = None
    else:
        read, append, write = (_scope(policy.filesystem, fs, verb) for verb in ("READ", "APPEND", "WRITE"))
        # reads are not checked, so only read everywhere is exact. Write includes append.
        if read != _EVERYWHERE or append > write or write not in _WRITE_ROOTS:
            raise ValueError(f"cannot enforce filesystem permissions {policy.names()}. Supported: FS_READ, "
                             "FS_READ | FS_WRITE_LOCATION_TREE, FS_READ | FS_WRITE, FS_UNRESTRICTED")
        roots = _WRITE_ROOTS[write]

    allowed = ()
    for flags, kind, events in ((policy.network, net, _NETWORK_EVENTS), (policy.process, proc, _PROCESS_EVENTS)):
        if kind.UNRESTRICTED in flags:
            allowed += events
        elif flags:
            raise ValueError(f"cannot enforce {kind.__name__.lower()} permissions {policy.names()}. "
                             f"Supported: none, UNRESTRICTED")

    try:
        from fastaudit import mk_audit
    except ImportError as e:
        raise ImportError("a restrictive Policy requires fastaudit: pip install 'numpty[security]'") from e

    def before_deny(event, *_):
        return event.startswith(allowed)

    return mk_audit(roots, before_deny=before_deny if allowed else None, monitor_calls=policy.monitor_calls)
