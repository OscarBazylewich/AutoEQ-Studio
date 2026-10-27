"""The parts every window shares (ui\\window_parts.py; .claude\\notes\\UI-RULES.md, 2026-10-27, the user's ask: the
same kind of thing done the same way everywhere): the message line (what was just done, Undo beside it when it can be
undone, which puts it back; the line never grows or shrinks as Undo comes and goes, so nothing above it moves; longer
words kept longer), a window's footer (its extras at the left, its message line, its main action, Close at the right,
plain), and what Enter does (the window's accent button or nothing, never a button Qt picks by itself; in a box being
typed in, only the box's own)."""
from helpers import qt

COVERS = ("ui.window_parts",)


def test_message_line_with_undo(qapp, check):
    from ui.window_parts import READ_MS, SAID_MS, UNDO_MS, MessageLine
    line = MessageLine()
    line.resize(520, 40)
    line.show()
    qt.pump(50)
    tall = line.sizeHint().height()
    put_back = []
    line.say("Removed “KZ” from your EQs to compare.", undo=lambda: put_back.append(True))
    qt.pump(50)
    offered = (line.undo_btn.isVisible(), line._timer.interval() == UNDO_MS, line.sizeHint().height() == tall)
    line.undo_btn.click()
    pressed = (put_back, line.text.text(), line.undo_btn.isVisible())
    line.say("Saved.")
    plain = (line.undo_btn.isVisible(), line._timer.interval() == SAID_MS)
    line.say("x" * 200)
    longer = line._timer.interval() == READ_MS * 200
    qt.close(line)
    check("window parts: the message line shows Undo beside what was just done when it can be undone (kept 20 s), "
          "and Undo puts it back and clears the line; none otherwise (6 s, longer for longer words); the line keeps "
          "Undo's room, so it never grows and nothing above it moves",
          offered == (True, True, True) and pressed == ([True], "", False) and plain == (False, True) and longer,
          (offered, pressed, plain, longer))


def test_a_time_asked_for_never_shortens_a_message(qapp, check):
    # (2026-10-27, the rules' review: a time passed in skipped the line's own, so messages went in 4 or 5 s, and a long
    # one's 10 s was less than its words need)
    from ui.window_parts import READ_MS, SAID_MS, UNDO_MS, MessageLine
    line = MessageLine()
    line.say("Saved.", 4000)
    short = line._timer.interval()
    line.say("x" * 200, 10000)
    long_words = line._timer.interval()
    line.say("Kept.", 30000)
    longer = line._timer.interval()
    line.say("Removed it.", 5000, undo=lambda: None)
    undo = line._timer.interval()
    line.say("Until the next one.", 0)
    kept = line._timer.isActive()
    qt.close(line)
    check("window parts: a time asked for only makes a message stay longer: never under 6 s (20 s with Undo) or what "
          "its words need; 0 keeps it until the next one",
          (short, long_words, longer, undo, kept) == (SAID_MS, READ_MS * 200, 30000, UNDO_MS, False),
          (short, long_words, longer, undo, kept))


def test_footer_order(qapp, check):
    from PySide6.QtWidgets import QDialog, QPushButton, QVBoxLayout
    from ui.window_parts import Footer
    dlg = QDialog()
    v = QVBoxLayout(dlg)
    v.addStretch(1)
    extra, main = QPushButton("Clear the history…"), QPushButton("Start")
    footer = Footer(dlg, [extra], main=[main])
    v.addWidget(footer)
    dlg.resize(700, 200)
    dlg.show()
    qt.pump(50)
    xs = [w.geometry().x() for w in (extra, footer.line, main, footer.close_btn)]
    right = footer.close_btn.geometry().right() >= footer.width() - 2
    plain = footer.close_btn.property("primary") not in (True, "true") and footer.close_btn.icon().isNull()
    footer.close_btn.click()
    qt.pump(20)
    closed = not dlg.isVisible()
    qt.close(dlg)
    check("window parts: a window's footer: its extras at the left, then its message line, its main action, and "
          "Close at the right end (plain: no accent, no symbol), which closes it",
          xs == sorted(xs) and right and plain and closed, (xs, right, plain, closed))


def test_enter_on_a_focused_button_presses_it(qapp, check):
    # (2026-10-27, the code's review: the footers' buttons don't take Enter by themselves, so Enter on a focused Close
    # pressed Run several's Start, on History's Undo its Show, and on Set up's Cancel Set up itself; and the keypad's
    # Enter slipped past, pressing a button Qt chose)
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QDialog, QLineEdit, QPushButton, QVBoxLayout, QWidget
    from ui.window_parts import Footer, dialog_band, enter_presses
    pressed = []
    dlg = QDialog()
    v = QVBoxLayout(dlg)
    box, show, start = QLineEdit(), QPushButton("Show A"), QPushButton("Start")
    show.clicked.connect(lambda: pressed.append("Show A"))
    start.clicked.connect(lambda: pressed.append("Start"))
    footer = Footer(dlg, main=[start])
    footer.close_btn.clicked.disconnect()
    footer.close_btn.clicked.connect(lambda: pressed.append("Close"))
    for w in (box, show, footer):
        v.addWidget(w)
    enter_presses(dlg, start)
    dlg.show()
    qt.pump(20)
    footer.close_btn.setFocus()
    QTest.keyClick(footer.close_btn, Qt.Key_Return)
    on_close = list(pressed)
    pressed.clear()
    show.setFocus()  # (a button Qt may then keep as its default)
    box.setFocus()
    QTest.keyClick(box, Qt.Key_Enter, Qt.KeypadModifier)
    keypad = list(pressed)
    qt.close(dlg)
    band_dlg = QDialog()
    v = QVBoxLayout(band_dlg)
    v.addWidget(QWidget())
    band, main = dialog_band(band_dlg, "Set up", lambda: pressed.append("Set up"))
    v.addWidget(band)
    band_dlg.show()
    qt.pump(20)
    cancel = next(b for b in band.findChildren(QPushButton) if b.text() == "Cancel")
    cancel.setFocus()
    pressed.clear()
    QTest.keyClick(cancel, Qt.Key_Return)
    band_cancel = (list(pressed), band_dlg.result(), band_dlg.isVisible())
    qt.close(band_dlg)
    check("window parts: Enter on a focused button presses that button (a footer's Close, a dialog's Cancel), not the "
          "window's main one; the keypad's Enter in a box being typed in is the box's too (never a button Qt chose)",
          on_close == ["Close"] and keypad == [] and band_cancel == ([], QDialog.Rejected, False),
          (on_close, keypad, band_cancel))


def test_enter_presses_the_accent_or_nothing(qapp, check):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QDialog, QLineEdit, QListWidget, QPushButton, QVBoxLayout
    from ui.window_parts import enter_presses
    pressed = []

    def window(with_main):
        dlg = QDialog()
        v = QVBoxLayout(dlg)
        box, lst, first, main = QLineEdit(), QListWidget(), QPushButton("Show A"), QPushButton("Start")
        for w in (box, lst, first, main):
            v.addWidget(w)
        first.clicked.connect(lambda: pressed.append("Show A"))
        main.clicked.connect(lambda: pressed.append("Start"))
        enter_presses(dlg, main if with_main else None)
        dlg.show()
        qt.pump(20)
        return dlg, box, lst

    seen = {}
    for with_main in (True, False):
        dlg, box, lst = window(with_main)
        for name, w in (("list", lst), ("box", box)):
            w.setFocus()
            QTest.keyClick(w, Qt.Key_Return)
            seen[(with_main, name)] = list(pressed)
            pressed.clear()
        qt.close(dlg)
    check("window parts: Enter presses the window's accent button (Start), or nothing when it has none, never the "
          "first button Qt finds by itself (Show A); in a box being typed in, Enter is the box's own",
          seen == {(True, "list"): ["Start"], (True, "box"): [], (False, "list"): [], (False, "box"): []}, seen)
