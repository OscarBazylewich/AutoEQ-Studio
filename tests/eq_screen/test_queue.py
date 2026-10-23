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
    made = set(os.listdir(eq_paths.OUTPUT_DIR)) - out_before
    q.close()
    page.S = kept_S
    page.svc.call("/api/settings", {"settings": page.S})
    # was eq_checks.py:2534
    check("queue: Run several makes an EQ for each IEM and target ticked, each saved and kept in History and Runs this "
          "session; your choice of files is as it was", done and len(said) == n >= 1
          and all(s.startswith("Done") for s in said) and len(made) >= n and len(page.session_runs) == min(20, runs + n)
          and len(page.history) >= hist + n and page.S["files"] == before, (done, said, sorted(made), runs, hist))


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
