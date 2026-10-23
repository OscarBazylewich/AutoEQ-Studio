"""The test runner (app\\tools\\run_tests.py, PLAN.md 6.1): the parts found from the paths given, each part's
environment, the summary built from a made-up check log (ok, FAIL, skip, xfail and note lines; a process that ended
early; nothing to run), whole runs on a made-up project (each part in its own pytest process: a failing check, a
process ended at once, a part with only slow tests, a part over --timeout ended with the child it started, a failed
check whose detail runs over several lines counted once, and relevant_tests.py's quick run saying what --quick left
out), the job object, the command line, and the one FAIL line without pytest.

The made-up projects are in tmp_path: pytest.ini with the real one's settings, a tests\\conftest.py that runs the real
tests\\conftest.py (so the same session, guard and check log), and a few test files."""
import json
import os
import re
import subprocess
import sys
import time

import pytest

from helpers import checks, paths, qt, session, subproc

run_tests = paths.import_tool("run_tests")


# ---------------------------------------------------------------- a made-up project
def make_project(top, files):
    """pytest.ini (the real one's settings, without its paths), tests\\conftest.py running the real one, and the
    test files given ({"part/test_x.py": text})."""
    top = str(top)
    os.makedirs(os.path.join(top, "tests"), exist_ok=True)
    with open(os.path.join(paths.PROJECT, "pytest.ini"), encoding="utf-8") as fh:
        ini = [line for line in fh.read().splitlines() if not line.startswith(("pythonpath", "testpaths"))]
    with open(os.path.join(top, "pytest.ini"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(ini) + "\n")
    conftest = os.path.join(paths.TESTS, "conftest.py")
    with open(os.path.join(top, "tests", "conftest.py"), "w", encoding="utf-8") as fh:
        fh.write("import sys\n"
                 f"sys.path[:0] = [{paths.TESTS!r}, {paths.TOOLS!r}]\n"
                 f"with open({conftest!r}, encoding='utf-8') as _fh:\n"
                 f"    exec(compile(_fh.read(), {conftest!r}, 'exec'))\n")
    for name, text in files.items():
        path = os.path.join(top, "tests", *name.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
    return top


PASSING = '''
def test_one(check):
    check("made-up: one", True)


def test_two(check):
    check("made-up: two", 1 + 1 == 2)
'''

FAILING = '''
def test_fine(check):
    check("made-up: fine", True)


def test_broken(check):
    check("made-up: deliberately failing", False, "on purpose")
    check("made-up: still checked after", True)
'''

ENDS_AT_ONCE = '''
import os


def test_before(check):
    check("made-up: before the end", True)


def test_ends_the_process(check):
    check("made-up: just before", True)
    os._exit(0)


def test_never_reached(check):
    check("made-up: never reached", True)
'''

ALL_SLOW = '''
import pytest


@pytest.mark.slow
def test_slow(check):
    check("made-up: slow", True)
'''

SOME_SLOW = '''
import pytest


def test_quick_one(check):
    check("made-up: quick one", True)


@pytest.mark.slow
def test_slow_one(check):
    check("made-up: slow one", True)
'''

# (a failed check whose detail runs over several lines, as Ruff's report does)
MANY_LINES = '''
def test_report_over_several_lines(check):
    check("made-up: a report over several lines", False, "first line\\n    second line\\n\\nFound 1 error.")
'''

WAITS = '''
import json
import os
import subprocess
import sys
import time


def test_starts_a_child_and_waits(check):
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(600)"])
    with open(os.path.join(os.environ["AUTOEQSTUDIO_TEST_OUT"], "pids.json"), "w") as fh:
        json.dump({"test": os.getpid(), "child": child.pid}, fh)
    check("made-up: the child started", True)
    time.sleep(600)
'''


def logs_place(text):
    """The output folder the run named in its first line."""
    m = re.search(r"^Running the tests: .*each part's log: (.+)\)\s*$", text, re.M)
    return m.group(1) if m else ""


# ---------------------------------------------------------------- the parts
def test_parts(tmp_path, check):
    top = str(tmp_path)
    for name in ("tests/a/test_x.py", "tests/a/sub/test_y.py", "tests/b/test_z.py", "tests/helpers/test_h.py",
                 "tests/fixtures/db/test_f.py", "tests/empty/readme.txt", "tests/test_loose.py", "tests/conftest.py",
                 "app/start.py"):
        path = os.path.join(top, *name.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "w").close()
    whole = run_tests.find_parts(["tests"], top, cwd=top)
    some = run_tests.find_parts(["tests/a/sub/test_y.py::test_q", os.path.join(top, "tests", "b", "test_z.py"),
                                 "tests\\b\\test_z.py"], top, cwd=top)
    once = run_tests.find_parts(["tests/a/test_x.py", "tests/a"], top, cwd=top)
    default = run_tests.find_parts([], top, cwd=str(tmp_path / "tests" / "a"))  # (from another folder: the project's)
    refused = []
    for bad in ("tests/helpers", "tests/fixtures/db/test_f.py", "tests/nothere", "app", "tests::test_x"):
        try:
            run_tests.find_parts([bad], top, cwd=top)
        except ValueError as e:
            refused.append(str(e))
    check("test runner: each path goes in its part, the first folder under tests (a file, a folder, one test by its "
          "name, a full path); the whole tests folder is every part that has tests",
          whole == {"a": ["tests/a"], "b": ["tests/b"], "tests": ["tests/test_loose.py"]}
          and some == {"a": ["tests/a/sub/test_y.py::test_q"], "b": ["tests/b/test_z.py"]} and default == whole,
          (whole, some, default))
    check("test runner: tests\\helpers and tests\\fixtures are never parts, and a part's own folder given isn't run "
          "twice", once == {"a": ["tests/a"]} and "helpers" not in whole and "fixtures" not in whole, (once, whole))
    check("test runner: a path that isn't a test folder or file of the project is refused in plain words",
          len(refused) == 5 and "holds no tests" in refused[0] and "no such test folder or file" in refused[2]
          and "isn't in the tests folder" in refused[3], refused)


def test_part_environment(tmp_path, monkeypatch, check):
    out = str(tmp_path)
    cpus = os.cpu_count() or 1
    side = run_tests.part_env("eq", out, 4, base={"PATH": "x"})
    alone = run_tests.part_env("eq", out, 1, base={})
    kept = run_tests.part_env("eq", out, 4, base={"AUTOEQSTUDIO_MAX_WORKERS": "3", "AUTOEQSTUDIO_TIME_FACTOR": "5",
                                                   "AUTOEQSTUDIO_CHECK_LOG": "elsewhere.jsonl"})
    check("test runner: each part gets its own check log, the runner's output folder, and Python's settings (no "
          "bytecode files, UTF-8 output, a crash's report)",
          side["AUTOEQSTUDIO_CHECK_LOG"] == os.path.join(out, "eq.jsonl") and side["AUTOEQSTUDIO_TEST_OUT"] == out
          and kept["AUTOEQSTUDIO_CHECK_LOG"] == os.path.join(out, "eq.jsonl") and side["PATH"] == "x"
          and all(side[k] == v for k, v in (("PYTHONDONTWRITEBYTECODE", "1"), ("PYTHONIOENCODING", "utf-8"),
                                            ("PYTHONFAULTHANDLER", "1"))), side)
    check("test runner: the worker cap and the time factor are kept when they're set, else set (the cap from the "
          "cores and the parts side by side, the time factor 2 only for parts side by side)",
          kept["AUTOEQSTUDIO_MAX_WORKERS"] == "3" and kept["AUTOEQSTUDIO_TIME_FACTOR"] == "5"
          and side["AUTOEQSTUDIO_MAX_WORKERS"] == str(max(1, min(4, cpus // 8)))
          and alone["AUTOEQSTUDIO_MAX_WORKERS"] == str(max(1, min(4, cpus // 2)))
          and side["AUTOEQSTUDIO_TIME_FACTOR"] == "2" and "AUTOEQSTUDIO_TIME_FACTOR" not in alone, (side, alone, kept))
    jobs = []
    for value in ("3", "x", "0", None):
        if value is None:
            monkeypatch.delenv("AUTOEQSTUDIO_TEST_JOBS", raising=False)
        else:
            monkeypatch.setenv("AUTOEQSTUDIO_TEST_JOBS", value)
        jobs.append(run_tests.default_jobs())
    usual = max(1, min(4, cpus // 4))
    check("test runner: how many parts run at once: AUTOEQSTUDIO_TEST_JOBS when it's a number, else a quarter of the "
          "cores (1 to 4)", jobs == [3, usual, usual, usual], jobs)


# ---------------------------------------------------------------- the summary, from a made-up log
def _start(t):
    return {"event": "start", "test": t}


def _report(t, when, outcome="passed", message=""):
    return {"event": "report", "test": t, "when": when, "outcome": outcome, "duration": 0.01, "message": message}


def _check(t, name, ok=True, detail=""):
    return {"event": "check", "test": t, "name": name, "ok": ok, "detail": detail}


def _passed(t, *checks):
    return [_start(t), _report(t, "setup"), *[_check(t, c) for c in checks], _report(t, "call"),
            _report(t, "teardown")]


T = "tests/eq/test_made_up.py::"
STRAY = qt.STRAY_CHECK


def test_summary_of_a_part_that_passed(check):
    log = [{"event": "session", "pid": 1, "root": "x", "python": "y"}, *_passed(T + "a", "one", "two"),
           *_passed(T + "b", "three")]
    res = run_tests.summarize("switcher", log, 0, seconds=2.34)
    check("test runner: a part that passed is one ok line: its checks, its tests and its time",
          res.lines() == ["ok   switcher: 3 checks in 2 tests (2.3 s)"] and not res.fails and not res.skips
          and not res.notes, res.lines())
    check("test runner: times are said in seconds, or minutes and seconds",
          run_tests.duration(2.34) == "2.3 s" and run_tests.duration(171) == "2 min 51 s", run_tests.duration(171))


def test_summary_of_failures_skips_and_notes(check):
    log = [
        {"event": "session", "pid": 1, "root": "x", "python": "y"},
        _start(T + "checks"), _report(T + "checks", "setup"), _check(T + "checks", "eq: fine"),
        _check(T + "checks", "eq: numbers kept within their limits", False, "too big"),
        _report(T + "checks", "call", "failed", "FAIL eq: numbers kept within their limits  (too big)"),
        _report(T + "checks", "teardown"),
        _start(T + "plain"), _report(T + "plain", "setup"), _report(T + "plain", "call", "failed", "assert 1 == 2"),
        _report(T + "plain", "teardown"),
        _start(T + "setup"), _report(T + "setup", "setup", "failed", "RuntimeError: the fixture broke"),
        _report(T + "setup", "teardown"),
        _start(T + "guarded"), _report(T + "guarded", "setup"), _report(T + "guarded", "call"),
        _report(T + "guarded", "teardown", "failed", T + "guarded: a write outside the test folders (open: C:\\x)"),
        _start(T + "known"), _report(T + "known", "setup"), _check(T + "known", "eq: the known bug", False, "still"),
        _report(T + "known", "call", "xfailed", "a known bug"), _report(T + "known", "teardown"),
        _start(T + "skipped"), _report(T + "skipped", "setup"),
        {"event": "check", "test": T + "skipped", "name": "eq: installer compiles", "ok": None, "skipped": True,
         "detail": "Inno Setup 6 isn't installed here"},
        _report(T + "skipped", "call", "skipped", "Inno Setup 6 isn't installed here"),
        _report(T + "skipped", "teardown"),
        _start(T + "qt"), _report(T + "qt", "setup"),
        {"event": "qt_error", "test": T + "qt", "text": "RuntimeError: already deleted"},
        {"event": "qt_error", "test": T + "qt", "text": "RuntimeError: already deleted"},
        _report(T + "qt", "call"),
        {"event": "allowed_strays", "test": T + "qt", "reason": "Find's rows", "found": [["QPushButton 'Show'", 3]]},
        _report(T + "qt", "teardown"),
        _start(T + "stray"), _report(T + "stray", "setup"), _report(T + "stray", "call"),
        _check(T + "stray", STRAY, False, "[('QLabel', 1)]"),
        _report(T + "stray", "teardown", "failed", f"FAIL {STRAY}  (shown during this test: [('QLabel', 1)])"),
        {"event": "guard", "test": T + "stray", "blocked": [T + "stray: a connection to example.com", "another"]},
    ]
    res = run_tests.summarize("eq", log, 1, seconds=5)
    fails = res.fails
    check("test runner: a failed check is one FAIL line naming its test, and the test's failure because of it isn't "
          "counted again",
          fails[0] == f"FAIL eq: eq: numbers kept within their limits  (too big)  [{T}checks]"
          and sum(T + "checks" in f for f in fails) == 1, fails)
    check("test runner: a test that failed with no failed check is one FAIL line with its message (and an error "
          "before or after a test, e.g. the guard's, too)",
          fails[1] == f"FAIL eq: the test failed: assert 1 == 2  [{T}plain]"
          and fails[2] == f"FAIL eq: an error before the test ran (in setting it up): RuntimeError: the fixture broke"
                          f"  [{T}setup]"
          and fails[3].startswith("FAIL eq: an error after the test (in its clean-up): ")
          and "a write outside the test folders" in fails[3], fails)
    check("test runner: a stray window's failed check is one FAIL line, and the guard's line after the last test is "
          "one more",
          fails[4] == f"FAIL eq: {STRAY}  ([('QLabel', 1)])  [{T}stray]"
          and fails[5] == f"FAIL eq: the test guard blocked, after the last test: {T}stray: a connection to "
                          f"example.com (and 1 more)  [{T}stray]" and len(fails) == 6, fails)
    check("test runner: a skipped test is a skip line with its reason; a test marked xfail that failed is an xfail "
          "line, and its failed checks are no failure",
          res.skips == [f"xfail {T}known: a known bug", f"skip {T}skipped: Inno Setup 6 isn't installed here"]
          and not any("known bug" in f for f in fails), res.skips)
    check("test runner: an error inside a Qt call-back is a note, not a failure (repeats counted), and so is a stray "
          "window an allow_strays mark let pass",
          res.notes == [f"note {T}qt: shown as windows of their own, allowed by its allow_strays mark (Find's rows): "
                        "QPushButton 'Show' (3 times)",
                        f"note {T}qt: an error inside a Qt call-back (not a failure): RuntimeError: already deleted "
                        "(2 times)"], res.notes)
    every = res.lines(show_all=True)
    check("test runner: --all prints every check's own line first (ok, FAIL, xfail, skip), then the part's lines",
          every[:6] == ["ok   eq: fine", "FAIL eq: numbers kept within their limits  (too big)",
                        "xfail eq: the known bug  (still)",
                        "skip eq: installer compiles  (Inno Setup 6 isn't installed here)",
                        f"FAIL {STRAY}  ([('QLabel', 1)])", fails[0]] and every[5:] == fails, every)
    check("test runner: the counts are the checks that ran and the tests started",
          res.checks == 4 and res.tests == 8, (res.checks, res.tests))


def test_summary_of_a_process_that_ended_early(check):
    txt = "C:\\out\\eq.txt"
    early = [*_passed(T + "a", "one"), _start(T + "b"), _report(T + "b", "setup"), _check(T + "b", "two")]
    timeout_output = "...\n" + "+" * 20 + " Timeout " + "+" * 20 + "\nstack\n"
    ended = run_tests.summarize("eq", early, 1, txt=txt, output=timeout_output)
    at_once = run_tests.summarize("eq", early, 0, txt=txt)
    check("test runner: a part whose process ended mid-test (pytest-timeout's stop, os._exit) is one FAIL line naming "
          "the last test started, whatever its exit code",
          ended.fails == [f"FAIL eq: the test process ended without finishing (a test ran past its time limit; exit "
                          f"code 1; last test started: {T}b; see {txt})"]
          and at_once.fails == [f"FAIL eq: the test process ended without finishing (exit code 0; last test started: "
                                f"{T}b; see {txt})"], (ended.fails, at_once.fails))
    collect = ("=== ERRORS ===\n____ ERROR collecting tests/eq/test_bad.py ____\nTraceback\n"
               "E   ModuleNotFoundError: No module named 'nothere'\n=== short test summary info ===\n"
               "ERROR tests/eq/test_bad.py\n!!! Interrupted: 1 error during collection !!!\n")
    stopped = run_tests.summarize("eq", [{"event": "session"}], 2, txt=txt, output=collect)
    usage = run_tests.summarize("eq", [], 4, txt=txt, output="ERROR: file or directory not found: tests/x\n")
    check("test runner: pytest stopping before any test (a test file that can't be read, a wrong argument) is one "
          "FAIL line with the error",
          stopped.fails == [f"FAIL eq: pytest stopped before running any test (exit code 2: tests/eq/test_bad.py: "
                            f"ModuleNotFoundError: No module named 'nothere'; see {txt})"]
          and usage.fails == [f"FAIL eq: pytest stopped before running any test (exit code 4: file or directory not "
                              f"found: tests/x; see {txt})"], (stopped.fails, usage.fails))
    nothing = run_tests.summarize("eq_screen", [{"event": "session"}], 5, quick=True)
    empty = run_tests.summarize("misc", [{"event": "session"}], 5)
    check("test runner: pytest's exit code 5 (no test collected) is a part with nothing to run, said in one line, "
          "and no failure",
          nothing.lines() == ["ok   eq_screen: nothing to run (every test here is slow, and --quick leaves those out)"]
          and not nothing.fails and empty.lines() == ["ok   misc: nothing to run (pytest found no test to run here)"],
          (nothing.lines(), empty.lines()))
    over = run_tests.summarize("eq", _passed(T + "a") + [_start(T + "b")], None, txt=txt, timed_out=True, timeout=0.5)
    check("test runner: a part past --timeout is one FAIL line saying so, with the last test started",
          over.fails == [f"FAIL eq: still running after 30.0 s (--timeout), so it was ended with everything it "
                         f"started (last test started: {T}b; see {txt})"], over.fails)
    crash = run_tests.summarize("eq", _passed(T + "a"), 3221225477, txt=txt,
                                output="Windows fatal exception: access violation\n")
    quiet = run_tests.summarize("eq", _passed(T + "a"), 1, txt=txt)
    check("test runner: an exit code the log doesn't explain is never taken for a pass (a crash after the last test, "
          "exit code 1 with no failure logged)",
          crash.fails == [f"FAIL eq: the test process ended badly after its last test (exit code 3221225477 "
                          f"(0xC0000005); Windows fatal exception: access violation; see {txt})"]
          and quiet.fails == [f"FAIL eq: pytest says something failed (exit code 1), but its check log shows no "
                              f"failure; see {txt}"], (crash.fails, quiet.fails))


def test_log_read_line_by_line(tmp_path, check):
    path = tmp_path / "part.jsonl"
    path.write_text('{"event": "start", "test": "a"}\nnot json\n[1, 2]\n{"event": "check", "test": "a", "na',
                    encoding="utf-8")
    check("test runner: the check log is read line by line, and a line cut short (a process ended mid-write) is left "
          "out", run_tests.read_log(str(path)) == [{"event": "start", "test": "a"}]
          and run_tests.read_log(str(tmp_path / "none.jsonl")) == [], run_tests.read_log(str(path)))


# ---------------------------------------------------------------- whole runs, on a made-up project
@pytest.mark.timeout(600)
def test_whole_runs(tmp_path, capsys, check):
    proj = make_project(tmp_path / "proj", {"good/test_good.py": PASSING, "bad/test_bad.py": FAILING,
                                            "ends/test_ends.py": ENDS_AT_ONCE, "slow/test_slow.py": ALL_SLOW})
    code = run_tests.run([], quick=True, jobs=2, root=proj)
    text = capsys.readouterr().out
    lines = text.strip().splitlines()
    kept = logs_place(text)
    check("test runner: each part runs in a pytest process of its own, and each says ok or FAIL",
          re.search(r"^ok   good: 2 checks in 2 tests \(", text, re.M) is not None
          and lines[0].startswith("Running the tests: 4 parts, 2 at a time"), text)
    check("test runner: a failing check's FAIL line names it and its test; the run then ends \"<n> check(s) "
          "failed.\" with exit code 1",
          "FAIL bad: made-up: deliberately failing  (on purpose)  [tests/bad/test_bad.py::test_broken]" in lines
          and lines[-1] == "2 check(s) failed." and code == 1, text)
    check("test runner: a test process that ends at once (os._exit) is one FAIL line naming the last test started",
          sum(line.startswith("FAIL ends:") for line in lines) == 1
          and any(line.startswith("FAIL ends: the test process ended without finishing (exit code 0; last test "
                                  "started: tests/ends/test_ends.py::test_ends_the_process;") for line in lines), text)
    check("test runner: with --quick a part whose every test is slow says it has nothing to run, and that's no "
          "failure",
          "ok   slow: nothing to run (every test here is slow, and --quick leaves those out)" in lines
          and not any(line.startswith("FAIL slow") for line in lines), text)
    check("test runner: when something failed, the temporary logs are kept and their place said; the totals count "
          "the checks that ran, the tests started and the parts",
          bool(kept) and os.path.isfile(os.path.join(kept, "bad.txt"))
          and os.path.isfile(os.path.join(kept, "bad.jsonl")) and f"The logs are kept: {kept}" in text
          and lines[-2].startswith("7 checks, 6 tests, 4 parts, "), (kept, lines[-3:]))

    capsys.readouterr()  # (the checks' own lines so far left out)
    code = run_tests.run(["tests/good", "tests/bad/test_bad.py::test_fine"], jobs=1, root=proj,
                         extra=["-k", "one or fine"])
    text = capsys.readouterr().out
    gone = logs_place(text)
    check("test runner: when everything passed the last line is \"All checks passed.\" with exit code 0, and the "
          "temporary logs are deleted; one test by its name and pytest's own arguments work",
          code == 0 and text.strip().splitlines()[-1] == "All checks passed." and bool(gone)
          and not os.path.exists(gone) and "ok   good: 1 check in 1 test (" in text
          and "ok   bad: 1 check in 1 test (" in text, text)

    out = os.path.join(str(tmp_path), "logs")
    capsys.readouterr()
    code = run_tests.run(["tests/good"], out=out, show_all=True, root=proj)
    text = capsys.readouterr().out
    check("test runner: --out keeps the logs there (each part's output and check log), and --all shows every check's "
          "own line",
          code == 0 and os.path.isfile(os.path.join(out, "good.txt")) and os.path.isfile(os.path.join(out,
                                                                                                   "good.jsonl"))
          and "ok   made-up: one\nok   made-up: two\nok   good: 2 checks in 2 tests" in text, text)


@pytest.mark.timeout(600)
def test_detail_over_several_lines_counted_once(tmp_path, capsys, check):
    # (the verification, V2: Ruff's report, a detail over several lines, made the summary count one failure twice:
    # the test's own failure ended with the report's last line, so it wasn't known as the checks')
    proj = make_project(tmp_path / "proj", {"lint/test_lint_like.py": MANY_LINES})
    code = run_tests.run(["tests/lint"], jobs=1, root=proj)
    lines = capsys.readouterr().out.strip().splitlines()
    fails = [line for line in lines if line.startswith("FAIL")]
    br = checks.LINE_BREAK
    check("test runner: a failed check whose detail runs over several lines (Ruff's report) is one FAIL line, the "
          "detail on it, and counted once",
          code == 1 and lines[-1] == "1 check(s) failed." and fails == [
              f"FAIL lint: made-up: a report over several lines  (first line{br}second line{br}Found 1 error.)  "
              "[tests/lint/test_lint_like.py::test_report_over_several_lines]"], lines)


@pytest.mark.timeout(600)
def test_quick_run_says_what_it_left_out(tmp_path, capsys, check):
    # (the verification, V2: relevant_tests.py --run --quick said "All checks passed." for a change only slow tests
    # check, e.g. the Guide's: every one of them was left out)
    proj = make_project(tmp_path / "proj", {"good/test_good.py": PASSING, "slow/test_slow.py": ALL_SLOW,
                                            "some/test_some.py": SOME_SLOW})
    said = {}
    for name, chosen, kw in (("chosen", [], {"say_left_out": True}), ("self-test", [], {}),
                             ("none slow", ["tests/good"], {"say_left_out": True}),
                             ("only slow", ["tests/slow"], {"say_left_out": True})):
        capsys.readouterr()
        code = run_tests.run(chosen, quick=True, jobs=3, root=proj, **kw)
        said[name] = (code, capsys.readouterr().out.strip().splitlines())
    code, lines = said["chosen"]
    note = run_tests.left_out_note(2)
    check("test runner: relevant_tests.py's quick run says how many of the chosen tests --quick left out as slow, in a "
          "note before the last line, and then ends \"All the checks that ran passed.\"",
          code == 0 and lines[-2:] == [note, "All the checks that ran passed."]
          and note.startswith("note: 2 of the chosen tests are slow") and "run without --quick before" in note,
          lines[-4:])
    (code_st, lines_st), (code_none, lines_none) = said["self-test"], said["none slow"]
    check("test runner: the self-test's quick run (selftest.py --quick, which the zip and installer gates run) and a "
          "quick run that left nothing out still end \"All checks passed.\", with no note",
          code_st == 0 and lines_st[-1] == "All checks passed." and code_none == 0
          and lines_none[-1] == "All checks passed." and not any(line.startswith("note:") for line in lines_st + lines_none),
          (lines_st[-3:], lines_none[-3:]))
    code_slow, lines_slow = said["only slow"]
    check("test runner: when every chosen test was slow, the note comes before \"Nothing ran\"",
          code_slow == 0 and lines_slow[-2:] == [run_tests.left_out_note(1), "Nothing ran: no test was left to run."]
          and run_tests.left_out_note(1).startswith("note: 1 of the chosen tests is slow"), lines_slow[-3:])


@pytest.mark.timeout(600)
def test_timeout_ends_everything(tmp_path, capsys, check):
    proj = make_project(tmp_path / "proj", {"waits/test_waits.py": WAITS})
    out = os.path.join(str(tmp_path), "out")
    minutes = qt.time_limit(0.1)  # (6 s, more on a busy PC: time for the part to start its child)
    code = run_tests.run(["tests/waits"], out=out, timeout=minutes, root=proj)
    text = capsys.readouterr().out
    try:
        with open(os.path.join(out, "pids.json"), encoding="utf-8") as fh:
            pids = json.load(fh)
    except (OSError, ValueError):
        pids = {}
    end = time.monotonic() + qt.time_limit(10)
    while any(session.process_alive(p) for p in pids.values()) and time.monotonic() < end:
        time.sleep(0.2)
    alive = [p for p in pids.values() if session.process_alive(p)]
    for pid in alive:  # (only if the check below fails: nothing is left running either way)
        subproc.kill_tree(pid)
    check("test runner: a part over --timeout is ended with everything it started (its pytest process and the child "
          "its test started both gone), and the run says so",
          code == 1 and len(pids) == 2 and not alive
          and "FAIL waits: still running after" in text
          and "last test started: tests/waits/test_waits.py::test_starts_a_child_and_waits" in text, (pids, alive, text))


def test_job_object_ends_its_processes(check):
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(600)"], stdin=subprocess.DEVNULL)
    job = run_tests.Job()
    try:
        added = job.add(proc.pid)
        active = job.active()
        job.close()
        try:
            proc.wait(qt.time_limit(20))
        except subprocess.TimeoutExpired:
            pass
        ended = proc.poll() is not None
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(20)
    check("test runner: a part's job object ends the processes in it when it's closed (Windows' "
          "JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE)", added and active == 1 and ended and job.error is None,
          (added, active, ended, job.error))


# ---------------------------------------------------------------- the command line
def test_command_line(monkeypatch, check):
    got = []
    monkeypatch.setattr(run_tests, "run", lambda *a, **k: got.append((a, k)) or 7)
    code = run_tests.main(["tests/eq", "tests/ui", "--quick", "--jobs", "3", "--out", "logs", "--all", "--timeout",
                           "0.5", "--", "-k", "theme", "-x"])
    plain = run_tests.main([])
    check("test runner: the command line reaches the run (the paths, --quick, --jobs, --out, --all, --timeout, and "
          "pytest's own arguments after --), and its exit code is the run's",
          code == 7 and plain == 7 and got[0] == ((["tests/eq", "tests/ui"],), {
              "quick": True, "jobs": 3, "out": "logs", "show_all": True, "extra": ["-k", "theme", "-x"],
              "timeout": 0.5}) and got[1][1]["timeout"] == 30.0 and got[1][1]["jobs"] is None, got)
    wrong = [run_tests.main(args) for args in (["--jobs", "0"], ["--timeout", "0"], ["--timeout", "soon"],
                                               ["--nothing"])]
    check("test runner: a wrong command line (no number of parts, no minutes, an unknown option) exits with 2",
          wrong == [2, 2, 2, 2] and len(got) == 2, wrong)


def test_without_pytest(check):
    code = ("import runpy, sys\n"
            "sys.modules['pytest'] = None  # (as if pytest weren't installed: importing it fails)\n"
            "script = sys.argv[1]\n"
            "sys.argv = [script, 'tests/switcher']\n"
            "runpy.run_path(script, run_name='__main__')\n")
    out = subproc.run_python(code, os.path.join(paths.TOOLS, "run_tests.py"), cwd=paths.PROJECT)
    lines = out.stdout.strip().splitlines()
    check("test runner: without pytest it says so in one line starting FAIL (how to install it) and exits with 1",
          out.returncode == 1 and len(lines) == 1 and lines[0] == run_tests.NO_PYTEST
          and lines[0].startswith("FAIL pytest isn't installed here")
          and "requirements-dev.txt" in lines[0], (out.returncode, out.stdout[-500:], out.stderr[-500:]))
