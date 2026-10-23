r"""AutoEQ Studio's self-test: every test in the tests folder (pytest), each part in a process of its own, on
temporary folders and a temporary copy of the app (your own files, the real Equalizer APO folder, AppData, the
registry and the internet are never used; the windows are drawn off-screen). Run it after any change, and before
saying a piece of work is done:

    ".venv\Scripts\python.exe" "app\tools\selftest.py" [--quick] [--all] [--out DIR] [--jobs N] [--timeout MINUTES]

--quick    leaves out only the slow tests: Make an EQ's screen (the page and its windows, Listen's card, the
           tracer's window) and long fitting runs. Everything else runs, the zips', the installer's, the launcher's
           and the app's own start and quit included, so the release tools run it before making anything
           (make_share_zip.py, make_installer.py) and stop when it fails.
--all      also prints every check's own line, ok or FAIL.
--out DIR  keeps each part's logs in DIR (pytest's output and its check log); without it they're deleted when
           everything passed, and kept (their place printed) when not.
--jobs N   how many parts run at once (else a quarter of this PC's cores, 1 to 4).
--timeout  a part still running after this many minutes (default 30) is ended, with everything it started.

It prints a line per part: "ok" with its number of checks, or a FAIL line for each check that failed (naming its
test); then each skipped test with its reason, the totals, and last "All checks passed." or "<n> check(s) failed."
(exit code 0 or 1; 2 for a wrong command line). Without pytest it says so in one FAIL line: the tests need
app\requirements-dev.txt (".venv\Scripts\python.exe" -m pip install -r app\requirements-dev.txt).

It is app\tools\run_tests.py on the whole tests folder. While working, run only the tests a change needs:
    ".venv\Scripts\python.exe" app\tools\relevant_tests.py --run --quick
or one test file: ".venv\Scripts\python.exe" -m pytest tests\<part>\test_<name>.py
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import run_tests  # noqa: E402


def _jobs(text):
    try:
        value = int(text)
    except ValueError:
        value = 0
    if value < 1:
        raise argparse.ArgumentTypeError(f"not a number of parts at once (1 or more): {text}")
    return value


def _minutes(text):
    try:
        value = float(text)
    except ValueError:
        value = 0.0
    if not value > 0:
        raise argparse.ArgumentTypeError(f"not a number of minutes above 0 (e.g. 30, or 0.5): {text}")
    return value


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    extra = []
    if "--" in argv:  # (anything after -- goes to pytest as it is, e.g. -- -x)
        at = argv.index("--")
        argv, extra = argv[:at], argv[at + 1:]
    parser = argparse.ArgumentParser(prog="selftest.py", description="AutoEQ Studio's self-test: every test, each "
                                     "part in its own process, with a short summary.",
                                     epilog="Anything after -- goes to pytest.")
    parser.add_argument("--quick", action="store_true", help="leave out Make an EQ's screen and long fitting runs")
    parser.add_argument("--all", action="store_true", dest="show_all", help="also every check's own line")
    parser.add_argument("--out", help="keep the logs in this folder")
    parser.add_argument("--jobs", type=_jobs, help="how many parts run at once")
    parser.add_argument("--timeout", type=_minutes, default=run_tests.DEFAULT_TIMEOUT,
                        help="minutes a part may run (default 30)")
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:  # (a wrong command line: argparse said why; --help: 0)
        return e.code if isinstance(e.code, int) else 2
    return run_tests.run([os.path.join(run_tests.PROJECT, "tests")], quick=args.quick, jobs=args.jobs, out=args.out,
                         show_all=args.show_all, extra=extra, timeout=args.timeout)


if __name__ == "__main__":
    # (UTF-8 whatever the console: check names have characters like ⓘ and →, which Windows' console code page lacks)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
