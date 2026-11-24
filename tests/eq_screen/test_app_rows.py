"""What the user sets for an EQ app, in Settings › Best fit of Make an EQ (ui\\eq_settings.py, its rows made from
eq_apps.user_items): Peace bands and Peace max gain (± dB), and Band counts to try for FxSound. Each row shows only
while the Best fit layout is that app's (through Your EQ app or the Layout list). The ⓘ after Your EQ app and the
line Settings to try follow the two Peace numbers. A run with several band counts: the items of Number of filters,
All results (no grid), Compare, History and the Queue say "bands"; a preset keeps the values; the Guide's step Your
values. One page for the file (the eq_screen fixture: Automatic settings off, filter counts 3 and 5 at its start)."""
import copy
import html
import json
import os
import re
from types import SimpleNamespace

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel

from helpers import eqpage, qt

BANDS, GAIN = "best_fit.per_app.peace.bands", "best_fit.per_app.peace.gain"
COUNTS = "best_fit.per_app.fxsound.band_counts"
FILTERS = "best_fit.filter_counts"
ALL_COUNTS = [5, 10, 15, 20, 31]
BOXES = ("num", "intlist", "numlist", "ranges")  # (the kinds of box that hold text)


@pytest.fixture(scope="module")
def rows(eq_screen):
    """The Settings fold open (a row hidden in a closed fold is not in sight), the settings as the page started."""
    page = eq_screen.page
    page.settings.fold.btn.setChecked(True)
    qt.pump(50)
    return page.settings


@pytest.fixture(autouse=True)
def settings_kept(eq_screen):
    """Each test of the file starts from the settings that the test before it started from: the settings put back
    after a test that changed them (an EQ app chosen, Automatic settings switched on, a value typed)."""
    page = eq_screen.page
    was = copy.deepcopy(page.S)
    yield
    if page.S != was:
        page.S = was
        page.changed(curves=True)
        eq_screen.wait_for(lambda: page.curves is not None and page.auto is not None, 30)
        qt.pump(200)


def _in_sight(page, path):
    return page.settings.form.fields[path].box.isVisibleTo(page)


def _label(page, path):
    """The words of the label above a box (the one label that its cell itself has)."""
    cell = page.settings.form.fields[path].parentWidget().parentWidget()
    own = cell.findChildren(QLabel, options=Qt.FindDirectChildrenOnly)
    return own[0].text() if len(own) == 1 else None


def _type(field, text, leave=True):
    """A value typed into a box, then (leave) the box left."""
    field.box.setText(text)
    field._typed()
    if leave:
        field._edit_finished()


def _line(page, key):
    """The one line of the ⓘ after Your EQ app for an app, without the link."""
    return html.unescape(page.app_note_text(key).split(" <a ")[0])


def test_rows_show_for_the_layout_of_their_app(eq_screen, rows, check):
    page, st = eq_screen.page, rows
    sight = lambda: {p: _in_sight(page, p) for p in (BANDS, GAIN, COUNTS, FILTERS)}
    page.choose_app("peace")
    peace = sight()
    labels = (_label(page, BANDS), _label(page, GAIN), _label(page, COUNTS))
    names = [st.form.fields[p].box.accessibleName() for p in (BANDS, GAIN, COUNTS)]
    kinds = [(st.form.fields[p].kind, st.form.fields[p].box.width()) for p in (BANDS, GAIN, COUNTS)]
    check("app rows: Your EQ app Peace shows Peace bands and Peace max gain (± dB) after Filter counts to try, and "
          "not Band counts to try",
          peace == {BANDS: True, GAIN: True, COUNTS: False, FILTERS: True}, peace)
    check("app rows: each box has its label above it, the same name for a screen reader, a number box short and the "
          "list long",
          labels == ("Peace bands", "Peace max gain (± dB)", "Band counts to try") and names == list(labels)
          and kinds == [("num", 110), ("num", 110), ("intlist", 360)], (labels, names, kinds))
    order = list(st.form.fields)
    check("app rows: the rows are in the Best fit section, after Shelf and before Error and selection",
          order.index("best_fit.low_shelf") < order.index(BANDS) < order.index(GAIN) < order.index(COUNTS)
          < order.index("scoring.band_hz.0"), order)
    page.choose_app("apo")
    apo = sight()
    check("app rows: Your EQ app Equalizer APO shows none of the three",
          apo == {BANDS: False, GAIN: False, COUNTS: False, FILTERS: True}, apo)
    st.changed("best_fit.layout", "app:peace")
    by_hand = (sight(), _line(page, "apo"))
    check("app rows: with Your EQ app Equalizer APO and the Layout list set to Peace, the Peace rows show (the values "
          "are for the layout in use)",
          by_hand[0] == {BANDS: True, GAIN: True, COUNTS: False, FILTERS: True}
          and by_hand[1] == "No limits (Custom Best fit layout overrides this EQ app's limits.)", by_hand)
    page.choose_app("peace")
    st.changed("best_fit.layout", "any")
    other = sight()
    check("app rows: with Your EQ app Peace and another Layout, the Peace rows do not show",
          other == {BANDS: False, GAIN: False, COUNTS: False, FILTERS: True}, other)
    page.choose_app("apo")


def test_peace_values(eq_screen, rows, check):
    page, st, said = eq_screen.page, rows, eq_screen.said
    page.choose_app("peace")
    eq_screen.wait_for(lambda: " filters" in page.estimate.text(), 30)
    bands, gain = st.form.fields[BANDS], st.form.fields[GAIN]
    start = (bands.box.text(), gain.box.text(), _line(page, "peace"), page.estimate.text())
    tips = (bands.box.toolTip(), gain.box.toolTip())
    check("app rows: the Peace boxes start at 31 and 30, and the ⓘ after Your EQ app says them",
          start[:3] == ("31", "30", "Up to 31 bands · ±30 dB"), start)
    check("app rows: the tooltip of each Peace box tells where the value is in Peace, then its limits",
          tips == ("Number of sliders set in Peace (each shelf uses one)\nAllowed: 1 to 31",
                   "“Maximum dB” in Peace settings › Sizes and Amounts\nAllowed: 1 to 99 dB"), tips)
    _type(bands, "4")
    changed = eq_screen.wait_for(lambda: page.estimate.text() != start[3], 30)
    got = (page.S["best_fit"]["per_app"]["peace"], _line(page, "peace"), page.app_note.text().split(" <a ")[0],
           page.estimate.text())
    check("app rows: 4 typed into Peace bands is the setting, the ⓘ reads “Up to 4 bands · ±30 dB” and the line "
          "Settings to try follows (no count above the bands)",
          got[0] == {"bands": 4, "gain": 30} and got[1] == "Up to 4 bands · ±30 dB" and html.unescape(got[2]) == got[1]
          and changed and "5 filters" not in got[3], (got, start[3]))
    _type(gain, "12")
    got = (page.S["best_fit"]["per_app"]["peace"], _line(page, "peace"))
    check("app rows: 12 typed into Peace max gain is the setting, and the ⓘ reads “Up to 4 bands · ±12 dB”",
          got == ({"bands": 4, "gain": 12}, "Up to 4 bands · ±12 dB"), got)
    st.auto_switched(True)
    page.refresh_auto()
    tags = (bands.tag.isVisible(), gain.tag.isVisible(), st.form.fields[FILTERS].tag.isVisible(),
            BANDS in page.S["auto"]["manual"], dict(page.S["best_fit"]["per_app"]["peace"]))
    st.auto_switched(False)
    check("app rows: with Automatic settings on, the Peace boxes have no tag and keep their values (they are facts "
          "about the user's Peace), while Filter counts to try has its tag",
          tags == (False, False, True, False, {"bands": 4, "gain": 12}), tags)
    _type(bands, "40", leave=False)
    red = (bool(bands.box.property("bad")), page.S["best_fit"]["per_app"]["peace"]["bands"])
    bands._edit_finished()
    moved = (page.S["best_fit"]["per_app"]["peace"]["bands"], bands.box.text(), said[-1])
    check("app rows: 40 in Peace bands is red and not used; on leaving the box it becomes 31, and the message says so",
          red == (True, 4) and moved == (31, "31", "Adjusted to 31 (allowed: 1 to 31)."), (red, moved))
    _type(gain, "30")
    # (1 is an allowed value of Peace bands: "Up to 1 bands" and "up to 1 peaking/shelf filters" were shown)
    _type(bands, "1")
    st.auto_switched(True)
    page.refresh_auto()
    one = (_line(page, "peace"), html.unescape(page.app_note.text().split(" <a ")[0]),
           "up to 1 peaking/shelf filter, gain" in st.why.text())
    st.auto_switched(False)
    check("app rows: 1 typed into Peace bands: the ⓘ reads “Up to 1 band · ±30 dB”, and About these settings “up to "
          "1 peaking/shelf filter”",
          one == ("Up to 1 band · ±30 dB", "Up to 1 band · ±30 dB", True), (one, st.why.text()))
    _type(bands, "31")
    page.choose_app("apo")


def test_the_info_mark_follows_only_the_layout_in_use(eq_screen, rows, check):
    page = eq_screen.page
    page.choose_app("apo")
    was = copy.deepcopy(page.S["best_fit"]["per_app"])
    page.S["best_fit"]["per_app"]["peace"] = {"bands": 10, "gain": 12}
    away = _line(page, "peace")  # (the line of Peace while another app's layout is in use: Peace's own numbers)
    page.S["best_fit"]["per_app"] = was
    words = type(page).app_note_text

    def note(app, bf):
        stand_in = SimpleNamespace(eq_app=lambda key: dict(app, layout="its own"), S={"eq_app": "k", "best_fit": bf})
        return html.unescape(words(stand_in, "k"))
    form = {"note": "Up to 31 bands", "note_form": "Up to {bands} {band_word} · ±{gain} dB",
            "user_defaults": {"bands": 31, "gain": 30}}
    found = {"another layout": away, "neutron": _line(page, "neutron"), "poweramp": _line(page, "poweramp"),
             "no values": note(form, {"layout": "its own"}),
             "one value": note(form, {"layout": "its own", "per_app": {"k": {"bands": 7}}}),
             "1 band": note(form, {"layout": "its own", "per_app": {"k": {"bands": 1}}}),
             "a wrong kind": note(form, {"layout": "its own", "per_app": {"k": 3}}),
             "another layout, its values": note(form, {"layout": "yours", "per_app": {"k": {"bands": 7}}})}
    check("app rows: the ⓘ of Peace says the user's numbers only while its layout is in use, and a missing or wrong "
          "value is the app's own; Neutron reads 4–130 bands and Poweramp is as it was",
          found == {"another layout": "Up to 31 bands · ±30 dB", "neutron": "4–130 bands",
                    "poweramp": "5–32 bands · ±15 dB · Q 0.1–12", "no values": "Up to 31 bands · ±30 dB",
                    "one value": "Up to 7 bands · ±30 dB", "1 band": "Up to 1 band · ±30 dB", "a wrong kind": "Up to 31 bands · ±30 dB",
                    "another layout, its values": "Up to 31 bands · ±30 dB (Custom Best fit layout overrides this "
                                                  "EQ app's limits.)"}, found)


def test_band_counts_box(eq_screen, rows, check):
    page, st, said = eq_screen.page, rows, eq_screen.said
    page.choose_app("fxsound")
    f = st.form.fields[COUNTS]
    eq_screen.wait_for(lambda: "bands" in page.estimate.text(), 30)
    off = ({p: _in_sight(page, p) for p in (COUNTS, FILTERS, "best_fit.low_shelf", BANDS)}, f.box.text(),
           f.tag.isVisible(), f.box.placeholderText(), st.fixed_note.text(), st.fixed_note.isVisibleTo(page),
           page.estimate.text().split(" · ")[0], f.box.toolTip())
    check("app rows: Your EQ app FxSound shows Band counts to try in place of Filter counts to try and Shelf; with "
          "Automatic settings off it reads 10 with no tag, and the gray line under it is as it was",
          off[:7] == ({COUNTS: True, FILTERS: False, "best_fit.low_shelf": False, BANDS: False}, "10", False,
                      "e.g., 10 or 10, 31", "FxSound: Best fit adjusts band gains only. Edit range and step in More "
                      "settings › Best fit.", True, "10 bands"), off)
    # (the line of Help gives a fact that the label lacks; the band counts are in the line of the limits only)
    check("app rows: the tooltip of Band counts to try tells what a run does with the counts, then the allowed values",
          off[7] == "One EQ per band count; Best result selects one\nAllowed: 5, 10, 15, 20, or 31", off[7])
    st.auto_switched(True)
    page.refresh_auto()
    auto = (f.box.text(), f.tag.isVisible() and f.tag.text(), page.S["best_fit"]["per_app"]["fxsound"],
            page.estimate.text().split(" · ")[0], page.estimate.toolTip().split(" · ")[0],
            "Band counts: tries 5, 10, 15, 20, and 31 (all that FxSound has)" in st.why.text())
    check("app rows: with Automatic settings on, Band counts to try reads 5, 10, 15, 20, 31 with the tag automatic, "
          "and Settings to try and About these settings say so",
          auto == ("5, 10, 15, 20, 31", "automatic", {"band_counts": ALL_COUNTS}, "5 EQs, 5 to 31 bands",
                   "FxSound: 5 EQs (5, 10, 15, 20, and 31 bands), -12 to +12 dB (1 dB steps)", True), auto)
    _type(f, "10")
    yours = (dict(page.S["best_fit"]["per_app"]["fxsound"]), COUNTS in page.S["auto"]["manual"], f.tag.text(),
             st.mine_text.text())
    mine_note = next((ln for ln in re.split(r"<li>|<br>", st.why.text()) if "Band counts" in ln), st.why.text())
    _type(f, "10, 31")
    eq_screen.wait_for(lambda: page.estimate.text().startswith("2 EQs"), 30)  # (the line follows after the plan)
    two = page.estimate.text().split(" · ")[0]
    st.make_auto(COUNTS)
    back = (dict(page.S["best_fit"]["per_app"]["fxsound"]), COUNTS in page.S["auto"]["manual"], f.tag.text(), f.box.text())
    check("app rows: the note of a value of the user says “band counts” one time, with one ( ) of its own",
          mine_note.count("and counts") == 1 and "(all that FxSound has)" in mine_note, mine_note)
    check("app rows: Settings to try names the two band counts of a list of two", two == "2 EQs, 10 and 31 bands", two)
    check("app rows: 10 typed is the user's value (your value ↺, named Band counts in Custom values); ↺ makes it "
          "automatic again",
          yours == ({"band_counts": [10]}, True, "your value ↺", "Custom values: Band counts (click “your value ↺” "
                    "to reset)")
          and back == ({"band_counts": ALL_COUNTS}, False, "automatic", "5, 10, 15, 20, 31"), (yours, back))
    # (no target or measurement selected: the automatic settings have no values, and the box shows what a run uses,
    # never an empty box. The state stood in: the page's automatic answer without values)
    kept = page.auto
    page.S["best_fit"]["per_app"]["fxsound"]["band_counts"] = [10]
    page.auto = {}
    st.refresh()
    empty = (f.box.text(), f.tag.text(), st.why.text())
    page.auto = kept
    page.refresh_auto()
    check("app rows: with no automatic values (no files selected), the box reads 10: it is never empty",
          empty == ("10", "automatic", "Select a target and measurement to enable automatic settings."), empty)
    st.auto_switched(False)
    got = {}
    for typed in ("5-31", "12", "40"):
        _type(f, "10")
        _type(f, typed, leave=False)
        red = (bool(f.box.property("bad")), page.S["best_fit"]["per_app"]["fxsound"]["band_counts"])
        f._edit_finished()
        got[typed] = (red, page.S["best_fit"]["per_app"]["fxsound"]["band_counts"], f.box.text(), said[-1])
    check("app rows: a count that FxSound does not have is red and not used; on leaving the box, 5-31 becomes 5, "
          "10, 15, 20, 31, 12 becomes 10 and 40 becomes 31, with the one message",
          got == {"5-31": ((True, [10]), ALL_COUNTS, "5, 10, 15, 20, 31",
                           "Adjusted to 5, 10, 15, 20, 31 (allowed: 5, 10, 15, 20, or 31)."),
                  "12": ((True, [10]), [10], "10", "Adjusted to 10 (allowed: 5, 10, 15, 20, or 31)."),
                  "40": ((True, [10]), [31], "31", "Adjusted to 31 (allowed: 5, 10, 15, 20, or 31).")}, got)
    unread = {}
    for typed in ("abc", "10.5", ""):
        _type(f, "10")
        _type(f, typed, leave=False)
        unread[typed] = (bool(f.box.property("bad")), f.box.toolTip(), page.S["best_fit"]["per_app"]["fxsound"]["band_counts"])
    check("app rows: a text that is no list in Band counts to try is red, and its message names only counts that "
          "FxSound has",
          all(v == (True, "Allowed: 5, 10, 15, 20, or 31", [10]) for v in unread.values())
          and all(int(n) in ALL_COUNTS for v in unread.values() for n in re.findall(r"\d+", v[1])), unread)
    _type(f, "10")
    page.choose_app("apo")
    sight = {}
    for layout in ("app:fxsound", "graphic_10", "bands", "any"):
        st.changed("best_fit.layout", layout)
        sight[layout] = (_in_sight(page, COUNTS), _in_sight(page, FILTERS))
    check("app rows: the Layout list set to FxSound shows Band counts to try; the 10-band graphic EQ and Your bands "
          "show neither box, and Parametric filters shows Filter counts to try",
          sight == {"app:fxsound": (True, False), "graphic_10": (False, False), "bands": (False, False),
                    "any": (False, True)}, sight)
    page.choose_app("apo")


@pytest.fixture(scope="module")
def five_counts(eq_screen, rows):
    """A run of FxSound's five band counts on the result card (Automatic settings off, the five counts typed)."""
    page = eq_screen.page
    page.choose_app("fxsound")
    page.S["auto"]["enabled"] = False
    _type(rows.form.fields[COUNTS], "5, 10, 15, 20, 31")
    before = page.run_result
    page.run_btn.click()
    eq_screen.wait_for(lambda: page.run_btn.isEnabled() and page.run_result is not before, 180)
    if page.run_result is None or page.run_result is before:
        raise RuntimeError(f"the FxSound run made no result: {page.progress_text.text()!r}")
    return page.run_result


def test_a_run_of_five_band_counts_on_the_result_card(eq_screen, five_counts, check):
    from ui.eq_page_cards import COUNT_LONGEST
    page, run = eq_screen.page, five_counts
    by_n = {r["n_filters"]: r for r in run["results"]}
    items = [page.count_combo.itemText(i) for i in range(page.count_combo.count())]
    want = [f"{n} bands  ·  {r['rms']:.2f} dB" + ("  ✓ selected for you" if r["id"] == run["pick"] else "")
            for n, r in sorted(by_n.items())]
    picked = next(r for r in run["results"] if r["id"] == run["pick"])["n_filters"]
    fm = page.count_combo.fontMetrics()
    widths = [fm.horizontalAdvance(t) for t in items]
    got = (sorted(by_n), items, page.count_lab.text(), page.all_btn.text(), page.res_sub.text())
    check("app rows: a run of FxSound's five band counts gives one result for each, and Number of filters lists each "
          "as “N bands · error”, the app's pick marked",
          got[0] == ALL_COUNTS and items == want and got[2] == "Number of filters" and got[3] == "All 5 results…",
          (got, want))
    check("app rows: each item of the list fits the width of the list (its longest item)",
          max(widths) <= fm.horizontalAdvance(COUNT_LONGEST), (widths, fm.horizontalAdvance(COUNT_LONGEST)))
    # (the same form as Settings to try, "-12 to +12 dB (1 dB steps)": the line said "-12.0 to +12.0 dB (1.0 dB
    # steps)")
    check("app rows: the line of the result names the band count of the pick, and the range and step of the sliders "
          "as Settings to try does",
          f"FxSound: {picked} bands, -12 to +12 dB (1 dB steps)" in got[4], got[4])
    half = page.run_label({"mode": "best_fit"}, {"engine": "graphic", "layout": "graphic_10", "n_filters": 10,
                                                 "gain_min": -6.5, "gain_max": 6.5, "step": 0.5})
    none = page.run_label({"mode": "best_fit"}, {"engine": "graphic", "layout": "graphic_10", "n_filters": 10})
    check("app rows: the line of a graphic EQ's result keeps a half dB, and a result with no range (an old History "
          "entry) still has its line",
          half == "10-band graphic EQ: 10 bands, -6.5 to +6.5 dB (0.5 dB steps)" and none.startswith("10-band graphic EQ: 10 bands"),
          (half, none))
    a, b = {"id": 1, "ear": 0.18, "ear_at": 2500.0, "engine": "graphic"}, {"id": 2, "ear": 0.47, "ear_at": 6200.0,
                                                                         "engine": "graphic"}
    far = dict(a, ear=0.52)
    notes = (page.pick_note({"pick": 1, "pick_case": "target", "ear_db": 0.25, "results": [a]}, a),
             page.pick_note({"pick": 1, "pick_case": "best", "ear_db": 0.25, "results": [far, b]}, far))
    check("app rows: the note of the pick says “bands” for a graphic EQ's result",
          notes == ("Audibly matches target: within 0.18 dB (limit: 0.25 dB), using the fewest bands needed",
                    "Couldn't match target: closest is 0.47 dB off near 6.2 kHz (fewer bands)"), notes)


def test_all_results_of_five_band_counts_has_no_grid(eq_screen, five_counts, check):
    from ui.all_results import AllResults
    page = eq_screen.page
    ar = AllResults(page)
    try:
        hidden = (ar.grid.isHidden(), ar.grid_title.isHidden(), ar.grid_note.isHidden())
        counts = sorted(ar.table.item(i, 1).value for i in range(ar.table.rowCount()))
        gains = {ar.table.item(i, 4).text() for i in range(ar.table.rowCount())}
        marked = [ar.table.item(i, 0).text() for i in range(ar.table.rowCount())
                  if "selected for you" in ar.table.item(i, 0).text()]
        check("all results: a run of a graphic EQ's band counts shows no error grid (each count has its own Q), and "
              "the table has a row for each of the 5 results, the pick marked, the slider range without decimals",
              hidden == (True, True, True) and counts == ALL_COUNTS and len(marked) == 1 and gains == {"-12 to 12"},
              (hidden, counts, marked, gains))
    finally:
        ar.close()
        ar.deleteLater()


def test_the_report_of_five_band_counts_has_no_grid(eq_screen, five_counts, check):
    # (the page sends "engine" with each result of the run: without it the Report drew the grid by filter count and
    # maximum Q, filled only on its diagonal. eq.report.grids_for alone was tested)
    page, run = eq_screen.page, five_counts
    page.run_result = run
    page.show_result(run["pick"])
    path = page.report(open_it=False)
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    shown = next(r for r in run["results"] if r["id"] == run["pick"])
    check("report: the Report of a run of FxSound's band counts has no error grid, and has the filter table of the "
          "result shown",
          "error by filter count and maximum Q" not in text and "Best fit: error by" not in text
          and text.count("<table") == 1 and f"{shown['n_filters']} bands" in text,
          (path, text.count("<table"), "error by filter count" in text))


def test_compare_and_history_say_bands(eq_screen, five_counts, check):
    from ui.compare_results import options
    from ui.history_window import HistoryWindow
    page, run = eq_screen.page, five_counts
    page.run_result = run
    page.show_result(run["pick"])
    shown = next(r for r in run["results"] if r["id"] == run["pick"])
    labels = [o["label"] for o in options(page) if o["run"] is run and not o["label"].startswith("Shown: ")]
    want = [f"#{run.get('n', '?')} · {r['n_filters']} bands · {r['rms']:.2f} dB"
            for r in sorted(run["results"], key=lambda r: r["n_filters"]) if r["id"] != run["pick"]]
    check("compare: the other results of a run of band counts read “#n · N bands · error”",
          len(want) == 4 and labels == want, (labels, want))
    entry = eqpage.save_result(eq_screen, "Band counts check")
    hist = [o["label"] for o in options(page) if o["run"] is None]
    hw = HistoryWindow(page, False)
    kept = []
    add = page.listen.add
    page.listen.add = lambda name, *a, **k: kept.append(name) or True  # (the name only: no EQ goes into the list)
    try:
        lines = [w.text().replace(chr(0xA0), " ") for w in hw.findChildren(QLabel)
                 if " bands" in w.text().replace(chr(0xA0), " ")]
        hw.keep_to_compare(entry)
    finally:
        page.listen.add = add
        hw.close()
        hw.deleteLater()
    n = shown["n_filters"]
    check("history: a saved result of a graphic EQ reads “N bands” in Compare's list and in the History window",
          entry["result"].get("engine") == "graphic" and any(h.endswith(f" · {n} bands") for h in hist)
          and any(f"· {n} bands ·" in t for t in lines), (hist, lines))
    check("history: Keep to compare names the EQ of a graphic result “Best fit, N bands (day time)”",
          len(kept) == 1 and kept[0].startswith(f"Best fit, {n} bands ("), kept)


@pytest.mark.timeout(600)
def test_calculate_from_a_card_with_bands_switched_off_keeps_its_band_count(eq_screen, five_counts, check):
    # (the band count of the card was taken from the number of filters switched on: the 10-band card with 5 bands
    # off gave the 5-band EQ, at other frequencies than the card)
    page, run = eq_screen.page, five_counts
    page.run_result = run
    ten = next(r for r in run["results"] if r["n_filters"] == 10)
    page.show_result(ten["id"])
    for f in page.EDIT[:5]:
        f["enabled"] = False
    sent = page.retry_from_card(False)
    try:
        page.retry_btn.menu().actions()[0].trigger()  # (Adjust them)
        eq_screen.wait_for(lambda: page.run_btn.isEnabled() and page.run_result is not run, 180)
        again = page.run_result
        rows = [r.get("rows") for r in (again or {}).get("results") or []] if again is not run else None
        freqs = [f["freq"] for f in again["results"][0]["filters"]] if rows else None
    finally:
        page.run_result = run
        page.show_result(run["pick"])
    check("app rows: Calculate from these filters on the 10-band FxSound card with 5 bands switched off sends the "
          "whole card, and the new result has the 10 bands of the card",
          len(sent["filters"]) == 5 and len(sent["card"]) == 10 and rows == [10]
          and freqs == [f["freq"] for f in ten["filters"]], (len(sent["filters"]), len(sent["card"]), rows, freqs))


@pytest.mark.timeout(600)
def test_a_queued_run_says_bands(eq_screen, five_counts, check):
    from ui.queue_window import QueueWindow, _ticked
    page = eq_screen.page
    kept_S = copy.deepcopy(page.S)
    q = QueueWindow(page)
    try:
        q.tgts.item(0).setCheckState(Qt.Checked)
        n = len(_ticked(q.devs)) * len(_ticked(q.tgts))
        q.start()
        done = eq_screen.wait_for(lambda: not q.running, 300)
        said = [q.table.item(i, 2).text() for i in range(q.table.rowCount())]
    finally:
        q.close()
        page.S = kept_S
        page.svc.call("/api/settings", {"settings": page.S})
    check("queue: a queued run of FxSound's band counts says “Done: N bands · error”",
          done and n >= 1 and len(said) == n and all(re.match(r"Done: \d+ bands · \d+\.\d\d dB · ", s) for s in said),
          (done, n, said))


def test_a_preset_keeps_the_values_of_an_app(eq_screen, rows, check):
    from eq import paths as eq_paths
    from eq import settings as eq_settings
    page = eq_screen.page
    was = copy.deepcopy(page.S)
    page.choose_app("peace")
    _type(rows.form.fields[BANDS], "10")
    eq_settings.save_preset("Peace ten", page.S)
    old = json.loads(json.dumps(page.S))
    del old["best_fit"]["per_app"]  # (a preset of a version before these settings: no such key in its file)
    os.makedirs(eq_paths.PRESET_DIR, exist_ok=True)
    with open(os.path.join(eq_paths.PRESET_DIR, "Before per app.json"), "w", encoding="utf-8") as fh:
        json.dump(old, fh)
    try:
        _type(rows.form.fields[BANDS], "20")
        page.load_preset("Peace ten")
        ten = (dict(page.S["best_fit"]["per_app"]["peace"]), rows.form.fields[BANDS].box.text(), _line(page, "peace"))
        page.load_preset("Before per app")
        before = (copy.deepcopy(page.S["best_fit"]["per_app"]), rows.form.fields[BANDS].box.text(), page.S["best_fit"]["layout"])
    finally:
        page.delete_preset("Peace ten")
        page.delete_preset("Before per app")
        page.S = was
        page.changed(curves=True)
        eq_screen.wait_for(lambda: page.curves is not None, 30)
    check("presets: a preset saved with Peace bands 10 loads 10; a preset without these settings loads Peace's 31 "
          "and 30 and FxSound's 10 bands, its layout kept",
          ten == ({"bands": 10, "gain": 30}, "10", "Up to 10 bands · ±30 dB")
          and before == ({"peace": {"bands": 31, "gain": 30}, "fxsound": {"band_counts": [10]}}, "31", "app:peace"),
          (ten, before))


def _play_your_values(s):
    """The Guide on the step Your values, its demo played to its end, then the Guide ended: (ended, the demo's
    errors, the words of its actions)."""
    from ui import guide, tour
    t = guide.start_eq(s.page)
    t.all_chk.setChecked(False)
    try:
        i = next(n for n, st in enumerate(t.steps) if st["title"] == "Your values")
        t.go_to_step(i)
        words = [a.get("say") for a in tour.demo_actions(t.steps[i])]
        t.speed = 8.0
        t.replay()
        ended = s.wait_for(lambda: not t.demo_running, 60)
        return ended, list(t.demo_errors), words, t.steps[i]["text"]
    finally:
        t.end()
        qt.pump(200)


@pytest.mark.timeout(600)
def test_the_guide_step_your_values(eq_screen, rows, check, monkeypatch):
    from ui import guide_eq, tour
    monkeypatch.setattr(tour, "_animations_on", lambda: True)
    page, st = eq_screen.page, rows
    st.fold.btn.setChecked(True)
    found, played = {}, {}
    for key in ("peace", "fxsound", "apo"):
        page.choose_app(key)
        st.auto_switched(True)
        page.refresh_auto()
        st.fold.btn.setChecked(True)
        qt.pump(50)
        box = guide_eq.first_value_box(st)
        found[key] = box.path if box is not None else None
        before = (json.dumps(page.S, sort_keys=True, default=str),
                  {p: (f.box.text(), f.tag.isVisible() and f.tag.text()) for p, f in st.form.fields.items()
                   if f.kind in BOXES})
        ended, errors, words, text = _play_your_values(eq_screen)
        st.fold.btn.setChecked(True)
        qt.pump(50)
        after = (json.dumps(page.S, sort_keys=True, default=str),
                 {p: (f.box.text(), f.tag.isVisible() and f.tag.text()) for p, f in st.form.fields.items()
                  if f.kind in BOXES})
        played[key] = (ended, errors, before == after, words, "boxes of that app are also here" in text)
    st.auto_switched(False)
    page.choose_app("apo")
    check("guide: the box of the step Your values is Filter counts to try with Peace (never a Peace box, which has "
          "no tag) and Band counts to try with FxSound",
          found == {"peace": FILTERS, "fxsound": COUNTS, "apo": FILTERS}, found)
    # (one text, true with the boxes in sight and without: with Equalizer APO no box of an EQ app shows, and "are
    # here" pointed at the label of another box)
    say = ["Type your value. Press Enter", "Or disable Automatic settings",
           "With Peace or FxSound, the boxes of that app show here"]
    check("guide: the demo of Your values plays to its end with Peace, with FxSound and with another app, its "
          "last action about the boxes of the EQ app, and no setting, box or tag is changed after it",
          all(v == (True, [], True, say, True) for v in played.values()), played)
    paths = guide_eq.app_paths(page)
    check("guide: the boxes of an EQ app that the demo looks for are the three rows of Settings",
          paths == [BANDS, GAIN, COUNTS], paths)
