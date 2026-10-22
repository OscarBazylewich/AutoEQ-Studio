"""An inner pytest run, for the machinery's own tests (tests\\infra): a small test project in pytester's folder that
uses this project's real tests\\conftest.py and helpers, run in a process of its own (pytester's subprocess mode).
It has a session folder of its own (inside this run's), and a check log of its own: the inner run's deliberate
failures never reach this run's log.

    result, log = inner.run(pytester, monkeypatch, {"test_x.py": "def test_a(check): ..."}, "-q")

result is pytester's RunResult (ret, outlines, parseoutcomes()); log is the inner check log's lines, read back.
Only tests\\infra imports it (it's no pytest plugin, and no test loads it unless it asks for it).
"""
import json
import os

from helpers import paths


def run(pytester, monkeypatch, files, *args, timeout=300):
    """The inner project written (a conftest.py that runs tests\\conftest.py, pytest.ini's settings but its paths,
    the given test files), then pytest run on it with the check log in pytester's folder."""
    conftest = os.path.join(paths.TESTS, "conftest.py")
    pytester.makepyfile(conftest=(
        "import sys\n"
        f"sys.path[:0] = [{paths.TESTS!r}, {paths.TOOLS!r}]\n"
        f"with open({conftest!r}, encoding='utf-8') as _fh:\n"
        f"    exec(compile(_fh.read(), {conftest!r}, 'exec'))\n"))
    with open(os.path.join(paths.PROJECT, "pytest.ini"), encoding="utf-8") as fh:
        ini = [line for line in fh.read().splitlines() if not line.startswith(("pythonpath", "testpaths"))]
    pytester.makefile(".ini", pytest="\n".join(ini))
    for name, text in files.items():
        pytester.path.joinpath(name).write_text(text, encoding="utf-8")
    log = pytester.path / "inner-log.jsonl"
    with monkeypatch.context() as m:  # (only for the inner run: this test's own checks still go to this run's log)
        m.delenv("AUTOEQSTUDIO_TEST_OUT", raising=False)
        m.setenv("AUTOEQSTUDIO_CHECK_LOG", str(log))
        result = pytester.runpytest_subprocess(*args, timeout=timeout)
    lines = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()] if log.exists() else []
    return result, lines
