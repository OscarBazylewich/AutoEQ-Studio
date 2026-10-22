"""Make an EQ's result (ui\\eq_page.py): the Run button's result (its numbers, its filters, the best for each filter
count), Retry from these filters, the result's automatic file name, Runs this session, Max Q and the Sliders view, a
website method's line with Use in single run, and the line on how a result sounds. Moved from eq_checks.py's
ui_checks, review_checks, review_low_checks and pick_note_checks.

One page for the file (the eq_screen fixture) and one chain of results, in the old order: the Run button's result,
then the Retry's (two runs this session), then the first one chosen again. The old checks also had a History EQ and
Run several's runs in Runs this session by then; the checks here need only what they name (two runs or more, a
result on the card)."""
import pytest
from PySide6.QtWidgets import QLineEdit

from helpers import eqpage
from ui.eq_page import file_base_name


@pytest.fixture(scope="module")
def chain(eq_screen):
    """What each check leaves for the next one in this file (as eq_checks.py ran them one after another): the run
    shown and its result."""
    # (your EQ app Equalizer APO, as the old checks had chosen it before their run, eq_checks.py line 1491)
    eq_screen.page.choose_app("apo")
    return {}


def test_run_button_makes_a_result(eq_screen, chain, check):
    page = eq_screen.page
    try:  # (lines 1528-1531: automatic settings off, Best fit with 3 and 5 filters, the Run button clicked)
        eqpage.quick_run(eq_screen)
    except RuntimeError as e:  # (no result: said by the check below)
        print(e)
    done = page.run_result is not None
    run, r = page.current()
    chain.update(run=run, r=r)
    # was eq_checks.py:1533
    check("ui: the Run button makes a result: its numbers, its filters, the best for each count",
          done and r and page.editor.table.rowCount() == len(r["filters"]) and page.count_combo.count() >= 1
          and page.result_box.isVisible() and "dB" in page.chips["error"].text(), page.progress_text.text())


def test_retry_from_these_filters(eq_screen, chain, check):
    page, run = eq_screen.page, chain["run"]
    page.set_view("table")  # (lines 1562-1563: the Table view and the run's own filters, as the old checks left them)
    page.revert()
    page.run(retry={"filters": page.active(), "add": False})
    retried = eq_screen.wait_for(lambda: page.run_btn.isEnabled() and page.run_result is not run, 180)
    # was eq_checks.py:1566
    check("ui: Retry from these filters: Best fit again from them (fine-tune)",
          retried and page.current()[1] is not None and page.run_result["mode"] == "best_fit", page.progress_text.text())
    chain["run"], chain["r"] = page.current()


def test_file_name_is_autoeq_locals(eq_screen, chain, check):
    page = eq_screen.page
    run, r = chain["run"], chain["r"]  # (the Retry's result, line 1568)
    # was eq_checks.py:1569
    check("ui: the result's file name is AutoEQ Local's (<IEM> to <target> - <method> <n>f)",
          page.name_edit.text() == file_base_name(run["device"], run["target_name"], "", run["mode"], r["n_filters"])
          and file_base_name("A", "B", "Poweramp / Poweramp Equalizer", "best_fit", 5) == "A to B - Poweramp, Poweramp Equalizer 5f",
          page.name_edit.text())


def test_runs_this_session_chosen_again(eq_screen, chain, check):
    page = eq_screen.page
    # (the Run button's run and the Retry's are this session's runs; the Retry's is shown)
    runs = list(page.session_runs)
    other = runs[0] if runs and runs[0] is not page.run_result else None
    if other:
        page.choose_run(id(other))
    # was eq_checks.py:1688
    check("review: the runs of this session are kept and one can be chosen again (Runs this session)",
          len(runs) >= 2 and page.runs_row.isVisibleTo(page) and other is not None and page.run_result is other,
          (len(runs), page.runs_combo.count()))


def test_max_q_and_the_sliders_view(eq_screen, chain, check):
    page = eq_screen.page
    page.show_result(page.run_result["pick"])  # (line 1827: the run's picked result shown again)
    page.set_view("sliders")
    boxes = page.editor.sliders_scroll.widget().findChildren(QLineEdit)
    page.set_view("table")
    # was eq_checks.py:1831
    check("review: the result shows Max Q; the Sliders view edits each filter's frequency and Q",
          page.chips["maxq"].text().startswith("Max Q") and len(boxes) >= 2 * len(page.EDIT), (page.chips["maxq"].text(), len(boxes)))


def test_website_method_line_and_use_in_single_run(eq_screen, chain, check):
    page = eq_screen.page
    mode = page.S["mode"]  # (the method before, as line 1834 kept it)
    # (lines 1843-1858: a made-up Website sweep run with one result put on the card, Use in single run, then
    # everything put back by hand, as the old check did)
    run_before = page.run_result
    fake = {"mode": "site_sweep", "pick": 1, "best": 1, "n": 99, "device": "X", "target_name": "Y",
            "results": [{"id": 1, "filters": [{"type": "PK", "freq": 1000, "gain": -3, "q": 1}], "n_filters": 1,
                         "rms": 1.0, "rows": 5, "freq_low": 20, "freq_high": 10000, "gain_min": -12, "gain_max": 6,
                         "q_min": 0.5, "q_max": 3, "preamp": -1.5, "max_boost": 0}]}
    page.run_result = fake
    page.show_result(1)
    shown = (page.site_row.isVisibleTo(page), "Filter rows <b>5</b>" in page.site_text.text(), page.site_use.isVisibleTo(page))
    page.use_in_single_run()
    copied = (page.S["mode"], page.S["site_single"]["rows"], "site_single.rows" in page.S["auto"]["manual"])
    page.S["mode"] = mode
    page.S["auto"]["manual"] = [m for m in page.S["auto"]["manual"] if not m.startswith("site_single.")]
    page.session_runs = [r for r in page.session_runs if r is not fake]
    page.run_result = run_before
    page.show_result(run_before["pick"])
    page.changed()
    # was eq_checks.py:1859
    check("review: a website method's result says what to type into squiglink's panel; Use in single run copies it",
          shown == (True, True, True) and copied == ("site_single", 5, True), (shown, copied))


def test_pick_note(eq_screen, check):
    page = eq_screen.page
    # (lines 2288-2295: made-up runs and results; pick_note works on them alone)
    r = {"id": 1, "ear": 0.18, "ear_at": 2500.0}
    best = {"id": 2, "ear": 0.47, "ear_at": 6200.0}
    same = page.pick_note({"pick": 1, "pick_case": "target", "ear_db": 0.25, "results": [r]}, r)
    far = {"id": 1, "ear": 0.52, "ear_at": 2500.0}  # (out of reach: the closest is the lowest ear error, 0.47 dB)
    out = page.pick_note({"pick": 1, "best": 1, "pick_case": "best", "ear_db": 0.25, "results": [far, best]}, far)
    other = page.pick_note({"pick": 1, "pick_case": "target", "ear_db": 0.25, "results": [r, best]}, best)
    none = page.pick_note({"pick": 1, "results": [r]}, r)
    alone = page.pick_note({"pick": 1, "pick_case": "best", "ear_db": 0.25, "results": [far]}, far)
    # was eq_checks.py:2296
    check("result: says it sounds the same as the target, or how far off the closest is and where (none for an old run); "
          "the closest one itself isn't said to have fewer filters (review 2)",
          same.startswith("Sounds the same as the target: within 0.18 dB") and "0.47 dB off around 6.2 kHz" in out
          and "fewer filters" in out and "most off around 6.2 kHz" in other and none == ""
          and alone.endswith("This is that closest one."), (same, out, other, none, alone))
