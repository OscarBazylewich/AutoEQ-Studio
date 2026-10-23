"""The Guides (ui\\guide.py over ui\\tour.py) on Make an EQ: every step's control there and in sight; → steps through
every step to Done; every step's demo played to its end with nothing of yours changed (and with Windows' animation
effects off, numbered markers instead); the card's Pause / Resume, the wheel and the step list; the tracer's Guide on
the sample graph; a resized window keeping the Guide's graph picture inside it; Tab staying in the Guide; the ring cut
to what its scroll area shows; and (2026-10-23) its Windows 11 look: its marks in the accent, light and dark, the
card's symbols drawn again when the theme changes, a demo's messages and keys fitting and gone when it stops; then the
checkers' findings on it: the windows the demos show fitting their frames beside the card (at the app's own size and
the window's smallest), every step in sight at the smallest size, one ring round two lit cards that touch, the step
list's headings as Windows 11's, Play demo only on a step with a demo; and after their recheck, the step list's button
with Windows 11's chevron, and the lists and menus a demo shows looking as the real ones.

Moved from eq_checks.py's guide_checks (lines 2625-2760), review_checks (1764-1780) and review_low_checks (1946-1948),
on a page opened as the old checks opened it (the eq_screen fixture) with the result they had on the card by then (a
run, Retry, saved, brought back with History's Show), 1100x900 as guide_checks made it (line 2632, kept for the
later checks there), offline throughout: the old checks were online here and the demos' Find… then refreshed every
database list from the internet, which nothing here needs.

Windows' animation effects: a tour reads them as it starts (tour._animations_on). The old checks ran where they were
on, so the demos glided; here they're taken as on for every tour of this file, whatever this PC's setting, and the
check of the markers turns them off itself, as the old one did (t.glide = False).

Two demos used to reach for a row of Find…'s list that Find… had drawn again meanwhile (it does every half second
while its lists load): "many results" ("QListWidgetItem already deleted") and "choose the measurement" ("QWidget
already deleted"). Fixed 2026-10-22 (ui\\guide_demos.py row_now): test_find_demos_while_find_redraws plays both while
Find… redraws its rows every 100 ms."""
import json

import pytest

from helpers import eqpage


@pytest.fixture(scope="module", autouse=True)
def glide():
    """Windows' animation effects taken as on for the tours of this file (see above)."""
    from ui import tour
    with pytest.MonkeyPatch.context() as m:
        m.setattr(tour, "_animations_on", lambda: True)
        yield


def _retry(s):
    """Retry from these filters: Best fit again from them (fine-tune), with the page's own Retry (line 1564), waited
    for (180 s)."""
    page = s.page
    run = page.run_result
    page.run(retry={"filters": page.active(), "add": False})
    if not s.wait_for(lambda: page.run_btn.isEnabled() and page.run_result is not run, 180):
        raise RuntimeError(f"Retry made no result: {page.progress_text.text()!r}")


@pytest.fixture(scope="module")
def s(eq_screen):
    """The page as guide_checks found it: the result the old checks had on the card by then (Best fit's Run with 3
    and 5 filters, Retry from its filters, saved as "UI check", brought back with History's Show: lines 1528-1587),
    so the page runs on below the Run button as it did there (the wheel's check scrolls it); then 1100x900, as
    guide_checks made it first (line 2632)."""
    eqpage.quick_run(eq_screen)
    _retry(eq_screen)
    eqpage.show_from_history(eq_screen, eqpage.save_result(eq_screen))
    eq_screen.page.resize(1100, 900)
    return eq_screen


@pytest.mark.timeout(900)  # (the result made first: two Best fit runs, each allowed 180 s times the time factor)
def test_every_step_points_at_a_control(s, check):
    from ui import guide, tour
    page = s.page
    probs = tour.problems(page, guide.eq_steps(page))
    # was eq_checks.py:2641
    check("guide: every step of Make an EQ's Guide points at a control that's there and in sight", not probs, probs)


def test_arrow_steps_through_to_done(s, check):
    from PySide6.QtCore import QEvent, Qt
    from PySide6.QtGui import QKeyEvent
    from ui import guide
    page = s.page
    fold = page.settings.fold.btn.isChecked()
    t = guide.start_eq(page)
    seen = []
    for _ in range(len(t.steps)):
        seen.append(t.title.text())
        t.keyPressEvent(QKeyEvent(QEvent.KeyPress, Qt.Key_Right, Qt.NoModifier))
    # was eq_checks.py:2648
    check("guide: → steps through every step to Done; the Settings fold is as it was", len(set(seen)) == len(t.steps)
          and not t.isVisible() and page.settings.fold.btn.isChecked() == fold, (len(set(seen)), t.isVisible()))


@pytest.mark.timeout(900)  # (every demo played, each waited for up to 20 s times the time factor)
def test_demos(s, check):
    # (three checks from one tour, as the old checks worked them out in one go before checking any)
    from PySide6.QtCore import QPoint, QPointF, Qt
    from PySide6.QtGui import QWheelEvent
    from PySide6.QtWidgets import QScrollArea
    from ui import guide, tour
    page, wait_for = s.page, s.wait_for
    # the demos: each played to its end (fast), nothing of yours changed after (settings, the graph's view, the
    # slider, the file name), and a demo left half-way is put back too
    before = json.dumps(page.sw.s, sort_keys=True, default=str)
    before_S = json.dumps(page.S, sort_keys=True, default=str)
    # (nothing a demo does may reach what changes your files or settings: every call to the EQ part is watched)
    real_call, changing = page.svc.call, []

    def watched(path, body=None):
        if path in ("/api/files/move", "/api/files/remove", "/api/use", "/api/presets/save", "/api/presets/delete",
                    "/api/presets/load", "/api/reset", "/api/settings", "/api/target/save", "/api/run", "/api/download"):
            changing.append(path)
        return real_call(path, body) if body is not None else real_call(path)
    with pytest.MonkeyPatch.context() as m:  # (page.svc is eq.service: its call watched until the tour ends)
        m.setattr(page.svc, "call", watched)
        kept = (page.view_combo.currentIndex(), page.yrange_combo.currentIndex(), page.channels_chk.isChecked(),
                page.sa_what.text(), page.name_edit.text(), page.settings.fold.btn.isChecked())
        t = guide.start_eq(page)
        t.all_chk.setChecked(False)
        played, stuck = 0, []
        for i, st in enumerate(t.steps):
            t.go(i)
            if not tour._demo(st):
                continue
            t.speed = 40.0
            t.replay()
            if wait_for(lambda: not t.demo_running, 20):
                played += 1
            else:
                stuck.append(st["title"])
        # with Windows' animation effects off: numbered markers on the controls and the list in the card, nothing moved
        t.glide = False
        t.go(next(n for n, st in enumerate(t.steps) if st["title"] == "How an EQ job goes"))
        t.replay()
        marked = (len(t.markers), "1." in t.acts_lab.text() and "5." in t.acts_lab.text(), t.demo_running)
        t.glide = True
        views = next(n for n, st in enumerate(t.steps) if st["title"] == "Graph views")
        t.go(views)
        t.speed = 40.0
        t.replay()
        wait_for(lambda: page.view_combo.currentData() == "rel" or not t.demo_running, 20)
        mid = page.view_combo.currentData()
        # the card's own controls: Pause and Resume; the wheel scrolls the page and pauses the demo, Resume scrolls back
        t.go(next(n for n, st in enumerate(t.steps) if st["title"] == "Run"))
        t.speed = 1.0
        t.replay()
        wait_for(lambda: t.demo_running, 5)
        t.toggle_pause()
        paused = (t.paused, t.pause_btn.text())
        t.toggle_pause()
        area = next(a for a in page.findChildren(QScrollArea) if a.widget() and a.widget().isAncestorOf(page.run_btn))
        bar = area.verticalScrollBar()
        at = bar.value()
        pos = QPointF(area.viewport().mapTo(page.window(), QPoint(40, 40)))
        t.wheelEvent(QWheelEvent(pos, pos, QPoint(0, 0), QPoint(0, -240), Qt.NoButton, Qt.NoModifier, Qt.NoScrollPhase,
                                 False))
        scrolled = (bar.value() != at, t.paused_by_you, "Resume" in t.pause_btn.text())
        t.toggle_pause()
        resumed = (bar.value() == at, t.paused)
        t.speed = 40.0
        wait_for(lambda: not t.demo_running, 20)
        # the step list: every step by chapter; one chosen opens it
        t.count_btn.click()
        listed = t.step_list.isVisible() and t.step_list.list.count() > len(t.steps)
        item = next(t.step_list.list.item(k) for k in range(t.step_list.list.count())
                    if t.step_list.list.item(k).data(Qt.UserRole) == 1)
        t.step_list._chosen(item)
        jumped = (t.i, t.step_list.isVisible())
        t.end()
    after = json.dumps(page.sw.s, sort_keys=True, default=str)
    after_S = json.dumps(page.S, sort_keys=True, default=str)
    now = (page.view_combo.currentIndex(), page.yrange_combo.currentIndex(), page.channels_chk.isChecked(),
           page.sa_what.text(), page.name_edit.text(), page.settings.fold.btn.isChecked())
    # was eq_checks.py:2725
    # (made firm 2026-10-22: a demo that fails ends as if it had finished, its error only in the log, so "played to
    # its end" counted it too; the tour's demo_errors names each one)
    check("guide: every step's demo plays to its end, a view it shows is put back when the tour ends mid-demo, and "
          "nothing of yours changed (settings, the graph's view, the search chosen, the file name)",
          played >= 20 and not stuck and not t.demo_errors and mid == "rel" and before == after
          and before_S == after_S and now == kept and not changing,
          (played, stuck, t.demo_errors, mid, before == after, before_S == after_S, now, kept, changing))
    # was eq_checks.py:2729
    check("guide: with Windows' animation effects off, a step's demo is numbered markers on its controls and a list "
          "in the card (nothing moves)", marked == (5, True, False), marked)
    # was eq_checks.py:2731
    # (2026-10-23, the Windows 11 look: "Resume" with Windows 11's play symbol beside it, where it was "▶ Resume")
    check("guide: the card's Pause / Resume; the wheel scrolls the page and pauses the demo, Resume scrolls back; the "
          "step list (3 of 28 ▾) goes straight to a step",
          paused == (True, "Resume") and scrolled == (True, True, True) and resumed == (True, False) and listed
          and jumped == (1, False), (paused, scrolled, resumed, listed, jumped))


@pytest.mark.timeout(900)
def test_find_demos_while_find_redraws(s, check):
    # (a bug the tests' reorganization found, fixed 2026-10-22: the demos kept a row of Find…'s list across their
    # pauses, while Find… draws its rows again every half second until its lists and This PC's search finish; the demo
    # then reached for a deleted row and stopped short, with an error inside a Qt call-back. Here Find… redraws every
    # 100 ms while both demos play at their own speed, so their pauses always see their rows drawn again)
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication
    from helpers import qt
    from ui import guide
    from ui.picker import Picker
    page, wait_for = s.page, s.wait_for

    redrawn = []

    def redraw():  # (every widget: the Guide shows Find… inside its own layer, not as a window of its own)
        for w in QApplication.allWidgets():
            if isinstance(w, Picker) and w.isVisible():
                w.render()
                redrawn.append(1)
    timer = QTimer()
    timer.timeout.connect(redraw)
    errors_before = len(qt.QT_ERRORS)
    played, stuck = [], []
    t = guide.start_eq(page)
    t.all_chk.setChecked(False)
    timer.start(100)
    try:
        for title in ("Choose your IEM or headphone", "Many results?"):
            t.go(next(n for n, st in enumerate(t.steps) if st["title"] == title))
            t.speed = 1.0
            t.replay()
            (played if wait_for(lambda: not t.demo_running, 90) else stuck).append(title)
    finally:
        timer.stop()
        t.end()
    errors = qt.QT_ERRORS[errors_before:]
    # (a demo that fails ends as if it had finished, its error only in the log: t.demo_errors names them)
    check("guide: the demos that use Find… (choose the measurement, many results) play to their end while Find… draws "
          "its rows again (as it does while its lists load), reaching for no row that's gone",
          len(played) == 2 and not stuck and not t.demo_errors and not errors and len(redrawn) >= 20,
          (played, stuck, t.demo_errors, errors, len(redrawn)))


@pytest.mark.timeout(900)  # (the tracer's sample traced first, then every demo of its Guide)
def test_tracers_guide(s, check):
    from PySide6.QtWidgets import QMessageBox
    from ui import guide, tour
    page, wait_for = s.page, s.wait_for
    eqpage.open_traced_sample(s)  # (page.tracer, as the old checks had made it by then: trace_checks, line 2772)
    tw = page.tracer
    tw.show()
    with pytest.MonkeyPatch.context() as m:  # (Yes: its picture removed)
        m.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.Yes))
        tw.remove_image()
    t = guide.start_trace(tw)
    opened = tw.t.has_image and tw.sample_open
    probs = tour.problems(tw, guide.trace_steps(tw))
    t.go(7)  # (Auto trace: the sample's curves traced for it)
    traced = sum(map(tw.t.has_data, tw.t.curves))
    t.all_chk.setChecked(False)
    demos, play = 0, []
    for i, st in enumerate(t.steps):
        t.go(i)
        play.append((st["title"], bool(tour._demo(st)), t.replay_btn.isVisible(), t.all_chk.isVisible()))
        if tour._demo(st):
            t.speed = 40.0
            t.replay()
            demos += wait_for(lambda: not t.demo_running, 20)
    t.end()
    # was eq_checks.py:2757
    check("guide: the tracer's Guide opens the sample graph, every step's control is there, its demo traces the "
          "sample, and the tracer is empty again after", opened and not probs and traced >= 2 and not tw.t.has_image
          and not tw.sample_open and demos >= 7, (opened, probs, traced, demos))
    # (2026-10-23: Play demo showed on the tracer's steps that have no demo, doing nothing: its row was put in the
    # card before the demo's box that hides on such a step)
    wrong = [(title, has, shown) for title, has, shown, opts in play if shown != has or opts != has]
    check("guide: the card's Play demo (and Play all steps, the speed) shows on a step with a demo and not on one "
          "without (the tracer's “How tracing a graph goes”, “Automatic settings” …)",
          not wrong and sum(not has for _t, has, _s, _o in play) >= 5, (wrong, play))
    tw.close()


def test_resized_window_and_tab(s, check):
    # (two checks from one tour, as the old checks had them: Tab's answer taken first, then the window resized)
    from ui import guide
    page, qapp = s.page, s.qapp
    t = guide.start_eq(page)
    kept_focus = t.focusNextPrevChild(True) is True and t.focusNextPrevChild(False) is True
    # (review 2) the window resized mid-demo: the kept graph picture is laid out again inside it
    win = t.win
    was_size = win.size()
    t.pin_graph(page.plot)
    win.resize(was_size.width() - 300, was_size.height())
    qapp.processEvents()
    t.place()
    pin_inside = t.pin is not None and t.rect().contains(t.pin.geometry())
    win.resize(was_size)
    qapp.processEvents()
    t.end()
    # was eq_checks.py:1778
    check("review: a resized window keeps the Guide's graph picture inside it, laid out again", pin_inside,
          (t.rect(), t.pin.geometry() if t.pin is not None else None))
    # was eq_checks.py:1780
    check("review: Tab stays in the Guide (the controls under it can't be reached)", kept_focus)


def test_ring_cut_to_the_scroll_area(s, check):
    from ui import tour
    page = s.page
    r = tour._rect(page.window(), [page.listen])
    # was eq_checks.py:1948
    check("review: the Guide's ring is cut to what its scroll area shows", r.height() <= page.window().height(), r.getRect())


def _on_step(page, title):
    """Make an EQ's Guide on a step, its demo not started (it would start by itself after a moment)."""
    from ui import guide
    t = guide.start_eq(page)
    t.all_chk.setChecked(False)
    t.speed = 0.01  # (its demo waits 45 s before it starts by itself: the check has the step to itself)
    t.go(next(n for n, st in enumerate(t.steps) if st["title"] == title))
    return t


def _pixel(img, x, y):
    """A picture's colour at a point of the window (its pixels are the window's times its pixel ratio)."""
    k = img.devicePixelRatio()
    return img.pixelColor(int(x * k), int(y * k)).name()


def _icon_colour(button):
    """The colour of a button's symbol (its first solid pixel), or None without one."""
    img = button.icon().pixmap(button.iconSize()).toImage()
    solid = [img.pixelColor(x, y) for x in range(img.width()) for y in range(img.height())
             if img.pixelColor(x, y).alpha() > 200]
    return solid[0].name() if solid else None


def test_the_guides_look_follows_the_theme(s, check):
    # (2026-10-23, the Windows 11 look: the Guide's own colours moved into the stylesheet, its marks drawn in the
    # accent; before, the ring round what a demo points at and a drag's trail were in c2, which became the graph's
    # pink EQ, and the card's tag and links in c1, the accent's fill colour rather than its text colour)
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QPalette
    from helpers import qt
    from ui import theme
    page, qapp = s.page, s.qapp
    found, symbols = {}, {}
    try:
        for dark in (False, True):
            theme.apply(qapp, dark=dark)
            qapp.processEvents()
            t = _on_step(page, "Run")
            try:
                qapp.processEvents()
                tok = theme.tokens()
                y = t.height() - 30
                t.trail = (QPointF(40, y), QPointF(240, y))
                t.hot_w = page.run_btn
                t.update()
                qapp.processEvents()
                img = t.win.grab().toImage()
                px = lambda x, yy, img=img: _pixel(img, x, yy)
                r = t._w_rect(page.run_btn).adjusted(-3, -3, 3, 3)
                ring = {px(x, yy) for x in range(int(r.left()) + 8, int(r.right()) - 8) for yy in (r.top() - 1, r.top())}
                h = t.holes[0]
                lit = {px(x, yy) for x in range(h.left() + 10, h.right() - 10) for yy in (h.top() - 1, h.top(), h.top() + 1)}
                found["dark" if dark else "light"] = {
                    "trail": px(140, y) == tok["accent"], "ring": tok["accent"] in ring, "lit": tok["accent"] in lit,
                    "tag": t.badge.palette().color(t.badge.foregroundRole()).name() == tok["accent_text"],
                    "links": t.skip_btn.palette().color(QPalette.ButtonText).name() == tok["accent_text"]
                    == t.end_btn.palette().color(QPalette.ButtonText).name()}
            finally:
                t.hot_w = t.trail = None
                t.end()
        t = _on_step(page, "Run")  # (the theme changed while a tour is open: its symbols drawn again)
        try:
            symbols["dark"] = (_icon_colour(t.replay_btn), theme.tokens()["ink"], t.replay_btn.text())
            theme.apply(qapp, dark=False)
            qapp.processEvents()
            symbols["light"] = (_icon_colour(t.replay_btn), theme.tokens()["ink"], t.replay_btn.text())
        finally:
            t.end()
    finally:
        qt.light(qapp)  # (the light theme back, whatever happened: every later test runs light)
        qapp.processEvents()
    check("guide: what's lit, what a demo points at and a drag's trail are drawn in the accent (Windows' own colour, no "
          "longer the graph's pink), the card's “Demo” tag and links in the accent's text colour, light and dark",
          len(found) == 2 and all(all(v.values()) for v in found.values()), found)
    check("guide: the card's buttons have Windows 11's symbols beside their words (Play demo …), drawn again in the "
          "theme's text colour when the theme changes while the Guide is open",
          len(symbols) == 2 and all(c == ink and words == "Play demo" for c, ink, words in symbols.values())
          and symbols["dark"][0] != symbols["light"][0], symbols)


def test_messages_and_keys_fit(s, check):
    # (2026-10-23: a message a demo shows measured itself before its look applied, so at Windows 11's text size it came
    # out 16 px tall, its words hidden; a key cap sat under the pointer's "demo" tag, which hid its name, and stayed on
    # the window when its demo stopped meanwhile, for the rest of the tour)
    from PySide6.QtCore import QPointF, QRect, QRectF, Qt
    from PySide6.QtGui import QFontMetrics
    from PySide6.QtWidgets import QLabel
    from ui import tour
    page, qapp = s.page, s.qapp
    t = _on_step(page, "Run")
    try:
        qapp.processEvents()
        n = t.note("Saved “My EQ”. (Demo: nothing was saved.) A message long enough to take two lines in the card.",
                   page.run_btn)
        m = n.contentsMargins()
        words = QFontMetrics(n.font()).boundingRect(QRect(0, 0, n.width() - m.left() - m.right(), 10000),
                                                    Qt.TextWordWrap, n.text()).height()
        tall = (n.height(), words + m.top() + m.bottom())
        t.cur = QPointF(300, 300)
        key = tour.Api(t).key("Enter")
        next(key)  # (the key shown, as the demo holds it)
        cap = [w for w in t.findChildren(QLabel) if w.objectName() == "tourKey" and w.isVisible()]
        beside = bool(cap) and not QRectF(cap[0].geometry()).intersects(t.tag_rect())
        t.stop_demo()  # (stopped while both are shown: Skip demo, Next, a step chosen from the list)
        left = [w.objectName() for w in t.findChildren(QLabel) if w.objectName() in ("tourNote", "tourKey")
                and w.isVisible()]
    finally:
        t.end()
    check("guide: a message a demo shows is as tall as its words, a key it shows sits beside the pointer's “demo” tag, "
          "and both go when the demo stops",
          tall[0] >= tall[1] and beside and not left, (tall, beside, left))


# The demos that show one of the app's windows inside the Guide (Find…, Which measurement, History), and the sizes
# they're looked at in: the app's own (its window as it first opens) and its window's smallest
WINDOW_DEMOS = ("Choose a target", "Choose your IEM or headphone", "Many results?",
                "Several measurements of the same model?", "History")
SIZES = {"the app's own size": (1040, 760), "the window's smallest": (965, 433)}


def _ancestors(w, until):
    p = w.parentWidget()
    while p is not None and p is not until:
        yield p
        p = p.parentWidget()


@pytest.mark.timeout(900)  # (five demos at two sizes, each waited for up to 30 s times the time factor)
def test_demo_windows_fit_their_frames(s, check, monkeypatch):
    # (2026-10-23, after the restyle: Which measurement's own smallest size, 700 x 660, was bigger than the frame the
    # Guide gives it at the app's own size, so it was cut 100 px at the right and 123 at the bottom, its Compare and
    # Close hidden; at the window's smallest size Find…, Which measurement and History were cut at the bottom and the
    # card covered them. Each window is looked at as it opens, its demo paused there as P pauses it)
    from PySide6.QtCore import QPoint, QRect
    from PySide6.QtWidgets import QAbstractButton, QAbstractScrollArea, QComboBox, QLineEdit, QScrollArea, QWidget
    from helpers import qt
    from ui import guide, tour
    page, wait_for = s.page, s.wait_for
    shown = []
    real = tour.Api.window

    def window(api, w, *a, **k):
        out = real(api, w, *a, **k)
        shown.append(w)
        api.t.toggle_pause()
        return out
    monkeypatch.setattr(tour.Api, "window", window)
    was = page.size()
    seen, bad, missing = {}, [], []
    try:
        for size_name, size in SIZES.items():
            page.resize(*size)
            qt.pump(200)
            t = guide.start_eq(page)
            t.all_chk.setChecked(False)
            try:
                for title in WINDOW_DEMOS:
                    t.go(next(n for n, st in enumerate(t.steps) if st["title"] == title))
                    n = len(shown)
                    t.speed = 4.0
                    t.replay()
                    wait_for(lambda n=n, t=t: len(shown) > n or not t.demo_running, 30)
                    if len(shown) == n:
                        missing.append((size_name, title))
                        continue
                    qt.pump(150)
                    wait_for(lambda t=t: not t.card_timer.isActive(), 5)  # (the card placed again, off the window)
                    qt.pump(100)
                    w = shown[-1]
                    frame = w.frame
                    inner = frame.rect().adjusted(1, 1, -1, -1)  # (inside its border)
                    # (a window taller than the tour's room scrolls inside its frame: what's in sight is its view)
                    area = next((a for a in frame.findChildren(QScrollArea) if a.objectName() == "tourWinScroll"), None)
                    view = inner if area is None else QRect(area.viewport().mapTo(frame, QPoint(0, 0)),
                                                            area.viewport().size()).intersected(inner)
                    body = QRect(w.mapTo(frame, QPoint(0, 0)), w.size())
                    tall = w.height() >= w.minimumSizeHint().height()  # (not squeezed: the room its parts need)
                    fits = tall and (inner.contains(body) if area is None else
                                     view.left() <= body.left() and body.right() <= view.right())
                    hidden = []
                    for c in w.findChildren(QWidget):
                        if not isinstance(c, (QAbstractButton, QLineEdit, QComboBox)) or not c.isVisible() \
                                or any(isinstance(p, QAbstractScrollArea) for p in _ancestors(c, w)):
                            continue  # (a row of one of its lists: they scroll)
                        if area is not None:
                            area.ensureWidgetVisible(c, 0, 0)  # (what scrolling the frame would bring into sight)
                        if not view.intersected(QRect(w.mapTo(frame, QPoint(0, 0)), w.size())).contains(
                                QRect(c.mapTo(frame, QPoint(0, 0)), c.size())):
                            words = c.currentText() if isinstance(c, QComboBox) else c.text()
                            hidden.append(words or c.accessibleName() or type(c).__name__)
                    if area is not None:
                        area.verticalScrollBar().setValue(0)
                    over = t.bubble.geometry().intersects(frame.geometry())
                    seen[(size_name, title)] = (frame.size().toTuple(), body.size().toTuple(), area is not None)
                    if not fits or hidden or over:
                        bad.append((size_name, title, w.windowTitle(), {"frame": frame.geometry().getRect(),
                                    "window": body.getRect(), "scrolls": area is not None, "hidden": hidden,
                                    "card over it": over}))
                    t.skip_demo()
            finally:
                t.end()
    finally:
        shown.clear()  # (the windows are gone with their demos: nothing kept of them)
        page.resize(was)
        qt.pump(200)
    check("guide: every window a demo shows (Find…, Which measurement, History) fits its frame (as wide as it; one "
          "taller than the tour has room for scrolls inside it), its buttons and boxes all in sight (or scrolled to), "
          "and the card beside it, not over it, at the app's own size (1040 x 760) and at the window's smallest "
          "(965 x 433)", not bad and not missing and len(seen) == len(WINDOW_DEMOS) * len(SIZES),
          (bad, missing, seen))


@pytest.mark.timeout(900)  # (every step's before and after, as test_every_step_points_at_a_control)
def test_every_step_in_sight_at_the_smallest_size(s, check):
    # (2026-10-23: at the window's smallest size tour.problems() said Choose your IEM or headphone was outside the
    # window: it measured straight after the step before had closed Adjust, before the page had settled; and the Guide
    # itself, going on from that step, scrolled the page past the Measurement card the same way)
    from helpers import qt
    from ui import guide, tour
    page = s.page
    was = page.size()
    lost = []
    try:
        page.resize(965, 360)  # (Make an EQ's room at the window's smallest, 965 x 433: its top bar and status line out)
        qt.pump(200)
        at = page.size().toTuple()
        probs = tour.problems(page, guide.eq_steps(page))
        t = guide.start_eq(page)  # (then the Guide itself, step by step with →, each step's demo not started)
        try:
            t.all_chk.setChecked(False)
            t.speed = 0.01
            for i in range(len(t.steps)):
                t.go(i)
                t.stop_demo()
                r = tour._rect(t.win, t.target or [])
                if not t.win.rect().intersects(r) or r.width() < 4 or r.height() < 4 or not t.holes:
                    lost.append((t.i + 1, t.steps[t.i]["title"], r.getRect()))
        finally:
            t.end()
    finally:
        page.resize(was)
        qt.pump(200)
    check("guide: at the window's smallest size too every step of Make an EQ's Guide points at a control that's there "
          "and in sight", not probs and at == (965, 360), (at, probs))
    check("guide: at the window's smallest size the Guide shows each step's control in sight as it goes from step to "
          "step (the page scrolled once it's laid out again: a fold the step before opened is closed by then)",
          not lost and at == (965, 360), (at, lost))


def test_ring_joins_cards_that_touch(s, check):
    # (2026-10-23: two lit cards that touch, step 1's Target and Measurement, were drawn as two rings whose round
    # corners met in a small notch at both sides, pointing in)
    from ui import guide, theme, tour
    page, qapp = s.page, s.qapp
    t = guide.start_eq(page)
    try:
        t.all_chk.setChecked(False)
        s.wait_for(lambda: t.demo_running, 10)  # (step 1's demo starts by itself: stopped, as Skip demo does)
        t.stop_demo()
        qapp.processEvents()
        tb, mb = tour._rect(t.win, [page.target_box]), tour._rect(t.win, [page.measurement_box])
        touch = mb.top() - tb.bottom() - 1 - 2 * tour.PAD  # (the room between their lit rectangles: none)
        y = (tb.bottom() + mb.top()) // 2  # (where they meet)
        left, right = min(tb.left(), mb.left()) - tour.PAD, max(tb.right(), mb.right()) + tour.PAD
        img = t.win.grab().toImage()
        acc = theme.tokens()["accent"]
        ring = (any(_pixel(img, x, y) == acc for x in range(left - 1, left + 2)),
                any(_pixel(img, x, y) == acc for x in range(right - 1, right + 3)))
        holes = [h.getRect() for h in t.holes]
    finally:
        t.end()
    check("guide: two lit cards that touch (step 1's Target and Measurement) are lit as one, the ring's sides running "
          "straight past where they meet (no notch)", touch <= 0 and ring == (True, True) and len(holes) == 1,
          (touch, ring, holes))


def test_step_list_headings(s, check):
    # (2026-10-23: the step list's chapter headings were small capitals, smaller and greyed: Windows 11's group
    # headings, and Find…'s, are the list's own text in semibold, their words as written)
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QFont
    from ui import theme
    page = s.page
    t = _on_step(page, "Run")
    try:
        t.count_btn.click()
        lst = t.step_list.list
        heads = [(lst.item(k).text(), lst.item(k).font().weight(), lst.item(k).font().pointSizeF(),
                  lst.item(k).foreground().color().name()) for k in range(lst.count())
                 if lst.item(k).data(Qt.UserRole) is None]
        size, ink = lst.font().pointSizeF(), theme.tokens()["ink"]
        chapters = list(dict.fromkeys(st.get("chapter") for st in t.steps))
    finally:
        t.end()
    check("guide: the step list's chapter headings are as Windows 11's (and Find…'s) group headings: their words as "
          "written (“1 · Choose”, not capitals), semibold, the list's own size and text colour",
          [h[0] for h in heads] == chapters and all(w == QFont.Weight.DemiBold and abs(p - size) < 0.01 and c == ink
                                                   for _t, w, p, c in heads), (heads, chapters, size, ink))


def _differs(c, bg, by=60):
    """A pixel clearly not the background (the shape's own, not its edge's faint blend)."""
    return sum(abs(a - b) for a, b in zip(c.getRgb()[:3], bg.getRgb()[:3])) > by


def _runs(img, x0, x1, y0, y1, bg):
    """The stretches [(first, last)] of columns with ink in them, left to right (a button's words, then its chevron)."""
    found, start = [], None
    for x in range(x0, x1 + 1):
        on = x < x1 and any(_differs(img.pixelColor(x, y), bg) for y in range(y0, y1))
        if on and start is None:
            start = x
        elif not on and start is not None:
            found.append((start, x - 1))
            start = None
    return found


def _ink_box(img, x0, x1, y0, y1, bg):
    """[left, top, right, bottom] of the ink in a part of a picture, or None."""
    pts = [(x, y) for x in range(x0, x1) for y in range(y0, y1) if _differs(img.pixelColor(x, y), bg)]
    return [min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)] if pts \
        else None


def _chevron(img, x0, x1, y0, y1, bg):
    """The last shape in a part of a picture: its size, whether it's open at its top's middle (as a chevron is; a typed
    ▾ is filled there), the room before it (after the shape before it) and after it; None without a shape."""
    found = _runs(img, x0, x1, y0, y1, bg)
    if not found:
        return None
    box = _ink_box(img, found[-1][0], found[-1][1] + 1, y0, y1, bg)
    return {"size": (box[2] - box[0] + 1, box[3] - box[1] + 1),
            "open": not _differs(img.pixelColor((box[0] + box[2]) // 2, box[1] + 1), bg),
            "before": found[-1][0] - found[-2][1] - 1 if len(found) > 1 else None, "after": x1 - 1 - box[2]}


def test_step_list_button_chevron(s, check):
    # (2026-10-23: the step list's button ended in a typed ▾, where the app's drop-downs and menu buttons have Windows
    # 11's chevron)
    from PySide6.QtCore import QPoint, QRect
    from helpers import qt
    from ui import theme
    page, qapp = s.page, s.qapp
    seen = {}
    try:
        for dark in (True, False):
            theme.apply(qapp, dark=dark)
            qapp.processEvents()
            t = _on_step(page, "Run")
            try:
                qapp.processEvents()
                b = t.count_btn  # (on its card: the button has no fill of its own)
                img = t.bubble.grab(QRect(b.mapTo(t.bubble, QPoint(0, 0)), b.size())).toImage()
                mine = _chevron(img, 2, img.width(), 3, img.height() - 3, img.pixelColor(1, img.height() // 2))
                combo = page.mode_combo  # (a drop-down's chevron, in the room at its right)
                img = combo.grab().toImage()
                theirs = _chevron(img, combo.width() - 26, combo.width() - 1, 4, combo.height() - 4,
                                  img.pixelColor(combo.width() - 3, 4))
                seen["dark" if dark else "light"] = (b.text(), mine, theirs and theirs["size"])
            finally:
                t.end()
    finally:
        qt.light(qapp)  # (the light theme back, whatever happened: every later test runs light)
        qapp.processEvents()
    check("guide: the step list's button shows Windows 11's chevron after its words, the drop-downs' own, clear of its "
          "words and its edge (not a typed ▾); light and dark",
          len(seen) == 2 and all("▾" not in words and mine and mine["open"] and (mine["before"] or 0) >= 5
                                 and mine["after"] >= 6 and theirs
                                 and all(abs(a - b) <= 1 for a, b in zip(mine["size"], theirs))
                                 for words, mine, theirs in seen.values()), seen)


def test_lists_a_demo_shows(s, check):
    # (2026-10-23: a drop-down's list a demo shows marked the row in use only in semibold, where the real list fills it
    # and puts the accent's bar beside it, the mark following the mouse, and had no search box where the real long list
    # has one; a menu a demo shows had a list's rows and round corners, a submenu a typed ▸ after its words)
    from PySide6.QtCore import QPoint, QRect
    from PySide6.QtWidgets import QLabel, QLineEdit, QMenu, QWidget
    from helpers import qt
    from ui import guide_demos, theme, tour
    page = s.page
    win, tk, combo = page.window(), theme.tokens(), page.mode_combo

    def row(img, r):
        """A row's look: its fill, the colour at its left edge (the accent's bar on a marked list row), its height,
        where its words start."""
        fill = img.pixelColor(r.right() - 6, r.center().y())
        words = next((x for x in range(r.left() + 4, r.right()) if any(
            _differs(img.pixelColor(x, y), fill, 100) for y in range(r.top() + 4, r.bottom() - 3))), None)
        return {"fill": fill.name(), "edge": img.pixelColor(r.left() + 1, r.center().y()).name(), "height": r.height(),
                "words": words if words is None else words - r.left()}

    def alike(a, b):
        return a["fill"] == b["fill"] and a["edge"] == b["edge"] and a["height"] == b["height"] \
            and a["words"] is not None and b["words"] is not None and abs(a["words"] - b["words"]) <= 1

    def after_arrow(img, r):
        """The room after a submenu's chevron, to its row's right edge (its last shape: the chevron)."""
        found = _runs(img, r.left() + 4, r.right() + 1, r.top() + 2, r.bottom() - 1, img.pixelColor(r.right() - 2,
                                                                                                    r.top() + 2))
        return r.right() - found[-1][1] if found else None

    def text_box(w):
        """A text box's look: its height, its fill, the line under it, where its (grey) words start, their colour
        (their darkest pixel)."""
        img = w.grab().toImage()
        bg = img.pixelColor(4, img.height() // 2)
        ink = [(x, y) for x in range(2, min(img.width() - 2, 160)) for y in range(4, img.height() - 4)
               if _differs(img.pixelColor(x, y), bg)]
        darkest = min((img.pixelColor(x, y) for x, y in ink), key=lambda c: c.lightness(), default=None)
        return {"height": img.height(), "fill": bg.name(), "line": img.pixelColor(img.width() // 2, img.height() - 1).name(),
                "words": min((x for x, _y in ink), default=None), "colour": darkest and darkest.name()}
    combo.showPopup()  # (the real list, as it opens)
    qt.pump(100)
    view = combo.view()
    pop = view.window()
    vr = view.visualRect(view.currentIndex())
    real = row(pop.grab().toImage(), QRect(view.viewport().mapTo(pop, vr.topLeft()), vr.size()))
    combo.hidePopup()
    qt.pump(50)
    page.app_combo.showPopup()  # (the real long list as it opens: its search box ready for typing)
    qt.pump(100)
    q = next(w for w in page.app_combo.findChildren(QWidget) if w.objectName() == "searchPopup").findChild(QLineEdit)
    q.setReadOnly(True)  # (its blinking caret not drawn, for the moment of the picture: its look is the same)
    qt.pump(50)
    real_box = dict(text_box(q), typing=q.hasFocus())
    q.setReadOnly(False)
    page.app_combo.hidePopup()
    qt.pump(50)
    t = _on_step(page, "Pick an EQ method")
    try:
        api = tour.Api(t)
        g = guide_demos.mock_combo(api, combo, combo.count() - 1)
        next(g)  # (the list shown, as the demo opens it)
        qt.pump(50)
        m = next(w for w in t.inside if isinstance(w, tour.Mock))
        cur = combo.currentIndex()
        mock = row(m.grab().toImage(), m.rows[cur].geometry())
        other = (cur + 1) % len(m.rows)
        m.hover(other)  # (the pointer on another row)
        qt.pump(50)
        img = m.grab().toImage()
        moved = (row(img, m.rows[other].geometry())["edge"], row(img, m.rows[cur].geometry())["fill"])
        under = m.geometry().top() - combo.mapTo(win, QPoint(0, combo.height())).y()  # (the room between them)
        t.stop_demo()
        g = guide_demos.mock_combo(api, page.app_combo, 5)  # (a long list: the real one has its search box)
        next(g)
        qt.pump(50)
        m = next(w for w in t.inside if isinstance(w, tour.Mock))
        box = m.findChild(QLabel, "tourMockSearch")
        mock_box = dict(text_box(box), typing=True) if box is not None else None
        search = box is not None and box.isVisible() and box.text() == q.placeholderText() \
            and box.geometry().bottom() < m.rows[0].geometry().top() and mock_box == real_box \
            and real_box["line"] == tk["accent"]
        t.stop_demo()
        items = [("No presets yet", False), "Save current settings as…", None, "Try for 5 minutes on ▸"]
        g = guide_demos.mock_menu(api, page.use_btn, items)  # (a menu, as the demos show Presets' and Use on device's)
        next(g)
        qt.pump(50)
        m = next(w for w in t.inside if isinstance(w, tour.Mock))
        m.hover(1)
        qt.pump(50)
        img = m.grab().toImage()
        menu = dict(row(img, m.rows[1].geometry()), corner=img.pixelColor(0, 0).name(),
                    arrow=after_arrow(img, m.rows[3].geometry()))
        t.stop_demo()
    finally:
        t.end()
    real_m = QMenu(page)  # (a real menu in the app's look, the same rows, its item pointed at)
    real_m.addAction("No presets yet").setEnabled(False)
    act = real_m.addAction("Save current settings as…")
    real_m.addSeparator()
    sub = real_m.addMenu("Try for 5 minutes on")
    sub.addAction("Headphones")
    real_m.resize(real_m.sizeHint())
    real_m.setActiveAction(act)
    img = real_m.grab().toImage()
    real_menu = dict(row(img, real_m.actionGeometry(act)), corner=img.pixelColor(0, 0).name(),
                     arrow=after_arrow(img, real_m.actionGeometry(sub.menuAction())))
    qt.close(real_m)
    check("guide: a drop-down's list a demo shows looks as the real one: the row in use filled with the accent's bar "
          "beside it, the mark following the pointer, the rows as tall and their words where the real list has them, "
          "just under its box; a long list with its search box above its rows, as the real one's",
          alike(mock, real) and real["fill"] == tk["sel"] and real["edge"] == tk["accent"]
          and moved == (tk["accent"], tk["menu"]) and 0 <= under <= 3 and search,
          (mock, real, moved, under, mock_box, real_box))
    check("guide: a menu a demo shows looks as a real one: the row pointed at filled without a bar, the rows as tall "
          "and their words where the real menu has them, its corners square, a submenu's chevron where the real one's "
          "is", alike(menu, real_menu) and menu["corner"] == real_menu["corner"] == tk["stroke"]
          and menu["edge"] == menu["fill"] and menu["arrow"] is not None and real_menu["arrow"] is not None
          and abs(menu["arrow"] - real_menu["arrow"]) <= 1, (menu, real_menu))
