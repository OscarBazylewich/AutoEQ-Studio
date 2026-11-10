"""Small helpers the window's screens share (ui\\window.py and its parts: ui\\devices_screen.py,
ui\\profiles_screen.py, ui\\settings_screen.py, ui\\setup_dialog.py): a line of words in the muted colour, a profile's
EQ in a few words, a warning card as Windows 11 draws one (its sign, its words, its action), and Windows 11's symbol
in front of words. And the parts every window of the app uses, so each kind of thing is done one way everywhere
(.claude\\notes\\UI-RULES.md): fit_to_screen (its size kept within the screen's room), MessageLine (what was just done,
with Undo), Footer (a window's last row: its extras, its message line, Close), dialog_band (a dialog's decision:
Windows 11's band of buttons), enter_presses (what Enter does in a window) and ScreenArea (a part that scrolls up and
down only, never narrower than its content: Settings, a device's card)."""
from PySide6.QtCore import QEvent, QObject, QSize, Qt, QTimer
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QSizePolicy, QWidget

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
        """text for SAID_MS, or UNDO_MS with undo, or longer for longer words; ms: longer still (a time asked for never
        makes it shorter: some said 4 or 5 s, and a long message's 10 s was less than its words need); 0: until the
        next message. undo: what Undo does (none: no Undo)."""
        self.text.setText(text)
        self.text.setToolTip(text)
        self._undo_fn = undo if text else None
        self.undo_btn.setVisible(self._undo_fn is not None)
        if ms != 0:
            ms = max(ms or 0, UNDO_MS if undo else SAID_MS, READ_MS * len(text))
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
    cancel = QPushButton(cancel_text)  # (it takes Enter when it's focused, as in Windows: off, Enter on a focused
    cancel.clicked.connect(dialog.reject)  # Cancel pressed the dialog's main button, Set up)
    fl.addWidget(main, 1)
    fl.addWidget(cancel, 1)
    return band, main


def ask_text(parent, title, label, text="", verb="OK", placeholder="", note=""):
    """A name asked for in Windows 11's dialog, as Paste filters' and Set up's (UI-RULES 2): the words and the box on
    the card's colour, the buttons on a band below, `verb` (Rename, Save) first, in the accent and Enter's, then Cancel.
    Returns (text, True), or (text, False) when it's cancelled. (Rename… and Save as… were Qt's own boxes, OK and
    Cancel at their right: a different look for the same kind of question.) placeholder: the gray words in the empty box
    (an example, or what an empty box gives); note: a gray text under the box (UI-RULES 26)."""
    from PySide6.QtWidgets import QDialog, QLineEdit, QVBoxLayout
    dlg = QDialog(parent)
    dlg.setWindowTitle(title)
    theme.mark(dlg, dialog=True)  # (the card's colour: theme_sheet's window_screens)
    outer = QVBoxLayout(dlg)
    outer.setContentsMargins(0, 0, 0, 0)
    outer.setSpacing(0)
    body = QWidget()
    v = QVBoxLayout(body)
    v.setContentsMargins(24, 24, 24, 20)  # (Windows 11's dialog padding)
    v.setSpacing(8)
    words = QLabel(label)
    words.setWordWrap(True)
    v.addWidget(words)
    box = QLineEdit(text)
    box.setAccessibleName(label)
    box.setPlaceholderText(placeholder)
    box.selectAll()
    v.addWidget(box)
    if note:
        v.addWidget(muted(note))
    outer.addWidget(body, 1)
    band, _main = dialog_band(dlg, verb, dlg.accept)
    outer.addWidget(band)
    dlg.setMinimumWidth(420)
    ok = dlg.exec() == QDialog.Accepted
    out = box.text()
    dlg.deleteLater()  # (asked once: not kept, hidden, under its parent)
    return out, ok


class _EnterOnly(QObject):
    """enter_presses' watch on a window: an Enter no control used presses its button, or nothing."""

    def __init__(self, window, button):
        super().__init__(window)
        self.button = button

    def eventFilter(self, obj, ev):
        # (the keypad's Enter comes with the keypad's modifier: it slipped past, and Qt pressed a button of its choosing)
        if ev.type() == QEvent.KeyPress and ev.key() in (Qt.Key_Return, Qt.Key_Enter) \
                and not ev.modifiers() & ~Qt.KeypadModifier:
            from PySide6.QtWidgets import QAbstractSpinBox, QKeySequenceEdit, QLineEdit, QPlainTextEdit
            pressed = focused_button(obj)
            if pressed is not None:  # (a focused button takes Enter, as in Windows: Cancel, Undo, Close; it pressed
                pressed.click()      # the accent one: Close pressed Run several's Start)
                return True
            # (the window's own focus, not the app's: the same whether or not it's the active window)
            typing = isinstance(obj.focusWidget(), (QLineEdit, QPlainTextEdit, QKeySequenceEdit, QAbstractSpinBox))
            b = self.button
            # (in a box being typed in, Enter is the box's own: a search searches; it pressed History's Show from its
            # search box, closing the window)
            if not typing and b is not None and b.isVisible() and b.isEnabled():
                b.click()
            return True
        return False


def focused_button(window):
    """The window's focused push button when it can be pressed, else None: Enter presses it, as in Windows (a footer's
    buttons don't take Enter by themselves, so that Qt never makes one the window's default: UI-RULES 4)."""
    from PySide6.QtWidgets import QPushButton, QToolButton
    f = window.focusWidget()
    return f if isinstance(f, (QPushButton, QToolButton)) and f.isEnabled() and f.isVisible() else None


def enter_presses(window, button=None):
    """What Enter does in a window (UI-RULES 4): presses `button` (its accent one), or nothing; never the first
    button Qt finds by itself (Compare's Enter pressed "Show A"). A focused button takes Enter itself (focused_button),
    and in a box being typed in Enter is only the box's (a search box searches: its returnPressed). The keypad's Enter
    the same. Returns the watch: its .button can change (a list's chosen row)."""
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


def glyph_label(name, role=None, said=""):
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
    row.addWidget(glyph_label("warning", role="warn"))
    words = QLabel(text)
    words.setWordWrap(True)
    row.addWidget(words, 1)
    if button is not None:
        row.addWidget(button, 0, Qt.AlignVCenter)
    return card, words


class EmptyText(QObject):
    """One gray line in the middle of an empty list or table (the UI audit, 2026-11-08: every empty list the same, and
    it tells the next step: "No filters. Click Add filter."). view: a QAbstractItemView (its model's rows are counted)
    or any widget with count() (rows), then refresh() after each change; text: the words, set_text() to change them.
    The line is drawn on the view's area (a child of it, never a window of its own)."""

    def __init__(self, view, text, count=None):
        super().__init__(view)
        self.view, self._count = view, count
        area = view.viewport() if hasattr(view, "viewport") else view
        self.label = QLabel(text, area)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setWordWrap(True)
        self.label.setAttribute(Qt.WA_TransparentForMouseEvents)
        theme.mark(self.label, role="muted")
        area.installEventFilter(self)
        model = view.model() if hasattr(view, "model") else None
        if model is not None:
            for sig in (model.rowsInserted, model.rowsRemoved, model.modelReset, model.layoutChanged):
                sig.connect(self.refresh)
        self.refresh()

    def set_text(self, text):
        self.label.setText(text)
        self.refresh()

    def rows(self):
        if self._count is not None:
            return self._count()
        model = self.view.model() if hasattr(self.view, "model") else None
        return model.rowCount() if model is not None else 0

    def refresh(self, *_a):
        try:
            area = self.label.parentWidget()
            if area is None:
                return
            self.label.setGeometry(16, 0, max(0, area.width() - 32), min(area.height(), 120) or area.height())
            self.label.setVisible(self.rows() == 0 and bool(self.label.text()))
        except RuntimeError:  # (its list was deleted with its window, and its model said so last)
            pass

    def eventFilter(self, obj, e):
        if e.type() in (QEvent.Resize, QEvent.Show):
            self.refresh()
        return False


def scroll_bar_in_margin(area, layout, side=14):
    """A screen that scrolls keeps its cards' right edge where it is when its scroll bar shows: the 12 px bar goes in
    the screen's right space, and 2 px stay between it and the cards (the UI audit, 2026-11-08: the cards stopped 12
    px farther from the window's edge than on the other screens, and the bars above them). area: the QScrollArea;
    layout: the layout of its content (its right margin follows the bar)."""
    bar = area.verticalScrollBar()

    def follow(*_a):
        m = layout.contentsMargins()
        right = 2 if bar.maximum() > 0 else side  # (the theme's scroll bar is 12 px wide)
        if m.right() != right:
            layout.setContentsMargins(m.left(), m.top(), right, m.bottom())
    bar.rangeChanged.connect(follow)
    follow()


class ScreenArea(QScrollArea):
    """A part that scrolls up and down only (the Settings screen, a device's card): its smallest width is the one its
    content needs, so the window's smallest width, or the line between the device list and the card, never cuts it.
    side: the space at the content's right that its scroll bar goes in (Settings' 14 px:
    scroll_bar_in_margin; 0: the bar beside the content). Without it, the Settings cards were cut 17 px at the window's
    smallest width, and a device's Rename… and ✕ when the line was dragged to the right. Measured again when its
    content changes size, or shows. Hidden (Settings while another screen shows), it keeps the width it had: Qt
    measures a hidden screen's rows again only when it shows (its APO row had all four buttons then, 962 px)."""

    def __init__(self, side=0):
        super().__init__()
        self.side, self._need = side, 0

    def minimumSizeHint(self):
        hint = super().minimumSizeHint()
        inner = self.widget()
        if inner is not None and inner.layout() is not None and self.isVisible():
            m = inner.layout().contentsMargins()
            bar = self.verticalScrollBar().sizeHint().width()  # (the theme's is 12 px; another style's can be wider)
            self._need = inner.minimumSizeHint().width() - m.right() + max(self.side, bar + 2) + 2 * self.frameWidth()
        return hint.expandedTo(QSize(self._need, 0))

    def showEvent(self, e):
        super().showEvent(e)
        self.updateGeometry()

    def eventFilter(self, obj, e):
        if obj is self.widget() and e.type() == QEvent.LayoutRequest:
            self.updateGeometry()  # (its content's smallest width may have changed)
        return super().eventFilter(obj, e)
