"""Make an EQ made in steps (ui\\eq_page.py, ui\\eq_page_cards.py, 2026-10-24: made in one go, the page froze the
window for ~0.45 s; now one step per turn of the window's event loop, each a few ms). What's checked, not how long
anything takes (timing checks come and go on a busy PC; the measurements are in the work's report):
- the page grows over many turns, ready only once it's whole, "Opening the EQ part…" until then and the page shown
  whole at once;
- each part goes into its final place in the step that makes it (the page's frame in the page before any card is
  made, nothing made in one step and placed in a later one), and the finished page's parts are where they were;
- made ahead (hidden in the window's stack while another screen shows, as the window makes it ahead: ui\\preload.py),
  it says nothing, no message box and no status line, until it's first shown; then what it kept is said; This PC is
  searched only once it has been seen;
- a damaged history.json at opening is said (it was set aside without a word: the notice rode on History's answer,
  which the opening dropped);
- ui.preload is held while the page opens and let go once: when it's whole, when the opening fails, when the page is
  deleted half-way;
- a page deleted half-way stops making itself (no error inside a Qt call-back), and a theme change half-way does no
  harm;
- "/" (Find…), Ctrl+V (a picture into the tracer) and a picture dropped on the page do nothing until it's ready.

The pages here are opened as helpers.eqpage.open_screen opens them (the settings the old screen checks started from,
offline, a stand-in device and APO folder), each by this file's own opener: one made ahead and watched as it opens,
shared by most tests, and a page of their own for the deleted one and the failed one."""
import dataclasses
import os

import pytest

from helpers import eqpage, qt, studio


_REAL = {}  # (ui.preload's own hold and release, taken before this file stands in for them)


def _key(widget):
    import shiboken6
    return shiboken6.getCppPointer(widget)[0]


def _content(page):
    """The page's own scroll areas (its frame, once made)."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QScrollArea
    return page.findChildren(QScrollArea, options=Qt.FindDirectChildrenOnly)


@dataclasses.dataclass
class Opened:
    s: object                 # helpers.eqpage.EqScreen (for close_screen)
    stack: object             # the stack of screens the page is in (None: the page shown on its own)
    other: object             # the screen shown while it's made ahead
    turns: list               # what each turn of the event loop saw while it opened (Watch)
    unplaced: dict            # {widget key: type}: made and not yet in a window's tree at the end of some turn
    holds: list               # ui.preload's hold() and release() as they were called, with the page's ready then
    before: dict = dataclasses.field(default_factory=dict)  # said before the page was first shown
    after: dict = dataclasses.field(default_factory=dict)   # said once it was


class Watch:
    """Looks at the page once per turn of the event loop, from before its opening starts until it's ready (a call to
    itself posted each time: the page's steps are posted calls too, so each step is seen on its own)."""

    def __init__(self, qapp, page, opened):
        from PySide6.QtCore import QObject
        self.qapp, self.page, self.o = qapp, page, opened
        self.before = {_key(w) for w in qapp.topLevelWidgets()}
        self.anchor = QObject()  # (the posted calls' context: deleted, they stop)
        self.ready_turns = 0
        self.turn()

    def turn(self):
        import shiboken6
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QWidget
        page = self.page
        if not shiboken6.isValid(page):
            return
        content = _content(page)
        self.o.turns.append({
            "widgets": len(page.findChildren(QWidget)), "ready": bool(page.ready),
            "opening shown": page.loading.isVisibleTo(page),
            "page shown": any(a.isVisibleTo(page) for a in content),
            "frame": bool(content), "frame holds": max((len(a.findChildren(QWidget)) for a in content), default=0),
            "cards made": hasattr(page, "graph_title")})
        for w in self.qapp.topLevelWidgets():  # (made this turn and not in a window yet: placed in a later one?)
            if w.parentWidget() is None and _key(w) not in self.before:
                self.o.unplaced[_key(w)] = type(w).__name__
        self.ready_turns += page.ready
        if self.ready_turns < 3:
            QTimer.singleShot(0, self.anchor, self.turn)

    def stop(self):
        import shiboken6
        from PySide6.QtCore import QCoreApplication, QEvent
        if shiboken6.isValid(self.anchor):
            self.anchor.deleteLater()
            QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)


def _open(tmp, monkeypatch, ahead, before_start=None):
    """Make an EQ opened as helpers.eqpage.open_screen opens it, by its own steps: ahead, the page goes into a stack of
    screens behind another one (a label), as the window makes it ahead; else it's shown on its own, as open_screen
    shows it. before_start(page) runs just before page.start(). ui.preload's hold() and release() are recorded."""
    import sys

    import net
    from PySide6.QtWidgets import QLabel, QStackedWidget
    from switcher import core, devices as D
    from switcher.apo import Apo
    from ui import preload, theme
    from ui.eq_page import EqPage
    qapp = qt.app()
    studio.reset(eqpage.OLD_START)
    theme.apply(qapp, dark=False)
    conf = os.path.join(tmp, "apo", "config")
    os.makedirs(conf)
    with open(os.path.join(conf, "config.txt"), "w") as fh:
        fh.write("Include: AutoEQ Studio\\switcher.txt\n")
    eps = [D.Endpoint("{5}", "Headset", "EarPods", D.ACTIVE, True)]
    sw = core.Switcher(os.path.join(tmp, "switcher.json"), Apo(conf), endpoints=lambda: eps, playing=lambda: "{5}")
    said = []
    service = sys.modules.get("eq.service")
    set_aside_before = list(service.SET_ASIDE) if service else []
    windows = {_key(w) for w in qapp.topLevelWidgets()}
    holds = []
    real_hold, real_release = _REAL.setdefault("hold", preload.hold), _REAL.setdefault("release", preload.release)
    page = EqPage(sw, lambda text, ms=0: said.append(text))
    monkeypatch.setattr(preload, "hold", lambda: (holds.append(("hold", page.ready)), real_hold())[1])
    monkeypatch.setattr(preload, "release", lambda: (holds.append(("release", page.ready)), real_release())[1])
    stack = other = None
    if ahead:
        stack = QStackedWidget()
        other = QLabel("Devices")  # (the screen you're on meanwhile)
        stack.addWidget(other)
        stack.addWidget(page)
        stack.setCurrentWidget(other)
        stack.resize(1000, 900)
        stack.show()
    else:
        page.resize(1000, 900)
        page.show()
    net.set_offline(True)
    s = eqpage.EqScreen(page, sw, said, qapp, conf, qt.wait_for, set_aside_before, windows)
    o = Opened(s, stack, other, [], {}, holds)
    if before_start is not None:
        before_start(page)
    o.watch = Watch(qapp, page, o)
    page.start()
    return o


def _history_file():
    return os.path.join(os.environ["AUTOEQSTUDIO_DATA"], "eq", "history.json")


@pytest.fixture(scope="module")
def ahead(tmp_path_factory, module_monkeypatch):
    """Make an EQ made ahead, hidden behind another screen, and watched as it opens: history.json damaged (cut off)
    and AutoEQ Local's files "brought over" (two, stood in: eq.bring_over), so it has a box and a status line to say.
    Waited for until it's ready with its curves and automatic settings; then shown, as a click on its tab shows it."""
    from eq import bring_over, library
    module_monkeypatch.setattr(bring_over, "needed", lambda: True)
    module_monkeypatch.setattr(bring_over, "bring_over", lambda: ["settings.json", "history.json"])
    searched, real_scan = [], library.start_scan
    module_monkeypatch.setattr(library, "start_scan", lambda cfg, force=False: (searched.append(force),
                                                                                real_scan(cfg, force))[1])

    def damage(page):
        with open(_history_file(), "w") as fh:
            fh.write("[{cut off")
    o = _open(str(tmp_path_factory.mktemp("ahead")), module_monkeypatch, True, damage)
    from helpers import dialogs
    page = o.s.page
    opened = qt.wait_for(lambda: page.curves is not None and page.auto is not None and page.ready, 90)
    qt.wait_for(lambda: o.watch.ready_turns >= 3, 10)
    o.watch.stop()
    qt.pump(300)
    o.before = {"opened": opened, "asked": list(dialogs.DIALOGS.asked), "said": list(o.s.said),
                "current": o.stack.currentWidget() is o.other, "searched": len(searched)}
    o.stack.setCurrentWidget(page)  # (the click on its tab)
    qt.wait_for(lambda: dialogs.DIALOGS.asked, 5)
    qt.pump(300)
    o.after = {"asked": list(dialogs.DIALOGS.asked), "said": list(o.s.said), "searched": len(searched)}
    yield o
    eqpage.close_screen(o.s)
    qt.close(o.stack)


def test_made_in_steps_and_ready_only_when_whole(ahead, check):
    turns = ahead.turns
    making = [t for t in turns if not t["ready"]]
    first_ready = next((t for t in turns if t["ready"]), {})
    grew = sorted({t["widgets"] for t in making if t["widgets"] > 1})  # (1: "Opening the EQ part…" alone)
    check("eq page: Make an EQ is made in steps, one per turn of the window's event loop (it grew in at least 8 of "
          "them: made in one go, it froze the window for ~0.45 s), ready only once it's whole",
          ahead.before["opened"] and len(grew) >= 8 and first_ready.get("widgets", 0) >= max(grew, default=1),
          (len(grew), grew[:12], first_ready.get("widgets")))
    check("eq page: while it's made, only “Opening the EQ part…” shows, and the page is shown whole in the turn it's "
          "ready (never seen half-made, nor used before it's ready)",
          bool(making) and all(t["opening shown"] and not t["page shown"] for t in making)
          and first_ready.get("page shown") is True and first_ready.get("opening shown") is False,
          ([t for t in making if not t["opening shown"] or t["page shown"]][:2], first_ready))


def test_each_part_placed_in_the_step_that_makes_it(ahead, check):
    from PySide6.QtWidgets import QLabel, QSpacerItem, QWidget
    page = ahead.s.page
    first_frame = next((t for t in ahead.turns if t["frame"]), {})
    # (the page's frame, its scroll area and column, put in the page first: the cards then go straight into it. Made
    # last and moved in whole, as before, every control was styled again: 149 ms)
    check("eq page: the page's frame (its scroll area and column) is in the page before any card is made, so the "
          "cards go straight into their place (the whole page moved in at the end cost 149 ms)",
          first_frame.get("cards made") is False and 0 < first_frame.get("frame holds", 99) < 12, first_frame)
    inside = {_key(w) for w in page.findChildren(QWidget)}
    late = sorted(name for key, name in ahead.unplaced.items() if key in inside)
    check("eq page: each part goes into its place in the step that makes it, never in a later one (a part moved "
          "once Qt has styled it is styled again, all of it: the settings' folds moved a step later cost 42 ms)",
          not late, late[:8])
    body = page.plot.parentWidget().parentWidget()  # (the graph's card's parent: the page's column)
    lay = body.layout()
    items = [lay.itemAt(i) for i in range(lay.count())]
    cards = [it.widget() for it in items if it.widget() is not None]
    want = [page.plot.parentWidget(), page.target_box, page.measurement_box, page.notice, page.eq_box,
            page.settings.fold, page.settings.adv, page.result_box, page.listen]
    tlay = page.target_box.layout()
    target_last = [tlay.itemAt(i).widget() for i in range(tlay.count() - 2, tlay.count())]

    def headings(form):
        return [lab.text() for lab in form.findChildren(QLabel) if lab.property("role") == "section"]
    adv, form = page.settings.adv_form, page.settings.form
    grids = {g.columnMinimumWidth(0) for g in adv._grids}
    names = {p: adv.fields[p].box.accessibleName() if p in adv.fields else None
             for p in ("best_fit.layout", "site.profile", "export.extra_headroom", "history.keep", "performance.cores")}
    seen = {"cards in order": cards == want, "a stretch last": isinstance(items[-1], QSpacerItem) or
            items[-1].spacerItem() is not None,
            "Adjust's row and panel last on the Target card": target_last == [page.settings.adjust_row,
                                                                             page.settings.adjust_panel],
            "Settings' sections": headings(form), "Advanced's sections": headings(adv),
            "Advanced's label column one width": len(grids) == 1, "names": names,
            "shown": [a.isVisibleTo(page) for a in _content(page)], "opening shown": page.loading.isVisibleTo(page)}
    check("eq page: the finished page's parts are where they were: the cards in order (graph, Target, Measurement, "
          "the notice, Make the EQ, Settings, Advanced, Your result, Listen), Adjust under the target, every section "
          "of both folds, Advanced's two halves one form (one label column, its boxes named for a screen reader)",
          seen["cards in order"] and seen["a stretch last"] and seen["Adjust's row and panel last on the Target card"]
          and seen["Settings' sections"] == ["Website AutoEQ: one run", "Website AutoEQ: find best settings",
                                             "Best fit", "Scoring", "Target"]
          and seen["Advanced's sections"] == ["Best fit", "Website sweep", "Website", "Saved files", "History",
                                              "This PC"]
          and seen["Advanced's label column one width"]
          and names == {"best_fit.layout": "Layout", "site.profile": "Which website to copy",
                        "export.extra_headroom": "Extra headroom (dB)", "history.keep": "History keeps",
                        "performance.cores": "CPU cores (0 = all but one)"}
          and seen["shown"] == [True] and seen["opening shown"] is False, seen)


def test_says_nothing_until_first_seen(ahead, check):
    before, after = ahead.before, ahead.after
    boxes = [text for kind, text in after["asked"] if kind == "warning"]
    check("eq page: made ahead behind another screen, it says nothing until it's first shown: no message box, no "
          "status line, no change of screen (made ahead while you're on Devices, it said them there)",
          before["opened"] and not before["asked"] and not before["said"] and before["current"], before)
    check("eq page: once first shown, what it kept is said: the files set aside (one box) and the status line "
          "(AutoEQ Local's files brought over)",
          len(boxes) == 1 and any(t.startswith("Brought over 2 files from AutoEQ Local") for t in after["said"]),
          after)


def test_this_pc_searched_once_seen(ahead, check):
    seen = (ahead.before["searched"], ahead.after["searched"])
    check("eq page: This PC is searched once the page has been seen: not while it's made ahead unseen (searching it "
          "then shared Python's lock with the window, and the steps took longer), then once it's shown",
          seen == (0, 1), seen)


def test_damaged_history_said(ahead, check):
    boxes = [text for kind, text in ahead.after["asked"] if kind == "warning"]
    bad = _history_file() + ".bad"
    check("eq page: a damaged history.json at opening is said (kept as history.json.bad, a new one started): it was "
          "set aside without a word (its notice came with History's answer, which the opening dropped)",
          any("history.json couldn't be read" in b and "history.json.bad" in b for b in boxes) and os.path.exists(bad),
          (boxes, os.path.exists(bad)))


def test_graphs_value_axes_one_width(ahead, check):
    # (2026-10-24, the checkers: pyqtgraph sized each graph's value axis to the first numbers it drew and kept it; made
    # ahead, the top graph was first drawn with its curves ("70") and the EQ graph under it empty ("0.9"), so their
    # axes were 36 and 40 px wide and the two graphs' left edges 4 px apart; and each jumped wider once its curves came)
    page = ahead.s.page
    qt.pump(200)
    widths = [round(p.getAxis("left").width(), 1) for p in (page.plot, page.eqplot)]
    page.draw()  # (drawn again with its curves)
    qt.pump(200)
    again = [round(p.getAxis("left").width(), 1) for p in (page.plot, page.eqplot)]
    check("eq page: both graphs' value axes are one width (the graphs' edges line up), made ahead too, and stay so "
          "when the curves are drawn again", widths[0] == widths[1] and again == widths and widths[0] > 0,
          (widths, again))


def test_preload_held_while_it_opens(ahead, check):
    holds = ahead.holds
    check("eq page: ui.preload is held while Make an EQ opens (its imports in the background shared Python's lock: each "
          "step took about twice as long) and let go once, when the page is whole",
          holds == [("hold", False), ("release", True)], holds)


def test_failed_opening_lets_go(tmp_path, monkeypatch, check):
    from eq import service
    real = service.call
    monkeypatch.setattr(service, "call", lambda path, body=None: {"error": "made up for the test"}
                        if path == "/api/state" else real(path, body))
    o = _open(str(tmp_path), monkeypatch, False)
    page = o.s.page
    try:
        said = qt.wait_for(lambda: page.loading.text().startswith("The EQ part couldn't open"), 60)
        o.watch.stop()
        holds = list(o.holds)
    finally:
        eqpage.close_screen(o.s)
    check("eq page: when the EQ part can't open, ui.preload is let go too (held for good, the code it loads ahead "
          "would wait for ever), and the page says so", said and holds == [("hold", False), ("release", False)],
          (said, holds))


def test_deleted_half_way(tmp_path, monkeypatch, check):
    import shiboken6
    from PySide6.QtCore import QCoreApplication, QEvent
    from ui import eq_page
    steps = {"after": 0, "gone": False}
    real_step = eq_page.EqPage._step

    def step(self):
        if steps["gone"]:
            steps["after"] += 1
        return real_step(self)
    monkeypatch.setattr(eq_page.EqPage, "_step", step)
    o = _open(str(tmp_path), monkeypatch, False)
    page, errors_before = o.s.page, len(qt.QT_ERRORS)
    caught = themed = False
    try:
        # (half-way: the Target card made, the page not whole)
        qt.wait_for(lambda: hasattr(page, "target_box") or page.ready, 60, step=0.001)
        caught = not page.ready
        if caught:
            from ui import theme
            theme.apply(o.s.qapp, dark=True)  # (Windows switched to dark while the page is half made)
            theme.apply(o.s.qapp, dark=False)
            themed = len(qt.QT_ERRORS) == errors_before
            o.watch.stop()
            page.close()
            page.deleteLater()
            QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
            steps["gone"] = not shiboken6.isValid(page)
            qt.pump(300)
            qt.settle(0.5, 30)
    finally:
        o.watch.stop()
        eqpage.close_screen(o.s)
    errors = qt.QT_ERRORS[errors_before:]
    check("eq page: a theme change while the page is half made does no harm (its graph is drawn in the new colours, "
          "what isn't made yet is made in them)", caught and themed, (caught, errors[:2]))
    check("eq page: deleted half-way, the page stops making itself (its steps' timer has the page as its context): no "
          "step runs on the deleted page, no error inside a Qt call-back, and ui.preload is let go",
          caught and steps["gone"] and steps["after"] == 0 and not errors
          and o.holds == [("hold", False), ("release", False)], (caught, steps, errors[:2], o.holds))


def test_keys_and_drops_wait_for_ready(ahead, check, dialogs):
    from PySide6.QtCore import QMimeData, QPoint, Qt
    from PySide6.QtGui import QColor, QDragEnterEvent, QDropEvent, QImage, QKeySequence, QShortcut
    from PySide6.QtWidgets import QApplication
    page = ahead.s.page
    keys = {sc.key().toString(): sc for sc in page.findChildren(QShortcut)}
    find, paste = keys.get("/"), keys.get(QKeySequence(QKeySequence.Paste).toString())
    img = QImage(400, 300, QImage.Format_RGB888)
    img.fill(QColor("white"))
    QApplication.clipboard().setImage(img)  # (the off-screen clipboard: this process's own)
    md = QMimeData()
    md.setImageData(img)
    tracer = getattr(page, "tracer", None)
    seen = {}
    try:
        page.ready = False  # (as while it's made: its requests can be made, it isn't whole)
        dialogs.asked.clear()
        find.activated.emit()
        paste.activated.emit()
        enter = QDragEnterEvent(QPoint(20, 20), Qt.CopyAction, md, Qt.LeftButton, Qt.NoModifier)
        enter.ignore()
        page.dragEnterEvent(enter)
        drop = QDropEvent(QPoint(20, 20), Qt.CopyAction, md, Qt.LeftButton, Qt.NoModifier)
        drop.ignore()
        page.dropEvent(drop)
        seen["not ready"] = {"asked": list(dialogs.asked), "drag accepted": enter.isAccepted(),
                             "drop accepted": drop.isAccepted(),
                             "tracer": getattr(page, "tracer", None) is not tracer and page.tracer.isVisible()}
        page.ready = True
        find.activated.emit()  # (ready: Find… opens; its window answers by itself, helpers.dialogs)
        seen["ready"] = {"asked": list(dialogs.asked)}
    finally:
        page.ready = True
        if getattr(page, "tracer", None) is not None and page.tracer is not tracer:
            page.tracer.close()
    check("eq page: “/” (Find…), Ctrl+V (a picture into the tracer) and a picture dropped on the page do nothing "
          "until the page is ready (while it's made, they'd open over half a page); ready, “/” opens Find…",
          seen["not ready"] == {"asked": [], "drag accepted": False, "drop accepted": False, "tracer": False}
          and any(kind == "exec" and "Picker" in text for kind, text in seen["ready"]["asked"]), seen)
