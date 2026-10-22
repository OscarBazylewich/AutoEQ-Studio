"""Claude's notes stay short: Claude Code reads .claude\\CLAUDE.md and .claude\\notes\\WORKLOG.md with every request,
so they keep to 1,500 words each and the worklog to its last five entries (older ones go to WORKLOG-archive.md: the
user, 2026-10-14). They're on the developer's PC only (git leaves .claude out): in a worktree or on GitHub there are
none, and the check says it's skipped and why. Moved from selftest.py's file_checks."""
import os

from helpers import capabilities
from helpers import paths as project

# (git ignores them, so relevant_tests.py chooses this test only when they're named)
COVERS_FILES = (".claude/CLAUDE.md", ".claude/notes/WORKLOG.md")

NAME = "files: CLAUDE.md and WORKLOG.md short (read with every request: 1,500 words at most, 5 entries)"


def test_claudes_notes_short(check):
    capabilities.require(capabilities.claude_notes, check, NAME)
    notes = {}
    for n, where in (("CLAUDE.md", (".claude",)), ("WORKLOG.md", (".claude", "notes"))):
        p = os.path.join(project.PROJECT, *where, n)
        if os.path.isfile(p):
            with open(p, encoding="utf-8") as fh:
                notes[n] = fh.read()
    long = [f"{n}: {len(t.split())} words" for n, t in notes.items() if len(t.split()) > 1500]
    entries = notes.get("WORKLOG.md", "").count("\n## 20")
    if entries > 5:
        long.append(f"WORKLOG.md: {entries} entries (move the oldest to WORKLOG-archive.md)")
    # was selftest.py:937
    check(NAME, not long, long)
