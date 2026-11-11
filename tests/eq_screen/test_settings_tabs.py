"""Make an EQ's More settings, a tab for each section (ui\\eq_settings.py over ui\\forms.py), on a page opened with a
saved method other than Best fit (Website AutoEQ: one set), as the review of 2026-11-10 found it: the tab it opens on,
each tab's height, the tick boxes' names and words; and the Adjust window's graph in the theme's colours. A page of
its own (the eq_screen fixture's opens with Best fit), offline."""
import pytest

from helpers import eqpage, qt


@pytest.fixture(scope="module")
def one_set(tmp_path_factory):
    s = eqpage.open_screen(str(tmp_path_factory.mktemp("settings_tabs")), settings={"mode": "site_single"})
    yield s
    eqpage.close_screen(s)


def test_more_settings_opens_on_a_tab_that_applies(one_set, check):
    page = one_set.page
    st, form = page.settings, page.settings.adv_form
    st.adv.btn.setChecked(True)
    qt.pump(100)
    shown = [b.text() for b in form.tab_btns.values() if not b.isHidden()]
    checked = [b.text() for b in form.tab_btns.values() if b.isChecked()]
    current = form.tab_btns[form.pages.currentIndex()].text()
    st.adv.btn.setChecked(False)
    # (it opened on Best fit's empty page with no tab selected: the form changed tab only while it showed)
    check("more settings: with a saved method other than Best fit, it opens on a tab that applies, selected, its "
          "settings in sight",
          page.S["mode"] == "site_single" and "Best fit" not in shown and checked == [current] and current in shown,
          (page.S["mode"], shown, checked, current))


def test_each_tab_as_high_as_its_settings(one_set, check):
    from PySide6.QtWidgets import QCheckBox
    page = one_set.page
    st, form = page.settings, page.settings.adv_form
    st.adv.btn.setChecked(True)
    seen, cut = {}, []
    try:
        for i, b in form.tab_btns.items():
            if b.isHidden():
                continue
            form.show_tab(i)
            qt.pump(100)
            p = form.pages.currentWidget()
            seen[b.text()] = (form.pages.height(), p.layout().totalHeightForWidth(form.pages.width()))
            cut += [c.text() for c in p.findChildren(QCheckBox) if c.isVisible() and c.width() < c.sizeHint().width()]
    finally:
        form.show_tab(next(i for i, b in form.tab_btns.items() if not b.isHidden()))
        st.adv.btn.setChecked(False)
    # (Qt's stack was as high as its highest page: up to 330 px of empty room above Calculate on the short tabs; and
    # the convolution file's words were cut at every width)
    check("more settings: each tab is as high as its own settings (History and This PC are short), and no tick box's "
          "words are cut",
          seen and all(abs(h - own) <= 2 for h, own in seen.values()) and seen["This PC"][0] < 120
          and seen["History"][0] < 200 and not cut, (seen, cut))


def test_tick_boxes_say_their_words(one_set, check):
    from PySide6.QtGui import QAccessible
    page = one_set.page
    names = {}
    for form in (page.settings.form, page.settings.adv_form):
        for path, f in form.fields.items():
            if f.kind == "check":
                iface = QAccessible.queryAccessibleInterface(f.box)
                names[path] = (iface.text(QAccessible.Name) if iface is not None else "", f.box.text())
    wrong = {p: n for p, n in names.items() if n[0] != n[1] or not n[0]}
    # (2026-11-10: "export.apo", "best_fit.start_keep" and "history.eqd_before" were what a screen reader said)
    check("more settings: a screen reader says each tick box's own words (never a setting's path or its tooltip)",
          len(names) >= 12 and not wrong, wrong or len(names))


def test_adjust_graph_in_the_theme(one_set, check):
    from PySide6.QtGui import QColor
    from ui import theme
    page = one_set.page
    st = page.settings
    st.open_adjust()
    qt.pump(100)
    want = QColor(theme.graph_colours()["axis"]).name()
    got = {ax: (st.adjust_plot.getAxis(ax).pen().color().name(), st.adjust_plot.getAxis(ax).textPen().color().name())
           for ax in ("left", "bottom")}
    st.adjust_window.close()
    # (pyqtgraph's own gray axes: the other graphs have the theme's)
    check("adjust: the target's graph has the axes of the page's graphs (the theme's colour)",
          all(v == (want, want) for v in got.values()), (want, got))


def test_layout_list_rows_are_short(one_set, check):
    # (the user, 2026-11-10: each of the 23 EQ apps read "EQ apps (Your EQ app): FxSound")
    from ui.eq_settings import layout_words
    box = one_set.page.settings.adv_form.fields["best_fit.layout"].box
    rows = [box.itemText(k) for k in range(box.count())]
    words = [layout_words({"name": n, "group": g}) for n, g in
             (("FxSound", "EQ apps (Your EQ app)"), ("Parametric filters", "Any"), ("10-band graphic EQ", "Graphic EQ"),
              ("Your bands", "Graphic EQ"))]
    check("more settings: a row of the Layout list is the layout's name (an EQ app: the app's name only; a graphic EQ "
          "whose name does not say so: “Graphic EQ: ” first)",
          words == ["FxSound", "Parametric filters", "10-band graphic EQ", "Graphic EQ: Your bands"]
          and "FxSound" in rows and "Graphic EQ: Your bands" in rows and not [r for r in rows if "EQ apps" in r],
          (words, rows))
