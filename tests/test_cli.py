import io
import sys

import pytest

from numpty import Policy
from numpty.cli import _fill, main

pytest.importorskip("fastaudit")

ARGV = "import sys; print(sys.argv[1:])"   # the child gets the policy names as arguments


@pytest.fixture
def numpty(tmp_path, monkeypatch, capsys):
    """Run `main(argv)` in tmp_path with `code` on stdin. Returns exit code, stdout, stderr."""
    monkeypatch.chdir(tmp_path)

    def call(argv, code=""):
        monkeypatch.setattr(sys, "stdin", io.StringIO(code))
        code = main(argv)
        out, err = capsys.readouterr()
        return code, out, err
    return call


def test_no_permission_is_default_policy(numpty):
    assert _fill([]) == Policy().names()
    assert numpty(["run"], ARGV)[1] == f"{Policy().names()}\n"


@pytest.mark.parametrize("names, expected", [
    ("FS_WRITE_LOCATION", ["FS_READ", "FS_WRITE_LOCATION"]),
    ("FS_READ,FS_WRITE", ["FS_READ", "FS_WRITE"]),
    ("FS_UNRESTRICTED", ["FS_UNRESTRICTED"]),
    ("NET_UNRESTRICTED", ["FS_READ", "NET_UNRESTRICTED"]),
    ("PROC_UNRESTRICTED", ["FS_READ", "PROC_UNRESTRICTED"]),
    ("PROC_C_EXTENSIONS", ["FS_READ", "PROC_C_EXTENSIONS"]),
    ("FS_WRITE_LOCATION,NET_UNRESTRICTED,PROC_UNRESTRICTED",
     ["FS_READ", "FS_WRITE_LOCATION", "NET_UNRESTRICTED", "PROC_UNRESTRICTED"]),
    ("UNRESTRICTED", ["FS_UNRESTRICTED", "NET_UNRESTRICTED", "PROC_UNRESTRICTED"]),
    ("FS_WRITE_LOCATION,FS_WRITE_LOCATION", ["FS_READ", "FS_WRITE_LOCATION"]),
])
def test_permission_names_reach_the_child(numpty, names, expected):
    assert numpty(["run", "-p", names], ARGV) == (0, f"{expected}\n", "")


@pytest.mark.parametrize("names", [["FS_READ_LOCATION_STRICT"], ["FS_READ_LOCATION", "NET_UNRESTRICTED"]])
def test_fill_leaves_given_dimension(names):
    assert _fill(names) == names


def test_write_location_alone_reads_and_writes_in_location(numpty, tmp_path):
    (tmp_path / "in.txt").write_text("x")
    code = "open('out.txt', 'w').write(open('in.txt').read() * 2)"
    assert numpty(["run", "-p", "FS_WRITE_LOCATION"], code)[0] == 0
    assert (tmp_path / "out.txt").read_text() == "xx"


def test_network_alone_keeps_read_only(numpty, tmp_path):
    (tmp_path / "in.txt").write_text("x")
    code, out, err = numpty(["run", "-p", "NET_UNRESTRICTED"], "print(open('in.txt').read()); open('a', 'w')")
    assert (code, out) == (126, "x\n")
    assert err.startswith("PermissionError:")


def test_passes_through_output_and_exit_code(numpty):
    code = "import sys; print('out'); print('err', file=sys.stderr); sys.exit(3)"
    assert numpty(["run"], code) == (3, "out\n", "err\n")


def test_timeout(numpty):
    code, _, err = numpty(["run", "-t", "0.5"], "import time; time.sleep(10)")
    assert code == 124 and "[timed out after 0.5s]" in err


def test_location(numpty, tmp_path):
    (tmp_path / "sub").mkdir()
    code, out, err = numpty(["run", "-p", "FS_WRITE_LOCATION", "-l", "sub"], "import os; print(os.getcwd())")
    assert (code, out.strip(), err) == (0, str((tmp_path / "sub").resolve()), "")


def test_location_without_location_permission_warns_and_runs(numpty):
    code, out, err = numpty(["run", "-l", "."], "print('ok')")
    assert (code, out) == (0, "ok\n")
    assert "warning" in err


@pytest.mark.parametrize("argv", [
    ["-p", "FS_READ", "-p", "FS_UNRESTRICTED"], ["-p", "FS_READ", "--permission", "FS_READ"],
    ["-l", ".", "-l", "/"], ["-t", "1", "-t", "100"],
])
def test_repeated_option_is_an_error(numpty, argv):
    with pytest.raises(SystemExit) as e:
        numpty(["run", *argv], "print('ran')")
    assert e.value.code == 2


@pytest.mark.parametrize("names", ["FS_EXECUTE", "READ", "NET_READ", "FS_WRITE_LOCATION_STRICT"])
def test_unknown_or_unenforceable_name_is_an_error(numpty, names):
    with pytest.raises(SystemExit) as e:
        numpty(["run", "-p", names], "print('ran')")
    assert e.value.code == 2


def test_missing_location_is_an_error(numpty):
    with pytest.raises(SystemExit) as e:
        numpty(["run", "-l", "missing"], "print('ran')")
    assert e.value.code == 2
