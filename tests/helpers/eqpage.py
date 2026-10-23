"""Make an EQ on the session, as the old EQ screen checks drove it (each function repeats eq_checks.py's own steps,
named by line). Qt and the app are imported inside the functions.

open_screen(tmp, settings=None)  the page opened and loaded (lines 1332-1371)
close_screen(s)                  everything it started stopped, its windows closed and deleted
quick_run(s)                     a quick Best fit run with the Run button (lines 1528-1532)
save_result(s, name)             Save under a file name (lines 1573-1578): the saved History entry
show_from_history(s, entry)      History's Show (line 1585)
use_on_device(s, name)           Use on device for the stand-in device (lines 1617-1620)
open_traced_sample(s)            the tracer on the app's sample graph, traced (lines 2770-2795)
"""
import dataclasses
import os

from helpers import qt, studio

# The settings the old EQ screen part opened on: it found the ones the old modules and requests parts had saved in
# the copy they shared (the requests part's automatic settings off, 2 worker cores, every file format ticked, its
# Best fit and website sweep values). Taken on 2026-10-22 from a real run of eq_checks.py --inner-modules and
# --inner-requests on eq_checks.make_copy()'s copy (a stand-in home and TEMP, offline): what its data\eq\settings.json
# held that differs from settings.with_auto({}).
OLD_START = {
    "site_sweep": {"filter_rows": [4, 6], "freq_high": [10000], "gain_ranges": [[-12, 6]], "q_max": [2]},
    "best_fit": {"filter_counts": [3, 5], "gain_max": [6], "q_max": [2]},
    "export": {"graphic": True, "poweramp": True, "uapp": True, "soundsource": True, "voicemeeter": True,
               "rockbox": True, "convolution": True},
    "performance": {"cores": 2},
    "auto": {"enabled": False},
}
DEVICE = "Headset|EarPods"  # (the stand-in device's key)


@dataclasses.dataclass
class EqScreen:
    page: object       # the EqPage
    sw: object         # its Switcher (a stand-in APO folder and device)
    said: list         # what the page said in the window's status line
    qapp: object
    apo_config: str    # the stand-in APO config folder
    wait_for: object   # helpers.qt.wait_for
    set_aside_before: list = dataclasses.field(default_factory=list)  # eq.service.SET_ASIDE before the page opened
    windows_before: set = dataclasses.field(default_factory=set)      # the top-level windows there before it


def _key(widget):
    import shiboken6
    return shiboken6.getCppPointer(widget)[0]


def open_screen(tmp, settings=None, size=(1000, 900)) -> EqScreen:
    """Make an EQ opened as the old checks opened it (lines 1332-1371): `settings` the EQ part starts from (None:
    OLD_START; {}: the defaults) with the studio as new; a stand-in APO folder in tmp whose config.txt includes
    AutoEQ Studio's file; one stand-in device, Headset (EarPods), playing; offline; the light theme; the page
    1000x900, shown and started, and waited for (90 s) until it has drawn the curves and the automatic settings.
    Raises with the page's note when it doesn't open."""
    import sys

    import net
    from switcher import core, devices as D
    from switcher.apo import Apo
    from ui import theme
    from ui.eq_page import EqPage
    qapp = qt.app()
    studio.reset(OLD_START if settings is None else settings)
    theme.apply(qapp, dark=False)
    conf = os.path.join(tmp, "apo", "config")
    os.makedirs(conf)
    with open(os.path.join(conf, "config.txt"), "w") as fh:
        fh.write("Include: AutoEQ Studio\\switcher.txt\n")
    eps = [D.Endpoint("{5}", "Headset", "EarPods", D.ACTIVE, True)]
    sw = core.Switcher(os.path.join(tmp, "switcher.json"), Apo(conf), endpoints=lambda: eps, playing=lambda: "{5}")
    said = []
    service = sys.modules.get("eq.service")
    before = list(service.SET_ASIDE) if service else []
    windows = {_key(w) for w in qapp.topLevelWidgets()}
    page = EqPage(sw, lambda text, ms=0: said.append(text))
    page.resize(*size)
    page.show()
    net.set_offline(True)  # (opening, the EQ part loads the database lists: never fetched in a test)
    page.start()
    s = EqScreen(page, sw, said, qapp, conf, qt.wait_for, before, windows)
    if not qt.wait_for(lambda: page.curves is not None and page.auto is not None, 90):
        note = page.graph_note.text() if hasattr(page, "graph_note") else page.loading.text()
        close_screen(s)
        raise RuntimeError(f"Make an EQ didn't open with the curves and the automatic settings in time: {note}")
    return s


def close_screen(s):
    """Sound stopped, a run that's going cancelled (and waited for), the page's own listeners taken out of
    eq.service.SET_ASIDE (those added since open_screen: once its notices are deleted, calling one raises "Signal
    source has been deleted"), the page's background loads let finish until all is quiet for half a second, the page
    closed and deleted (the windows it owns go with it), and every other window it opened and left open closed (and
    deleted when nothing owns it)."""
    import sys

    import shiboken6
    from PySide6.QtCore import QCoreApplication, QEvent, QThreadPool
    page = s.page
    if shiboken6.isValid(page) and getattr(page, "listen", None) is not None:
        page.stop_sound()
    service = sys.modules.get("eq.service")
    if service is not None:
        if service.JOB.get("status") == "running":
            service.call("/api/cancel")
            qt.wait_for(lambda: service.JOB.get("status") != "running", 60)
        service.SET_ASIDE[:] = [fn for fn in service.SET_ASIDE if any(fn is b for b in s.set_aside_before)]
    # (quiet first, not only "nothing running now": each load that ends starts the next as its answer arrives (the
    # curves, their analysis, the automatic settings). Since 2026-10-23 the page's loads name it as their owner
    # (ui.tasks.background), so an answer arriving once the page is deleted is dropped; waiting for quiet still lets a
    # test's last load finish rather than be cut off, as the app would have it)
    qt.settle(0.5, 30)
    QThreadPool.globalInstance().waitForDone(30000)
    qt.pump(50)
    # (the page first: the windows it made with itself as their owner go with it, the pop-up lists and menus of its
    # controls too. Deleting one of those before its owner aborted the whole process when the page went after it)
    if shiboken6.isValid(page):
        page.close()
        page.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    for w in [w for w in s.qapp.topLevelWidgets() if _key(w) not in s.windows_before]:
        if shiboken6.isValid(w) and w.isVisible():  # (still open: closed; deleted when it has no owner)
            w.close()
            if w.parentWidget() is None:
                w.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    QThreadPool.globalInstance().waitForDone(30000)
    qt.pump(50)


def quick_run(s, counts=(3, 5)) -> dict:
    """A quick Best fit run with the Run button (lines 1528-1532): automatic settings off, these filter counts, no
    random starts, boosts up to 6 dB, Q up to 2, not seeded from the website's; waited for (180 s). The result."""
    page = s.page
    page.S["auto"]["enabled"] = False
    page.S["best_fit"].update(filter_counts=list(counts), random_starts=0, gain_max=[6], q_max=[2], seed_with_site=False)
    before = page.run_result
    page.run_btn.click()  # (the button itself, as the old check did: a click passes Qt's checked=False on)
    s.wait_for(lambda: page.run_btn.isEnabled(), 180)
    if page.run_result is None or page.run_result is before:
        from helpers import dialogs
        raise RuntimeError(f"the run made no result: {page.progress_text.text()!r} {dialogs.DIALOGS.asked[-1:]}")
    return page.run_result


def save_result(s, name="UI check") -> dict:
    """Save filters under this file name (lines 1573-1578): the saved EQ's History entry."""
    page = s.page
    page.name_edit.setText(name)
    page.save()
    key = page.entry_now(True)["key"]
    entry = next((e for e in page.history if e.get("key") == key and e.get("saved")), None)
    if entry is None:
        raise RuntimeError(f"Save made no History entry for {name!r}: {s.said[-1:]}")
    return entry


def show_from_history(s, entry):
    """History's Show (line 1585): the EQ back on the result card, as a result of its own."""
    s.page.bring_back(entry)


def use_on_device(s, name="UI check"):
    """Use on device for the stand-in device (lines 1617-1620): the result becomes its profile, switched on. The
    device's record."""
    page = s.page
    page.name_edit.setText(name)
    page.name_edit.setProperty("auto", False)
    page.use_on(DEVICE)
    return s.sw.record(DEVICE)


def open_traced_sample(s) -> tuple:
    """The tracer on the app's sample graph (lines 2770-2795): opened, the picture loaded, its axis labels read (or
    +90 and +40 dB typed when Windows has no text reader), Auto trace three times. (tracer window, the sample's
    truth, the three Auto trace messages)."""
    from ui import ocr
    from ui.trace_window import sample_image
    img, truth = sample_image()
    page = s.page
    page.open_trace()
    tw = page.tracer
    tw.load_image(img, "Sample IEM")
    s.wait_for(lambda: not tw.reading, 60)
    try:
        ocr._get_engine()
    except ocr.Unavailable:
        tw.t.v.update(d1="90", d2="40")
    msgs = [tw.t.auto_trace() for _ in range(3)]
    return tw, truth, msgs
