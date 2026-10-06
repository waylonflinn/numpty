import os
import socket
import subprocess
import sys
import threading

import pytest

from numpty import Policy
from numpty.functions import append_file, read_file, write_file

pd = pytest.importorskip("pandas")
pytest.importorskip("fastaudit")

FS, NET, PROC = Policy.Filesystem, Policy.Network, Policy.Process


@pytest.fixture
def dirs(tmp_path, monkeypatch):
    """Current directory `cwd` with a subfolder and a file, a folder `outside`, and a symlink from cwd to outside."""
    cwd, outside = tmp_path / "cwd", tmp_path / "outside"
    (cwd / "sub").mkdir(parents=True)
    outside.mkdir()
    (cwd / "a.txt").write_text("a")
    (outside / "b.txt").write_text("b")
    (cwd / "link").symlink_to(outside)
    monkeypatch.chdir(cwd)
    return cwd, outside


def connect():
    try:
        socket.create_connection(("127.0.0.1", 9), timeout=0.2).close()
    except (ConnectionError, TimeoutError):
        pass   # reached the network layer


ACTIONS = {
    "read": lambda d: read_file(str(d[1] / "b.txt")),
    "write": lambda d: write_file("a.txt", "x"),
    "append": lambda d: append_file("a.txt", "x"),
    "write_subfolder": lambda d: write_file("sub/c.txt", "x"),
    "pandas": lambda d: pd.DataFrame({"x": [1]}).to_csv("sub/d.csv"),
    "write_outside": lambda d: write_file(str(d[1] / "c.txt"), "x"),
    "dotdot": lambda d: write_file("sub/../../outside/c.txt", "x"),
    "symlink": lambda d: write_file("link/c.txt", "x"),
    "pandas_outside": lambda d: pd.DataFrame({"x": [1]}).to_csv(str(d[1] / "d.csv")),
    "subprocess": lambda d: subprocess.run(["true"]),
    "network": lambda d: connect(),
    "thread": lambda d: threading.Thread(target=lambda: None).start(),
}
IN_TREE = {"write", "append", "write_subfolder", "pandas"}
OUTSIDE = {"write_outside", "dotdot", "symlink", "pandas_outside"}

POLICIES = {
    "read": (Policy(), {"read"}),
    "write_tree": (Policy(FS.READ | FS.WRITE_LOCATION), {"read"} | IN_TREE),
    "write": (Policy(FS.READ | FS.WRITE), {"read"} | IN_TREE | OUTSIDE),
    "fs_unrestricted": (Policy(FS.UNRESTRICTED), {"read"} | IN_TREE | OUTSIDE),
    "network": (Policy(network=NET.UNRESTRICTED), {"read", "network"}),
    "process": (Policy(process=PROC.UNRESTRICTED), {"read", "subprocess", "thread"}),
    "unrestricted": (Policy.UNRESTRICTED, set(ACTIONS)),
}


@pytest.mark.parametrize("policy_name", POLICIES)
@pytest.mark.parametrize("action", ACTIONS)
def test_enforcement(dirs, policy_name, action):
    policy, allowed = POLICIES[policy_name]
    with policy.enforcement():
        if action in allowed:
            ACTIONS[action](dirs)
        else:
            with pytest.raises(PermissionError):
                ACTIONS[action](dirs)


def test_no_checks_outside_enforcement(dirs):
    Policy()
    write_file(str(dirs[1] / "c.txt"), "x")


@pytest.mark.parametrize("flags", [
    FS(0), FS.WRITE, FS.READ_LOCATION_STRICT, FS.READ_LOCATION | FS.WRITE_LOCATION, FS.READ | FS.APPEND,
    FS.READ | FS.APPEND_LOCATION, FS.READ | FS.WRITE_LOCATION_STRICT, FS.READ | FS.APPEND | FS.WRITE_LOCATION,
])
def test_unenforceable_filesystem_raises(flags):
    with pytest.raises(ValueError, match="filesystem"):
        Policy(flags)


@pytest.mark.parametrize("flags", [NET.READ, NET.WRITE, NET.READ_LOCATION])
def test_unenforceable_network_raises(flags):
    with pytest.raises(ValueError, match="network"):
        Policy(network=flags)


@pytest.mark.parametrize("flags", [
    FS.READ | FS.READ_LOCATION_STRICT, FS.READ | FS.WRITE | FS.WRITE_LOCATION, FS.READ | FS.APPEND | FS.WRITE,
    FS.READ | FS.APPEND_LOCATION_STRICT | FS.WRITE_LOCATION, FS.UNRESTRICTED | FS.APPEND,
])
def test_redundant_flags_accepted(flags):
    Policy(flags)


def test_names_round_trip():
    policy = Policy(FS.READ | FS.WRITE_LOCATION, process=PROC.UNRESTRICTED)
    assert policy.names() == ["FS_READ", "FS_WRITE_LOCATION", "PROC_UNRESTRICTED"]
    again = Policy.from_names(policy.names())
    assert (again.filesystem, again.network, again.process) == (policy.filesystem, policy.network, policy.process)


def test_from_names_unrestricted():
    policy = Policy.from_names(["UNRESTRICTED"])
    assert policy.names() == Policy.UNRESTRICTED.names() == ["FS_UNRESTRICTED", "NET_UNRESTRICTED", "PROC_UNRESTRICTED"]


@pytest.mark.parametrize("name", ["READ", "FS_EXECUTE", "PROC_READ"])
def test_from_names_unknown_raises(name):
    with pytest.raises(ValueError, match="unknown"):
        Policy.from_names([name])


def test_missing_fastaudit_raises_import_error(monkeypatch):
    monkeypatch.setitem(sys.modules, "fastaudit", None)
    with pytest.raises(ImportError, match=r"numpty\[security\]"):
        Policy()
    Policy.from_names(["UNRESTRICTED"])   # needs no fastaudit


def test_other_policy_inside_active_policy_denied():
    outer, inner = Policy(), Policy(FS.UNRESTRICTED)
    with outer.enforcement():
        with pytest.raises(PermissionError):
            with inner.enforcement():
                pass


def test_policy_made_inside_active_policy_denied():
    with Policy().enforcement():
        with pytest.raises(PermissionError):
            Policy()


def test_c_extensions_names_round_trip():
    policy = Policy.from_names(["FS_READ", "PROC_C_EXTENSIONS"])
    assert policy.process == PROC.C_EXTENSIONS
    assert policy.names() == ["FS_READ", "PROC_C_EXTENSIONS"]


@pytest.mark.parametrize("process, monitor_calls", [
    (PROC(0), True), (PROC.C_EXTENSIONS, False), (PROC.UNRESTRICTED, False),
    (PROC.UNRESTRICTED | PROC.C_EXTENSIONS, False),
])
def test_c_extensions_turns_off_monitor_calls(monkeypatch, process, monitor_calls):
    import fastaudit
    seen = {}
    monkeypatch.setattr(fastaudit, "mk_audit", lambda *a, **kw: seen.update(kw))
    Policy(process=process)
    assert seen["monitor_calls"] is monitor_calls


def test_c_extensions_alone_enforces_no_process_permission(dirs):
    with Policy(process=PROC.C_EXTENSIONS).enforcement():
        with pytest.raises(PermissionError):
            subprocess.run(["true"])
