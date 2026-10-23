"""Other processes (helpers.subproc, PLAN.md 3.4 and 3.10): a bit of Python and what it printed, a copy of the
program, a running copy refused without its own test data folder, ending a process tree, and children ending with
the test process that started them, however it ends: those started through helpers.subproc, and (the verification,
V4) those a test process starts itself, a process pool's worker too, when the test process is killed half way."""
import os
import subprocess
import time

import pytest

from helpers import inner, paths, qt, session, subproc

pytest_plugins = ["pytester"]

# (an inner pytest's test: a child it starts itself and a worker of a process pool, as the app's fits start theirs,
# neither through helpers.subproc; their ids written in the inner check log, which is written at once; then the test
# process killed, as Task Manager's End task kills it: nothing of Python's runs after)
INNER_KILLED = '''
import concurrent.futures
import ctypes
import os
import subprocess
import sys


def test_starts_its_own_and_is_killed():
    from helpers import checks, subproc
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(600)"])
    pool = concurrent.futures.ProcessPoolExecutor(1)
    worker = pool.submit(os.getpid).result(timeout=120)
    checks.log({"event": "pids", "child": child.pid, "worker": worker, "contained": subproc.this_process})
    k32 = ctypes.WinDLL("kernel32")
    k32.GetCurrentProcess.restype = ctypes.c_void_p
    k32.TerminateProcess.argtypes = [ctypes.c_void_p, ctypes.c_uint]
    k32.TerminateProcess(k32.GetCurrentProcess(), 9)
'''


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
    # (the foundation's review: without the stand-in APO folder a copy would use the real one, where --uninstall
    # takes AutoEQ Studio's line out of config.txt; nor may it be given any of your real folders)
    S = session.SESSION
    real_apo = os.path.join(S.real_env.get("ProgramFiles") or "C:\\Program Files", "EqualizerAPO", "config")
    data = {"AUTOEQSTUDIO_DATA": os.path.join(tmp_path, "data")}
    without = {"no APO folder": session.child_env(AUTOEQSTUDIO_APO_CONFIG=None, **data),
               "the real APO folder": session.child_env(AUTOEQSTUDIO_APO_CONFIG=real_apo, **data),
               "no EQ Switcher stand-in": session.child_env(AUTOEQSTUDIO_OLD_SETTINGS=None, **data),
               "your real home": session.child_env(USERPROFILE=S.real_home, **data),
               "the real TEMP": session.child_env(TEMP=S.real_temp, **data),
               "the folders left out": session.child_env(without_folders=True, **data)}
    said = {}
    for what, env in without.items():
        try:
            subproc.RunningCopy(str(tmp_path), env)
            said[what] = "started"
        except ValueError:
            said[what] = "refused"
    build = os.path.join(tmp_path, "build")
    os.makedirs(build)
    open(os.path.join(build, "test-build.txt"), "w").close()
    build_ok = subproc.RunningCopy(build, session.child_env(AUTOEQSTUDIO_APO_CONFIG=None, **data))
    check("subproc: a running copy is refused without the stand-in APO folder or EQ Switcher's stand-in settings "
          "inside the test folders, or when given any real folder (home, TEMP); a test build may go without APO",
          all(v == "refused" for v in said.values()) and build_ok.app_dir == build, said)


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


@pytest.mark.timeout(300)
def test_test_process_takes_its_own_children_with_it(pytester, monkeypatch, check):
    # (the verification, V4: a test process started directly with pytest and ended half way, by a crash,
    # pytest-timeout's stop or a kill, while Make an EQ was fitting, left the fitting workers running, idle, until
    # ended by hand. tests\conftest.py now puts every test process in a job object of its own)
    result, log = inner.run(pytester, monkeypatch, {"test_inner_killed.py": INNER_KILLED}, "-q")
    got = next((r for r in log if r.get("event") == "pids"), {})
    pids = [got.get("child"), got.get("worker")]
    end = time.monotonic() + qt.time_limit(20)
    while any(p and session.process_alive(p) for p in pids) and time.monotonic() < end:
        time.sleep(0.2)
    alive = [p for p in pids if p and session.process_alive(p)]
    for pid in alive:  # (only when the check fails: nothing is left running either way)
        subproc.kill_tree(pid)
    check("subproc: a test process killed half way takes everything it started itself with it (a child, and a process "
          "pool's worker as the app's fits start them), from inside the job object a runner put it in",
          result.ret == 9 and all(pids) and not alive and (got.get("contained") or {}).get("in_job") is True,
          (result.ret, got, alive, result.errlines[-5:]))
