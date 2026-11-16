"""Make an EQ's Settings: the "your value ↺" tag of a setting, pressed with the keyboard (ui\\forms.py's Field.set_tag;
2026-11-15, found by the verifier of the Calculate fault). The tag goes off when it says "automatic", and Qt gave the
focus of a control that goes off to the next control in the page's order: the next setting, and the page scrolled to
it (670 px to 791 px, measured). Now the value's box beside the tag gets the focus first, after it shows the automatic
value (a box with the focus keeps what it shows), and the page stays where it is. One page for the file (the eq_screen
fixture)."""
from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from helpers import qt


def _tab_to(w):
    """The focus on w with the Tab key, from the control before it in the page's order."""
    before = w.previousInFocusChain()
    while not (before.focusPolicy() & Qt.TabFocus and before.isVisible() and before.isEnabled()):
        before = before.previousInFocusChain()
    before.setFocus(Qt.OtherFocusReason)
    QTest.keyClick(before, Qt.Key_Tab)
    qt.pump(30)


def test_your_value_tag_with_the_keyboard_keeps_the_page(eq_screen, check):
    from ui.forms import Fold, number_text
    page = eq_screen.page
    st = page.settings
    fold = st.auto_on.parentWidget()
    while fold is not None and not isinstance(fold, Fold):
        fold = fold.parentWidget()
    fold.btn.setChecked(True)  # (Settings open)
    page.S["auto"]["enabled"] = True
    page.refresh_auto()
    # (a number box whose automatic value is not the value set here: the box must show the change)
    path = next(p for p in st.auto_paths if p in st.form.fields and st.form.fields[p].kind == "num"
                and type(st.form.get(p)) in (int, float))
    auto_value = st.form.get(path)
    page.S["auto"]["manual"] = [path]
    from eq import settings as eq_settings
    eq_settings.set_path(page.S, path, auto_value + 1)
    st.refresh()
    page.activateWindow()
    qt.pump(300)
    field = st.form.fields[path]
    tag = field.tag
    _tab_to(tag)
    area = page.page_area
    bar, vp = area.verticalScrollBar(), area.viewport()
    # (the tag at the bottom of the view: the next setting is under it, out of sight)
    bar.setValue(tag.mapTo(area.widget(), QPoint(0, 0)).y() + tag.height() - vp.height() + 2)
    qt.pump(100)
    at, had, said, shown = bar.value(), QApplication.focusWidget() is tag, tag.text(), field.box.text()
    try:
        QTest.keyClick(tag, Qt.Key_Space)
        qt.pump(400)
        f = QApplication.focusWidget()
        seen = f is not None and vp.rect().contains(QRect(f.mapTo(vp, QPoint(0, 0)), f.size()))
        check("settings: Space on a setting's “your value ↺” tag makes the value automatic, the page stays where it "
              "is, and the focus goes to the value's box beside the tag, in sight (the page scrolled to the next "
              "setting, 121 px)",
              had and said == "your value ↺" and tag.text() == "automatic" and bar.value() == at
              and f is field.box and seen,
              (path, had, said, tag.text(), at, bar.value(), type(f).__name__ if f else None, f is field.box, seen))
        check("settings: the box of a value made automatic with the keyboard shows the automatic value (a box with "
              "the focus keeps what it shows)",
              shown == number_text(auto_value + 1) and st.form.get(path) == auto_value
              and field.box.text() == number_text(auto_value),
              (path, shown, auto_value, st.form.get(path), field.box.text()))
        QTest.keyClick(field.box, Qt.Key_X)  # (not a number: nothing is set, the box keeps it)
        qt.pump(50)
        typed = field.box.text()
        st.refresh()
        qt.pump(50)
        check("settings: what you type in that box stays in it when the settings show again (a box with the focus "
              "keeps what you type)",
              typed == number_text(auto_value) + "x" and field.box.text() == typed and field.box.hasFocus(),
              (typed, field.box.text(), field.box.hasFocus()))
    finally:
        page.S["auto"]["enabled"] = False
        page.S["auto"]["manual"] = []
        st.refresh()
        qt.pump(100)


def test_the_box_shows_new_values_only_until_the_focus_goes(eq_screen, check):
    # (2026-11-15, round 3: the box that gets the focus of the tag shows each new value until you type in it or the
    # focus goes. The verifier's mutation D10 kept that mark after the focus went: when you clicked in the box again,
    # a new value replaced what the box showed under your cursor. No test found it)
    from eq import settings as eq_settings
    from ui.forms import Fold, number_text
    page = eq_screen.page
    st = page.settings
    fold = st.auto_on.parentWidget()
    while fold is not None and not isinstance(fold, Fold):
        fold = fold.parentWidget()
    fold.btn.setChecked(True)  # (Settings open)
    page.S["auto"]["enabled"] = True
    page.refresh_auto()
    path = next(p for p in st.auto_paths if p in st.form.fields and st.form.fields[p].kind == "num"
                and type(st.form.get(p)) in (int, float))
    auto_value = st.form.get(path)
    page.S["auto"]["manual"] = [path]
    eq_settings.set_path(page.S, path, auto_value + 1)
    st.refresh()
    page.activateWindow()
    qt.pump(300)
    field = st.form.fields[path]
    try:
        _tab_to(field.tag)
        QTest.keyClick(field.tag, Qt.Key_Space)  # (the value automatic, the focus in its box)
        qt.pump(200)
        had = field.box.hasFocus()
        QTest.keyClick(field.box, Qt.Key_Tab)  # (the focus to the next control, nothing typed)
        qt.pump(50)
        st.refresh()
        qt.pump(50)
        left = not field.box.hasFocus()
        field.box.setFocus(Qt.MouseFocusReason)  # (a click in the box again)
        qt.pump(50)
        shown = field.box.text()
        eq_settings.set_path(page.S, path, auto_value + 5)  # (a new value, as a new automatic value comes)
        st.refresh()
        qt.pump(50)
        seen = (had, left, shown, field.box.text(), field.box.hasFocus())
    finally:
        page.S["auto"]["enabled"] = False
        page.S["auto"]["manual"] = []
        st.refresh()
        qt.pump(100)
    check("settings: after the focus left the box of a value made automatic with the keyboard, a click in the box "
          "again keeps what the box shows when a new value comes (the new value replaced it under the cursor)",
          seen == (True, True, number_text(auto_value), number_text(auto_value), True), seen)
