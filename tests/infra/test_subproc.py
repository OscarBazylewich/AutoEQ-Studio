"""Other processes (helpers.subproc, PLAN.md 3.4 and 3.10): a bit of Python and what it printed, a copy of the
program, a running copy refused without its own test data folder, ending a process tree, and children ending with
the test process that started them, however it ends."""
import os
import subprocess
import time

import pytest

from helpers import paths, session, subproc


def test_run_python(check):
    out = subproc.run_python("import json, os, sys; print('a line'); print(json.dumps({'a': 1, 'arg': sys.argv[1], "
                             "'data': os.environ.get('AUTOEQSTUDIO_DATA'), "
                             "'log': os.environ.get('AUTOEQSTUDIO_CHECK_LOG')}))", "x", env={"EXTRA": "1"})
    d = out.data or {}
    check("subproc: run_python runs a bit of Python in the session's environment (never the check log) and reads the "
          "last line it printed as JSON",
          out.returncode == 0 and d.get("a") == 1 and d.get("arg") == "x" and d.get("data") == session.SESSION.data
          and d.get("log") is None and "a line" in out.stdout, (out.returncode, out.stdout[-300:], out.stderr[-300:]))


def test_app_copy(tmp_path, check):
    plain = subproc.app_copy(os.path.join(tmp_path, "plain"))
    inst = subproc.app_copy(os.path.join(tmp_path, "inst"), installed=True, test_build=True)
    names = set(os.listdir(plain))
    check("subproc: app_copy copies the program without its tools, caches and data; installed.txt and "
          "test-build.txt only when asked",
          os.path.isfile(os.path.join(plain, "start.py")) and "tools" not in names and "__pycache__" not in names
          and "data" not in names and "installed.txt" not in names and "test-build.txt" not in names
          and os.path.isfile(os.path.join(inst, "installed.txt")) and os.path.isfile(os.path.join(inst, "test-build.txt"))
          and os.path.basename(plain) == "app", sorted(names))


def test_running_copy_needs_its_own_data_folder(tmp_path, check):
    refused = []
    for env in ({k: v for k, v in os.environ.items() if k != "AUTOEQSTUDIO_DATA"},
                dict(os.environ, AUTOEQSTUDIO_DATA=os.path.join(paths.PROJECT, "data"))):
        try:
            subproc.RunningCopy(str(tmp_path), env)
        except ValueError:
            refused.append(True)
    ok = subproc.RunningCopy(str(tmp_path), dict(os.environ, AUTOEQSTUDIO_DATA=os.path.join(tmp_path, "data")))
    check("subproc: a running copy is refused without a test data folder of its own (none, or one outside the session)",
          refused == [True, True] and ok.start_py == os.path.join(str(tmp_path), "start.py"), refused)


def test_kill_tree(check):
    p = subproc.start_python("import subprocess, sys, time; subprocess.Popen([sys.executable, '-c', "
                             "'import time; time.sleep(120)']); time.sleep(120)")
    time.sleep(1)
    subproc.kill_tree(p.pid)
    try:
        p.wait(20)
        ended = True
    except subprocess.TimeoutExpired:
        ended = False
    check("subproc: kill_tree ends a process and what it started", ended and p.returncode is not None, p.returncode)


@pytest.mark.timeout(120)
def test_children_end_with_their_starter(check):
    # (a middle process starts a sleeper through helpers.subproc, says its id, and ends abruptly with os._exit, as
    # pytest-timeout ends a test process: the sleeper must end with it)
    code = ("import json, os, sys; sys.path[:0] = [sys.argv[1]]; from helpers import subproc\n"
            "p = subproc.start_python('import time; time.sleep(120)')\n"
            "print(json.dumps({'pid': p.pid}), flush=True)\n"
            "os._exit(3)\n")
    out = subproc.run_python(code, paths.TESTS)
    pid = (out.data or {}).get("pid")
    end = time.monotonic() + 20
    while pid and session.process_alive(pid) and time.monotonic() < end:
        time.sleep(0.2)
    alive = bool(pid) and session.process_alive(pid)
    if alive:
        subproc.kill_tree(pid)
    check("subproc: a process started through helpers.subproc ends when the process that started it ends abruptly",
          out.returncode == 3 and pid and not alive, (out.returncode, pid, alive, out.stderr[-300:]))

