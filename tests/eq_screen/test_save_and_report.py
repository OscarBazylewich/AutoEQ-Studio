"""Save filters and Report on Make an EQ (ui\\eq_page.py, eq\\exports.py, eq\\report.py): Save writes the file under
the File name; Save with no file ticked says so and keeps nothing in History; Report writes the HTML report. Moved
from eq_checks.py's ui_checks and review_checks: one page for the file (the eq_screen fixture) with a quick run of its
own (the result the old checks saved), its saved EQ brought back from History for the report, as the old check had
it."""
import os

import pytest

from helpers import eqpage


@pytest.fixture(scope="module")
def chain(eq_screen):
    """A result on the card (eq_checks.py lines 1528-1532), and what Save leaves for the report."""
    page = eq_screen.page
    page.choose_app("apo")  # (line 1491: your EQ app Equalizer APO, so Save writes only its file)
    eqpage.quick_run(eq_screen)  # (raises when the run makes no result)
    return {}


def test_save_writes_the_file(eq_screen, chain, check):
    page, said = eq_screen.page, eq_screen.said
    top = os.environ["AUTOEQSTUDIO_ROOT"]  # (the app's "your files" folder: the old checks' copy, here the session's)
    page.name_edit.setText("UI check")  # (lines 1573-1574)
    page.save()
    chain["entry"] = next((e for e in page.history if e.get("saved")), None)
    # was eq_checks.py:1575
    check("ui: Save filters writes the file under the File name", os.path.isfile(os.path.join(top, "Saved EQs", "UI check - filters.txt"))
          and any("Saved" in s for s in said), said[-1:])


def test_save_with_no_file_ticked_and_report(eq_screen, chain, check, dialogs):
    page = eq_screen.page
    if chain.get("entry") is None:
        raise RuntimeError("Save made no History entry: the History EQ this check starts from isn't there")
    # (the saved EQ brought back with History's Show: the result the old check found on the card, line 1583. A report
    # of that name is already in Saved EQs, as in the old run: Save above wrote one (a report is among the files Save
    # writes unless it's unticked), so Replace? is asked and answered Yes, as there)
    eqpage.show_from_history(eq_screen, chain["entry"])
    # (lines 1672-1680)
    page.show_result(page.current()[0]["pick"]) if page.current()[1] is None and page.run_result else None
    exp = dict(page.S["export"])
    n_hist = len(page.history)
    page.S["export"].update({k: False for k in exp if isinstance(exp[k], bool)})
    dialogs.asked.clear()  # (the message boxes said so far: the old BOXES)
    page.save()
    nothing = (any("No file is ticked" in text for _kind, text in dialogs.asked), len(page.history) == n_hist)
    page.S["export"].update(exp)
    path = page.report(open_it=False)
    # was eq_checks.py:1681
    check("review: Save with no file ticked says so (no “Saved”, nothing in History); Report writes the HTML report",
          nothing == (True, True) and path and os.path.isfile(path) and path.endswith(" - report.html"), (nothing, path))
