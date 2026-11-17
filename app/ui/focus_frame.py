"""The focus frame: a frame round the control with the focus, shown only while the person uses the keyboard (the
user's decision, 2026-11-16: no button of the app showed clearly which one has the focus). The look is that of
Windows 11's focus visual: a line in the text's colour with a thin line in the opposite colour inside it, so that it
is clear on a card, on the window and on the accent button, in light and in dark (theme_tokens.py: "focus_outer",
"focus_inner"). It is drawn outside the control, in a widget of its own (_Ring), so no control changes its size, its
place or one of its pixels.

Which controls: KINDS. Push buttons and tool buttons (✕, the rows that open, ⓘ) are the approved ones; tick boxes,
round buttons, drop-down lists and sliders get the same frame (inferred). Text boxes keep their own focus style, and
a control that draws its own keyboard focus says so with the property ownFocus (the filter editor's sliders).
theme_sheet.py's focus_frame part takes Fusion's own focus box off the buttons, so that there is one look.

When it shows (measured with PySide6 6.11.2, 2026-11-16):
- Qt sets Qt.WA_KeyboardFocusChange on a window when Tab, Shift+Tab or an arrow key moves the focus in it, and takes
  it off at the next move of the focus by anything else (a click, the code, a window that becomes active). It is
  set before QApplication.focusChanged is sent, so the attribute read there says "a key moved the focus".
- A key that does not move the focus (Space on a button, a letter in a box) and a mouse press change nothing that Qt
  tells, so two watches look for them, each only while it can change something:
  with the keyboard not in use, the control with the focus is watched for a key press (the frame then shows on it,
  as the filter editor's sliders show theirs from the first arrow key); with the keyboard in use, the windows that
  had the focus since then are watched for a mouse press (the frame goes: a click anywhere, also one that moves no
  focus, on a label or on the control with the frame).
- A menu that a button opens takes the keys and the clicks itself and moves no focus (measured: the button keeps
  the focus while its menu shows), so each menu and list that pops up is watched while it shows, for the two
  (watch_popup: theme.py's filter, which sees each pop-up as it shows, tells of it). Without that, the frame stayed
  after a click on a menu's item.
- A turn of the mouse wheel on a control whose focus policy has the wheel in it (Qt.WheelFocus: in the app, the
  drop-down lists) gives that control the focus with no mouse button down (measured: the cause in its focus events
  is Qt.MouseFocusReason, but QApplication.focusChanged tells no cause). Qt hands the turn to the window's native
  part first, and moves the focus while it takes the turn on to the control (measured). So the native parts watched
  for a mouse press are watched for a turn too, and a move of the focus while a turn is handed on is the mouse's, as
  a click's: no frame (it went to the list, found by a verifier). A turn that moves no focus, as one that scrolls
  the page, changes nothing: the frame stays on its control. Qt does not tell when it is done with an event, so
  "handed on" ends at the app's next free moment, or at a key press before that (measured off-screen: without this,
  Tab showed no frame after a turn with no pass of the event loop between the two; on Windows that is a turn and a
  key that waited while the app was busy: from memory of Qt's source, not measured).
- While the keyboard is in use, the frame follows the focus wherever the app puts it in the window (Cancel while a
  job runs), and it is hidden while no window of the app is active.
- A window shows the frame only after a key was pressed in it since the last mouse press (inferred): a window that
  the app opens shows none until its first key, as Qt's own attribute is each window's. (With one state for the
  whole app, a window opened with the keyboard would show the frame at once, as Windows does; but a window that the
  code shows long after a key would show it too, and the tests of the windows' parts, which show their windows
  that way, would find the frame among the parts whenever an earlier test had pressed a key.)

No Python runs on each event of the app: FocusFrame is an event filter only on the few objects above (one control,
or the windows' native parts, a menu or list while it shows, and the framed control with its parents up to the
frame's parent), never on the application. One move of the focus by the code, in the main window with the theme
(the median of 300, measured 2026-11-16): 11 µs before the frame was there, 19 µs with the mouse in use, 40 µs with
the frame in one parent, and 131 µs when the frame goes to another parent (tests\\ui\\test_focus_frame.py checks
that it stays under 1 ms).

Where it is: a child of the control's window, or of the view of the scroll area the control is in (as Qt's own
QFocusFrame), so a scroll area cuts the frame as it cuts the control. It is stacked directly above the part of that
parent that holds the control: what covers the control (the graph that floats over Make an EQ's page, a message
bubble, the Guide's layers) covers the frame too. Its objectName is "focusFrame" (the tests find it by that).
Qt's QFocusFrame itself was not used: with the app's style it is a square 2 px line under the control, cut by the
control's own parent (measured), and its place and shape come from the style, not from the code.
"""
import weakref

import shiboken6
from PySide6.QtCore import QEvent, QObject, QPoint, QRect, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QGuiApplication, QPainter, QPen
from PySide6.QtWidgets import (QAbstractButton, QAbstractItemView, QAbstractScrollArea, QApplication, QComboBox,
                               QSlider, QWidget)

from ui import theme

# The sizes of Windows 11's focus visual (from memory, not read from a document in this work: WinUI's focus visual
# has a 2 px primary line and a 1 px secondary line, 3 px outside the control); the corner is a control's 4 px corner
# (theme_sheet.py) plus the margin.
MARGIN = 3
OUTER = 2
INNER = 1
RADIUS = 4 + MARGIN
KINDS = (QAbstractButton, QComboBox, QSlider)
# (keys that are not "the person uses the keyboard" by themselves)
_MODIFIER_KEYS = (Qt.Key_Shift, Qt.Key_Control, Qt.Key_Alt, Qt.Key_Meta, Qt.Key_AltGr, Qt.Key_CapsLock,
                  Qt.Key_NumLock, Qt.Key_ScrollLock)
_CHORD = Qt.ControlModifier | Qt.AltModifier | Qt.MetaModifier
# (event types read once: the filter compares each event's type with them)
_MOVE, _RESIZE, _SHOW, _HIDE = QEvent.Move, QEvent.Resize, QEvent.Show, QEvent.Hide
_PARENT, _ZORDER = QEvent.ParentChange, QEvent.ZOrderChange
_PRESSES = (QEvent.MouseButtonPress, QEvent.NonClientAreaMouseButtonPress)
_WHEEL = QEvent.Wheel
_KEYS = (QEvent.ShortcutOverride, QEvent.KeyPress)  # (ShortcutOverride comes first, also for a key a shortcut takes)
_WATCHED = (_MOVE, _RESIZE, _SHOW, _HIDE, _PARENT, _ZORDER, *_PRESSES, _WHEEL, *_KEYS)

_engine = None


def install(app):
    """The app's one focus frame, made at the first call (theme.apply calls this each time: the frame is drawn again
    in the theme's colours)."""
    global _engine
    if _engine is None or not shiboken6.isValid(_engine):
        _engine = FocusFrame(app)
    else:
        _engine.redraw()
    return _engine


def framed():
    """The control the frame shows on now, or None."""
    return _engine.framed() if _engine is not None and shiboken6.isValid(_engine) else None


def keyboard_in_use():
    """Does the person use the keyboard (a key was the last thing pressed, not a mouse button)?"""
    return bool(_engine is not None and shiboken6.isValid(_engine) and _engine.keyboard)


def _alive(obj):
    return obj is not None and shiboken6.isValid(obj)


def _held(widget):
    """A way back to a watched widget, as a call: a child is held as it is (Qt owns it, and PySide6 can let go of the
    Python object of a widget that Qt made, as a message box's buttons, while it is watched); a window is held weakly,
    so that the watch never keeps a window of Python's alive."""
    return weakref.ref(widget) if widget.isWindow() else lambda: widget


class _Ring(QWidget):
    """The frame as drawn: two rounded lines along its own edge, nothing inside. The mouse goes through it, it takes
    no focus, and its parent is told nothing about it (as Qt's QFocusFrame: a parent that places its children by
    itself leaves it alone). Made without a parent and never shown so: FocusFrame gives it one before it shows."""

    def __init__(self, engine):
        super().__init__()
        self.setObjectName("focusFrame")
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_NoChildEventsForParent)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setFocusPolicy(Qt.NoFocus)
        self.engine = engine
        self.radius = RADIUS
        self.placing = False

    def moveEvent(self, e):
        # (a list that scrolls moves every child of its view, this one too: back to its control)
        if not self.placing and _alive(self.engine):
            self.engine.place()

    def paintEvent(self, _e):
        t = theme.tokens()
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(Qt.NoBrush)
        box = QRectF(self.rect())
        for colour, width, inset in ((t["focus_outer"], OUTER, OUTER / 2), (t["focus_inner"], INNER, OUTER + INNER / 2)):
            r = max(self.radius - inset, 0)
            p.setPen(QPen(QColor(colour), width))
            p.drawRoundedRect(box.adjusted(inset, inset, -inset, -inset), r, r)
        p.end()


class FocusFrame(QObject):
    """The one focus frame of the app (install()). keyboard: a key was the last thing pressed, not a mouse button."""

    def __init__(self, app):
        super().__init__(app)
        self.keyboard = False
        self._keyed = []       # the windows in which a key was pressed since the last mouse press (held weakly)
        self._ring = None
        self._target = None    # the framed control (_held)
        self._chain = []       # the control and its parents up to the frame's parent (_held), watched for a move
        self._key_at = None    # keyboard not in use: the control watched for a key press (_held)
        self._presses = []     # keyboard in use: the windows' native parts watched for a mouse press
        self._popups = []      # the menus and lists that show now, each with its native part (watch_popup)
        self._wheel = False    # keyboard in use: Qt hands a turn of the mouse wheel on now (it can move the focus)
        app.focusChanged.connect(self._focus_changed)

    # ------------------------------------------------------------ what is asked from outside
    def framed(self):
        w = self._target() if self._target is not None else None
        ring = self._ring
        return w if _alive(w) and _alive(ring) and ring.isVisible() else None

    def redraw(self):
        if _alive(self._ring):
            self._ring.update()

    # ------------------------------------------------------------ keyboard or mouse
    def _focus_changed(self, _old, _new):
        # (the control with the focus now, not the one the signal names: a slot before this one, as the Guide's, can
        # have moved the focus again)
        w = QApplication.focusWidget()
        self._watch_key(None)
        if w is None:  # (no window of the app is active, or nothing has the focus)
            self._aim(None)
            return
        if QGuiApplication.mouseButtons() != Qt.NoButton or self._wheel:  # (a click or the wheel moved the focus)
            self._mouse()
        elif w.window().testAttribute(Qt.WA_KeyboardFocusChange):  # (Tab, Shift+Tab or an arrow key moved it)
            self._key_in(w.window())
        if self.keyboard:
            self._watch_presses(w.window())
            self._aim(w)
        else:
            self._watch_key(w)

    def _key_in(self, window):
        """A key was pressed in this window: the keyboard is in use, and the window can show the frame (for a menu or
        a list that pops up, the window of the control it belongs to as well: the focus goes back there)."""
        self.keyboard = True
        marks = [k for k in self._keyed if _alive(k())]
        owner = window.parentWidget() if window.windowType() == Qt.Popup else None
        for win in (window, owner.window() if owner is not None else None):
            if win is not None and not any(k() is win for k in marks):
                marks.append(weakref.ref(win))
        self._keyed = marks

    def _keyed_in(self, window):
        return any(k() is window for k in self._keyed)

    def _mouse(self):
        """A mouse button was pressed: the keyboard is not in use, and the frame goes."""
        self.keyboard = False
        self._keyed = []
        for win in self._presses:
            if _alive(win):
                win.removeEventFilter(self)
        self._presses = []
        self._aim(None)

    def _wheel_over(self):
        self._wheel = False

    def _watch_presses(self, window):
        handle = window.windowHandle()
        if handle is not None and not any(h is handle for h in self._presses) \
                and not any(h is handle for _p, h in self._popups):
            self._presses = [h for h in self._presses if _alive(h)]
            self._presses.append(handle)
            handle.installEventFilter(self)

    def watch_popup(self, popup):
        """A menu or a list that pops up, watched while it shows for a key (on itself: a menu gets its keys) and for
        a mouse press (on its native part: a press on one of its parts too)."""
        self._popups = [(p, h) for p, h in self._popups if _alive(p) and p is not popup]
        handle = popup.windowHandle()
        self._presses = [h for h in self._presses if h is not handle]
        popup.installEventFilter(self)
        if handle is not None:
            handle.installEventFilter(self)
        self._popups.append((popup, handle))

    def _popup_hidden(self, obj):
        for popup, handle in self._popups:
            if popup is obj:
                popup.removeEventFilter(self)
                if _alive(handle):
                    handle.removeEventFilter(self)
                self._popups = [(p, h) for p, h in self._popups if p is not obj]
                return

    def _watch_key(self, widget):
        old = self._key_at() if self._key_at is not None else None
        if _alive(old) and not any(p is old for p, _h in self._popups):  # (a menu that shows stays watched)
            old.removeEventFilter(self)
        self._key_at = None
        if widget is not None:
            self._key_at = _held(widget)
            widget.installEventFilter(self)

    def eventFilter(self, obj, e):
        t = e.type()
        if t not in _WATCHED:
            return False
        if t is _MOVE or t is _RESIZE:
            self.place()
        elif t in _PRESSES:
            if self.keyboard and e.spontaneous():  # (the person's own press, not one that a demo of the Guide makes)
                self._mouse()
                self._watch_key(QApplication.focusWidget())
        elif t is _WHEEL:
            # (only at a native part, which gets the turn before the focus moves: a control gets it after that)
            if self.keyboard and not self._wheel and e.spontaneous() and obj.isWindowType():
                self._wheel = True
                QTimer.singleShot(0, self._wheel_over)
        elif t in _KEYS:
            if e.spontaneous():
                self._wheel = False  # (a move of the focus from here on is this key's, not the wheel's)
                if e.key() not in _MODIFIER_KEYS and not e.modifiers() & _CHORD:
                    w = QApplication.focusWidget()
                    if w is not None and not (self.keyboard and self._keyed_in(w.window())):  # (the first key here)
                        self._key_in(w.window())
                        self._watch_key(None)
                        self._watch_presses(w.window())
                        self._aim(w)
        elif t is _HIDE or t is _SHOW:
            if t is _HIDE and self._popups:
                self._popup_hidden(obj)
            if self._target is not None and obj is self._target():
                self.place()
        elif self._target is not None:  # (the control or one of its parents went to another parent, or up or down)
            self._aim(self._target())
        return False

    # ------------------------------------------------------------ the frame
    @staticmethod
    def wants(w):
        """Is w a control that gets the frame?"""
        return isinstance(w, KINDS) and not w.isWindow() and not w.property("ownFocus")

    @staticmethod
    def _where(w):
        """(the frame's parent, w and its parents under that parent): the view of the nearest scroll area that w is in,
        else w's window."""
        chain, p = [w], w.parentWidget()
        while p is not None and not p.isWindow():
            if isinstance(p, QAbstractScrollArea) and chain[-1] is p.viewport():
                return chain.pop(), chain
            chain.append(p)
            p = p.parentWidget()
        return p, chain

    def _aim(self, w):
        """The frame on w, when w is a control that gets it and the keyboard is in use in its window; else no frame."""
        for held in self._chain:
            x = held()
            if _alive(x):
                x.removeEventFilter(self)
        self._chain, self._target = [], None
        shows = self.keyboard and _alive(w) and self.wants(w) and self._keyed_in(w.window())
        parent, chain = self._where(w) if shows else (None, [])
        if parent is None:
            if _alive(self._ring):
                self._ring.hide()
            return
        ring = self._ring if _alive(self._ring) else None
        if ring is None:
            ring = self._ring = _Ring(self)
        if ring.parentWidget() is not parent:
            ring.setParent(parent)
        self._target = _held(w)
        for x in chain:
            x.installEventFilter(self)
        self._chain = [_held(x) for x in chain]
        # (directly above the part of the parent that holds the control: what the app puts over that part, as the
        # graph that floats over Make an EQ's page, covers the frame as it covers the control. In the view of a list
        # or a table the cells are side by side in the view, closer than the frame is wide: above them all)
        above = None
        if not isinstance(parent.parentWidget(), QAbstractItemView):
            found = False
            for c in parent.findChildren(QWidget, options=Qt.FindDirectChildrenOnly):
                if found and c is not ring:
                    above = c
                    break
                found = found or c is chain[-1]
        if above is not None:
            ring.stackUnder(above)
        else:
            ring.raise_()
        ring.radius = (w.height() + 2 * MARGIN) / 2 if w.property("online") or w.property("tag") else RADIUS
        self.place()

    def place(self):
        """The frame round its control as the control is now: MARGIN outside it, hidden with it. A side with less room
        than MARGIN to the parent's edge comes in to that edge, while the control is whole on that side (a table's
        first row and a button at the right edge of a scroll area had no line there: measured, 2026-11-16); a
        control that the view cuts has its frame cut with it."""
        w = self._target() if self._target is not None else None
        ring = self._ring
        if not _alive(w) or not _alive(ring):
            return
        parent = ring.parentWidget()
        if parent is None or not w.isVisible() or not parent.isAncestorOf(w):
            ring.hide()
            return
        at = w.mapTo(parent, QPoint(0, 0))
        left, top, right, bottom = at.x(), at.y(), at.x() + w.width(), at.y() + w.height()
        room_w, room_h = parent.width(), parent.height()
        x0 = 0 if left >= 0 > left - MARGIN else left - MARGIN
        y0 = 0 if top >= 0 > top - MARGIN else top - MARGIN
        x1 = room_w if right <= room_w < right + MARGIN else right + MARGIN
        y1 = room_h if bottom <= room_h < bottom + MARGIN else bottom + MARGIN
        ring.placing = True
        try:
            ring.setGeometry(QRect(x0, y0, x1 - x0, y1 - y0))
        finally:
            ring.placing = False
        if not ring.isVisible():
            ring.show()
