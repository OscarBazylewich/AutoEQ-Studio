"""Make an EQ's page deleted while its background loads still run: their answers are dropped (ui.tasks.background
with the page as their owner), never reaching the deleted page. A bug the tests' reorganization found, fixed
2026-10-23: the page's loads named no owner, so a load still on its way answered a deleted page ("Internal C++ object
(QLabel) already deleted", from refresh_auto). In the app the page lives as long as the window; tests delete pages."""
from helpers import eqpage, qt


def test_loads_answering_a_deleted_page(tmp_path, check):
    from PySide6.QtCore import QCoreApplication, QEvent, QThreadPool
    s = eqpage.open_screen(str(tmp_path / "page"))
    page = s.page
    errors_before = len(qt.QT_ERRORS)
    try:
        page.load_curves()  # (each answer starts the next: the curves, their analysis, the automatic settings)
        page.load_analysis()
        page.close()
        page.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)  # (gone while its loads still run)
        done = QThreadPool.globalInstance().waitForDone(int(qt.time_limit(30) * 1000))
        qt.pump(300)  # (their answers delivered)
    finally:
        eqpage.close_screen(s)
    errors = qt.QT_ERRORS[errors_before:]
    check("eq page: the answers of its background loads (the curves, their analysis) that arrive after the page was "
          "deleted are dropped, never reaching the deleted page", done and not errors, (done, errors))
