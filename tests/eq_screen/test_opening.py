"""Make an EQ opening (ui\\eq_page.py): the app's files drawn (the curves, the automatic settings), the line under
File name saying what Save writes from the start (2026-10-23), and your EQ app setting the method and what Save
writes. Moved from eq_checks.py's ui_checks (the page opened as the old checks opened it: helpers.eqpage.open_screen,
on the settings they started from).

At the end: no control was shown as a window of its own while this file ran. The stray watch itself (helpers.qt)
watches every Qt test of the session, from before the page is made: the stray_check fixture fails the test in which a
control was shown as a window of its own, naming it, and at the end of a session in which none ever was, the check is
logged once as ok (tests\\conftest.py). The last test here checks that the watch is really there and found nothing."""
import pytest

from helpers import qt


@pytest.fixture(scope="module", autouse=True)
def strays_before():
    """Whether the stray watch had found something before this file (in a test of another file marked allow_strays):
    then only what it finds during this file can be told apart. (First: before the page is opened.)"""
    watch = qt.stray_watch()
    return watch is not None and watch.seen_any


@pytest.fixture(scope="module", autouse=True)
def settled(strays_before, eq_screen):
    """After the file's last test, the page's background work finished before the eq_screen fixture closes it: each
    load that ends starts the next in the background (the curves, their analysis, the automatic settings), and one
    still on its way once the page is deleted answers a page that's gone (an error inside a Qt call-back, "Internal
    C++ object already deleted"). Quiet for half a second: nothing running, nothing new started. (strays_before
    first: taken before the page opens.)"""
    yield
    from PySide6.QtCore import QThreadPool
    idle = {"n": 0}

    def quiet():
        idle["n"] = idle["n"] + 1 if QThreadPool.globalInstance().activeThreadCount() == 0 else 0
        return idle["n"] >= 25
    qt.wait_for(quiet, 30)


def test_opens_with_the_apps_files(eq_screen, check):
    page = eq_screen.page
    loaded = page.curves is not None and page.auto is not None  # (open_screen waited up to 90 s for them)
    # was eq_checks.py:1372
    check("ui: the EQ screen opens with the app's files and draws them (the curves, the automatic settings)",
          loaded and page.target_combo.count() >= 1 and page.measurement_combo.count() >= 1
          and "→" in page.graph_title.text(), (loaded, page.graph_note.text()))


def test_says_what_save_writes_from_the_start(eq_screen, check):
    # (before anything changes a setting, so before the next test: the line under File name was empty when the page
    # opened, and filled in only once a setting changed. The Guide's save demo points at it. Found 2026-10-23)
    page = eq_screen.page
    line = page.formats_line.text()
    check("ui: the line under File name says what Save filters writes as soon as the page opens",
          line.startswith("Save filters writes"), line)


def test_eq_app_sets_method_and_files(eq_screen, check):
    page = eq_screen.page
    page.choose_app("poweramp")
    try:
        # was eq_checks.py:1376
        check("ui: your EQ app sets the method and Save writes exactly its file",
              page.S["eq_app"] == "poweramp" and page.S["mode"] == "best_fit"
              and [k for k in ("apo", "poweramp", "graphic") if page.S["export"][k]] == ["poweramp"]
              and "Poweramp" in page.formats_line.text(), page.S["export"])
    finally:
        page.choose_app("apo")  # (back as the old checks put it, line 1491)


def test_no_control_shown_as_a_window_of_its_own(eq_screen, check, strays_before):
    # (last in this file: the page has opened and been worked; a control shown as a window of its own in an earlier
    # test of this file has failed that test already, through the stray_check fixture, which then empties `found`)
    watch = qt.stray_watch()
    installed = watch is not None
    # was eq_checks.py:1642
    check("ui: no control is ever shown as a window of its own (each flashed on the screen: Find…'s rows showed one "
          "Show button each while the lists loaded, 779 in a session, and each cost the window's time)",
          installed and not watch.found and (strays_before or not watch.seen_any),
          ("the stray watch isn't installed" if not installed else (watch.found[:5], watch.seen_any)))
