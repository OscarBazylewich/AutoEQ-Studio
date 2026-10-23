"""Make an EQ's page as a whole (ui\\eq_page.py): the online database lists loaded as it opens, the dark theme and
back (the graph follows), and its keys: "/" opens Find…, a picture pasted opens the tracer with it. Moved from
eq_checks.py's review_checks and review_low_checks, on a page opened as the old checks opened it (the eq_screen
fixture), offline: the lists are the saved ones (tests\\fixtures\\db)."""
import os

import pytest

from helpers import qt


@pytest.fixture(scope="module", autouse=True)
def settled(eq_screen):
    """After the file's last test, the page's background work finished before the eq_screen fixture closes it: each
    load that ends starts the next in the background (the curves, their analysis, the automatic settings), and one
    still on its way once the page is deleted answers a page that's gone (an error inside a Qt call-back, "Internal
    C++ object already deleted"). Quiet for half a second: nothing running, nothing new started."""
    yield
    from PySide6.QtCore import QThreadPool
    idle = {"n": 0}

    def quiet():
        idle["n"] = idle["n"] + 1 if QThreadPool.globalInstance().activeThreadCount() == 0 else 0
        return idle["n"] >= 25
    qt.wait_for(quiet, 30)


def test_database_lists_loaded_on_opening(eq_screen, check):
    from eq import databases
    lists = os.path.exists(os.path.join(os.environ["AUTOEQSTUDIO_DATA"], "eq", "cache", "databases.json"))
    # (a refresh an earlier step started, e.g. by opening Find…, may still be going: it was the flaky part)
    eq_screen.wait_for(lambda: not databases.status()["loading"], 60)
    st = databases.status()
    # was eq_checks.py:1661
    check("review: the online database lists are loaded when Make an EQ opens (offline: the saved ones)",
          not st["loading"] and (st["count"] > 0 or not lists), (st["loading"], st["count"], lists))


def test_dark_theme_and_back(eq_screen, check):
    from ui import theme
    page, qapp = eq_screen.page, eq_screen.qapp
    try:
        theme.apply(qapp, dark=True)
        qapp.processEvents()
        dark = (page.plot.backgroundBrush().color().name(), theme.graph_colours()["bg"].lower())
        theme.apply(qapp, dark=False)
        qapp.processEvents()
        light = (page.plot.backgroundBrush().color().name(), theme.graph_colours()["bg"].lower())
    finally:
        qt.light(qapp)  # (the light theme back, whatever happened: every later test runs light)
        qapp.processEvents()
    # was eq_checks.py:1811
    check("review: the EQ screen switches to the dark theme and back (the graph follows)",
          dark[0] == dark[1] and light[0] == light[1] and dark[0] != light[0], (dark, light))


def test_slash_and_pasted_picture(eq_screen, check):
    from PySide6.QtGui import QColor, QImage, QShortcut
    from PySide6.QtWidgets import QApplication
    page = eq_screen.page
    keys = [sc.key().toString() for sc in page.findChildren(QShortcut)]
    # (the off-screen clipboard is this process's own: Windows' clipboard isn't touched)
    img = QImage(400, 300, QImage.Format_RGB888)
    img.fill(QColor("white"))
    QApplication.clipboard().setImage(img)
    page.paste_picture()
    pasted = page.tracer.isVisible() and page.tracer.t.has_image
    page.tracer.close()
    # was eq_checks.py:1899
    check("review: “/” opens Find…; a picture pasted on Make an EQ opens the tracer with it", "/" in keys and pasted,
          (keys, pasted))
