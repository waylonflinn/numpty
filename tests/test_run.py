import os
import time

import pytest

from numpty import Policy, RunTool, Tool
from numpty.run import run

pytest.importorskip("fastaudit")

FS = Policy.Filesystem
WRITE_LOCATION = Policy(FS.READ | FS.WRITE_LOCATION)


def test_run_returns_output(tmp_path):
    p = run("import sys; print('out'); print('err', file=sys.stderr)", location=str(tmp_path))
    assert (p.returncode, p.stdout, p.stderr) == (0, "out\n", "err\n")


def test_run_starts_in_location(tmp_path):
    assert run("import os; print(os.getcwd())", location=str(tmp_path)).stdout.strip() == str(tmp_path.resolve())


def test_default_policy_denies_write_with_reason(tmp_path):
    p = run("open('a.txt', 'w')", location=str(tmp_path))
    assert p.returncode == 126
    assert p.stderr.startswith("PermissionError:") and "a.txt" in p.stderr
    assert not (tmp_path / "a.txt").exists()


def test_write_location_allows_write_in_location(tmp_path):
    p = run("open('a.txt', 'w').write('x')", WRITE_LOCATION, str(tmp_path))
    assert p.returncode == 0
    assert (tmp_path / "a.txt").read_text() == "x"


def test_write_location_denies_write_outside(tmp_path):
    (tmp_path / "cwd").mkdir()
    p = run("open('../a.txt', 'w')", WRITE_LOCATION, str(tmp_path / "cwd"))
    assert p.returncode == 126
    assert not (tmp_path / "a.txt").exists()


def test_timeout_keeps_output(tmp_path):
    p = run("import time; print('started'); time.sleep(10)", location=str(tmp_path), timeout=0.5)
    assert p.returncode == 124
    assert p.stdout == "started\n"
    assert p.stderr.endswith("[timed out after 0.5s]\n")


def test_timeout_kills_children(tmp_path):
    code = "import subprocess, time; print(subprocess.Popen(['sleep', '30']).pid); time.sleep(10)"
    p = run(code, Policy.UNRESTRICTED, str(tmp_path), timeout=1)
    assert p.returncode == 124
    pid = int(p.stdout)
    for _ in range(50):   # the orphan is reaped by init
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return
        time.sleep(0.05)
    os.kill(pid, 9)
    raise AssertionError("child of the timed-out process still runs")


def test_os_exit_code_and_output_kept(tmp_path):
    p = run("import os; print('before'); os._exit(3)", location=str(tmp_path))
    assert (p.returncode, p.stdout) == (3, "before\n")


def test_sys_exit_code(tmp_path):
    assert run("import sys; sys.exit(5)", location=str(tmp_path)).returncode == 5


def test_exception_traceback_shows_code_frames_only(tmp_path):
    p = run("x = 1\n1/0\n", location=str(tmp_path))
    assert p.returncode == 1
    assert p.stderr.startswith("Traceback")
    assert 'File "<run>", line 2' in p.stderr and "1/0" in p.stderr
    assert "_child" not in p.stderr and "numpty" not in p.stderr
    assert p.stderr.rstrip().endswith("ZeroDivisionError: division by zero")


def test_syntax_error(tmp_path):
    p = run("def f(:", location=str(tmp_path))
    assert p.returncode == 1
    assert "SyntaxError" in p.stderr and "_child" not in p.stderr


def test_os_permission_error_is_not_a_denial(tmp_path):
    locked = tmp_path / "locked"
    locked.mkdir(mode=0o500)
    try:
        p = run("open('locked/a.txt', 'w')", Policy.UNRESTRICTED, str(tmp_path))
    finally:
        locked.chmod(0o700)
    assert p.returncode == 1
    assert "Errno 13" in p.stderr


def test_location_modules_do_not_replace_bootstrap(tmp_path):
    hijack = "open('hijacked', 'w').close()\n"
    (tmp_path / "fastaudit.py").write_text(hijack)
    (tmp_path / "numpty").mkdir()
    (tmp_path / "numpty" / "__init__.py").write_text(hijack)
    p = run("print('ok')", WRITE_LOCATION, str(tmp_path))
    assert (p.returncode, p.stdout) == (0, "ok\n")
    assert not (tmp_path / "hijacked").exists()


def test_location_module_importable(tmp_path):
    (tmp_path / "helper.py").write_text("X = 7\n")
    assert run("import helper; print(helper.X)", location=str(tmp_path)).stdout == "7\n"


def test_default_policy_denies_process(tmp_path):
    p = run("import subprocess; subprocess.run(['true'])", location=str(tmp_path))
    assert p.returncode == 126


def test_unrestricted_can_start_process(tmp_path):
    p = run("import subprocess; print(subprocess.run(['echo', 'hi'], capture_output=True, text=True).stdout)",
            Policy.UNRESTRICTED, str(tmp_path))
    assert (p.returncode, p.stdout) == (0, "hi\n\n")


def test_run_tool_is_a_tool():
    tool = RunTool(timeout=5)
    assert isinstance(tool, Tool)
    assert tool.name == "run" and "5s" in tool.description


def test_run_tool_returns_stdout(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert RunTool().run({"code": "print('hi')"}) == "hi\n"


def test_run_tool_default_policy_denies(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    out = RunTool().run({"code": "print('a'); open('a.txt', 'w')"})
    assert out.startswith("a\n\n[exit 126]\nPermissionError:")
    assert not (tmp_path / "a.txt").exists()


def test_run_tool_passes_policy(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert RunTool().run({"code": "open('a.txt', 'w')"}, policy=WRITE_LOCATION) == ""
    assert (tmp_path / "a.txt").exists()


def test_run_tool_timeout(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    out = RunTool(timeout=0.5).run({"code": "import time; time.sleep(10)"})
    assert "[exit 124]" in out and "[timed out after 0.5s]" in out


def test_run_tool_truncates_to_max_output(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    out = RunTool(max_output=100).run({"code": "print('x' * 500)"})
    assert len(out) == 100 and "TRUNCATED" in out
