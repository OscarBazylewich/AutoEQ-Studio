"""Small helpers the window's screens share (ui\\window.py and its parts: ui\\devices_screen.py,
ui\\profiles_screen.py, ui\\settings_screen.py, ui\\setup_dialog.py): a line of words in the muted colour, a profile's
EQ in a few words, a warning card as Windows 11 draws one (its sign, its words, its action), and Windows 11's symbol
in front of words. And the parts every window of the app uses, so each kind of thing is done one way everywhere
(.claude\\notes\\UI-RULES.md): fit_to_screen (its size kept within the screen's room), MessageLine (what was just done,
with Undo), Footer (a window's last row: its extras, its message line, Close), dialog_band (a dialog's decision:
Windows 11's band of buttons) and enter_presses (what Enter does in a window)."""
from PySide6.QtCore import QEvent, QObject, Qt, QTimer
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QWidget

from ui import theme

SAID_MS, UNDO_MS = 6000, 20000  # (how long a message line keeps what it says at least; with Undo beside it, longer)
READ_MS = 70  # (and as long as its words take to read: about this long a letter; 30 words, about 12 s)


def fit_to_screen(window, size, smallest=None):
    """A window kept within the screen's free room: the size it opens at and its smallest size no bigger than the room
    above the taskbar, less its title bar. A 1920 x 1080 laptop at 150 % has about 1280 x 672 px of it (569 high at
    175 %): opened taller, a window's bottom row (Close…) was under the taskbar, out of reach. size: (width, height) it
    opens at; smallest: (width, height), either one None to leave it to the window's own parts (smallest None: both).
    The screen: the one its owner (the main window) is on, where it opens; a window without one, the screen it opens
    on. Returns how many pixels lower than `smallest`'s height its smallest height had to be (0 on a screen with room,
    or without a smallest height): what its lists and chart give up, or scroll."""
    owner = window.parentWidget().window() if window.parentWidget() is not None else window
    free = owner.screen().availableGeometry()
    (w, h), (min_w, min_h) = size, smallest or (None, None)
    low = min_h
    if free.height() > 0:
        h = min(h, free.height() - 40)            # (its title bar above it: about 31 px at 150 %)
        if min_h is not None:
            low = min(min_h, free.height() - 80)  # (and some room to spare)
    if free.width() > 0:
        w = min(w, free.width() - 20)
        if min_w is not None:
            min_w = min(min_w, free.width() - 40)
    if min_w is not None:
        window.setMinimumWidth(min_w)
    if low is not None:
        window.setMinimumHeight(low)
    window.resize(w, h if low is None else max(h, low))
    return 0 if min_h is None else min_h - low


class MessageLine(QWidget):
    """A window's message line (UI-RULES 24): what was just done, for SAID_MS, or with Undo beside it for UNDO_MS
    (clicked: the act put back, the line cleared). The main window's is at its bottom; another window's is in its
    Footer. A long message never widens the window: it's cut at the edge, its tooltip whole."""

    def __init__(self, role="muted"):
        super().__init__()
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        self.text = QLabel()
        self.text.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        if role:
            theme.mark(self.text, role=role)
        row.addWidget(self.text, 1)
        from ui import icons
        self.undo_btn = QPushButton("Undo")
        icons.put(self.undo_btn, "undo")
        self.undo_btn.setAutoDefault(False)
        self.undo_btn.clicked.connect(self._undo)
        keep = self.undo_btn.sizePolicy()  # (its room kept while it's hidden: the line, and the window's bottom bar,
        keep.setRetainSizeWhenHidden(True)  # never grows when Undo comes and goes, so nothing above it moves)
        self.undo_btn.setSizePolicy(keep)
        self.undo_btn.hide()
        row.addWidget(self.undo_btn)
        self._undo_fn = None
        self._timer = QTimer(self, singleShot=True, timeout=lambda: self.say("", 0))

    def say(self, text, ms=None, undo=None):
        """text for ms milliseconds (None: SAID_MS, or UNDO_MS with undo, or longer for longer words; 0: until the next
        message); undo: what Undo does (none: no Undo)."""
        self.text.setText(text)
        self.text.setToolTip(text)
        self._undo_fn = undo if text else None
        self.undo_btn.setVisible(self._undo_fn is not None)
        ms = max(UNDO_MS if undo else SAID_MS, READ_MS * len(text)) if ms is None else ms
        if ms and text:
            self._timer.start(ms)
        else:
            self._timer.stop()

    def _undo(self):
        fn = self._undo_fn
        self.say("", 0)
        if fn is not None:
            fn()


class Footer(QWidget):
    """A window's last row (UI-RULES 1): its extra actions at the left, then its message line (self.line: say()), then
    its main action when it has one (main: Run several's Start, as a Windows dialog's OK), then Close at the right: no
    accent, no symbol; Esc does the same (a dialog's own). close=False: no Close."""

    def __init__(self, window, extras=(), close=True, main=()):
        super().__init__()
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        for b in extras:
            row.addWidget(b)
        if extras:
            row.addSpacing(8)
        self.line = MessageLine()
        row.addWidget(self.line, 1)
        for b in main:  # (a window's main action, as a Windows dialog's: right before Close, in the accent)
            row.addWidget(b)
        self.close_btn = None
        if close:
            self.close_btn = QPushButton("Close")
            self.close_btn.setAutoDefault(False)
            self.close_btn.clicked.connect(window.reject if hasattr(window, "reject") else window.close)
            row.addWidget(self.close_btn)

    def say(self, text, ms=None, undo=None):
        self.line.say(text, ms, undo)


def dialog_band(dialog, main_text, on_main, cancel_text="Cancel"):
    """A dialog's decision as Windows 11's dialogs show it (UI-RULES 2): the buttons on a band in the window's colour
    across its bottom, sharing the width; the main one first, named by its verb, in the accent and Enter's; Cancel
    last, Esc's too. The dialog's own layout has no margins: its words go in a part with them, the band under it.
    Returns (band, the main button)."""
    band = QFrame()
    band.setObjectName("dialogFooter")
    fl = QHBoxLayout(band)
    fl.setContentsMargins(24, 16, 24, 16)
    fl.setSpacing(8)
    main = QPushButton(main_text)
    theme.mark(main, primary=True)
    main.setDefault(True)
    main.clicked.connect(on_main)
    cancel = QPushButton(cancel_text)
    cancel.setAutoDefault(False)
    cancel.clicked.connect(dialog.reject)
    fl.addWidget(main, 1)
    fl.addWidget(cancel, 1)
    return band, main


class _EnterOnly(QObject):
    """enter_presses' watch on a window: an Enter no control used presses its button, or nothing."""

    def __init__(self, window, button):
        super().__init__(window)
        self.button = button

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.KeyPress and ev.key() in (Qt.Key_Return, Qt.Key_Enter) and not ev.modifiers():
            from PySide6.QtWidgets import QAbstractSpinBox, QKeySequenceEdit, QLineEdit, QPlainTextEdit
            # (the window's own focus, not the app's: the same whether or not it's the active window)
            typing = isinstance(obj.focusWidget(), (QLineEdit, QPlainTextEdit, QKeySequenceEdit, QAbstractSpinBox))
            b = self.button
            # (in a box being typed in, Enter is the box's own: a search searches; it pressed History's Show from its
            # search box, closing the window)
            if not typing and b is not None and b.isVisible() and b.isEnabled():
                b.click()
            return True
        return False


def enter_presses(window, button=None):
    """What Enter does in a window (UI-RULES 4): presses `button` (its accent one), or nothing; never the first
    button Qt finds by itself (Compare's Enter pressed "Show A"). A focused button still takes Enter itself, and in a
    box being typed in Enter is only the box's (a search box searches: its returnPressed). Returns the watch: its
    .button can change (a list's chosen row)."""
    watch = _EnterOnly(window, button)
    window.installEventFilter(watch)
    return watch


def muted(text=""):
    """A line of words in the theme's muted colour, wrapping."""
    lab = QLabel(text)
    lab.setWordWrap(True)
    theme.mark(lab, role="muted")
    return lab


def profile_line(p):
    """A profile's EQ in a few words ("5 filters, pre-amp -3.2 dB", or "GraphicEQ, …"); empty for no profile."""
    if not p:
        return ""
    n = p.get("filters", 0)
    what = "GraphicEQ" if p.get("graphic") and not n else f"{n} filter{'' if n == 1 else 's'}"
    return f"{what}, pre-amp {p.get('preamp', 0):g} dB"


def glyph(name, role=None, said=""):
    """Windows 11's symbol `name` (ui\\icons.py's GLYPHS: "warning", "clock" …) as a label in front of words, in the
    colour of its role ("warn" …) or of a rule for its objectName: the stylesheet colours it, so it follows light,
    dark and the accent by itself. said: what a screen reader reads for it ("Warning")."""
    from PySide6.QtGui import QFontDatabase
    from ui import icons
    lab = QLabel(chr(int(icons.GLYPHS[name], 16)))
    font = lab.font()
    font.setFamily("Segoe Fluent Icons" if "Segoe Fluent Icons" in QFontDatabase.families() else "Segoe MDL2 Assets")
    lab.setFont(font)  # (only the family: the size is the stylesheet's, the colour its role's)
    lab.setAlignment(Qt.AlignCenter)
    lab.setAccessibleName(said or name.capitalize())
    theme.mark(lab, glyph=True, **({"role": role} if role else {}))
    return lab


def warning_card(text, button=None):
    """A warning as Windows 11 shows one (an InfoBar): the warning sign, the words (wrapping), and the action's button
    at the right, on the theme's warning colours (card="warn"). Returns (card, its words' label)."""
    card = QFrame()
    theme.mark(card, card="warn")
    row = QHBoxLayout(card)
    row.setContentsMargins(8, 6, 8, 6)
    row.setSpacing(12)
    row.addWidget(glyph("warning", role="warn"))
    words = QLabel(text)
    words.setWordWrap(True)
    row.addWidget(words, 1)
    if button is not None:
        row.addWidget(button, 0, Qt.AlignVCenter)
    return card, words
