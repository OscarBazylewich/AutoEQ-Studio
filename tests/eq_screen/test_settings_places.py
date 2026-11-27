"""Where Make an EQ's settings are (the control audit of 2026-11-27): AutoEQ TrebleStartFrom only with the Website
methods, and "Custom values" naming only the settings whose boxes show. A page of its own, offline, opened with Best
fit."""
import pytest

from helpers import eqpage, qt


@pytest.fixture(scope="module")
def places(tmp_path_factory):
    s = eqpage.open_screen(str(tmp_path_factory.mktemp("settings_places")), settings={"mode": "best_fit"})
    yield s
    eqpage.close_screen(s)


def _mode(s, mode):
    s.page.set_mode(mode)
    qt.settle(0.5, 60)
    s.page.settings.refresh()


def _applies(st, path):
    return any(f.applies(path) for f in st.forms())


def test_treble_start_from_only_with_the_website_methods(places, check):
    page, st = places.page, places.page.settings
    seen = {}
    try:
        for mode in ("best_fit", "site_single", "site_sweep"):
            _mode(places, mode)
            seen[mode] = (_applies(st, "site.treble_start_from"), _applies(st, "site.profile"))
    finally:
        _mode(places, "best_fit")
    check("settings: AutoEQ TrebleStartFrom shows only with the two Website methods; Which website to copy shows with "
          "every method", seen == {"best_fit": (False, True), "site_single": (True, True), "site_sweep": (True, True)},
          seen)
    page.S["auto"]["enabled"] = True
    st.changed("site.treble_start_from", 9000)
    try:
        with_bf = (not st.mine_box.isHidden(), st.mine_text.text())
        _mode(places, "site_single")
        with_site = (not st.mine_box.isHidden(), st.mine_text.text())
    finally:
        st.make_auto("site.treble_start_from")
        _mode(places, "best_fit")
    # (Custom values named AutoEQ TrebleStartFrom with Best fit, with no box in sight to reset it)
    check("settings: Custom values names AutoEQ TrebleStartFrom only while its box shows (a Website method)",
          not with_bf[0] and with_site[0] and "AutoEQ TrebleStartFrom" in with_site[1], (with_bf, with_site))


def test_filter_rows_to_try_in_settings(places, check):
    st = places.page.settings
    try:
        _mode(places, "site_sweep")
        got = (st.form.applies("site_sweep.filter_rows"), "site_sweep.filter_rows" in st.adv_form.fields,
               st.sweep_note.text())
    finally:
        _mode(places, "best_fit")
    # (it was in More settings › Website best settings, with a gray line in Settings that repeated it)
    check("settings: with Website AutoEQ: find the best settings, Filter rows to try is in Settings (as Best fit's "
          "Filter counts to try), not in More settings, and the gray line no longer repeats it",
          got[0] and not got[1] and got[2].startswith("Testing: frequency to ") and "filter rows" not in got[2], got)


PAIRS = {"best_fit.gain_min": ("best_fit.gain_max", "Gain from (dB)"), "best_fit.q_min": ("best_fit.q_max", "Q from"),
         "site_sweep.freq_low": ("site_sweep.freq_high", "Frequency from"),
         "site_sweep.q_min": ("site_sweep.q_max", "Q from")}


def test_a_from_and_its_to_values_in_one_cell(places, check):
    from PySide6.QtWidgets import QLabel
    from ui import forms
    f = places.page.settings.adv_form.fields
    seen = {}
    for lo, (hi, label) in PAIRS.items():
        a, b = f[lo], f[hi]
        cell = a.parentWidget().parentWidget()  # (the boxes' row, then the cell: its label above it)
        words = [w.text() for w in cell.findChildren(QLabel) if w.parentWidget() is cell]
        seen[lo] = {"one cell": b.parentWidget().parentWidget() is cell, "label": words[:1] == [label],
                    "widths": a.box.width() + b.box.width() + forms.PAIR_TO + 2 * forms.PAIR_GAP == forms.LONG,
                    "own tooltips": bool(b.box.toolTip()) and b.box.toolTip() != a.box.toolTip(),
                    "own Help": (a.box.property("help_key"), b.box.property("help_key")) == (lo, hi)}
    bad = {p: [k for k, v in s.items() if not v] for p, s in seen.items() if not all(s.values())}
    # (each "from" was a cell, and its list of "to" values another one in the next row of the other column)
    check("settings: Best fit's gain and Q, and the sweep's frequency and Q: the “from” number and its list of “to” "
          "values in one cell (one label, the pair as wide as one long box), each box with its own tooltip and Help",
          not bad, bad)
    from eq import settings
    names = {p: settings.AUTO_NAMES[p] for p in ("best_fit.gain_min", "best_fit.gain_max", "best_fit.q_max")}
    check("settings: the names that Custom values and the automatic notes use follow the cell's words",
          names == {"best_fit.gain_min": "Gain from", "best_fit.gain_max": "Gain “to” values",
                    "best_fit.q_max": "Q “to” values"}, names)


def test_saved_files_file_types_as_a_group(places, check):
    from PySide6.QtCore import QPoint
    from PySide6.QtWidgets import QLabel
    page, st = places.page, places.page.settings
    form = st.adv_form
    i = next(k for k, b in form.tab_btns.items() if b.text() == "Saved files")
    was = form.pages.currentIndex()
    st.adv.btn.setChecked(True)
    form.show_tab(i)
    qt.pump(100)
    try:
        tab = form.pages.currentWidget()
        heads = [w.text() for w in tab.findChildren(QLabel) if w.property("role") == "section" and w.isVisible()]
        y = lambda p: form.fields[p].mapTo(tab, QPoint(0, 0)).y()
        last = max(y("export." + k) for k in ("apo", "report", "convolution"))
        after = y("export.preamp_rounding")
    finally:
        form.show_tab(was)
        st.adv.btn.setChecked(False)
    # (Pre-amp rounding sat beside “An HTML report”, in the flow of the file types)
    check("settings: More settings › Saved files has the heading “File types” over the tick boxes, and its other "
          "settings start on a row under them", heads == ["File types"] and after > last, (heads, last, after))
