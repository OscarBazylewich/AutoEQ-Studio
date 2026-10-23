"""The Guides (ui\\guide.py over ui\\tour.py) on Make an EQ: every step's control there and in sight; → steps through
every step to Done; every step's demo played to its end with nothing of yours changed (and with Windows' animation
effects off, numbered markers instead); the card's Pause / Resume, the wheel and the step list; the tracer's Guide on
the sample graph; a resized window keeping the Guide's graph picture inside it; Tab staying in the Guide; the ring cut
to what its scroll area shows.

Moved from eq_checks.py's guide_checks (lines 2625-2760), review_checks (1764-1780) and review_low_checks (1946-1948),
on a page opened as the old checks opened it (the eq_screen fixture) with the result they had on the card by then (a
run, Retry, saved, brought back with History's Show), 1100x900 as guide_checks made it (line 2632, kept for the
later checks there), offline throughout: the old checks were online here and the demos' Find… then refreshed every
database list from the internet, which nothing here needs.

Windows' animation effects: a tour reads them as it starts (tour._animations_on). The old checks ran where they were
on, so the demos glided; here they're taken as on for every tour of this file, whatever this PC's setting, and the
check of the markers turns them off itself, as the old one did (t.glide = False).

Two demos print an error inside a Qt call-back, known app bugs left as they are (PLAN.md open question 1): "many
results" (ui\\guide_eq.py line 88, many_results, "QListWidgetItem already deleted") and "choose the measurement"
(ui\\guide_demos.py line 296, choose_row, "QWidget already deleted"); guide.py lines 473 and 300 before the Guide was
split into three files. They don't fail the test (helpers.qt records them)."""
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
    check("guide: every step's demo plays to its end, a view it shows is put back when the tour ends mid-demo, and "
          "nothing of yours changed (settings, the graph's view, the search chosen, the file name)",
          played >= 20 and not stuck and mid == "rel" and before == after and before_S == after_S and now == kept
          and not changing, (played, stuck, mid, before == after, before_S == after_S, now, kept, changing))
    # was eq_checks.py:2729
    check("guide: with Windows' animation effects off, a step's demo is numbered markers on its controls and a list "
          "in the card (nothing moves)", marked == (5, True, False), marked)
    # was eq_checks.py:2731
    check("guide: the card's Pause / Resume; the wheel scrolls the page and pauses the demo, Resume scrolls back; the "
          "step list (3 of 28 ▾) goes straight to a step",
          paused == (True, "▶ Resume") and scrolled == (True, True, True) and resumed == (True, False) and listed
          and jumped == (1, False), (paused, scrolled, resumed, listed, jumped))


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
    demos = 0
    for i, st in enumerate(t.steps):
        t.go(i)
        if tour._demo(st):
            t.speed = 40.0
            t.replay()
            demos += wait_for(lambda: not t.demo_running, 20)
    t.end()
    # was eq_checks.py:2757
    check("guide: the tracer's Guide opens the sample graph, every step's control is there, its demo traces the "
          "sample, and the tracer is empty again after", opened and not probs and traced >= 2 and not tw.t.has_image
          and not tw.sample_open and demos >= 7, (opened, probs, traced, demos))
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
