"""Starting the app (start.py): one copy at a time (starting it again shows the running one and ends), the
installer's --uninstall (the running copy quits, AutoEQ Studio's line leaves APO's config.txt, the log's every line is
dated, and this copy's Start with Windows is turned off) and --quit (with nothing running: done at once), and the
restart after a restore (the new copy waits for the old one to quit, then starts). Moved from selftest.py's
installed_checks.

The first four start real copies of the program, one after another, as the installer and Windows would: a copy in
the test folder (helpers.subproc.RunningCopy) with a data folder of its own there (so it has a one-copy channel of its
own and no mutex: it can never reach the app you're running), the stand-in Equalizer APO folder and EQ Switcher's
stand-in settings. Its settings say Offline and no hotkey: it never goes online when it opens Make an EQ, nor tries
the hotkey. The copy's Start with Windows entry never points at it, so --uninstall writes nothing to the registry.
They run as a chain, in this order (the second ends the copy the first started); the copy is always ended at the end
of the file (--quit, then anything left ended), and helpers.subproc's job object ends it if this process dies. The
last runs start.py's uninstall() in this process, with Start with Windows and the APO folders stood in for."""
import json
import os
import re
import subprocess
import sys
import time
import types

import pytest

from helpers import apo, qt, session, subproc
from switcher.apo import Apo

# (the copies run start.py, and through it the app: relevant_tests.py can't see that from this file's imports)
COVERS = ("start", "ui.app", "ui.winsys", "switcher.apo")


@pytest.fixture(scope="module")
def copies(tmp_path_factory):
    """A copy of the program in the test folder, a stand-in APO folder with AutoEQ Studio's line in its config.txt,
    and the environment its copies start in (selftest.py lines 1167-1174); every copy started from it ended at the
    end of the file."""
    top = str(tmp_path_factory.mktemp("start"))
    run = os.path.join(top, "run")
    app = subproc.app_copy(run)
    conf = apo.fake_apo(run)
    Apo(conf).install_line()
    data = os.path.join(run, "data")
    os.makedirs(data)
    with open(os.path.join(data, "settings.json"), "w", encoding="utf-8") as fh:
        json.dump({"offline": True, "hotkey": "", "onoff_hotkey": ""}, fh)  # (never online, never the hotkey: see above)
    env = session.child_env(AUTOEQSTUDIO_APO_CONFIG=conf, AUTOEQSTUDIO_OLD_SETTINGS=os.path.join(top, "none.json"),
                            AUTOEQSTUDIO_DATA=data, AUTOEQSTUDIO_ROOT=os.path.join(run, "root"))
    state = types.SimpleNamespace(program=subproc.RunningCopy(app, env), conf=conf, running=None)
    try:
        yield state
    finally:
        state.program.stop()


def test_one_copy_at_a_time(copies, check):
    c = copies.program
    copies.running = c.start("--tray")
    c.wait_started(1)  # (until its log says it started: a minute at most, as before, more on a busy PC)
    second = c.run("--tray")
    # was selftest.py:1181
    check("one copy: starting it again shows the running one and ends; the first keeps running (review 2)",
          second.returncode == 0 and copies.running.poll() is None and c.started() == 1,
          (second.returncode, copies.running.poll(), second.stderr[-300:]))


def test_uninstall_quits_and_takes_apos_line_out(copies, check):
    if copies.running is None:
        pytest.fail("This test continues test_one_copy_at_a_time (--uninstall ends the copy that test starts): run the "
                    "whole file.", pytrace=False)
    c, running = copies.program, copies.running
    un = c.run("--uninstall")
    try:
        ended = running.wait(qt.time_limit(20)) is not None
    except subprocess.TimeoutExpired:
        subproc.kill_tree(running.pid)
        ended = False
    lines = [line for line in c.log().splitlines() if line.strip()]
    dated = bool(lines) and all(re.match(r"\d{4}-\d\d-\d\d \d\d:\d\d:\d\d  ", line) for line in lines)
    # was selftest.py:1193
    check("installer: --uninstall makes the running copy quit and takes AutoEQ Studio out of APO's config.txt; the "
          "log's every line has its date and time", un.returncode == 0 and ended and not Apo(copies.conf).set_up() and dated,
          (un.returncode, ended, Apo(copies.conf).set_up(), lines[-4:], un.stderr[-300:]))


def test_quit_with_nothing_running(copies, check):
    none = copies.program.run("--quit")
    # was selftest.py:1197
    check("installer: --quit with nothing running ends at once, without an error", none.returncode == 0,
          (none.returncode, none.stderr[-300:]))


def test_restart_waits_for_the_old_copy(copies, check):
    # ((review 2) the restart after a restore: the new copy (--restarted) waits for the old one to quit, then starts)
    c = copies.program
    before = c.started()
    old = c.start("--tray")
    first = c.wait_started(before + 1)
    new = c.start("--restarted", "--tray")
    time.sleep(3)  # (not a time limit: how long the new copy must be seen waiting while the old one runs)
    waited = new.poll() is None and c.started() == before + 1  # (still waiting: not started yet)
    # (this --quit used to wait its whole 15 s and end with 1 most times: the new copy takes over the one-copy channel
    # as soon as the old one has gone, so the channel never looked empty to it. Fixed 2026-10-22: it waits for the
    # process it asked, which Windows names from the channel)
    t = time.monotonic()
    asked = c.run("--quit")  # (the old one quits)
    took = time.monotonic() - t
    then = c.wait_started(before + 2)
    old_gone = old.poll() is not None
    c.run("--quit")
    for p in (old, new):
        try:
            p.wait(qt.time_limit(20))
        except subprocess.TimeoutExpired:
            subproc.kill_tree(p.pid)
    # was selftest.py:1221
    check("restart: the copy started by a restore waits for the old one to quit, then starts (one copy at a time)",
          first and waited and then and old_gone, (first, waited, then, old_gone))
    check("restart: --quit asked while a restart waits ends as soon as the old copy has quit, saying it did (exit code "
          "0), not after waiting 15 s for the channel the new copy took over",
          asked.returncode == 0 and took < qt.time_limit(10), (asked.returncode, round(took, 1)))


def test_uninstall_turns_start_with_windows_off(monkeypatch, check):
    # ((review 2) --uninstall turns off this copy's Start with Windows. The stand-ins are what keep it safe: with
    # autostart_on saying True, the real set_autostart(False) would delete your own Start with Windows entry (the
    # guard would block that registry write too). Patched where the names live: ui.winsys, and the paths module start
    # uses)
    monkeypatch.setattr(sys, "path", list(sys.path))  # (start.py puts its folder first on the path when imported)
    import start
    from ui import winsys
    turned = []
    monkeypatch.setattr(winsys, "set_autostart", lambda on: turned.append(on))
    monkeypatch.setattr(start.paths, "apo_folders", lambda: (None, None))
    monkeypatch.setattr(winsys, "autostart_on", lambda value=None: True)
    start.uninstall()
    # was selftest.py:1235
    check("installer: --uninstall turns this copy's Start with Windows off", turned == [False], turned)
