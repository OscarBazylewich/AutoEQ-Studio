"""The self-test's one command (app\\tools\\selftest.py, ".venv\\Scripts\\python.exe" app\\tools\\selftest.py
[--quick]): since the consolidation (2026-10-22) the front of app\\tools\\run_tests.py on the whole tests folder, its
options passed on as they are, a wrong command line refused (exit code 2) before anything runs. The runs themselves
are run_tests.py's (test_runner.py); the release tools' gate runs it (make_share_zip.selftest)."""
import os

from helpers import paths as project

# (for app\tools\relevant_tests.py: the tools these tests import through helpers.paths.import_tool)
COVERS = ("selftest", "run_tests")


def test_front_of_the_runner(check, monkeypatch):
    st = project.import_tool("selftest")
    calls = []
    monkeypatch.setattr(st.run_tests, "run", lambda paths, **kw: calls.append((list(paths), kw)) or 0)
    whole = [os.path.join(st.run_tests.PROJECT, "tests")]
    code = st.main(["--quick", "--all", "--out", "OUT", "--jobs", "3", "--timeout", "0.5", "--", "-x"])
    check("selftest.py: the whole tests folder through run_tests.py, with its options (--quick, --all, --out, --jobs, "
          "--timeout, and what follows -- for pytest)",
          code == 0 and calls == [(whole, {"quick": True, "jobs": 3, "out": "OUT", "show_all": True, "extra": ["-x"],
                                           "timeout": 0.5})], calls)
    calls.clear()
    default = st.main([])
    first = list(calls)
    bad = [st.main(args) for args in (["--nope"], ["--jobs", "0"], ["--timeout", "x"], ["tests/ui"])]
    check("selftest.py: with no options every test (Make an EQ's too); a wrong command line refused (exit code 2) "
          "before anything runs",
          default == 0 and len(first) == 1 and first[0][0] == whole and first[0][1]["quick"] is False
          and bad == [2, 2, 2, 2] and calls == first, (default, bad, calls))
