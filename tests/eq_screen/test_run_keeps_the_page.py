"""Make an EQ's page while a run goes on (ui\\eq_page_result.py's run and _poll_job; the user's find, 2026-11-13: a
click on Calculate took the page to its top). A click on Calculate gives it the focus, as Space does. The run turns
Calculate, Queue… and Calculate from these filters off, and Qt gave the focus of a button that it turns off to the next
control in the page's order: the Target row's Adjust…, at the page's top. The page's scroll area then scrolled to that
control (597 px to 0, measured). Cancel, hidden with the focus at the end of a run, did the same. Now Cancel gets the
focus while the run goes on, and the button that the run began from gets it back at the end; the page stays where it
is, and the result card is scrolled into sight at the end as before (UI-RULES 30). One page for the file (the
eq_screen fixture)."""
from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from helpers import qt


def _name(w):
    """A control as a check's detail names it: its class and its words."""
    if w is None:
        return None
    words = w.text() if callable(getattr(w, "text", None)) else ""
    return f"{type(w).__name__} {words or w.accessibleName()!r}"


def _quick(page, counts=(3, 5)):
    page.choose_app("apo")
    page.S["auto"]["enabled"] = False
    page.S["best_fit"].update(filter_counts=list(counts), random_starts=0, gain_max=[6], q_max=[2],
                              seed_with_site=False)
    page.set_way("auto", remember=False)


def _in_sight(page, w):
    """Whether all of the widget shows in the page's scroll area."""
    vp = page.page_area.viewport()
    return w.isVisible() and vp.rect().contains(QRect(w.mapTo(vp, QPoint(0, 0)), w.size()))


def _at_calculate(page):
    """The page scrolled so that Calculate is in sight and not at the page's top, the window active (a click and a
    key go to an active window only). The page's position: its scroll bar's value."""
    page.activateWindow()
    page.page_area.ensureWidgetVisible(page.run_btn, 0, 200)
    qt.pump(60)
    return page.page_area.verticalScrollBar().value()


def _tab_to(page, w):
    """The focus on w with the Tab key, as a keyboard user puts it there: from the control before it in the page's
    order. (The window then draws the focus frame, as after any key that moves the focus.)"""
    before = w.previousInFocusChain()
    while not (before.focusPolicy() & Qt.TabFocus and before.isVisible() and before.isEnabled()):
        before = before.previousInFocusChain()
    before.setFocus(Qt.OtherFocusReason)
    QTest.keyClick(before, Qt.Key_Tab)
    qt.pump(30)


def _done(eq_screen):
    """The run waited for (180 s): whether it ended."""
    page = eq_screen.page
    return eq_screen.wait_for(lambda: page.run_btn.isEnabled(), 180)


def _result_in_sight(page):
    area, box = page.page_area, page.result_box
    top = box.mapTo(area.widget(), QPoint(0, 0)).y()
    bar = area.verticalScrollBar()
    return box.isVisible() and bar.value() <= top <= bar.value() + area.viewport().height()


def test_a_click_on_calculate_keeps_the_page(eq_screen, check):
    page = eq_screen.page
    _quick(page)
    bar = page.page_area.verticalScrollBar()
    at = _at_calculate(page)
    calc_y = page.run_btn.mapTo(page.page_area.viewport(), QPoint(0, 0)).y()
    seen = {}
    QTest.mouseClick(page.run_btn, Qt.LeftButton, Qt.NoModifier, QPoint(10, 10))
    seen["after the click"] = bar.value()
    qt.pump(100)
    seen["the run started"] = bar.value()
    focus = QApplication.focusWidget()
    cancel_seen = _in_sight(page, page.cancel_btn)
    eq_screen.wait_for(lambda: page.progress.value() > 0 or page.run_btn.isEnabled(), 60)
    seen["while it runs"] = bar.value()
    done = _done(eq_screen)
    seen["when it is done"] = bar.value()  # (the result card is scrolled to 0 ms after this)
    qt.pump(150)
    check("eq page: a click on Calculate leaves the page where it was while the run goes on (it went to the page's "
          "top, to the Target row's Adjust…)",
          at > 0 and calc_y > 0 and done and set(seen.values()) == {at}, (at, calc_y, seen))
    check("eq page: while a run goes on, the keyboard focus is on its Cancel, in sight (it went to the Target row's "
          "Adjust…)", focus is page.cancel_btn and cancel_seen, (_name(focus), cancel_seen))
    focus = QApplication.focusWidget()
    check("eq page: a run done, its result card is scrolled into sight, and the focus is on Calculate again",
          _result_in_sight(page) and focus is page.run_btn, (bar.value(), _name(focus)))


def test_space_on_calculate_keeps_the_page(eq_screen, check, tmp_path):
    from ui import theme
    page = eq_screen.page
    _quick(page, counts=(4, 6, 8, 10))  # (a longer run: the pictures are taken while it goes on)
    bar = page.page_area.verticalScrollBar()
    _at_calculate(page)
    _tab_to(page, page.run_btn)
    at = bar.value()
    tabbed = QApplication.focusWidget() is page.run_btn
    QTest.keyClick(page.run_btn, Qt.Key_Space)
    # (the page kept as it is while a run goes on, for the pictures: the job's end is read only when its timer starts
    # again. A run that ended before the dark picture failed the check under a full test load)
    page._poll.stop()
    after = bar.value()
    qt.pump(100)
    focus, running = QApplication.focusWidget(), not page.run_btn.isEnabled()
    cancel_seen = _in_sight(page, page.cancel_btn)
    pictures = {}
    try:
        for dark in (False, True):  # (the page while the run goes on: Cancel with the focus frame, in both themes)
            theme.apply(qt.app(), dark=dark)
            qt.pump(150)
            name = "run-dark.png" if dark else "run-light.png"
            pictures[name] = (qt.picture(page).save(str(tmp_path / name)), not page.run_btn.isEnabled())
    finally:
        theme.apply(qt.app(), dark=False)
        page._poll.start()
    done = _done(eq_screen)
    qt.pump(150)
    end_focus = QApplication.focusWidget()
    check("eq page: Space on Calculate (the focus put there with Tab) leaves the page where it was, and the focus goes "
          "to Cancel, in sight",
          tabbed and running and at > 0 and after == at and focus is page.cancel_btn and cancel_seen,
          (tabbed, running, at, after, _name(focus), cancel_seen))
    check("eq page: pictures of the page while a run goes on, in light and dark (Cancel with the focus)",
          pictures == {"run-light.png": (True, True), "run-dark.png": (True, True)}, (pictures, str(tmp_path)))
    check("eq page: a run started with Space ends with the focus on Calculate again",
          done and end_focus is page.run_btn, _name(end_focus))


def test_cancel_gives_the_focus_back_to_calculate(eq_screen, check):
    page = eq_screen.page
    _quick(page, counts=(4, 6, 8, 10))
    bar = page.page_area.verticalScrollBar()
    _at_calculate(page)
    QTest.mouseClick(page.run_btn, Qt.LeftButton, Qt.NoModifier, QPoint(10, 10))
    page._poll.stop()  # (Cancel kept in sight until it is clicked, however soon the job ends: read when it starts)
    qt.pump(50)
    at = bar.value()
    QTest.mouseClick(page.cancel_btn, Qt.LeftButton, Qt.NoModifier, QPoint(10, 10))
    clicked = QApplication.focusWidget() is page.cancel_btn  # (a click gives Cancel the focus)
    page._poll.start()
    done = _done(eq_screen)
    qt.pump(150)
    focus = QApplication.focusWidget()
    check("eq page: Cancel clicked, the page stays where it was when the run stops, and the focus goes back to "
          "Calculate (Cancel, hidden with the focus, gave it to the Target row's Adjust… at the page's top)",
          clicked and done and bar.value() == at and focus is page.run_btn and not page.cancel_btn.isVisible(),
          (clicked, at, bar.value(), _name(focus), page.progress_text.text()))


def test_calculate_from_these_filters_gives_the_focus_to_cancel(eq_screen, check):
    page = eq_screen.page
    _quick(page)
    if page.current()[1] is None:
        QTest.mouseClick(page.run_btn, Qt.LeftButton, Qt.NoModifier, QPoint(10, 10))
        _done(eq_screen)
        qt.pump(150)
    page.activateWindow()
    page.page_area.ensureWidgetVisible(page.retry_btn, 0, 200)
    qt.pump(60)
    # (the button's menu closed, the focus is on the button again when its action starts the run: Qt's menu)
    page.retry_btn.setFocus(Qt.MouseFocusReason)
    adjust = page.retry_btn.menu().actions()[0]
    adjust.trigger()
    qt.pump(100)
    focus = QApplication.focusWidget()
    cancel_seen = _in_sight(page, page.cancel_btn)
    done = _done(eq_screen)
    qt.pump(150)
    end_focus = QApplication.focusWidget()
    check("eq page: Calculate from these filters gives the focus to Cancel, in sight with the run's progress (it went "
          "to the filters' table), and back to Calculate from these filters at the end",
          adjust.text() == "Adjust them" and focus is page.cancel_btn and cancel_seen and done
          and end_focus is page.retry_btn,
          (adjust.text(), _name(focus), cancel_seen, _name(end_focus)))


def test_a_focus_moved_during_the_run_stays_there(eq_screen, check):
    # (2026-11-15, the verifier: the focus goes back to the button of the run only when Cancel still has it. A keyboard
    # user who goes on to a different control while the app calculates keeps the focus there at the end)
    page = eq_screen.page
    _quick(page, counts=(4, 6, 8, 10))
    _at_calculate(page)
    QTest.mouseClick(page.run_btn, Qt.LeftButton, Qt.NoModifier, QPoint(10, 10))
    page._poll.stop()  # (the run kept going on until the focus has moved: read when its timer starts)
    qt.pump(50)
    on_cancel = QApplication.focusWidget() is page.cancel_btn
    QTest.keyClick(page.cancel_btn, Qt.Key_Tab)  # (to the next control in the page's order)
    qt.pump(50)
    moved_to = QApplication.focusWidget()
    page._poll.start()
    done = _done(eq_screen)
    qt.pump(150)
    end_focus = QApplication.focusWidget()
    check("eq page: a focus that the user moves from Cancel to a different control while the run goes on stays on "
          "that control when the run is done",
          on_cancel and done and moved_to not in (None, page.cancel_btn, page.run_btn) and end_focus is moved_to,
          (on_cancel, done, _name(moved_to), _name(end_focus)))


def test_a_run_whose_button_went_gives_the_focus_to_calculate(eq_screen, check):
    # (2026-11-15, the verifier: at the end the focus goes back to the button of the run only when it shows and is on.
    # The result card can go while the run goes on, its EQ removed from EQs that you made: Calculate from these
    # filters is hidden then, and a hidden control with the focus is a keyboard user's place lost)
    page = eq_screen.page
    _quick(page, counts=(4, 6, 8, 10))
    if page.current()[1] is None:
        QTest.mouseClick(page.run_btn, Qt.LeftButton, Qt.NoModifier, QPoint(10, 10))
        _done(eq_screen)
        qt.pump(150)
    page.activateWindow()
    page.page_area.ensureWidgetVisible(page.retry_btn, 0, 200)
    qt.pump(60)
    page.retry_btn.setFocus(Qt.MouseFocusReason)  # (its menu closed: the focus on the button again, Qt's menu)
    page.retry_btn.menu().actions()[0].trigger()
    page._poll.stop()  # (the run kept going on until the card has gone: read when its timer starts)
    qt.pump(50)
    on_cancel = QApplication.focusWidget() is page.cancel_btn
    while page.session_runs:  # (Remove on the result card until no EQ is left: the card goes)
        page.remove_run()
    qt.pump(50)
    gone = not page.retry_btn.isVisible() and QApplication.focusWidget() is page.cancel_btn
    QTest.keyClick(page.cancel_btn, Qt.Key_Space)  # (the run stopped with the keyboard)
    page._poll.start()
    done = _done(eq_screen)
    qt.pump(150)
    end_focus = QApplication.focusWidget()
    check("eq page: a run from Calculate from these filters whose result card went meanwhile gives the focus to "
          "Calculate at the end, in sight (not to the hidden Calculate from these filters)",
          on_cancel and gone and done and end_focus is page.run_btn and _in_sight(page, page.run_btn),
          (on_cancel, gone, done, _name(end_focus), end_focus is not None and end_focus.isVisible()))
