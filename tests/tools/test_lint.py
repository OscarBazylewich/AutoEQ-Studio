"""Ruff, the linter (ruff.toml in the main folder): no unused or undefined names, no likely bugs, in the program
(app\\) and its tests (tests\\). Only where it's installed (the development environment: it isn't part of the app):
skipped, and said, without it. Moved from selftest.py's lint_checks."""
import subprocess

from helpers import capabilities, qt, session
from helpers import paths as project

# (for app\tools\relevant_tests.py: what Ruff reads)
COVERS_FILES = ("app/**/*.py", "tests/**/*.py", "ruff.toml")

NAME = "code: Ruff finds nothing (unused or undefined names, likely bugs)"


def test_ruff_finds_nothing(check):
    ok, ruff = capabilities.ruff()
    if not ok:  # (the old check's words)
        check.skipped("Ruff isn't installed here (\".venv\\Scripts\\python.exe -m pip install ruff\")", NAME)
    # (--no-cache: Ruff leaves no .ruff_cache folder in the project; run in the main folder, so ruff.toml applies)
    out = subprocess.run([ruff, "check", "--no-cache", "--quiet", "app", "tests"], capture_output=True, text=True,
                         encoding="utf-8", errors="replace", cwd=project.PROJECT, env=session.child_env(),
                         timeout=qt.time_limit(120))
    # was selftest.py:1091
    check(NAME, out.returncode == 0, (out.stdout + out.stderr)[-600:])
