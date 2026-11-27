"""Make an EQ's Website values from the measurement's database (feature 5, the owner's decisions of 2026-11-25), on a
page opened with Website AutoEQ: one set and the automatic settings on, the sample measurement recorded as from HBB
(an AutoEQ panel with no gain or Q boxes), offline: the list Which website to copy (its two pinned choices, then every
website A to Z, with its search box), the gray line under it for each case, the 7 values automatic and a typed one
yours, the gain and Q boxes fixed and off for HBB (and on again for listener800), Other, Best fit's own values, a
measurement from a file, and the names a screen reader reads."""
import os

import pytest

from helpers import eqpage, qt

HBB = "https://hbb.squig.link/"
L800 = "https://listener800.github.io/5128iem.html"
FIXED = ("site_single.gain_min", "site_single.gain_max", "site_single.q_min", "site_single.q_max")


@pytest.fixture(scope="module")
def web(tmp_path_factory):
    from eq import inputs, rigs, settings
    s = eqpage.open_screen(str(tmp_path_factory.mktemp("website_values")), settings={"mode": "site_single"})
    _t, meas = inputs.selected(settings.load())
    s.names = [os.path.basename(p) for p in meas]
    rigs.record_source(s.names, {"site_url": HBB, "site": "HBB", "name": "Sample"})
    _reload(s)
    yield s
    eqpage.close_screen(s)


def _reload(s):
    """The curves again (as a change of measurement does), waited for with their analysis and automatic values."""
    s.page.load_curves()
    qt.settle(0.5, 60)
    s.wait_for(lambda: s.page.curves is not None and s.page.auto is not None, 60)


def _choose(s, value):
    s.page.settings.changed("site.profile", value)
    qt.settle(0.5, 60)


def _boxes(st):
    return {p: (st.form.fields[p].box.isEnabled(), st.form.fields[p].box.text(), st.form.fields[p].box.toolTip(),
                st.form.fields[p].tag.isVisibleTo(st.form)) for p in FIXED}


def test_the_list(web, check):
    from ui.search_combo import natural_key
    box = web.page.settings.adv_form.fields["site.profile"].box
    rows = [(box.itemData(i), box.itemText(i)) for i in range(box.count())]
    names = [t for _v, t in rows[2:]]
    check("website values: Which website to copy has The database of the measurement and Other on top, then every "
          "graph website A to Z (not AutoEq), and opens with its search box",
          rows[:2] == [("auto", "The database of the measurement"), ("custom", "Other")] and len(rows) > 150
          and names == sorted(names, key=natural_key) and all(v.startswith("site:http") for v, _t in rows[2:])
          and "AutoEq (GitHub)" not in names and box.has_search_box() and box.pinned == 2
          and box.currentData() == "auto", rows[:4])


def test_the_database_of_the_measurement(web, check):
    page, st = web.page, web.page.settings
    from eq import site_values
    hbb = site_values.table_entry(HBB)["values"]
    tags = {p: st.adv_form.fields[p].tag.text() for p in site_values.PATHS}
    check("website values: the gray line names the measurement's database, the day its values were read and its fixed "
          "gain and Q", st.site_note.text() == "HBB: values from its website (read 2026-11-24). No gain or Q boxes on "
                                              "its AutoEQ panel, so gain -12 to 12 dB and Q 0.5–2 are fixed.",
          st.site_note.text())
    check("website values: the 7 values are HBB's, each “automatic”",
          all(page.S["site"][k] == v for k, v in hbb.items()) and set(tags.values()) == {"automatic"}, (page.S["site"], tags))
    b = _boxes(st)
    check("website values: Gain from/to and Q from/to are off, show HBB's fixed values, no tag, the reason in their "
          "tooltip (a screen reader reads it)",
          [x[:2] for x in b.values()] == [(False, "-12"), (False, "12"), (False, "0.5"), (False, "2")]
          and b["site_single.gain_min"][2] == "Fixed on HBB (no gain boxes on its AutoEQ panel)"
          and b["site_single.q_max"][2] == "Fixed on HBB (no Q boxes on its AutoEQ panel)"
          and not any(x[3] for x in b.values()), b)
    why = st.why.text()
    check("website values: About these settings has the gray line's words and a line for each fixed value",
          "HBB: values from its website" in why and "Gain -12 to 12 dB: fixed on HBB (no gain boxes)" in why
          and "Q 0.5–2: fixed on HBB (no Q boxes)" in why, why)


def test_sweep_fixed_values(web, check):
    page, st = web.page, web.page.settings
    page.set_mode("site_sweep")
    qt.settle(0.5, 60)
    try:
        f = st.adv_form.fields
        rr = f["site_sweep.gain_ranges"].box
        got = (rr.isEnabled(), rr.text(), f["site_sweep.q_min"].box.isEnabled(), f["site_sweep.q_max"].box.text(),
               f["site_sweep.q_max"].box.isEnabled())
        note = st.sweep_note.text()
        check("website values: with the sweep, Gain ranges, Q from and Q “to” values are off with HBB's values, and the "
              "line of what is tried says them", got == (False, "-12 to 12", False, "2", False)
              and "gain -12 to 12" in note and "Q to 2." in note, (got, note))
    finally:
        page.set_mode("site_single")
        qt.settle(0.5, 60)


def test_a_website_with_the_boxes(web, check):
    st = web.page.settings
    _choose(web, "site:" + L800)
    try:
        b = _boxes(st)
        check("website values: a website by name with gain and Q boxes (listener800): its values, its line, the boxes on",
              st.site_note.text() == "listener800 5128 IEMs: values from its website (read 2026-11-24)"
              and web.page.S["site"]["normalization"] == "Hz~" and all(x[0] for x in b.values())
              and all(x[2] != "" and "Fixed" not in x[2] for x in b.values()), (st.site_note.text(), b))
    finally:
        _choose(web, "auto")


def test_a_value_of_your_own(web, check):
    page, st = web.page, web.page.settings
    f = st.adv_form.fields["site.smooth_level"]
    f.box.setText("2")
    f._typed()
    qt.settle(0.5, 60)
    _reload(web)  # (a new load of the curves, as another measurement gives)
    yours = (page.S["site"]["smooth_level"], f.tag.text())
    st.make_auto("site.smooth_level")
    qt.settle(0.5, 60)
    back = (page.S["site"]["smooth_level"], f.tag.text())
    check("website values: a value typed is yours (custom ↺) and stays through new curves; its tag gives the "
          "database's value back", yours == (2, "custom ↺") and back == (5, "automatic"), (yours, back))


def test_other(web, check):
    page, st = web.page, web.page.settings
    from eq import site_values
    before = {k: page.S["site"][k] for k in site_values.KEYS}
    _choose(web, "custom")
    try:
        tags = [st.adv_form.fields[p].tag.isVisibleTo(st.adv_form) for p in site_values.PATHS]
        check("website values: Other changes no value, hides the 7 tags, fixes nothing, and its line says so",
              {k: page.S["site"][k] for k in site_values.KEYS} == before and not any(tags)
              and all(x[0] for x in _boxes(st).values())
              and st.site_note.text() == "Other: values below stay as you set them", (tags, st.site_note.text()))
    finally:
        _choose(web, "auto")


def test_best_fit_keeps_its_own_values(web, check):
    page, st = web.page, web.page.settings
    loads = []
    real = page.load_curves
    page.load_curves = lambda: (loads.append(1), real())[1]
    try:
        page.set_mode("best_fit")
        qt.settle(0.5, 60)
        got = (page.S["site"]["smooth_level"], page.S["site"]["normalization"], st.site_note.text(), len(loads))
    finally:
        del page.load_curves
        page.set_mode("site_single")
        qt.settle(0.5, 60)
    check("website values: changing to Best fit loads the curves once, with the app's own values, and the line says so",
          got == (3, "Hz~", "Best fit keeps its own values; the database's values are for the Website methods", 1), got)


def test_a_measurement_from_a_file(web, check):
    from eq import rigs
    st = web.page.settings
    rigs.forget_source(web.names)
    _reload(web)
    try:
        check("website values: a measurement from a file: the usual values, no box fixed, and the line tells to select "
              "the website", st.site_note.text() == "Measurement isn't from a database, so the usual squig.link values "
                                                    "apply. To copy a website, select it in this list."
              and web.page.S["site"]["treble_start_from"] == 7000 and all(x[0] for x in _boxes(st).values()),
              st.site_note.text())
    finally:
        rigs.record_source(web.names, {"site_url": HBB, "site": "HBB", "name": "Sample"})
        _reload(web)


def test_names_a_screen_reader_reads(web, check):
    st = web.page.settings
    f = st.adv_form.fields["site.profile"]
    names = (f.box.accessibleName(), st.site_note.accessibleName(), st.form.fields["site_single.gain_min"].box.accessibleName())
    check("website values: the list is named by its label, the gray line by its own words, a fixed box by its label",
          names == ("Which website to copy", "", "Gain from (dB)") and st.site_note.text(), names)
