"""Run several… on Make an EQ (ui\\queue_window.py): an EQ made for each IEM and target ticked, each saved (never over
a file) and kept in History and Runs this session, your choice of files as it was after. Moved from eq_checks.py's
queue_checks: one page for the file (the eq_screen fixture). The window ticks the IEM in use by itself; the check
ticks the first two targets, and the app has one (the sample target), as the old check found it: one EQ is made, in
Best fit's worker processes. Then its look (Windows 11's, 2026-10-23): the symbol on Start, the headings, and the
window at its smallest."""
import copy
import os

from PySide6.QtCore import Qt

from eq import paths as eq_paths
from helpers import qt
from ui.queue_window import QueueWindow, _ticked


def test_run_several(eq_screen, check):
    page = eq_screen.page
    page.choose_app("apo")  # (your EQ app as the old checks had chosen it, line 1491: each EQ saved as APO's file)
    # (lines 2514-2533: quick runs for the check, no automatic settings and one filter count; the window's start
    # waited for, then the settings put back and saved)
    before = copy.deepcopy(page.S["files"])
    kept_S = copy.deepcopy(page.S)
    page.S["auto"]["enabled"] = False
    page.S["mode"] = "best_fit"
    page.S["best_fit"].update(filter_counts=[5], random_starts=0, seed_with_site=False)
    runs, hist = len(page.session_runs), len(page.history)
    out_before = set(os.listdir(eq_paths.OUTPUT_DIR)) if os.path.isdir(eq_paths.OUTPUT_DIR) else set()
    q = QueueWindow(page)
    targets = [q.tgts.item(i) for i in range(q.tgts.count())]
    for it in targets[:2]:
        it.setCheckState(Qt.Checked)
    n = len(_ticked(q.devs)) * len(_ticked(q.tgts))
    q.start()
    done = eq_screen.wait_for(lambda: not q.running, 300)
    said = [q.table.item(i, 2).text() for i in range(q.table.rowCount())]
    end = q.footer.line.text.text()
    made = set(os.listdir(eq_paths.OUTPUT_DIR)) - out_before
    q.close()
    page.S = kept_S
    page.svc.call("/api/settings", {"settings": page.S})
    # was eq_checks.py:2534
    check("queue: Run several makes an EQ for each IEM and target ticked, each saved and kept in History and Runs this "
          "session; your choice of files is as it was", done and len(said) == n >= 1
          and all(s.startswith("Done") for s in said) and len(made) >= n and len(page.session_runs) == min(20, runs + n)
          and len(page.history) >= hist + n and page.S["files"] == before, (done, said, sorted(made), runs, hist))
    # (the text survey, area 20, 2026-11-24: a row's result and the last message in the owner's words)
    check("queue: each row says “Done · {n} filters · {x} dB · saved as {file}”, and the message line “Completed {k} "
          "of {n} EQs” with no period",
          all(s.startswith("Done · ") and " dB · saved as " in s for s in said)
          and end == f"Completed {n} of {n} EQ{'' if n == 1 else 's'}", (said, end))


def test_run_several_texts_of_the_text_survey(eq_screen, check, monkeypatch):
    # (the text survey, area 20, 2026-11-24: the line at the top, the count before Start, a row's progress and its
    # failure in the owner's words; a row's progress joins only the parts it has, so it never starts with “ · ”)
    from PySide6.QtWidgets import QLabel
    page = eq_screen.page
    q = QueueWindow(page)
    try:
        lead = next(lab.text() for lab in q.findChildren(QLabel) if lab.wordWrap())
        for lst in (q.devs, q.tgts):
            for i in range(lst.count()):
                lst.item(i).setCheckState(Qt.Unchecked)
        counts = [q.count_lab.text()]
        q.devs.item(0).setCheckState(Qt.Checked)
        q.tgts.item(0).setCheckState(Qt.Checked)
        counts.append(q.count_lab.text())
        q.table.setRowCount(1)
        q.i = 0
        monkeypatch.setattr(q, "next_job", lambda: None)  # (one row only: the queue does not go on)
        rows, jobs = [], [{"status": "running", "message": "Best fit adds one filter at a time: 3/12", "elapsed": 6.2},
                          {"status": "running", "message": "", "elapsed": 4},
                          {"status": "running", "message": "Best fit adds one filter at a time: 1/12"},
                          {"status": "error", "message": "No measurement"}, {"status": "error"}]
        for job in jobs:
            monkeypatch.setattr(page.svc, "call", lambda path, body=None, job=job: job if body is None else {})
            q.poll()
            rows.append(q.table.item(0, 2).text())
        q.timer.stop()
    finally:
        monkeypatch.undo()
        qt.close(q)
    check("queue: the texts of the text survey: the line at the top, “Select an IEM and a target”, “1 EQ queued”; a "
          "row's progress is the job's message and the time (no “In progress: ”), its failure “Failed: …” or “Failed”",
          lead == ("Generates an EQ for each selected IEM and target, saves each to History, and exports to Saved EQs if "
                   "a file type is set in More settings › Saved files. Closing this window stops the queue.")
          and counts == ["Select an IEM and a target", "1 EQ queued"]
          and rows == ["Best fit adds one filter at a time: 3/12 · 6 s", "4 s", "Best fit adds one filter at a time: 1/12",
                       "Failed: No measurement", "Failed"], (lead, counts, rows))


def test_run_several_look(eq_screen, check):
    from PySide6.QtWidgets import QLabel
    q = QueueWindow(eq_screen.page)
    q.show()
    qt.pump(150)
    heads = [lab for lab in q.findChildren(QLabel) if lab.text() in ("IEMs and headphones", "Targets")]
    looks = (not q.start_btn.icon().isNull(), q.start_btn.text(), [lab.property("role") for lab in heads],
             bool(q.table.horizontalHeader().defaultAlignment() & Qt.AlignLeft))
    q.resize(q.minimumSize())  # (the smallest the window can be made)
    qt.pump(200)
    lead = next(lab for lab in q.findChildren(QLabel) if lab.wordWrap())
    row = q.devs.sizeHintForRow(0) if q.devs.count() else 30
    smallest = (q.width(), q.height(), lead.heightForWidth(lead.width()), lead.height(), q.devs.viewport().height(),
                q.table.viewport().height(), row)
    qt.close(q)
    check("queue: Start shows Windows 11's Run symbol beside its word; the two lists are named by headings; the "
          "results' headings stand over their words", looks == (True, "Start", ["section", "section"], True), looks)
    check("queue: at its smallest the window's words are whole and the lists and the results keep room for a few "
          "rows (they had one, and the words ran over each other)",
          smallest[2] <= smallest[3] and smallest[4] >= 3 * smallest[6] and smallest[5] >= 3 * smallest[6], smallest)


def test_run_several_fits_a_small_screen(eq_screen, check, monkeypatch):
    # (2026-10-24, left from the restyle: it opened 720 high, under the taskbar of a 1920 x 1080 laptop at 150 % (672
    # px above it) and 175 %)
    seen = qt.on_screens(monkeypatch, lambda: QueueWindow(eq_screen.page))
    big = seen[qt.BIG_SCREEN]
    check("queue: Run several opens within a laptop's screen at 150 % and 175 % (above the taskbar, its smallest size "
          "too), its parts not squeezed; on a big screen as before (900 x 720, its smallest 640 x 520)",
          all(seen[s]["fits"] for s in qt.SMALL_SCREENS) and big["fits"] and big["opens"] == (900, 720)
          and big["smallest"] == (640, 520), seen)


def test_run_several_lists_a_to_z(eq_screen, check):
    # (2026-10-27, the rules' review: its targets were in plain order, "IEM 10" before "IEM 2", UI-RULES 22)
    page = eq_screen.page
    kept = page.inputs.get("targets")
    try:
        page.inputs["targets"] = ["Target 10.csv", "target 2.csv", "Alpha.csv"]
        q = QueueWindow(page)
        names = [q.tgts.item(i).text() for i in range(q.tgts.count())]
        qt.close(q)
    finally:
        page.inputs["targets"] = kept
    check("queue: Run several's targets are A to Z, numbers as numbers (as every list)",
          names == ["Alpha", "target 2", "Target 10"], names)


def test_run_several_long_names_fit_their_list(eq_screen, check):
    # (a code review, 2026-11-10: a long target's name made a scroll bar across its list, and the end of the name was
    # out of sight; now the row is as wide as the list and the name goes on to a second line)
    page = eq_screen.page
    kept = page.inputs.get("targets")
    long = ("A target with a very long name that is wider than the list of targets in the queue window, "
            "and longer still.csv")
    try:
        page.inputs["targets"] = [long, "Short.csv"]
        q = QueueWindow(page)
        q.show()
        q.resize(q.minimumSize())
        qt.pump(200)
        lst = q.tgts
        row = next(i for i in range(lst.count()) if lst.item(i).data(Qt.UserRole) == long)
        rect = lst.visualItemRect(lst.item(row))
        bar = lst.horizontalScrollBar()
        found = (bar.isVisible(), bar.maximum(), rect.height(), lst.sizeHintForRow(1 - row),
                 lst.item(row).toolTip() == os.path.splitext(long)[0])
        qt.close(q)
    finally:
        page.inputs["targets"] = kept
    check("queue: a long name in a list goes on to more lines in the list's width (no scroll bar across), its whole "
          "name in its tooltip",
          not found[0] and found[1] == 0 and found[2] > found[3] and found[4], found)


def _focus_name(w):
    if w is None:
        return None
    return f"{type(w).__name__} {w.text() if callable(getattr(w, 'text', None)) else w.accessibleName()!r}"


def test_run_several_keeps_the_focus_on_its_buttons(eq_screen, check):
    # (2026-11-15, the verifier of the Calculate fault: Space on Start turned Start off with the focus, and Qt gave the
    # focus to Close; a second Space then closed the window and stopped the queue. Now Cancel gets the focus while the
    # queue runs, as Calculate's Cancel, and Start gets it back when the queue is done. Space on Cancel turns Cancel
    # off: the results' table has the focus until the queue stops)
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication
    page = eq_screen.page
    kept_S = copy.deepcopy(page.S)
    page.S["auto"]["enabled"] = False
    page.S["mode"] = "best_fit"
    page.S["best_fit"].update(filter_counts=[5], random_starts=0, seed_with_site=False)
    seen = {}
    try:
        for how in ("done", "cancelled"):
            q = QueueWindow(page)
            try:
                q.tgts.item(0).setCheckState(Qt.Checked)
                q.show()
                q.activateWindow()
                qt.pump(100)
                q.start_btn.setFocus(Qt.TabFocusReason)
                QTest.keyClick(q.start_btn, Qt.Key_Space)
                qt.pump(50)
                d = {"while it runs": _focus_name(QApplication.focusWidget()), "running": q.running}
                if how == "cancelled":
                    QTest.keyClick(q.cancel_btn, Qt.Key_Space)
                    qt.pump(50)
                    d["after Cancel"] = _focus_name(QApplication.focusWidget())
                d["stopped"] = eq_screen.wait_for(lambda q=q: not q.running, 300)
                qt.pump(50)
                d["at the end"] = _focus_name(QApplication.focusWidget())
                d["window open"] = q.isVisible()
                # (the result's first word: “Done · 5 filters · …”, “Canceled”)
                d["result"] = q.table.item(0, 2).text().split(" · ")[0].split(":")[0] if q.table.rowCount() else None
                seen[how] = d
            finally:
                qt.close(q)
    finally:
        page.S = kept_S
        page.svc.call("/api/settings", {"settings": page.S})
    start, cancel = "QPushButton 'Start'", "QPushButton 'Cancel'"
    check("queue: Space on Start gives the focus to Cancel while the queue runs, and back to Start when it is done; "
          "the window stays open (the focus went to Close, and a second Space closed the window and stopped the queue)",
          seen.get("done") == {"while it runs": cancel, "running": True, "stopped": True, "at the end": start,
                               "window open": True, "result": "Done"}, seen.get("done"))
    check("queue: Space on Cancel stops the queue, the focus on the results' table until it stops, then on Start (it "
          "went to Close)",
          seen.get("cancelled") == {"while it runs": cancel, "running": True,
                                    "after Cancel": "QTableWidget 'Result of each EQ'", "stopped": True,
                                    "at the end": start, "window open": True, "result": "Canceled"},
          seen.get("cancelled"))


def test_run_several_from_a_list_gives_the_focus_back_to_that_list(eq_screen, check):
    # (2026-11-15, round 3 of the fault of Calculate: the Enter key in a list starts the queue too. At the end the
    # focus goes back to that list, not to Start. The verifier's mutation D6 gave it to Start, and no test found it)
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication
    page = eq_screen.page
    kept_S = copy.deepcopy(page.S)
    page.S["auto"]["enabled"] = False
    page.S["mode"] = "best_fit"
    page.S["best_fit"].update(filter_counts=[5], random_starts=0, seed_with_site=False)
    try:
        q = QueueWindow(page)
        try:
            q.tgts.item(0).setCheckState(Qt.Checked)
            q.show()
            q.activateWindow()
            qt.pump(100)
            q.tgts.setFocus(Qt.TabFocusReason)
            QTest.keyClick(q.tgts, Qt.Key_Return)
            qt.pump(50)
            d = {"while it runs": _focus_name(QApplication.focusWidget()), "running": q.running}
            d["stopped"] = eq_screen.wait_for(lambda: not q.running, 300)
            qt.pump(50)
            d["at the end"] = _focus_name(QApplication.focusWidget())
        finally:
            qt.close(q)
    finally:
        page.S = kept_S
        page.svc.call("/api/settings", {"settings": page.S})
    check("queue: the Enter key in the Targets list starts the queue, Cancel has the focus while it runs, and the list "
          "has it again when the queue is done (the focus went to Start)",
          d == {"while it runs": "QPushButton 'Cancel'", "running": True, "stopped": True,
                "at the end": "QListWidget 'Targets'"}, d)
