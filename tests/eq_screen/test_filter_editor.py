"""Editing the result's filters on Make an EQ (ui\\filter_editor.py under ui\\eq_page.py): a typed value changes the
error, the title, the file name and the line on how it sounds at once; a value past the edit limits is red and not
used; Revert gives the run's filters back and Sort alone isn't an edit; the Sliders view edits the same filters.
Moved from eq_checks.py's ui_checks: one page for the file (the eq_screen fixture), a quick run of its own (the
result the old checks edited), then the edits one after another in the old order."""
import pytest
from PySide6.QtWidgets import QSlider

from helpers import eqpage


@pytest.fixture(scope="module")
def chain(eq_screen):
    """The Run button's result on the card (eq_checks.py lines 1528-1532), and what each edit leaves for the next."""
    page = eq_screen.page
    page.choose_app("apo")  # (your EQ app as the old checks had chosen it before their run, line 1491)
    eqpage.quick_run(eq_screen)  # (raises when the run makes no result)
    run, r = page.current()
    return {"run": run, "r": r}


def test_editing_a_filter(eq_screen, chain, check):
    page, run = eq_screen.page, chain["run"]
    # (lines 1537-1541: filter 1's gain box in the table typed 3 dB higher, as a person types it)
    before = (page.chips["error"].text(), page.name_edit.text())
    box = page.editor.table.cellWidget(0, 4)
    box.setText(str(page.EDIT[0]["gain"] + 3))
    box.textEdited.emit(box.text())
    after = (page.chips["error"].text(), page.res_title.text(), page.name_edit.text(), page.pick_lab.text())
    chain.update(before=before, box=box)
    # was eq_checks.py:1542
    check("ui: editing a filter: the error, the title (edited), the file name (… edited) and the line on how it sounds "
          "follow at once",
          after[0] != before[0] and after[1].endswith("edited") and after[2] == before[1] + " edited"
          and (after[3].startswith("As edited: sounds within") or not run.get("pick_case")), (before, after))


def test_value_past_the_edit_limits(eq_screen, chain, check):
    page, box = eq_screen.page, chain["box"]
    box.setText("99999")  # (lines 1546-1547: the same box)
    box.textEdited.emit(box.text())
    # was eq_checks.py:1548
    check("ui: editing: a value past the edit limits is red and not used", box.property("bad") is True
          and page.EDIT[0]["gain"] != 99999)


def test_revert_and_sort(eq_screen, chain, check):
    page, before = eq_screen.page, chain["before"]
    page.revert()  # (lines 1550-1551)
    page.sort_filters()
    # was eq_checks.py:1552
    check("ui: Revert gives the run's filters back; Sort alone isn't an edit",
          page.chips["error"].text() == before[0] and not page.edited() and page.name_edit.text() == before[1],
          page.chips["error"].text())


def test_sliders_edit_the_same_filters(eq_screen, chain, check):
    page, r = eq_screen.page, chain["r"]
    # (lines 1555-1559: a new filter, then the Sliders view, the last slider dragged to +2.5 dB)
    page.add_filter()
    n = len(page.active())
    page.set_view("sliders")
    sl = page.editor.sliders_scroll.widget().findChildren(QSlider)
    sl[-1].setValue(25)
    # was eq_checks.py:1560
    check("ui: the sliders edit the same filters (a new one at 1 kHz, its gain dragged to +2.5 dB)",
          n == len(r["filters"]) + 1 and page.EDIT[-1]["freq"] == 1000 and page.EDIT[-1]["gain"] == 2.5, page.EDIT[-1])
    page.set_view("table")  # (lines 1562-1563: the Table view again, the run's own filters)
    page.revert()
