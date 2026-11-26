"""Make an EQ's Gain ranges as rows of two boxes (ui\\forms.py's RangeRows in More settings › Website best settings;
feature 4, the owner's decisions of 2026-11-24 and 2026-11-25), on a page opened with the method Website AutoEQ: find
the best settings (the eq_screen fixture's opens with Best fit), offline: a value typed lands in the settings as yours,
the gray line of the ranges tried says "to", the tab grows with its rows, every control has a name and is reached by
Tab, Tab goes row by row with real keys, and the Guide's step "Settings" shows the rows and Add a range and puts the
fold and the tab back."""
import pytest
from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QWidget

from helpers import eqpage, qt

GAIN = "site_sweep.gain_ranges"
COVERS = ("a11y",)  # (app\tools\a11y.py, imported through helpers.paths.import_tool: no import statement shows it)


@pytest.fixture(scope="module")
def sweep(tmp_path_factory):
    s = eqpage.open_screen(str(tmp_path_factory.mktemp("gain_ranges")), settings={"mode": "site_sweep"})
    yield s
    eqpage.close_screen(s)


@pytest.fixture
def shown(sweep):
    """More settings open on its Website best settings tab, the window active; after the test: Gain ranges
    automatic again, the tab and the fold as they were."""
    page = sweep.page
    st = page.settings
    form = st.adv_form
    kept = (st.adv.btn.isChecked(), form.pages.currentIndex())
    st.adv.btn.setChecked(True)
    form.show_tab(next(i for i, b in form.tab_btns.items() if b.text() == "Website best settings"))
    page.activateWindow()
    qt.pump(150)
    yield page, form.fields[GAIN]
    if QApplication.focusWidget() is not None:
        QApplication.focusWidget().clearFocus()
    st.make_auto(GAIN)
    form.show_tab(kept[1])
    st.adv.btn.setChecked(kept[0])
    qt.pump(50)


def _in_sight(page, w):
    vp = page.page_area.viewport()
    return w.isVisible() and vp.rect().contains(QRect(w.mapTo(vp, QPoint(0, 0)), w.size()))


def _type(page, box, keys):
    page.page_area.ensureWidgetVisible(box, 0, 120)
    box.setFocus(Qt.TabFocusReason)
    box.selectAll()
    QTest.keyClicks(box, keys)
    qt.pump(50)


def test_a_typed_value_on_the_page(shown, check):
    page, f = shown
    rows = f.box.rows
    first = int(rows[0].lo.text())
    _type(page, rows[0].hi, "8")
    sw = page.S["site_sweep"]
    note = page.settings.sweep_note.text()
    got = (sw["gain_ranges"][0], GAIN in page.S["auto"]["manual"], f.tag.text(), f"gain {first} to 8" in note,
           ".." in note)
    check("gain ranges on the page: a number typed in a row is in the settings at once, as your value (“custom ↺”), "
          "and the gray line of the ranges tried writes it “-12 to 8”",
          got == ([first, 8], True, "custom ↺", True, False), (got, note))


def test_the_tab_as_high_as_its_rows(shown, check):
    page, f = shown
    form = page.settings.adv_form
    before = form.pages.height()
    for _ in range(3):
        QTest.mouseClick(f.box.add_btn, Qt.LeftButton)
        qt.pump(100)
    tab = form.pages.currentWidget()
    own = tab.layout().totalHeightForWidth(form.pages.width())
    whole = QRect(QPoint(0, 0), tab.size())
    cut = [type(w).__name__ + " " + (w.accessibleName() or "") for w in tab.findChildren(QWidget)
           if w.isVisible() and not whole.contains(QRect(w.mapTo(tab, QPoint(0, 0)), w.size()))]
    n = len([r for r in f.box.rows if r.widget.isVisible()])
    check("gain ranges on the page: after Add a range the Website best settings tab is as high as its rows (taller "
          "than before), and no control on it is cut",
          abs(form.pages.height() - own) <= 2 and form.pages.height() > before and not cut
          and n == len(page.S["site_sweep"]["gain_ranges"]), (before, form.pages.height(), own, cut, n))


def test_named_and_reachable(shown, check):
    from helpers import paths
    a11y = paths.import_tool("a11y")
    page, f = shown
    QTest.mouseClick(f.box.add_btn, Qt.LeftButton)
    qt.pump(50)
    QTest.mouseClick(f.box.rows[0].x, Qt.LeftButton)  # (a row hidden, kept for a later Add a range)
    qt.pump(100)
    hidden = [r for r in f.box.rows if not r.widget.isVisible()]
    found = (a11y.unnamed(page), a11y.unreachable(page))
    check("gain ranges on the page: with the method Website AutoEQ: find the best settings, every control of the page "
          "has a name for a screen reader and Tab reaches it (a hidden row there too)",
          hidden and found == ([], []), (len(hidden), found))


def test_tab_row_by_row_on_the_page(shown, check):
    page, f = shown
    form = page.settings.adv_form
    before, after = form.fields["site_sweep.freq_high"].box, form.fields["site_sweep.q_min"].box

    def seq():
        page.page_area.ensureWidgetVisible(before, 0, 120)
        before.setFocus(Qt.TabFocusReason)
        out = []
        for _ in range(40):
            QTest.keyClick(QApplication.focusWidget(), Qt.Key_Tab)
            w = QApplication.focusWidget()
            out.append(w)
            if w is after or w is None:
                break
        return out

    def want():
        rows = [r for r in f.box.rows if r.widget.isVisible()]
        ws = [w for r in rows for w in (r.lo, r.hi, r.x) if w.isVisible()] + [f.box.add_btn]
        return ws + ([f.tag] if f.tag.isVisible() and f.tag.isEnabled() else []) + [after]
    QTest.mouseClick(f.box.add_btn, Qt.LeftButton)
    qt.pump(100)
    added = (seq(), want())
    QTest.mouseClick(f.tag, Qt.LeftButton)  # ("custom ↺": the automatic rows back)
    qt.pump(100)
    auto = (seq(), want())
    check("gain ranges on the page: Tab goes from Frequency “to” values row by row (first box, second box, ✕), then "
          "Add a range, the tag, and Q from: after Add a range, and after a click on “custom ↺”",
          added[0] == added[1] and auto[0] == auto[1] and f.tag.text() == "automatic",
          ([type(w).__name__ for w in added[0]], len(added[1]), [type(w).__name__ for w in auto[0]], len(auto[1])))


def test_guide_shows_the_rows(sweep, check):
    from ui import guide
    page = sweep.page
    st = page.settings
    form = st.adv_form
    kept = (st.adv.btn.isChecked(), form.pages.currentIndex())
    rows = form.fields[GAIN].box
    t = guide.start_eq(page)
    seen = {"box": False, "add": False, "tab": False}

    def look():
        seen["box"] |= _in_sight(page, rows.rows[0].lo) and t.hot_w is rows.rows[0].lo
        seen["add"] |= _in_sight(page, rows.add_btn) and t.hot_w is rows.add_btn
        seen["tab"] |= form.tab_btns[form.pages.currentIndex()].text() == "Website best settings"
        return not t.demo_running
    try:
        t.all_chk.setChecked(False)
        t.go_to_step(next(n for n, s in enumerate(t.steps) if s["title"] == "Settings"))
        t.speed = 2.0
        t.replay()
        sweep.wait_for(lambda: t.demo_running, 5)
        sweep.wait_for(look, 60)
        t.go_to_step(t.i - 1)  # (the step left)
        qt.pump(100)
        back = (st.adv.btn.isChecked(), form.pages.currentIndex())
    finally:
        t.end()
    check("guide: with the method Website AutoEQ: find the best settings, the step “Settings” points at Gain ranges' "
          "first box and at Add a range, both in sight on the Website best settings tab, then the fold and the tab are "
          "back as they were", all(seen.values()) and back == kept, (seen, back, kept))
