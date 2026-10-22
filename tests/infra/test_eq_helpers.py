"""Make an EQ's helpers (helpers.eqpage, helpers.eq.file_reset; PLAN.md 3.4): each does what it says, in the old
EQ screen checks' order (open, run, save, show from History, use on device, trace the sample, close), close_screen
leaves nothing running, and file_reset() puts everything back as new. Slow: it opens Make an EQ (twice)."""
import json
import multiprocessing
import os
import threading
import time

import pytest

from helpers import eq, eqpage, qt, session, studio

S = session.SESSION


def _threads():
    """Python's own threads now, but for pytest-timeout's timer and V8's idle event loops: the EQ part keeps a V8
    for each thread that used one (engines' _kept), as the app does, and V8 (mini-racer) keeps an event loop thread
    beside each. Those are counted apart (_v8_loops)."""
    return {t.ident for t in threading.enumerate() if not isinstance(t, threading._DummyThread)
            and not t.name.startswith("pytest_timeout") and "run_event_loop" not in t.name}


def _v8_loops():
    return sum("run_event_loop" in t.name for t in threading.enumerate())


@pytest.fixture(scope="module")
def screen(tmp_path_factory):
    import sys
    service = sys.modules.get("eq.service")
    state = {"threads": _threads(), "v8": _v8_loops(), "set_aside": list(service.SET_ASIDE) if service else None}
    s = eqpage.open_screen(str(tmp_path_factory.mktemp("helpers_screen")))
    s.before = state
    yield s
    eqpage.close_screen(s)  # (again, should the last test not have got that far: nothing happens twice)


def test_open_screen_on_old_start(screen, check):
    import net
    page = screen.page
    S_ = page.S
    check("eq helpers: open_screen opens Make an EQ on the old checks' starting settings (OLD_START: automatic "
          "settings off, 2 cores, every file format, the requests' Best fit values), offline, its curves drawn",
          page.curves is not None and page.auto is not None and S_["auto"]["enabled"] is False
          and S_["performance"]["cores"] == 2 and S_["best_fit"]["filter_counts"] == [3, 5]
          and all(S_["export"][k] for k in eqpage.OLD_START["export"]) and net.offline()
          and screen.sw.record(eqpage.DEVICE) is not None, {k: S_[k] for k in ("auto", "performance", "best_fit")})


@pytest.mark.timeout(400)
def test_quick_run(screen, check):
    r = eqpage.quick_run(screen)
    run, shown = screen.page.current()
    check("eq helpers: quick_run makes a Best fit result with the Run button (3 and 5 filters)",
          r["mode"] == "best_fit" and r["results"] and shown and shown["filters"]
          and sorted({x["n_filters"] for x in r["results"]}) == [3, 5], [x.get("n_filters") for x in r["results"]])


def test_save_result(screen, check):
    entry = eqpage.save_result(screen)
    saved = os.listdir(os.path.join(S.studio, "Saved EQs"))
    check("eq helpers: save_result saves the result under its file name and gives its History entry",
          entry["saved"] and "UI check - filters.txt" in saved and entry["filters"], saved)
    screen.entry = entry


def test_show_from_history(screen, check):
    eqpage.show_from_history(screen, screen.entry)
    page = screen.page
    check("eq helpers: show_from_history brings the saved EQ back as a result of its own (“From History”)",
          page.run_result.get("history") == screen.entry["base"] and page.res_sub.text().startswith("From History"),
          page.res_sub.text())


def test_use_on_device(screen, check):
    rec = eqpage.use_on_device(screen)
    with open(os.path.join(screen.apo_config, "AutoEQ Studio", "switcher.txt")) as fh:
        text = fh.read()
    check("eq helpers: use_on_device makes the result the stand-in device's profile, switched on, in APO's file",
          rec["active"] and screen.sw.profile_name(rec["active"]) == "UI check"
          and "Include: profiles\\UI check.txt" in text, rec)


@pytest.mark.timeout(400)
def test_open_traced_sample(screen, check):
    tw, truth, msgs = eqpage.open_traced_sample(screen)
    check("eq helpers: open_traced_sample opens the tracer on the sample graph and traces its three curves",
          [c["label"] for c in tw.t.curves] == ["L", "R", "L2"] and len(msgs) == 3 and "chans" in truth,
          ([c["label"] for c in tw.t.curves], msgs))


def test_close_screen(screen, check):
    import sys

    import shiboken6
    from PySide6.QtCore import QThreadPool
    page = screen.page
    eqpage.close_screen(screen)
    qt.wait_for(lambda: _threads() <= screen.before["threads"] and not multiprocessing.active_children(), 20)
    service = sys.modules["eq.service"]
    before = screen.before["set_aside"] or []
    check("eq helpers: close_screen leaves no thread or worker process running, the page deleted, and the EQ "
          "part's set-aside listeners as they were before the page opened",
          not shiboken6.isValid(page) and QThreadPool.globalInstance().activeThreadCount() == 0
          and not multiprocessing.active_children() and _threads() <= screen.before["threads"]
          and _v8_loops() <= screen.before["v8"] + 1  # (at most this thread's kept V8, as in the app)
          and len(service.SET_ASIDE) == len(before) and all(a is b for a, b in zip(service.SET_ASIDE, before)),
          ([t.name for t in threading.enumerate() if t.ident in _threads() - screen.before["threads"]],
           _v8_loops() - screen.before["v8"], multiprocessing.active_children(), len(service.SET_ASIDE)))


def test_open_screen_on_the_defaults(tmp_path, check):
    s = eqpage.open_screen(str(tmp_path), {})
    try:
        S_ = s.page.S
        check("eq helpers: open_screen with {} opens Make an EQ on the default settings",
              S_["auto"]["enabled"] is True and S_["performance"]["cores"] == 0 and s.page.curves is not None,
              {k: S_[k] for k in ("auto", "performance")})
    finally:
        eqpage.close_screen(s)


@pytest.mark.timeout(400)
def test_eq_fixtures(fresh_studio, eq_cfg, sample_curves, db_guard, api, check):
    from eq import databases, settings
    curves, meas_texts, target_text = sample_curves
    try:
        databases._get("https://example.invalid/")
        stood_in = False
    except OSError as e:
        stood_in = "no internet in the tests" in str(e)
    state = api.call("/api/state")
    api.call("/api/open", {"what": "output"})
    cfg = settings.with_auto({"auto": {"enabled": False}, "performance": {"cores": 2},
                              "best_fit": {"filter_counts": [3], "random_starts": 0}})
    job = api.run_and_wait("/api/run", {"mode": "best_fit", "settings": cfg})
    check("eq helpers: the EQ fixtures: the default settings, the sample curves (the 10 seatings and the target), "
          "downloads stood in for, requests answered, a folder's opening recorded (never done), a run waited for",
          eq_cfg == settings.with_auto({}) and len(curves["f"]) > 100 and len(meas_texts) == 10 and target_text
          and stood_in and state.get("settings") and api.opened == [os.path.join(S.studio, "Saved EQs")]
          and job.get("status") == "done" and job["result"]["results"],
          (stood_in, api.opened, job.get("status"), job.get("message")))


@pytest.mark.timeout(400)
def test_file_reset(check):
    import sys

    import net
    from eq import service, settings
    cfg = settings.with_auto({"auto": {"enabled": False}, "best_fit": {"filter_counts": list(range(3, 13))}})
    started = service.call("/api/run", {"mode": "best_fit", "settings": cfg})
    service.SET_ASIDE.append(lambda text: None)
    net.set_offline(False)
    with open(os.path.join(S.studio, "Targets", "extra target.txt"), "w") as fh:
        fh.write("20 1\n20000 1\n")
    os.makedirs(os.path.join(S.studio, "Saved EQs"), exist_ok=True)
    with open(os.path.join(S.studio, "Saved EQs", "an EQ.txt"), "w") as fh:
        fh.write("Preamp: -1 dB\n")
    t = time.monotonic()
    eq.file_reset()
    took = time.monotonic() - t
    with open(os.path.join(S.data, "eq", "settings.json"), encoding="utf-8") as fh:
        saved = json.load(fh)
    check("eq helpers: file_reset() leaves no run going (one going is cancelled), no set-aside listener, the app "
          "offline, and the studio as new",
          "id" in started and service.JOB.get("status") != "running" and not service.SET_ASIDE and net.offline()
          and os.listdir(os.path.join(S.studio, "Targets")) == [studio.target_path().split(os.sep)[-1]]
          and len(os.listdir(os.path.join(S.studio, "Measurements"))) == 10
          and not os.listdir(os.path.join(S.studio, "Saved EQs"))
          and saved == {"library": {"folders": [os.path.join(S.studio, "samples")]}}
          and not os.path.exists(os.path.join(S.data, "eq", "history.json")) and "eq.service" in sys.modules,
          (started, service.JOB.get("status"), took, saved))
