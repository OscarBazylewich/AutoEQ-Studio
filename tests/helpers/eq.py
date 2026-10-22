"""The EQ part's helpers (the EQ part is imported inside the functions, from the session's copy).

sample_load(cfg=None)  the sample target and device loaded as a run loads them (pipeline.load): (curves, measurement
                       texts, target text)
DbGuard                the online databases' module state saved and put back (as eq_checks.py did by hand), and
                       downloads stood in for (stub_get)
Api                    requests to the EQ part as the window makes them (service.call), a run waited for, and what it
                       was asked to open (never opened)
reset_caches()         the EQ part's caches back to as-loaded (only the modules already imported)
file_reset(settings)   what tests\\eq and tests\\eq_screen run before every file: no run going, nothing set aside,
                       offline, the studio as new, no window left open
"""
import sys
import time

from helpers import qt, studio


def sample_load(cfg=None) -> tuple:
    from eq import pipeline, settings
    return pipeline.load(cfg or settings.with_auto({}), studio.target_path(), studio.measurement_paths())


class DbGuard:
    """save() and restore() of eq.databases' module state: its lists and their state, the configs it keeps, where
    its lists are saved, squig.link's list's failed try, the sites added, and the functions tests stand in for."""

    NAMES = ("_get", "items", "directory", "refresh_now", "sites_for", "_index_squig", "CACHE_PATH", "DIRECTORY_PATH")

    def __init__(self):
        self.saved = None

    def save(self):
        from eq import databases as db
        self.saved = {"attrs": {n: getattr(db, n) for n in self.NAMES},
                      "state": dict(db._state), "list": db.items(), "confs": dict(db._confs),
                      "dir_failed": dict(db._dir_failed), "extra_sites": dict(db._extra_sites),
                      "dir_sites": dict(db._dir_sites)}

    def stub_get(self, fn=None):
        """databases._get (the one place the EQ part downloads) replaced: by default it raises OSError."""
        from eq import databases as db

        def no_internet(url, **k):
            raise OSError("no internet in the tests")
        db._get = fn or no_internet

    def restore(self):
        from eq import databases as db
        s = self.saved
        if s is None:
            return
        for n, v in s["attrs"].items():
            setattr(db, n, v)
        db._state.clear()
        db._state.update(s["state"])
        db.set_items(s["list"])
        for name in ("confs", "dir_failed", "extra_sites", "dir_sites"):
            target = getattr(db, "_" + name)
            target.clear()
            target.update(s[name])


class Api:
    """Requests to the EQ part as the window makes them. opened: what /api/open was asked to open (the api fixture
    puts a recorder in place of service.open_path: nothing is opened with Windows)."""

    def __init__(self):
        self.opened = []

    def call(self, route, body=None) -> dict:
        from eq import service
        return service.call(route, body)

    def run_and_wait(self, route, body, timeout=180) -> dict:
        """Start a run (e.g. "/api/run") and wait (time_limit(timeout)) until it has ended: the job as /api/job says
        it ended (status done, error or cancelled; {"status": "timeout"} when it didn't end in time), or the
        request's own error."""
        r = self.call(route, body)
        if "error" in r:
            return r
        end = time.monotonic() + qt.time_limit(timeout)
        while time.monotonic() < end:
            j = self.call("/api/job")
            if j.get("status") != "running":
                self.call("/api/job", {"ack": True})
                return j
            time.sleep(0.2)
        self.call("/api/cancel")
        return {"status": "timeout"}


def _wait(cond, sec):
    end = time.monotonic() + qt.time_limit(sec)
    while not cond() and time.monotonic() < end:
        time.sleep(0.05)
    return cond()


def reset_caches():
    """The EQ part's caches as-loaded, in the modules already imported: the curves files read last
    (pipeline._LAST_TEXTS) and the site runs kept for reuse (_SWEEPS), the last comparison (compare._LAST), This
    PC's list (when it isn't being searched: waited for), and the database lists loaded (when they aren't being
    loaded: waited for)."""
    mods = sys.modules
    if "eq.pipeline" in mods:
        mods["eq.pipeline"]._LAST_TEXTS.clear()
        mods["eq.pipeline"]._SWEEPS.clear()
    if "eq.compare" in mods:
        mods["eq.compare"]._LAST.clear()
    if "eq.library" in mods:
        lib = mods["eq.library"]
        if _wait(lambda: not lib._state["scanning"], 30):
            lib._state.update(scanning=False, seen=0, found=0, cloud=0, folders=[], finished=None, items=[], error="")
    if "eq.databases" in mods:
        db = mods["eq.databases"]
        if _wait(lambda: not db._state["loading"], 30):
            db.set_items([])
            db._state.update(loading=False, sites=[], updated=None)
            db._state.pop("again", None)
            db._confs.clear()
            db._rows_made.clear()
            db._dir_failed["at"] = 0.0
            db._extra_sites.clear()
            db._dir_sites.clear()
            db._dir_sites.update(mtime=None, sites=[], by_url={})


def file_reset(settings=None):
    """Before every file of tests\\eq and tests\\eq_screen (their folder conftests): a run still going cancelled and
    waited for, the set-aside listeners and notices emptied, offline, every window left open closed and deleted
    (first, so none of them saves anything afterwards), and the studio as new (helpers.studio.reset, which empties
    the caches)."""
    if "eq.service" in sys.modules:
        service = sys.modules["eq.service"]
        service.SET_ASIDE.clear()  # (first: a page that's gone mustn't be told anything by the requests below)
        if service.JOB.get("status") == "running":
            service.call("/api/cancel")
            _wait(lambda: service.JOB.get("status") != "running", 60)
        service.call("/api/job", {"ack": True})
    import net
    import textfile
    net.set_offline(True)
    textfile.take_set_aside()
    _close_windows()
    studio.reset(settings)


def _close_windows():
    """Every top-level window still shown, closed, and deleted when it has no owner (one with an owner, e.g. a
    control's pop-up list, goes with its owner: deleting it first can abort the process), and the Help window's place
    emptied, so the next Help opens a new one."""
    if "PySide6.QtWidgets" not in sys.modules:
        return
    from PySide6.QtWidgets import QApplication
    qapp = QApplication.instance()
    if not isinstance(qapp, QApplication):
        return
    import shiboken6
    from PySide6.QtCore import QCoreApplication, QEvent
    shown = [w for w in qapp.topLevelWidgets() if w.isVisible()]
    for w in shown:
        w.close()
        if w.parentWidget() is None:
            w.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    qt.pump(20)
    hw = sys.modules.get("ui.help_window")
    if hw is not None and hw._window is not None and not shiboken6.isValid(hw._window):
        hw._window = None
