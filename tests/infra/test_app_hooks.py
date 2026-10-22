"""The four small app changes the tests rely on (PLAN.md section 4): the tests' cap on worker processes, a window's
Online/Offline listener let go once the window is gone, the checkbox tick picture written whole, and no crash box
for the tests' copies of the app. Each is invisible to users (the old checks and the snapshot prove that)."""
import os
import time

from helpers import session, subproc

COVERS = ("ui.theme", "start")  # (reached here through other processes: their code names them as text)


def test_worker_cap(monkeypatch, check):
    from eq import pipeline, settings
    monkeypatch.setattr(pipeline, "free_memory", lambda: None)  # (plenty: the count follows only the settings)
    cfg = settings.with_auto({"performance": {"cores": 8}})
    got = {}
    for cap in ("3", "1", "0", "x", None):
        if cap is None:
            monkeypatch.delenv("AUTOEQSTUDIO_MAX_WORKERS", raising=False)
        else:
            monkeypatch.setenv("AUTOEQSTUDIO_MAX_WORKERS", cap)
        got[cap] = pipeline.workers(cfg)
    check("app hooks: AUTOEQSTUDIO_MAX_WORKERS caps the worker processes (a number above 0 only; without it the "
          "setting decides)", got == {"3": 3, "1": 1, "0": 8, "x": 8, None: 8}, got)


def test_dead_windows_listener_let_go(qapp, monkeypatch, check):
    import shiboken6
    from PySide6.QtWidgets import QLabel

    import net
    monkeypatch.setattr(net, "_listeners", [])
    heard = []
    label = QLabel("gone soon")
    net.on_change(label.setVisible)  # (a window's listener: the window is deleted below)
    net.on_change(heard.append)
    shiboken6.delete(label)
    net.set_offline(False)
    net.set_offline(True)

    def other(on):
        raise RuntimeError("something else went wrong")
    net.on_change(other)
    try:
        net.set_offline(False)
        raised = False
    except RuntimeError:
        raised = True
    kept = len(net._listeners) == 2 and other in net._listeners
    net._listeners.remove(other)
    net.set_offline(True)  # (back offline, as the whole session is)
    check("app hooks: Online/Offline lets go of a listener whose window is gone (Qt: \"already deleted\") and still "
          "tells the others; any other error isn't hidden",
          heard[:2] == [False, True] and kept and raised, (heard, kept, raised))


def test_tick_written_whole(check):
    code = ("import glob, json, os, sys, tempfile; sys.path.insert(0, sys.argv[1])\n"
            "from PySide6.QtWidgets import QApplication\n"
            "from PySide6.QtGui import QImage\n"
            "app = QApplication([])\n"
            "from ui import theme\n"
            "tick = os.path.join(tempfile.gettempdir(), 'autoeq-studio-tick.png')\n"
            "if os.path.exists(tick): os.remove(tick)\n"
            "theme.apply(app, dark=False)\n"
            "img = QImage(tick)\n"
            "drawn = [os.path.isfile(tick), img.width(), img.height(), 'autoeq-studio-tick.png' in app.styleSheet()]\n"
            "os.remove(tick)\n"
            "real = os.replace\n"
            "def taken(a, b): raise PermissionError(13, 'another copy put it there first')\n"
            "os.replace = taken\n"
            "theme.apply(app, dark=True)\n"
            "os.replace = real\n"
            "parts = glob.glob(os.path.join(tempfile.gettempdir(), '*.part'))\n"
            "print(json.dumps({'drawn': drawn, 'parts': parts, 'in_place': os.path.exists(tick),"
            " 'temp': tempfile.gettempdir()}))\n")
    out = subproc.run_python(code, session.SESSION.app)
    d = out.data or {}
    check("app hooks: the checkbox tick is drawn into this session's TEMP, whole (a .part file put in place), and "
          "nothing is left behind when another copy put it there first",
          d.get("drawn") == [True, 28, 28, True] and d.get("parts") == [] and d.get("in_place") is False
          and session.inside(d.get("temp", "?")), (d, out.stderr[-400:]))


def test_crash_without_a_box(tmp_path, check):
    app = subproc.app_copy(str(tmp_path))
    with open(os.path.join(app, "ui", "app.py"), "w", encoding="utf-8") as fh:
        fh.write('raise RuntimeError("a made-up crash for the test")\n')
    env = session.child_env(AUTOEQSTUDIO_DATA=os.path.join(tmp_path, "data"),
                            AUTOEQSTUDIO_ROOT=os.path.join(tmp_path, "root"),
                            AUTOEQSTUDIO_APO_CONFIG=os.path.join(tmp_path, "apo", "config"))
    copy = subproc.RunningCopy(app, env)
    t = time.monotonic()
    done = copy.run("--tray", timeout=60)
    took = time.monotonic() - t
    log = copy.log()
    check("app hooks: a copy whose start crashes ends at once (exit code 1) with its traceback in its log and no "
          "message box, under AUTOEQSTUDIO_NO_MESSAGE_BOX",
          done.returncode == 1 and "a made-up crash for the test" in log and "Traceback" in log and took < 30,
          (done.returncode, took, log[-400:], done.stderr[-300:]))
