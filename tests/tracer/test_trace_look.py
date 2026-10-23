"""The tracer's window in Windows 11's look (ui\\trace_window.py and theme_sheet.py's tracer part: the restyle's
stage 2, 2026-10-23): the picture's card drawn in the theme's colours and following a change, no control with a style
of its own (the traced colour's swatch: only that colour; a drop-down's search list neither), the chosen curve's row
marked as a chosen list row (and the mark moved without rebuilding the rows), its dot and ✕ filled when pointed at,
the Automatic settings card's content at a card's inset, nothing cut or squeezed at the new sizes, Windows 11's symbols
beside the main actions' words, each curve's dot and ✕ named with the curve's name for a screen reader, and the notes
and the zoom bar taking no room while they've nothing to show.

On Make an EQ (the eq_screen fixture), each test with a tracer's window of its own (deleted at its end) and the app's
sample graph, its dB values typed whatever Windows' text reader read (as test_trace_window.py does)."""
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QFocusEvent, QPalette
from PySide6.QtWidgets import (QApplication, QCheckBox, QLabel, QLineEdit, QPushButton, QStyle, QStyleOptionComboBox,
                               QToolButton, QWidget)

from helpers import qt
from ui.search_combo import SEARCH_FROM
from ui.trace_window import TOOLS, TraceWindow, sample_image

COVERS = ("ui.eq_page",)  # (the window is opened for Make an EQ's page)


def _new(eq_screen):
    """A tracer's window of this test's own, at its usual size, as Make an EQ opens it (qt.close deletes it)."""
    tw = TraceWindow(eq_screen.page)
    tw.fill_comp()
    tw.resize(1320, 860)
    tw.show()
    qt.pump(100)
    return tw


def _sample(eq_screen, tw, curves):
    """The sample graph in the window, its dB values typed, Auto trace `curves` times."""
    img, _s = sample_image()
    tw.load_image(img, "Sample IEM")
    eq_screen.wait_for(lambda: not tw.reading, 60)
    tw.t.v.update(d1="90", d2="40")
    for _ in range(curves):
        tw.auto_trace()
    qt.pump(100)


def _near(colour, want, by=6):
    """A QColor within `by` of the colour `want` (#rrggbb) in each of red, green and blue."""
    w = [int(want[i:i + 2], 16) for i in (1, 3, 5)]
    return all(abs(a - b) <= by for a, b in zip((colour.red(), colour.green(), colour.blue()), w))


def test_picture_card_follows_the_theme(eq_screen, check):
    from ui import theme
    qapp = eq_screen.qapp
    tw = _new(eq_screen)
    seen = {}
    try:
        for dark in (True, False):
            theme.apply(qapp, dark=dark)
            qt.pump(100)
            t = theme.tokens()
            img = tw.stage.grab().toImage()
            h = img.height()
            seen["dark" if dark else "light"] = (img.pixelColor(6, h // 2).name(), t["card"].lower(),
                                                 _near(img.pixelColor(0, h // 2), t["line"]))
    finally:
        qt.light(qapp)  # (the light theme back, whatever happened: every later test runs light)
        qt.pump(50)
    # (a drop-down's long list, with its search box, opened once so it's looked at too: "The graph shows" given more
    # choices than open without it. It had a style of its own until 2026-10-23, and this check let it off)
    for k in range(SEARCH_FROM + 1):
        tw.comp.addItem(f"relative to target {k}", f"target {k}.csv")
    tw.comp.showPopup()
    qt.pump(50)
    tw.comp.hidePopup()
    own = sorted(w.objectName() or type(w).__name__ for w in tw.findChildren(QWidget) if w.styleSheet())
    qt.close(tw)
    check("tracer: the picture's card is drawn in the theme's card colour and border, dark and light (it follows a "
          "change), and no control of the window has a style of its own",
          all(px == card and line for px, card, line in seen.values()) and seen["dark"][0] != seen["light"][0]
          and not own, (seen, own))


def test_chosen_curve_row(eq_screen, check):
    from ui import theme
    tw = _new(eq_screen)
    _sample(eq_screen, tw, 2)
    tw.select_curve(0)
    qt.pump(50)
    first = [r.property("trRow") for r in tw.curve_rows]
    rows = list(tw.curve_rows)
    QApplication.sendEvent(rows[1].findChild(QLineEdit), QFocusEvent(QEvent.FocusIn, Qt.MouseFocusReason))
    qt.pump(50)
    moved = ([r.property("trRow") for r in tw.curve_rows], tw.curve_rows == rows)
    img = rows[1].grab().toImage()
    fill, want = img.pixelColor(img.width() // 2, 1).name(), theme.tokens()["subtle_sel"].lower()
    swatch = tw.swatch.styleSheet()
    # a contrast theme (a stand-in, as tests\\ui\\test_theme.py's): the chosen row in Windows' highlight colour, its
    # words in the highlight's text colour (not the theme's white text on it)
    qapp = eq_screen.qapp
    try:
        theme.apply(qapp, dark=False, contrast=dict(theme.LIGHT, bg="#000000", card="#000000", ink="#ffffff",
                                                    muted="#ffffff", field="#000000", subtle_sel="#1aebff",
                                                    sel_ink="#000000"))
        qt.pump(50)
        words = rows[1].findChild(QLabel)
        img = rows[1].grab().toImage()
        contrast = (img.pixelColor(img.width() // 2, 1).name(), words.palette().color(QPalette.WindowText).name())
    finally:
        qt.light(qapp)  # (the light theme back, whatever happened: every later test runs light)
        qt.pump(50)
    qt.close(tw)
    check("tracer: the chosen curve's row is marked as a chosen list row (a quiet fill, the accent's bar; in a contrast "
          "theme Windows' highlight, its words in the highlight's text colour), and typing in another curve's name "
          "moves the mark there without rebuilding the rows; the traced colour's swatch sets only that colour (its "
          "frame follows the theme)",
          first == ["chosen", ""] and moved == (["", "chosen"], True) and fill == want
          and contrast == ("#1aebff", "#000000") and swatch.startswith("background: rgb(") and "border" not in swatch,
          (first, moved, fill, want, contrast, swatch))


def test_chosen_rows_buttons_pointed_at(eq_screen, check):
    # (2026-10-23: pointed at, the chosen curve's dot and ✕ showed almost no fill: the quiet buttons' own fill on the
    # chosen row's, #eaeaea on #ececec in light, #383838 on #3a3a3a in dark. Now as Find…'s row's ✕: Windows 11 lays
    # a quiet button's fill, the text's colour at 6 % (4 % pressed), over the row's)
    from PySide6.QtCore import QPoint, QPointF
    from PySide6.QtGui import QMouseEvent
    from ui import theme
    qapp = eq_screen.qapp
    tw = _new(eq_screen)
    _sample(eq_screen, tw, 2)
    tw.select_curve(0)
    qt.pump(50)

    def laid_over(under, ink, alpha):
        return [round(u * (1 - alpha / 255) + int(ink[k:k + 2], 16) * alpha / 255) for u, k in zip(under, (1, 3, 5))]
    seen = {}
    try:
        for dark in (True, False):
            theme.apply(qapp, dark=dark)
            qt.pump(100)
            row, ink = tw.curve_rows[0], theme.tokens()["sel_ink"]
            for name, b in zip(("dot", "✕"), row.findChildren(QPushButton)):
                b.setAttribute(Qt.WA_UnderMouse, True)  # (the mouse on it, as Qt tells a button)
                mid = QPointF(b.rect().center())
                QApplication.sendEvent(b, QMouseEvent(QEvent.MouseMove, mid, QPointF(b.mapToGlobal(mid)), Qt.NoButton,
                                                      Qt.NoButton, Qt.NoModifier))
                for state, alpha in (("pointed at", 15), ("pressed", 10)):
                    b.setDown(state == "pressed")
                    b.update()
                    qt.pump(50)
                    img = row.grab().toImage()
                    under = img.pixelColor(img.width() // 2, 1)  # (the row's own fill, above its name's box)
                    fill = img.pixelColor(b.mapTo(row, QPoint(3, b.height() // 2)))  # (inside it, beside its symbol)
                    want = laid_over((under.red(), under.green(), under.blue()), ink, alpha)
                    seen[f"{'dark' if dark else 'light'}, {name} {state}"] = (
                        fill.name(), under.name(), all(abs(a - w) <= 2 for a, w in zip(fill.getRgb()[:3], want)))
                b.setDown(False)
                b.setAttribute(Qt.WA_UnderMouse, False)
                b.update()
    finally:
        qt.light(qapp)  # (the light theme back, whatever happened: every later test runs light)
        qt.pump(50)
    qt.close(tw)
    check("tracer: the chosen curve's dot and ✕, pointed at or pressed, show a fill of their own over the chosen row's "
          "(its text colour at 6 %, 4 % pressed, as Find…'s row's ✕ and Windows 11's quiet buttons), dark and light",
          len(seen) == 8 and all(fill != under and ok for fill, under, ok in seen.values()), seen)


def test_cards_content_at_one_inset(eq_screen, check):
    # (2026-10-23: the Automatic settings card, a card frame, kept Qt's own 9 px layout margin on top of the card's
    # padding: its heading, its fold and its words started 5 px further in than the numbered cards' under it)
    from PySide6.QtCore import QPoint
    from ui import theme_sheet
    tw = _new(eq_screen)
    auto, axes = tw.auto_on.parentWidget(), tw.boxes["d1"].parentWidget()

    def sides(w, card):  # (how far in from the card's left edge, and from its right edge)
        at = w.mapTo(card, QPoint(0, 0)).x()
        return at, card.width() - at - w.width()
    got = {"Automatic settings": sides(tw.auto_on, auto)[0], "Why these settings": sides(tw.why, auto)[0],
           "the card's right": sides(tw.auto_state, auto)[1], "1 Axes": sides(tw.boxes["d1"], axes)[0],
           "1 Axes' right": sides(tw.boxes["d2"], axes)[1]}
    qt.close(tw)
    inset = theme_sheet.CARD + 1  # (inside its 1 px border)
    check("tracer: the Automatic settings card's content starts and ends at a card's inset, as the numbered cards' "
          "under it", set(got.values()) == {inset}, (got, inset))


def test_nothing_cut_at_the_new_sizes(eq_screen, check):
    tw = _new(eq_screen)
    _sample(eq_screen, tw, 3)

    def cut():
        """Buttons, tick boxes and one-line labels narrower than their words; the settings' side wider than its
        room (it would be cut at the right: it can't scroll sideways)."""
        out = [(type(w).__name__, w.text() or w.toolTip()[:24], w.width(), w.sizeHint().width())
               for w in tw.findChildren(QWidget) if w.isVisible()
               and (isinstance(w, (QPushButton, QToolButton, QCheckBox)) or isinstance(w, QLabel) and not w.wordWrap()
                    and w.text()) and w.width() < w.sizeHint().width()]
        side, room = tw.side_scroll.widget(), tw.side_scroll.viewport().width()
        if max(side.width(), side.minimumSizeHint().width()) > room:
            out.append(("the side", side.width(), side.minimumSizeHint().width(), room))
        return out
    at_default = cut()
    combo = tw.comp
    combo.setCurrentIndex(0)
    opt = QStyleOptionComboBox()
    combo.initStyleOption(opt)
    field = combo.style().subControlRect(QStyle.CC_ComboBox, opt, QStyle.SC_ComboBoxEditField, combo).width()
    words = (combo.itemText(0), combo.fontMetrics().horizontalAdvance(combo.itemText(0)))
    slider = tw.tol.width()
    tw.resize(tw.minimumSizeHint())
    qt.pump(100)
    at_least = cut()
    qt.close(tw)
    check("tracer: nothing is cut or squeezed at Windows 11's sizes (10.5 pt text, symbols beside the words): every "
          "button, tick box and label as wide as its words, the settings' side within its room, “the actual response "
          "(not compensated)” whole in its drop-down, the colour tolerance slider at least 150 px; at the usual size "
          "and the window's smallest",
          not at_default and not at_least and words[0].startswith("the actual response") and field >= words[1]
          and slider >= 150, (at_default, at_least, field, words, slider))


def test_symbols_beside_the_words(eq_screen, check):
    tw = _new(eq_screen)
    _sample(eq_screen, tw, 0)  # (a picture: the zoom bar shows)
    words = {"Open image…": tw.open_btn, "Remove image": tw.remove_btn, "Guide": tw.guide_btn,
             "Choose an image file…": tw.stage.choose_btn, "Another curve": tw.add_btn, "Auto trace": tw.auto_btn,
             "Undo": tw.edit_btns["undo"], "Redo": tw.edit_btns["redo"], "Add as measurement": tw.save_meas,
             "Save .txt…": tw.download_btn, "Fit": tw.stage.zoom_btns["fit"],
             **{text: tw.tool_btns[key] for key, text, _tip in TOOLS}}
    wrong = [w for w, b in words.items() if b.text() != w or b.icon().isNull()]
    alone = {k: (b.text(), b.icon().isNull(), b.accessibleName()) for k, b in tw.stage.zoom_btns.items() if k != "fit"}
    qt.close(tw)
    check("tracer: Windows 11's symbols beside the main actions' and the tools' words (the words kept; Guide and "
          "Another curve without their old “? ” and “+ ”), zoom in and out as symbols alone, named for a screen reader",
          not wrong and alone == {"out": ("", False, "Zoom out (-)"), "in": ("", False, "Zoom in (+)")},
          (wrong, alone))


def test_curve_rows_named_for_a_screen_reader(eq_screen, check):
    # (2026-10-23: every curve's dot was read as “Trace into this curve” and every ✕ as “Delete this curve”, so a
    # screen reader couldn't tell the curves apart; the row's buttons now the shared quiet ones, as the zoom bar's)
    tw = _new(eq_screen)
    _sample(eq_screen, tw, 2)
    names = [[b.accessibleName() for b in r.findChildren(QPushButton)] for r in tw.curve_rows]
    box = tw.curve_rows[1].findChild(QLineEdit)
    box.setText("Right")
    box.textEdited.emit("Right")  # (as typing it does)
    renamed = [b.accessibleName() for b in tw.curve_rows[1].findChildren(QPushButton)]
    quiet = sorted({b.property("quiet") for r in tw.curve_rows for b in r.findChildren(QPushButton)}
                   | {b.property("quiet") for b in tw.stage.zoom_btns.values()})
    qt.close(tw)
    check("tracer: each curve's dot and ✕ are named with the curve's name for a screen reader (“Select curve L”, "
          "“Delete curve L”), again when it's renamed; they and the zoom bar's buttons are the shared quiet buttons",
          names == [["Select curve L", "Delete curve L"], ["Select curve R", "Delete curve R"]]
          and renamed == ["Select curve Right", "Delete curve Right"] and quiet == ["true"], (names, renamed, quiet))


def test_notes_and_zoom_bar_take_no_room_when_empty(eq_screen, check):
    tw = _new(eq_screen)
    fresh = (tw.axis_note.isVisible(), tw.save_note.isVisible(), tw.stage.zoom_box.isVisible())
    _sample(eq_screen, tw, 0)
    loaded = (tw.axis_note.isVisible() and bool(tw.axis_note.text()), tw.stage.zoom_box.isVisible(),
              tw.save_note.isVisible() == bool(tw.save_note.text()))
    tw.remove_image()  # (nothing traced: removed without asking)
    qt.pump(50)
    removed = (tw.axis_note.isVisible(), tw.save_note.isVisible(), tw.stage.zoom_box.isVisible())
    qt.close(tw)
    check("tracer: a note with nothing to say takes no room (no empty row at a card's foot), and the zoom bar shows "
          "only with a picture (on a new window too)",
          fresh == (False, False, False) and loaded == (True, True, True) and removed == (False, False, False),
          (fresh, loaded, removed))
