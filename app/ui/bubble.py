"""Bubbles: a few words that point at a control (Windows 11's teaching tip, small), drawn on the window over its
controls (a child of the window, never a window of its own). The UI audit (2026-11-08, the user's selection): the
messages and the "do this first" texts show where you look, not in a line at the window's bottom or in a box that
stops all work until OK.

- tell(anchor, text): "do this first" (UI-RULES 25): at the button that you clicked (anchor None: the control with
  the focus), with ✕; a click at a different position, Esc or a new bubble closes it.
- Messages(window): the main window's messages (UI-RULES 24): say(text, ms, undo) shows a bubble near the control
  that you used last (the focus, when you used the keyboard or the mouse in the last minute), else at the bottom of
  the window, for 6 s or more (window_parts.SAID_MS / READ_MS), 20 s with Undo in it (Ctrl+Z also undoes while it
  shows). A window of its own keeps its message line in its footer (UI-RULES 1).
- InfoMark(text): the ⓘ symbol after a label (the gray notes under the boxes, now behind it): its tooltip has the
  words; a click, Space or Enter shows them in a bubble, where links work.
A screen reader hears a bubble as an alert. last(kind) gives the bubble shown last of a kind (for the tests).
"""
from PySide6.QtCore import QEvent, QObject, QPoint, QRect, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QAccessible, QColor, QKeySequence, QPainter, QPainterPath, QPen, QShortcut
from PySide6.QtWidgets import (QAbstractButton, QAbstractSlider, QAbstractSpinBox, QApplication, QComboBox, QFrame,
                               QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit, QPushButton, QToolButton, QWidget)

from ui import theme

ARROW = 8     # (px: the point's height)
WORDS = 380   # (px: the words wrap at this width)
RECENT_MS = 60000  # (a message goes near the focused control only if you used the keyboard or the mouse this recently)
_open = {}    # (id of the window, kind) -> the bubble of that kind shown on it now
_last = {}    # kind -> the bubble shown last of that kind


def plain(text):
    """Words with their HTML (links, bold) taken out: what a screen reader reads."""
    from PySide6 import QtGui
    if not QtGui.Qt.mightBeRichText(text or ""):
        return text or ""
    from PySide6.QtGui import QTextDocument
    doc = QTextDocument()
    doc.setHtml(text)
    return doc.toPlainText()


class Bubble(QFrame):
    """One bubble on a window: the words, Undo when there is one, then ✕. It points at its anchor (below it when
    there is room, else above it) and follows it while the page scrolls; it closes when the anchor goes."""

    def __init__(self, win, kind):
        super().__init__(win)
        self.setObjectName("bubble")
        self.kind, self.anchor, self.below, self.point = kind, None, True, None
        self.setFocusPolicy(Qt.NoFocus)
        row = QHBoxLayout(self)
        row.setSpacing(8)
        self.text = QLabel()
        self.text.setWordWrap(True)
        self.text.setTextFormat(Qt.AutoText)
        self.text.setMaximumWidth(WORDS)
        self.text.setTextInteractionFlags(Qt.LinksAccessibleByMouse | Qt.LinksAccessibleByKeyboard)
        row.addWidget(self.text, 1)
        from ui import icons
        self.undo_btn = QPushButton("Undo")
        icons.put(self.undo_btn, "undo")
        self.undo_btn.setToolTip("Undo (Ctrl+Z)")
        self.undo_btn.setAutoDefault(False)
        self.undo_btn.clicked.connect(self._undo)
        self.undo_btn.hide()
        row.addWidget(self.undo_btn, 0, Qt.AlignVCenter)
        self.close_btn = QToolButton()
        self.close_btn.setText("✕")
        self.close_btn.setToolTip("Close")
        self.close_btn.setAccessibleName("Close the message")
        theme.mark(self.close_btn, quiet=True)
        self.close_btn.clicked.connect(self.close_now)
        row.addWidget(self.close_btn, 0, Qt.AlignTop)
        self._undo_fn = self._links = None
        self._size_key = None  # (what its size was measured for: see place)
        self._timer = QTimer(self, singleShot=True, timeout=self.close_now)
        # (the page under it scrolls, the window resizes: only while the window shows, see eventFilter)
        self._follow = QTimer(self, interval=150, timeout=self.place)
        self.hide()
        win.installEventFilter(self)

    def eventFilter(self, obj, e):
        """The window shown again or restored (from the tray, from minimized): the bubble follows its anchor again."""
        if obj is self.parentWidget() and e.type() in (QEvent.Show, QEvent.WindowStateChange) \
                and not self.isHidden() and not self._follow.isActive():
            QTimer.singleShot(0, self, self._resume)
        return False

    def _resume(self):
        if not self.isHidden() and _window_shows(self.parentWidget()):
            self._follow.start()
            self.place()

    # ---------------------------------------------------------------- showing
    def show_text(self, text, anchor=None, ms=None, undo=None, links=None):
        """The words (and Undo when undo is given) at anchor (None: the bottom of the window), for ms (None: until a
        click elsewhere, ✕ or Esc)."""
        self.text.setText(text)
        if self._links is not None:  # (the links of the words before)
            self.text.linkActivated.disconnect(self._links)
        self._links = links
        if links is not None:
            self.text.linkActivated.connect(links)
        words = plain(text)  # (once: for rich text it is a whole text document)
        self.setAccessibleName(words)
        # (as wide as its words, up to WORDS: Qt broke a short message into lines of two or three words)
        self.text.ensurePolished()
        widest = max((self.text.fontMetrics().horizontalAdvance(line) for line in words.splitlines()), default=0)
        self.text.setMinimumWidth(min(WORDS, widest + 2))
        self._undo_fn = undo
        self.undo_btn.setVisible(undo is not None)
        self.anchor = anchor
        self.place()
        if self.isHidden() and self.text.text() == "":  # (place() closed it: its anchor is out of view)
            return
        self.show()
        self.raise_()
        if _window_shows(self.parentWidget()):
            self._follow.start()
        if ms:
            self._timer.start(ms)
        else:
            self._timer.stop()
        _last[self.kind] = self
        ev = QAccessible.updateAccessibility
        try:
            from PySide6.QtGui import QAccessibleEvent
            ev(QAccessibleEvent(self, QAccessible.Alert))
        except (ImportError, RuntimeError, TypeError):  # (no screen reader support in this Qt)
            pass

    def place(self):
        """Its place: under the anchor's middle (above it at the window's bottom), always within the window."""
        win = self.parentWidget()
        if win is None:
            return
        if not _window_shows(win):  # (minimized or in the tray: nothing to follow; _resume starts it again)
            self._follow.stop()
            return
        a = self.anchor
        try:
            gone = a is not None and (not a.isVisible() or not in_view(a, win))
        except RuntimeError:  # (the anchor was deleted)
            gone = True
        if gone:
            if self.kind == "say":  # (a message stays: at the window's bottom now)
                self.anchor = a = None
            else:
                self.close_now()
                return
        self.setContentsMargins(0, 0, 0, 0)
        lay = self.layout()
        W, H = win.width(), win.height()
        # (its size measured again only when its words or its point changed: the size is the slow part, and the
        # follow timer places it every 150 ms. Above or below, the point takes the same height)
        size_key = (self.text.text(), self.undo_btn.isVisibleTo(self), a is not None)
        if a is None:
            self.below, self.point = True, None
            lay.setContentsMargins(14, 8, 8, 8)
            if size_key != self._size_key:
                self._size_key = size_key
                self.adjustSize()
            self.move(max(8, (W - self.width()) // 2), max(8, H - self.height() - 16))
            self.update()
            return
        if size_key != self._size_key:
            self._size_key = size_key
            lay.setContentsMargins(14, 8 + ARROW, 8, 8)
            self.adjustSize()
        w, h = self.width(), self.height()
        r = QRect(a.mapTo(win, QPoint(0, 0)), a.size())
        y = r.bottom() + 2
        self.below = not (y + h > H - 4 and r.top() - 2 - h >= 4)  # (no room under it: above it)
        lay.setContentsMargins(14, 8 + ARROW, 8, 8) if self.below else lay.setContentsMargins(14, 8, 8, 8 + ARROW)
        if not self.below:
            y = r.top() - 2 - h
        y = max(4, min(y, H - h - 4))
        x = max(8, min(r.center().x() - w // 2, W - w - 8))
        self.point = max(16, min(r.center().x() - x, w - 16))
        self.move(x, y)
        self.update()

    def paintEvent(self, e):
        t = theme.tokens()
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        body = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        if self.point is not None:
            body = body.adjusted(0, ARROW, 0, 0) if self.below else body.adjusted(0, 0, 0, -ARROW)
        path = QPainterPath()
        path.addRoundedRect(body, 8, 8)
        if self.point is not None:
            tip = QPainterPath()
            x = self.point
            if self.below:
                tip.moveTo(x - ARROW, body.top() + 1)
                tip.lineTo(x, body.top() - ARROW)
                tip.lineTo(x + ARROW, body.top() + 1)
            else:
                tip.moveTo(x - ARROW, body.bottom() - 1)
                tip.lineTo(x, body.bottom() + ARROW)
                tip.lineTo(x + ARROW, body.bottom() - 1)
            tip.closeSubpath()
            path = path.united(tip)
        p.setPen(QPen(QColor(t["stroke"]), 1))
        p.setBrush(QColor(t["menu"]))
        p.drawPath(path)

    # ---------------------------------------------------------------- closing
    def close_now(self):
        self._timer.stop()
        self._follow.stop()
        self._undo_fn = None
        self.text.setText("")
        self._size_key = None
        self.hide()
        if _closer:  # (the app-wide watch goes with the last bubble that it watched)
            _closer[0].forget(self)

    def _undo(self):
        fn = self._undo_fn
        self.close_now()
        if fn is not None:
            fn()

    def can_undo(self):
        return self.isVisible() and self._undo_fn is not None


class _Closer(QObject):
    """The app-wide watch while a "do this first" or ⓘ bubble shows: a click outside it, or Esc, closes it. Put on the
    app only while one shows (an app-wide watch sees every event of every control)."""

    def __init__(self):
        super().__init__()
        self.bubbles = []

    def watch(self, b):
        if b not in self.bubbles:
            self.bubbles.append(b)
        if len(self.bubbles) == 1:
            QApplication.instance().installEventFilter(self)

    def forget(self, b):
        """b closed (by its time, its ✕, Undo or the code): not watched; the app-wide watch off with the last one."""
        if b in self.bubbles:
            self.bubbles.remove(b)
            if not self.bubbles:
                QApplication.instance().removeEventFilter(self)

    def watching(self):
        return bool(self.bubbles)

    def eventFilter(self, obj, e):
        t = e.type()
        if t not in (QEvent.MouseButtonPress, QEvent.KeyPress):
            return False
        if t == QEvent.KeyPress and (e.key() != Qt.Key_Escape or QApplication.activePopupWidget() is not None):
            return False  # (Esc goes to an open menu or list first: it closes that, and the bubble stays)
        for b in list(self.bubbles):
            try:
                if not b.isVisible():
                    self.forget(b)
                    continue
                if t == QEvent.KeyPress:
                    if b.window().isActiveWindow():
                        b.close_now()
                        return True
                    continue
                # (a press in the bubble: its ✕, its links, its words. The app sees a press first on the window's
                # native part (a QWindow, not a widget), so where the press is decides, not which object has it)
                if _press_in(b, obj, e):
                    continue
                b.close_now()
            except RuntimeError:  # (deleted with its window)
                self.forget(b)
        return False


_closer = []


def _press_in(b, obj, e):
    """True when the press e (to obj: a widget or a window's native part) is on the bubble b."""
    if isinstance(obj, QWidget):
        if obj is b or b.isAncestorOf(obj):
            return True
        if obj.window() is not b.window():
            return False
    elif getattr(obj, "isTopLevel", None) is not None and obj is not b.window().windowHandle():
        return False  # (a press on a different window: a menu, a dialog)
    try:
        at = e.globalPosition().toPoint()
    except AttributeError:
        return False
    return b.rect().contains(b.mapFromGlobal(at))


def _window_shows(win):
    """The window shows on the screen (not minimized, not hidden in the tray)."""
    return win is not None and win.isVisible() and not win.isMinimized()


def in_view(w, win):
    """Some of w is in view in win: not scrolled out of a scroll area (or any other parent that clips it)."""
    r = w.rect()
    p = w
    while p is not None and p is not win:
        parent = p.parentWidget()
        if parent is None:
            break
        r = QRect(p.mapToParent(r.topLeft()), r.size()).intersected(parent.rect())
        if r.isEmpty():
            return False
        p = parent
    return True


def _bubble(win, kind):
    key = (id(win), kind)
    b = _open.get(key)
    try:
        if b is not None and b.parentWidget() is win:
            return b
    except RuntimeError:
        pass
    b = _open[key] = Bubble(win, kind)
    win.destroyed.connect(lambda *_a, key=key: _open.pop(key, None))
    return b


def _focus_in(win):
    """The control that you used last in win (the focus), if it is one a message can point at."""
    w = QApplication.focusWidget()
    if w is None or w.window() is not win or not w.isVisible():
        return None
    if isinstance(w, (QAbstractButton, QComboBox, QLineEdit, QAbstractSpinBox, QAbstractSlider, QPlainTextEdit)):
        return w
    return None


def tell(anchor, text, near=None, links=None):
    """A "do this first" text at anchor (the button that you clicked; None: the focused control of near's window, or
    near itself). Closes on a click elsewhere, ✕ or Esc. Returns the bubble."""
    if anchor is None and near is not None:
        anchor = _focus_in(near.window()) or near
    if anchor is None:
        return None
    win = anchor.window()
    b = _bubble(win, "tell")
    b.show_text(text, anchor, links=links)
    if not _closer:
        _closer.append(_Closer())
    # (watched from the next event on: the click that opened it is over by then)
    QTimer.singleShot(0, b, lambda: b.isVisible() and _closer[0].watch(b))
    return b


def last(kind="tell"):
    """The bubble shown last of a kind ("tell", "say", "info"), or None (the tests read its words)."""
    b = _last.get(kind)
    try:
        return b if b is not None and b.parentWidget() is not None else None
    except RuntimeError:
        return None


class Messages:
    """The main window's messages: say() as window_parts.MessageLine's, in a bubble near the control that you used
    (UI-RULES 24). text and undo_btn: the bubble's (the tests read them)."""

    def __init__(self, win):
        self.win = win
        self.bubble = _bubble(win, "say")
        self.text, self.undo_btn = self.bubble.text, self.bubble.undo_btn
        QShortcut(QKeySequence(QKeySequence.Undo), win, lambda: self.bubble.can_undo() and self.bubble._undo(),
                  context=Qt.WindowShortcut)

    def say(self, text, ms=None, undo=None):
        from ui import winsys
        from ui.window_parts import READ_MS, SAID_MS, UNDO_MS
        b = self.bubble
        if not text:
            b.close_now()
            b.text.setText("")
            return
        if ms != 0:
            ms = max(ms or 0, UNDO_MS if undo else SAID_MS, READ_MS * len(text))
        recent = winsys.idle_ms() < RECENT_MS
        b.show_text(text, _focus_in(self.win) if recent else None, ms=ms or None, undo=undo)


class InfoMark(QToolButton):
    """The ⓘ after a label: its words in the tooltip; a click (or Space, Enter) shows them in a bubble, where its links
    work (links: what a link does). set_text() changes them (a note that follows the settings)."""

    def __init__(self, text="", name="", links=None):
        super().__init__()
        self._text = ""  # (read as it is made: the theme's watch asks a button for its words)
        self.setObjectName("infoMark")
        self.setAutoRaise(True)
        self.setCursor(Qt.PointingHandCursor)
        self._links, self._name = links, name
        from ui import icons
        icons.put(self, "info")
        theme.mark(self, quiet=True, info=True)
        self.ensurePolished()
        self.setFixedSize(self.sizeHint().expandedTo(QSize(28, 24)))  # (never squeezed in a small window)
        self.clicked.connect(self.show_words)
        self.set_text(text)

    def set_text(self, text):
        self._text = text
        self.setToolTip(text)
        self.setAccessibleName(f"About {self._name}" if self._name else "More information")
        self.setAccessibleDescription(plain(text))
        if not text:
            self.hide()
        elif self.isHidden() and self.parentWidget() is not None:  # (never shown before it has a parent: it would
            self.show()                                               # flash as a window of its own)

    def text_now(self):
        return self._text

    def text(self):  # (its words, not a button's: the Guide stages a note's words as it did a label's)
        return self._text

    def setText(self, text):
        self.set_text(text)

    def show_words(self):
        if not self._text:
            return
        b = _bubble(self.window(), "info")
        b.show_text(self._text, self, links=self._links)
        _last["info"] = b
        if not _closer:
            _closer.append(_Closer())
        QTimer.singleShot(0, b, lambda: b.isVisible() and _closer[0].watch(b))
