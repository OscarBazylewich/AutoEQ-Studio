"""Guided tours with demonstrations (AutoEQ Local's tour.js, natively), shared by Make an EQ's Guide and the tracer's.

A tour is a list of steps. Each step lights one or more real controls (the rest of the window dimmed), explains them
in a card, and can carry a demo: actions played by a drawn pointer on a layer above the window. Clicks never reach
the window while a tour runs, and what a demo shows (a list opened, a value typed, a curve on the graph) is put back
when it ends: nothing of yours changes. When the tour ends, the focus goes back to the control that had it before
(Tour.end_focus).

The card: the step list (e.g. "1 · Select · 3 of 31", Windows 11's chevron after it: go straight to any step; at its
foot Play all steps, one after another, and the demos' speed, ¼× to 4×) and ✕ (close the Guide, Esc) at the top
right, a progress bar, "Demo · your work does not change" in gray under it, the title and words, the demo's actions
(while it plays, only the one playing now), Play demo / Play again (R; Show the steps with animation effects off),
Wait (P), Complete the demo, a step's own buttons (e.g. Open Help), Start again (the last step), Back / Next (← →).
The card goes where it covers least of what's lit, what the demo uses and the pointer (and no marker, when it can),
and stays put while that's as good as anywhere else.
The look is Windows 11's, as the rest of the app: the card and what a demo shows inside the tour are styled by name in
ui\\theme_sheet.py's guide_and_help part (#tourCard, #tourMock, #tourNote …); what's drawn here by hand takes
theme.tokens() as it's drawn: the accent (Windows' own colour) marks what's lit, what the pointer is on, a click and a
drag; the card's symbols and its list of actions are drawn again when the theme changes.
The page can be scrolled at any time (the wheel, Page Up/Down, Up/Down): the spotlight follows, and the keys still
scroll the page once what was lit is out of sight; scrolling while a demo plays pauses it, and Continue scrolls back to
where the demo was and carries on.
With Windows' animation effects off nothing plays: each action is a numbered marker on its control, with the list of
actions in the card. As the markers show, the page moves once at most, to where the most of them show without
taking what's lit out of sight (show_markers). A marker stays on its control when the page scrolls, and is drawn
while its disc is whole in sight and off the card (marker_points).

A step: {"chapter", "title", "text" (str or fn), "target": fn -> a widget or [widgets] (lit), "alt": fn -> the
control(s) lit when the target isn't on screen (with "alt_text" and "alt_demo"), "ready": fn -> bool (offered in the
step list), "before"/"after" (show what the step needs, put it back), "avoid": fn -> widgets the card keeps off,
"demo": [actions] or fn -> [actions], "buttons": [(label, fn)] (end the tour, then fn)}.
A demo's actions (each with "say": a few words, shown in the card and beside the pointer; "hold": ms to stay; "x",
"y": where on the control, 0-1; a control is a function giving the widget):
- {"at": control}: the pointer moves there, the control ringed while it's on it
- {"click": control, "then": f}: and clicks (a ripple only: nothing is pressed). f() (or f(api)) shows what the click
  would: it returns the function that puts it back, None, or a generator (a demo of its own, see run)
- {"type": control, "text": "…", "keep": False}: the text appears letter by letter over the field (drawn: the field
  is unchanged); keep: it stays until the demo ends, or until api.untype(field) takes it away
- {"drag": control, "from": (x, y), "to": (x, y), "set": f(p), "undo": g, "label": f(p)}: press and drag, leaving a
  trail; set(p) shows each moment (0-1), undo() puts it back, label(p) the words beside the pointer
- {"run": f(api)}: a generator: the demo's own moves (api: move, ripple, sleep, tween, note, mock lists, a window
  shown inside the tour, the graph kept in sight, curves on the graph, staging a control; every change undone)
- {"note": control, "text": "…"}: a message under the control, as the app would show it
- {"key": "Enter"}: a key shown as a key cap by the pointer
- {"spot": control}: the spotlight moved to it
- {"wait": ms}
problems() lists the steps whose control or demo's control isn't there or can't be seen (for checks).
"""
import inspect
import os
import weakref

from PySide6.QtCore import QEvent, QMargins, QObject, QPoint, QPointF, QRect, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import (QAbstractScrollArea, QCheckBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget,
                               QListWidgetItem, QPushButton, QScrollArea, QSlider, QToolButton, QVBoxLayout, QWidget)

from ui import icons, placed, theme

PAD = 6
CARD_W = 390
SIDE_MIN = 420  # (a window a demo shows goes beside the card when it can be this wide there: 527 px at the smallest)
SPEEDS = [0.25, 0.5, 1.0, 2.0, 4.0]
# The numbered markers (Windows' animation effects off), in px:
MARK_R = 13      # a marker's disc (11) and its outline (2): what must be in sight for it to be drawn
MARK_GAP = 3     # the card stays this far from a marker's disc
MARK_EDGE = 8    # a marker's control counts as shown when it's this far inside its page's view, top and bottom,
MARK_STRIP = 60  # or, taller than this, with this much of it there (the graph: a strip the disc fits in)
MARK_COST = 10 ** 8  # the card over a marker: more than any area it can cover (the fewest markers first, then area)
_kept = {"speed": 1.0, "all": False}  # (the speed and Play all steps, for this session)
_themed = {"hooked": False, "tours": []}  # (the tours made, held weakly: drawn again when the theme changes)


def _retheme():
    import shiboken6
    for ref in list(_themed["tours"]):
        t = ref()
        if t is None or not shiboken6.isValid(t):
            _themed["tours"].remove(ref)
        else:
            t.retheme()


def _set_symbol(button, name):
    """Windows 11's symbol `name` (ui\\icons.py's GLYPHS) beside a card button's words, in the theme's text colour;
    None: no symbol. Kept on the button (its "symbol"), so it's drawn again in a new theme (Tour.retheme)."""
    button.setProperty("symbol", name or "")
    t = theme.tokens()
    if name:
        button.setIcon(icons.glyph(name, t["ink"], off_colour=t["disabled"]))
        button.setIconSize(QSize(22, 16))
    else:
        from PySide6.QtGui import QIcon
        button.setIcon(QIcon())


def scroll_into_view(w, ymargin=60):
    p = w.parentWidget()
    while p is not None:
        if isinstance(p, QScrollArea) and p.widget() is not None and p.widget().isAncestorOf(w):
            p.ensureWidgetVisible(w, 40, ymargin)
        p = p.parentWidget()


def scroll_all_into_view(ws):
    """The page scrolled so the widgets are in sight together, in its upper part when they fit (their top when they
    don't); widgets in no scrolling page: each brought into sight."""
    ws = [w for w in ws if w is not None and _alive(w) and w.isVisible()]
    if not ws:
        return
    area = None
    p = ws[0].parentWidget()
    while p is not None:
        if isinstance(p, QScrollArea) and p.widget() is not None and p.widget().isAncestorOf(ws[0]):
            area = p
            break
        p = p.parentWidget()
    if area is None or not all(area.widget().isAncestorOf(w) for w in ws):
        for w in reversed(ws):
            scroll_into_view(w)
        return
    content = area.widget()
    top = min(w.mapTo(content, QPoint(0, 0)).y() for w in ws)
    bottom = max(w.mapTo(content, QPoint(0, 0)).y() + w.height() for w in ws)
    vh = area.viewport().height()
    bar = area.verticalScrollBar()
    want = top - max(16, int((vh - (bottom - top)) * 0.3)) if bottom - top + 32 <= vh else top - 16
    if top < bar.value() + 8 or bottom > bar.value() + vh - 8:  # (already in sight: left where it is)
        bar.setValue(max(bar.minimum(), min(bar.maximum(), want)))


def _settle():
    """The window laid out after a change (a fold a step opened or closed): every layout's waiting work done, a few
    rounds (a layout that changes asks its parent's again), then the other events."""
    from PySide6.QtWidgets import QApplication
    for _ in range(3):
        QApplication.sendPostedEvents(None, QEvent.LayoutRequest)
        QApplication.processEvents()


def _shown(t):
    ws = t if isinstance(t, (list, tuple)) else [t] if t is not None else []
    return [w for w in ws if w is not None and _alive(w) and w.isVisible()]


def _alive(w):
    try:
        w.objectName()
        return True
    except RuntimeError:  # (its Qt side has gone)
        return False


def _rect(win, ws):
    """The widgets' rectangle together, in the window, cut to what their scroll areas show (a tall control lights
    only its visible part)."""
    r = QRect()
    for w in ws:
        one = QRect(w.mapTo(win, QPoint(0, 0)), w.size())
        p = w.parentWidget()
        while p is not None and p is not win:
            if isinstance(p, QAbstractScrollArea) and p.viewport().isAncestorOf(w):
                vp = p.viewport()
                one = one.intersected(QRect(vp.mapTo(win, QPoint(0, 0)), vp.size()))
            p = p.parentWidget()
        r = r.united(one)
    return r


def _overlap(a, b):
    c = a.intersected(b)
    return 0 if c.isEmpty() else c.width() * c.height()


JOIN = 8  # (px: two lit rectangles' sides this close are one side when they meet: the ring's corner radius)
GAP = 4   # (px: and they meet when they're this close)


def _joined(rects):
    """Lit rectangles that touch or overlap edge to edge, as one: one over the other with their left and right sides
    within JOIN px of each other, or side by side with their tops and bottoms so; the others as they are."""
    from itertools import combinations
    rs = list(rects)
    again = True
    while again:
        again = False
        for i, j in combinations(range(len(rs)), 2):
            a, b = rs[i], rs[j]
            stacked = abs(a.left() - b.left()) <= JOIN and abs(a.right() - b.right()) <= JOIN \
                and a.top() <= b.bottom() + 1 + GAP and b.top() <= a.bottom() + 1 + GAP
            beside = abs(a.top() - b.top()) <= JOIN and abs(a.bottom() - b.bottom()) <= JOIN \
                and a.left() <= b.right() + 1 + GAP and b.left() <= a.right() + 1 + GAP
            if stacked or beside:
                rs[i] = a.united(b)
                del rs[j]
                again = True
                break
    return rs


def _animations_on():
    """Windows' "Animation effects" (Accessibility › Visual effects): off, a demo is numbered markers.
    AUTOEQSTUDIO_ANIMATIONS answers first, "1" for on and "0" for off: the tests set it (tests\\helpers\\session.py),
    so a demo plays the same on every machine (2026-11-22: 2 tests that play a demo failed on GitHub's machine, and
    on this PC with the effects taken as off)."""
    asked = os.environ.get("AUTOEQSTUDIO_ANIMATIONS")
    if asked in ("0", "1"):
        return asked == "1"
    try:
        import ctypes
        v = ctypes.c_int(1)
        ctypes.windll.user32.SystemParametersInfoW(0x1042, 0, ctypes.byref(v), 0)  # SPI_GETCLIENTAREAANIMATION
        return bool(v.value)
    except (AttributeError, OSError):
        return True


ACTIONS = ("at", "click", "type", "drag", "note", "spot")


def _control(a):
    k = next((k for k in ACTIONS if k in a), None)
    if k is None:
        return None
    try:
        w = a[k]() if callable(a[k]) else a[k]
    except (AttributeError, KeyError, RuntimeError, IndexError, TypeError):
        return None
    return w if isinstance(w, QWidget) and _alive(w) else None


def demo_actions(st, alt=False):
    """A step's demo actions as a list (its "demo", or "alt_demo" when alt: a list, or a function that makes one);
    [] when it has none. Public: the Guide's tests play each step's actions too."""
    d = st.get("alt_demo" if alt else "demo")
    return (d() if callable(d) else d) or []


def _val(x):
    return x() if callable(x) else x


def _arg_count(fn):
    """How many arguments a "then" takes (0: then(); 1: then(api))."""
    try:
        ps = inspect.signature(fn).parameters.values()
    except (TypeError, ValueError):
        return 0
    return len([p for p in ps if p.default is p.empty and p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)])


# ---------------------------------------------------------------- the pieces drawn above the window
class _Layer(QWidget):
    """The demo, drawn above the card (clicks go through it)."""

    def __init__(self, tour):
        super().__init__(tour)
        self.tour = tour
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        self.tour.paint_demo(p)


class _Glass(QWidget):
    """Over what a demo shows inside the tour (a window, a list): clicks stop here, so it's only looked at."""

    def __init__(self, tour):
        super().__init__(tour)
        self.setAttribute(Qt.WA_NoSystemBackground)

    def mousePressEvent(self, e):
        e.accept()

    def wheelEvent(self, e):
        self.parentWidget().wheelEvent(e)


class _Follow(QObject):
    def __init__(self, tour):
        super().__init__(tour)
        self.tour = tour

    def eventFilter(self, obj, e):
        if e.type() in (QEvent.Resize, QEvent.Move, QEvent.Show):
            self.tour.place()
        return False


class _Grows(QObject):
    """A demo window's frame told that the parts inside it changed size (Qt's LayoutRequest): then() a moment later,
    once Qt has laid them out again (several at once count as one). Goes with the frame."""

    def __init__(self, frame, then):
        super().__init__(frame)
        self.timer = QTimer(self, singleShot=True, interval=0, timeout=then)
        frame.installEventFilter(self)

    def eventFilter(self, obj, e):
        if e.type() == QEvent.LayoutRequest:
            self.timer.start()
        return False


def _needed_height(w, width):
    """The height a demo's window needs at its smallest, its words wrapped at its frame's width."""
    need = w.minimumSizeHint().height()
    lay = w.layout()
    if lay is not None and lay.hasHeightForWidth():
        need = max(need, lay.minimumHeightForWidth(width - 2))
    return need


def _scroll_holder(w):
    """A demo's window taller than the tour has room for, in a scroll area (tourWinScroll) as wide as its frame: it
    scrolls only up and down."""
    holder = QScrollArea()
    holder.setObjectName("tourWinScroll")
    holder.setWidgetResizable(True)
    holder.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    holder.setFocusPolicy(Qt.NoFocus)
    holder.setWidget(w)
    return holder


class _Bar(QWidget):
    """The tour's progress: a thin bar, as the app's progress bars (the accent on a quiet track)."""

    def __init__(self):
        super().__init__()
        self.setFixedHeight(4)
        self.frac = 0.0

    def paintEvent(self, _e):
        t = theme.tokens()
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(t["track"]))
        p.drawRoundedRect(QRectF(self.rect()), 2, 2)
        p.setBrush(QColor(t["accent"]))
        p.drawRoundedRect(QRectF(0, 0, self.width() * self.frac, self.height()), 2, 2)


class _Count(QToolButton):
    """The card's step list button (#tourCount): the chapter and the step (e.g. "1 · Select  ·  3 of 31"), then
    Windows 11's chevron at its right, as a drop-down has it. The chevron is the theme's own picture, which
    theme_sheet's guide_and_help gives the button as its icon, with 26 px of padding at its right for it: the chevron
    (12 px) 8 px from the edge, 6 px after the words. The style draws the words (it would put an icon before them),
    this the chevron after them."""

    def __init__(self):
        super().__init__()
        self.setToolButtonStyle(Qt.ToolButtonTextOnly)

    def paintEvent(self, e):
        super().paintEvent(e)
        icon = self.icon()
        if icon.isNull():
            return
        p = QPainter(self)
        icon.paint(p, QRect(self.width() - 8 - 12, (self.height() - 12) // 2, 12, 12))
        p.end()


class _SubRow(QLabel):
    """A menu's row that opens a submenu, in a Mock: its words, and Windows 11's chevron pointing right 8 px from its
    right edge, in the room a menu's row keeps there, as a real menu's (the theme's own picture: #tourMockArrow)."""

    def __init__(self, text):
        super().__init__(text)
        self.arrow = QLabel(self)
        self.arrow.setObjectName("tourMockArrow")
        self.arrow.setFixedSize(12, 12)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self.arrow.move(self.width() - 8 - 12, (self.height() - 12) // 2)


class Mock(QFrame):
    """A list as the app would open it, drawn inside the tour, looking as the real one does (#tourMock in
    theme_sheet.py): a drop-down's list (kind "list") opens with its chosen row marked as the real list marks it, the
    quiet fill and the accent's bar beside it, and the mark follows the pointer down the rows as the real one's does
    (hover); a long list (search: its box's grey words) has its search box above its rows, as the real one (typed:
    the words typed in it, in the text's colour, the rows those left); a menu (kind "menu") marks only the row pointed
    at, filled, and a row whose words end in " ▸" opens a submenu: Windows 11's chevron at its right, as a real
    menu's."""

    def __init__(self, tour, items, current=-1, width=None, kind="list", search=None, typed=False):
        super().__init__(tour)
        self.setObjectName("tourMock")
        self.setProperty("kind", kind)
        v = QVBoxLayout(self)
        m = 6 if search else 4  # (as the real lists: the long one's, the short one's and a menu's)
        v.setContentsMargins(m, m, m, m)
        v.setSpacing(0)
        if search:
            box = QLabel(search)
            box.setObjectName("tourMockSearch")
            box.setProperty("typed", typed)  # (typed words, in the text's colour; else the box's grey hint)
            v.addWidget(box)
            v.addSpacing(4)
        self.rows = []
        for it in items:
            if it is None:
                sep = QFrame()
                sep.setObjectName("tourSep")
                v.addWidget(sep)
                self.rows.append(sep)
                continue
            text, on = (it, True) if isinstance(it, str) else it
            lab = _SubRow(text[:-2]) if kind == "menu" and text.endswith(" ▸") else QLabel(text)
            lab.setProperty("off", not on)
            v.addWidget(lab)
            self.rows.append(lab)
        if width:  # (at least as wide as its box; wider when a row's words need it, as the real list)
            self.setMinimumWidth(width)
        self.ensurePolished()  # (its rows measured in their own look, their padding: they're polished with it)
        self.adjustSize()
        self.hover(current if kind == "list" else -1)

    def row(self, i):
        return self.rows[i] if 0 <= i < len(self.rows) else None

    def hover(self, i):
        for k, r in enumerate(self.rows):
            if isinstance(r, QLabel) and bool(r.property("hover")) != (k == i):
                r.setProperty("hover", k == i)
                r.style().unpolish(r)
                r.style().polish(r)


class _Note(QLabel):
    """A message as the app would show it (#tourNote), or a key cap (#tourKey), drawn inside the tour."""

    def __init__(self, tour, text, key=False):
        super().__init__(text, tour)
        self.setObjectName("tourKey" if key else "tourNote")
        self.setWordWrap(not key)
        self.setMaximumWidth(320)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        # (measured in its own look: before it's styled, its font is smaller and its padding none, and a message came
        # out 16 px tall, its words hidden, 2026-10-23)
        self.ensurePolished()
        if key:
            self.adjustSize()
        else:  # (as wide as its words, up to 320 px, then wrapped: a wrapped label alone sizes itself too narrow)
            m = self.contentsMargins()
            longest = max(self.fontMetrics().horizontalAdvance(line) for line in (text or ' ').splitlines())
            w = min(320, longest + m.left() + m.right() + 4)
            self.setFixedWidth(w)
            self.setFixedHeight(self.heightForWidth(w))


# ---------------------------------------------------------------- what a demo's own moves can use
class Api:
    """For a demo's own moves (run, or then(api)): generators to yield from (move, ripple, sleep, tween, note, key)
    and helpers; every change made through it is undone when the demo ends."""

    def __init__(self, tour):
        self.t = tour

    # timing and the pointer
    def sleep(self, ms):
        yield ms

    def pt(self, w, fx=0.5, fy=0.5):
        return self.t._point(w, fx, fy)

    def move(self, to, ms=650, also=None):
        if to is not None:
            yield from self.t._move(QPointF(to), ms, also)

    def move_to(self, w, fx=0.5, fy=0.5, ms=650):
        yield from self.move(self.pt(w, fx, fy), ms)

    def ripple(self):
        yield from self.t._click_ripple()

    def tween(self, ms, fn):
        t = self.t
        frames = max(1, round(ms / t.speed / 16)) if t.glide else 1
        for n in range(1, frames + 1):
            p = n / frames
            fn(2 * p * p if p < 0.5 else 1 - (-2 * p + 2) ** 2 / 2)
            t.update()
            yield 16 * t.speed

    def at(self, w, fx=0.5, fy=0.5, hold=700, say=None):
        if say is not None:
            self.say(say)
        p = self.pt(w, fx, fy)
        if p is None:
            yield hold
            return
        yield from self.move(p)
        self.hot(w)
        yield hold
        self.hot(None)

    def click(self, w, fx=0.5, fy=0.5, hold=300):
        p = self.pt(w, fx, fy)
        if p is None:
            yield hold
            return
        yield from self.move(p)
        self.hot(w)
        yield from self.ripple()
        yield hold
        self.hot(None)

    def type(self, w, text, keep=False, hold=500, fx=0.25):
        p = self.pt(w, fx, 0.5)
        if p is None:
            yield hold
            return
        yield from self.move(p)
        yield from self.ripple()
        entry = [w, ""]
        self.t.typed.append(entry)
        for n in range(1, len(text) + 1):
            entry[1] = text[:n]
            self.t.update()
            yield 75
        yield hold
        if not keep:
            self.t.typed.remove(entry)
            self.t.update()

    def untype(self, w):
        """The text a demo typed (kept) over the field w taken away: the field shows its own value again, as the
        demo's change went back."""
        self.t.typed = [e for e in self.t.typed if e[0] is not w]
        self.t.update()

    def say(self, text):
        self.t.say = text or ""
        self.t.update()

    def hot(self, w):
        self.t.hot_w = w
        self.t.update()

    # the spotlight and the card
    def spot_on(self, *ws):
        self.t.spot_on(*ws)

    def spot_to(self, *ws):
        self.t.spot_to(*ws)

    def keep_clear(self, w):
        self.t.keep_clear(w)

    def undo(self, fn):
        self.t.undos.append(fn)

    # messages
    def note(self, text, near=None, hold=1400, below=True):
        n = self.t.note(text, near, below)
        yield hold
        self.t.drop(n)

    def key(self, text, hold=900):
        """A key cap beside the pointer's "demo" tag (under it, the tag hid the key's name), taken away with the demo
        if it stops meanwhile (it stayed on the window for the rest of the tour, 2026-10-23)."""
        n = _Note(self.t, text, key=True)
        tag = self.t.tag_rect() if self.t.cur is not None else None
        if tag is not None:
            n.move(int(tag.right() + 6), int(tag.center().y() - n.height() / 2))
        else:
            n.move(int(self.t.width() / 2), int(self.t.height() / 2))
        n.show()
        self.t.inside.append(n)
        self.t.raise_layer()
        yield hold
        self.t.drop(n)

    # staging the window (put back when the demo ends, unless the app changed it again meanwhile)
    def stage(self, get, put, value):
        old = get()
        put(value)
        now = get()
        self.undo(lambda: get() == now and put(old))

    def stage_text(self, w, text):
        self.stage(w.text, w.setText, text)

    def stage_visible(self, w, on):
        old = not w.isHidden()
        w.setVisible(on)
        self.undo(lambda: w.setVisible(old))

    def stage_enabled(self, w, on):
        self.stage(w.isEnabled, w.setEnabled, on)

    def stage_blocked(self, get, put, value, w):
        """The same, the control's signals blocked: what it would show, nothing done."""
        from PySide6.QtCore import QSignalBlocker

        def quiet(v):
            with QSignalBlocker(w):
                put(v)
        self.stage(get, quiet, value)

    def stage_index(self, combo, i):
        self.stage_blocked(combo.currentIndex, combo.setCurrentIndex, i, combo)

    def stage_checked(self, box, on):
        self.stage_blocked(box.isChecked, box.setChecked, on, box)

    def stage_value(self, w, v):
        self.stage_blocked(w.value, w.setValue, v, w)

    # what the demo opens inside the tour
    def mock(self, near, items, current=-1, width=None, below=True, kind="list", search=None, typed=False):
        """A list as it would open just under (or over) a control (kind "list": a drop-down's, at least as wide as its
        box, as the real one; "menu": a menu's, as wide as its rows), its look the real one's (Mock; search: its search
        box's words, typed: typed in it); closed when the demo ends."""
        if width is None and kind == "list" and near is not None:
            width = near.width()
        m = Mock(self.t, items, current, width, kind, search, typed)
        self.t.show_inside(m, near, below, gap=2)
        return m

    def _frame(self, title):
        """A window's frame as the app's windows look inside the tour (#tourWin): its title bar (the title, the close
        symbol) over the window's background. (frame, the layout under the title bar)"""
        frame = QFrame(self.t)
        frame.setObjectName("tourWin")
        v = QVBoxLayout(frame)
        v.setContentsMargins(1, 1, 1, 6)  # (6 below: the window's square corners kept inside the frame's round ones)
        v.setSpacing(0)
        bar = QFrame()
        bar.setObjectName("tourWinBar")
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(12, 7, 10, 7)
        name = QLabel(title)
        name.setObjectName("tourWinTitle")
        bl.addWidget(name, 1)
        x = QLabel()
        x.setObjectName("tourWinClose")
        bl.addWidget(x)
        Tour.draw_close(x)
        v.addWidget(bar)
        return frame, v

    def prompt(self, title, label, near=None, value="", verb="OK"):
        """A question as the app would ask it (a name to type: a small window with its title, its buttons as
        window_parts.ask_text's: `verb` first, in the accent, then Cancel, sharing the width), inside the tour: .edit,
        .ok; closed after."""
        f, outer = self._frame(title)
        f.setProperty("prompt", True)
        v = placed(outer, QVBoxLayout())
        v.setContentsMargins(14, 4, 14, 8)
        v.setSpacing(8)
        v.addWidget(QLabel(label))
        f.edit = QLineEdit(value)
        v.addWidget(f.edit)
        row = placed(v, QHBoxLayout())
        f.ok = QPushButton(verb)
        theme.mark(f.ok, primary=True)
        row.addWidget(f.ok, 1)
        row.addWidget(QPushButton("Cancel"), 1)
        for c in [f] + f.findChildren(QWidget):
            c.setFocusPolicy(Qt.NoFocus)
        f.setFixedWidth(360)
        f.adjustSize()
        self.t.show_inside(f, near, True)
        return f

    def close(self, w):
        self.t.drop(getattr(w, "frame", None) or w)

    def window(self, w, near=None, size=None):
        """A window of the app (a QDialog made for the demo) shown inside the tour as a window: a frame with its title,
        only looked at (clicks stop at the glass over it, the keys stay with the tour), at the left with the card's
        room kept at the right, so the card is never over it. Its own smallest size doesn't hold here: it's as wide
        as its frame, its parts shrinking into it (its lists scroll), and the frame is as tall as its parts need when
        the tour has the room; else (Other measurements of this model at the window's smallest size) the window keeps
        its height and scrolls inside its frame, what a demo points at scrolled into sight (2026-10-23: at Windows
        11's sizes Other measurements of this model was cut off at the right and the bottom, and at the window's
        smallest size the card covered Find… and History; squeezed into the frame, its words overlapped and its graph
        was a sliver). Parts that need more room later grow the frame, or the window scrolls in it (_refit). Closed
        when the demo ends; returns the dialog."""
        frame, v = self._frame(w.windowTitle())
        w.setMinimumSize(0, 0)  # (its own window's smallest size: the frame's room decides here)
        w.setParent(frame, Qt.Widget)
        w.setAutoFillBackground(True)
        for c in [frame, w] + w.findChildren(QWidget):
            c.setFocusPolicy(Qt.NoFocus)
        W, H = self.t.width(), self.t.height()
        hint = w.size() if size is None else size
        room = W - CARD_W - 48  # (the card beside it)
        side = room >= SIDE_MIN
        width = min(hint.width(), room if side else W - 40)
        frame.ensurePolished()
        bar = frame.findChild(QFrame, "tourWinBar")
        extra = bar.sizeHint().height() + 8  # (the title bar, the frame's border and its room below)
        need = _needed_height(w, width)
        height = min(max(hint.height(), need) + extra, H - 16)
        if need + extra > height:  # (no room for it in the tour: it scrolls inside its frame)
            v.addWidget(_scroll_holder(w), 1)
        else:
            v.addWidget(w, 1)
        QWidget.resize(frame, width, height)
        self.t.show_inside(frame, near, True, side=side)
        self.t.setFocus()
        w.frame = frame
        self._refit(frame, w)  # (laid out now: what's around it measured, not guessed, 1 px short before)
        _Grows(frame, lambda: self._refit(frame, w))
        return w

    def _refit(self, frame, w):
        """A demo's window whose parts came to need more room than its frame gives: the frame made taller, kept inside
        the tour; with no more room in the tour, the window scrolls inside it, as one that opened so does."""
        if not (_alive(frame) and _alive(w)) or not frame.isVisible() or w.parentWidget() is not frame:
            return  # (gone, or scrolling in its frame already: its scroll area follows by itself)
        t = self.t
        need = _needed_height(w, frame.width())
        if w.height() >= need:
            return
        around = frame.height() - w.height()  # (its title bar, the frame's border and its room below, as laid out)
        height = min(need + around, t.height() - 16)
        if need + around > height:
            lay = frame.layout()
            lay.removeWidget(w)
            lay.addWidget(_scroll_holder(w), 1)
        frame.setGeometry(frame.x(), max(8, min(frame.y(), t.height() - 8 - height)), frame.width(), height)
        t.follow(force=True)
        t.place_card()

    def scroll_to(self, w, ymargin=60):
        scroll_into_view(w, ymargin)
        self.t.follow(force=True)

    # the graph: kept in sight, curves drawn on it
    def pin_graph(self, page, keep=None):
        """The graph kept in sight at the top while the page scrolls under it to the control the demo is about
        (AutoEQ Local's pinned graph): a live picture of it, refreshed as the demo changes it. When the graph and
        the control both fit on screen as they are, the page only scrolls to show both."""
        t = self.t
        plot = page.plot
        if keep is not None:
            scroll_into_view(keep)
        t.follow(force=True)
        whole = lambda w: _rect(t.win, [w]).height() >= w.height() - 2
        if keep is None or (whole(plot) and _shown(keep) and whole(keep)):
            scroll_into_view(plot, 10)
            if keep is not None:
                scroll_into_view(keep)
            if whole(plot) and (keep is None or whole(keep)):
                t.spot_on(plot)
                yield 200
                return
        t.pin_graph(plot)
        if keep is not None:
            t.below_pin(keep)
        t.spot_on(t.pin)
        yield 250

    def curve(self, page, vals, colour, width=2.2, style=Qt.SolidLine, name=None):
        """A curve (absolute dB, on the graph's frequencies) drawn on the graph for the demo; taken off after."""
        import numpy as np
        import pyqtgraph as pg
        c = page.curves
        if not c:
            return None
        f = np.asarray(c["f"])
        item = page.plot.plot(f, self.on_graph(page, vals), pen=pg.mkPen(colour, width=width, style=style), name=name)

        def off():
            try:
                page.plot.removeItem(item)
                if name:
                    page.legend.removeItem(item)
            except (RuntimeError, ValueError, AttributeError):
                pass
        self.undo(off)
        return item

    @staticmethod
    def on_graph(page, vals):
        """Absolute dB as the graph draws them (relative to the target in the "Relative to target" view)."""
        import numpy as np
        v = np.asarray(vals, dtype=float)
        if (getattr(page, "_drawn", None) or {}).get("rel"):
            v = v - np.asarray(page.curves["target"], dtype=float)
        return v

    def morph(self, page, item, a, b, ms=1300):
        import numpy as np
        if item is None:
            yield ms
            return
        a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
        f = np.asarray(page.curves["f"])
        yield from self.tween(ms, lambda p: item.setData(f, self.on_graph(page, a + (b - a) * p)))


# ---------------------------------------------------------------- the step list
class _Steps(QFrame):
    """Every step, by chapter (the card's step button, #tourCount): click one to go straight to it (Play all steps is
    then cleared). It opens as a menu does (#tourSteps), as wide as its longest step (up to the window's width) and as
    tall as its rows, with Play all steps and the demos' speed at its foot: under the step button, or above it when
    there is more room there, and never past the window's edges (its rows scroll; the foot stays in sight)."""

    def __init__(self, tour):
        super().__init__(tour)
        self.tour = tour
        self.setObjectName("tourSteps")
        v = QVBoxLayout(self)
        v.setContentsMargins(4, 4, 4, 4)
        self.list = QListWidget()
        self.list.setAccessibleName("Steps")
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list.itemActivated.connect(self._chosen)
        self.list.itemClicked.connect(self._chosen)
        v.addWidget(self.list)
        # (Play all steps and the demos' speed at the list's foot: they change the step, as the list does, and the card
        # has one row less on each step with a demo. The UI audit, 2026-11-08)
        tour.play_opts.setParent(self)
        v.addWidget(tour.play_opts)
        self.hide()

    def open(self):
        tr, t = self.tour, theme.tokens()
        self.list.clear()
        self.list.ensurePolished()
        base = QFont(self.list.font())  # (the list's own font: an item's font() is the app's smaller default)
        ch = None
        now = None
        for i, s in enumerate(tr.steps):
            if s.get("chapter") != ch:
                ch = s.get("chapter")
                # (a chapter's heading as Windows 11's group headings and Find…'s: its words as written, semibold)
                h = QListWidgetItem(ch or "")
                h.setFlags(Qt.NoItemFlags)
                f = QFont(base)
                f.setWeight(QFont.Weight.DemiBold)
                h.setFont(f)
                h.setForeground(QColor(t["ink"]))  # (not the greyed colour of a row that can't be chosen)
                self.list.addItem(h)
            ok = tr.available(i)
            it = QListWidgetItem(f"{i + 1:>2}   {_val(s['title'])}" + ("   · demo" if s.get("demo") or s.get("alt_demo") else ""))
            it.setData(Qt.UserRole, i)
            if not ok:
                it.setForeground(QColor(t["muted"]))
                it.setToolTip("Its control is not on the screen (for example, there is no result): the next available step "
                              "opens")
            if i == tr.i:
                f = QFont(base)
                f.setBold(True)
                it.setFont(f)
                now = it
            self.list.addItem(it)
        b = tr.bubble.geometry()
        btn = tr.count_btn.geometry()
        rows = sum(max(self.list.sizeHintForRow(k), 1) for k in range(self.list.count()))
        foot = tr.play_opts.sizeHint().height() + self.layout().spacing()
        want = rows + 12 + foot
        # (under the step button; above it when the card is low and there is more room there. Always inside the
        # window, its rows scrolling: with the card low in a 600 px window, its foot was cut off, 2026-11-10)
        below_top = b.top() + btn.bottom() + 16
        room_below = tr.height() - 8 - below_top
        above_bottom = b.top() + btn.top() - 4
        room_above = above_bottom - 8
        if want <= room_below or room_below >= room_above:
            h = max(1, min(want, room_below, tr.height() - 16))
            top = below_top
        else:
            h = max(1, min(want, room_above, tr.height() - 16))
            top = above_bottom - h
        top = max(8, min(top, tr.height() - 8 - h))
        # (its longest step in sight: the list's room is its width less the frame, the row's padding and the scroll bar)
        widest = max([QFontMetrics(self.list.item(k).font() if self.list.item(k).data(Qt.FontRole) is not None
                                   else base).horizontalAdvance(self.list.item(k).text())
                      for k in range(self.list.count())] or [0])
        w = min(max(b.width() - 16, widest + 60), tr.width() - 16)
        x = max(8, min(b.left() + 8, tr.width() - w - 8))
        self.setGeometry(x, top, w, h)
        self.show()
        self.raise_()
        tr.layer.raise_()
        tr.layer.update()  # (a marker under the list isn't drawn: all of the layer, not only the list's part of it)
        if now is not None:
            self.list.setCurrentItem(now)
            self.list.scrollToItem(now, QListWidget.PositionAtCenter)  # (the steps before and after it in sight)
        self.list.setFocus()

    def close_list(self):
        if self.isVisible():
            self.hide()
            self.tour.layer.update()  # (the markers that were under the list)
            self.tour.setFocus()

    def _chosen(self, it):
        i = it.data(Qt.UserRole)
        if i is None:
            return
        self.close_list()
        self.tour.all_chk.setChecked(False)
        self.tour.go_to_step(i)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.close_list()
            return
        super().keyPressEvent(e)


# ---------------------------------------------------------------- the tour
class Tour(QWidget):
    def __init__(self, host, steps, on_end=None, start=0, had_focus=None):
        """had_focus: the control with the focus before the Guide (the focus goes back to it at the end, end_focus);
        None: the window's control with the focus now."""
        win = host.window()
        had_focus = had_focus if had_focus is not None else win.focusWidget()
        super().__init__(win)
        self.win, self.steps, self.on_end = win, steps, on_end
        self.host, self.had_focus = host, had_focus
        self.i, self.alt = -1, False
        self.target = None
        self.spots, self.holes, self.avoid = [], [], []   # lit widgets, their rectangles; what the card keeps off
        self.inside = []           # what the demo shows inside the tour (lists, windows, notes)
        # the demo: its actions run one by one (a generator: each yield is how long to wait, in the demo's ms)
        self.gen, self.undos, self.demo_running, self.paused, self.paused_by_you = None, [], False, False, False
        self.demo_errors = []      # "step title: error" for each demo that ended on an error (the checks read it)
        self.scrolled = {}         # paused by your scrolling: where every scrolling part was, for Continue
        self.cur = None            # the pointer (in the window), or None before a demo
        self.hot_w = None          # the control the pointer is on (ringed)
        self.ripple = None         # (x, y, 0-1)
        self.trail = None          # (from QPointF, to QPointF)
        self.typed = []            # [[control, text]]: text drawn over a field
        self.markers = []          # [(control, x, y, n)]: the demo's actions with animation effects off
        self.marks_seen = ([], [])  # the markers in sight and the ones drawn, as follow() last saw them
        self.file_chip = None      # [QPointF, name]: a file being dragged in
        self.acts, self.act_now = [], -1
        self.say = ""
        self.pin = self.pin_src = None
        self.speed = _kept["speed"]
        self.glide = _animations_on()
        self.timer = QTimer(self, singleShot=True)
        self.timer.timeout.connect(self._tick)
        self.next_timer = QTimer(self, singleShot=True)  # (Play all steps: the next step)
        self.next_timer.timeout.connect(self._auto_next)
        self.follow_timer = QTimer(self, interval=150, timeout=self.follow)  # (the spotlight keeps to what it lights)
        self.card_timer = QTimer(self, singleShot=True, interval=120, timeout=self.place_card)
        self.pin_timer = QTimer(self, interval=120, timeout=self._pin_refresh)
        self.setFocusPolicy(Qt.StrongFocus)
        self._build_card()
        if not _themed["hooked"]:  # (once: every tour open drawn again when the theme changes)
            _themed["hooked"] = True
            theme.on_change(_retheme)
        _themed["tours"].append(weakref.ref(self))
        self.glass = _Glass(self)
        self.glass.hide()
        self.step_list = _Steps(self)
        self.layer = _Layer(self)
        self.follow_obj = _Follow(self)
        win.installEventFilter(self.follow_obj)
        self.setGeometry(win.rect())
        self.show()
        self.raise_()
        self.setFocus()
        from PySide6.QtWidgets import QApplication
        QApplication.instance().focusChanged.connect(self._keep_focus)
        self.follow_timer.start()
        self.go_to_step(start)

    def _build_card(self):
        self.bubble = QFrame(self)
        self.bubble.setObjectName("tourCard")  # (its look: theme_sheet.py's guide_and_help, by these names)
        theme.mark(self.bubble, card=True)
        self.bubble.setFixedWidth(CARD_W)
        b = QVBoxLayout(self.bubble)
        b.setContentsMargins(16, 12, 16, 14)
        b.setSpacing(4)
        top = placed(b, QHBoxLayout())
        self.count_btn = _Count()
        self.count_btn.setObjectName("tourCount")
        self.count_btn.setToolTip("Go to a step")
        self.count_btn.setAccessibleName("Steps")
        self.count_btn.clicked.connect(self._toggle_list)
        top.addWidget(self.count_btn)
        top.addStretch(1)
        # (✕ at the top right closes the Guide, as Windows 11's teaching tips (Esc too): the UI audit, 2026-11-08)
        self.end_btn = QToolButton()
        self.end_btn.setText("✕")
        self.end_btn.setToolTip("Close the Guide (Esc)")
        self.end_btn.setAccessibleName("Close the Guide")
        theme.mark(self.end_btn, quiet=True)
        self.end_btn.clicked.connect(self.end)
        top.addWidget(self.end_btn, 0, Qt.AlignTop)
        b.addSpacing(2)
        self.bar = _Bar()
        b.addWidget(self.bar)
        self.badge = QLabel("Demo · your work does not change")
        self.badge.setObjectName("tourBadge")  # (gray words: theme_sheet's guide_and_help)
        b.addWidget(self.badge)
        b.addSpacing(4)
        self.chapter = self.count_btn  # (an older name: nothing reads it now)
        self.title = QLabel()
        self.title.setObjectName("tourTitle")
        self.title.setWordWrap(True)
        b.addWidget(self.title)
        self.text = QLabel()
        self.text.setWordWrap(True)
        b.addWidget(self.text)
        self.acts_lab = QLabel()
        self.acts_lab.setWordWrap(True)
        self.acts_lab.setTextFormat(Qt.RichText)
        b.addWidget(self.acts_lab)
        self.steps_list = self.acts_lab  # (an older name: nothing reads it now)
        # (the demo's controls in one box, hidden on a step without a demo: the row of buttons was put in the card
        # first, so Qt kept it out of the box, and Play demo showed on the tracer's steps that have none, doing
        # nothing, 2026-10-23; the rows as far apart as they were)
        self.demo_box = QWidget()
        dv = QVBoxLayout(self.demo_box)
        dv.setContentsMargins(0, 0, 0, 0)
        dv.setSpacing(6)
        b.addWidget(self.demo_box)
        demo_row = placed(dv, QHBoxLayout())
        self.replay_btn = QPushButton("Play demo")
        _set_symbol(self.replay_btn, "play")
        self.replay_btn.setToolTip("Play this step's demo again (R)")
        self.replay_btn.clicked.connect(self.replay)
        demo_row.addWidget(self.replay_btn)
        self.pause_btn = QPushButton("Wait")
        _set_symbol(self.pause_btn, "pause")
        self.pause_btn.setToolTip("Wait or continue the demo (P)")
        self.pause_btn.clicked.connect(self.toggle_pause)
        demo_row.addWidget(self.pause_btn)
        self.skip_btn = QPushButton("Complete the demo")
        theme.mark(self.skip_btn, link=True)
        self.skip_btn.clicked.connect(self.skip_demo)
        demo_row.addWidget(self.skip_btn)
        demo_row.addStretch(1)
        self.play_opts = QWidget()  # (put in the step list's foot: _Steps)
        opts = QHBoxLayout(self.play_opts)
        opts.setContentsMargins(8, 4, 8, 4)
        self.all_chk = QCheckBox("Play all steps")
        self.all_chk.setToolTip("The Guide plays the demo of each step and then goes to the next step automatically")
        self.all_chk.setChecked(_kept["all"])
        self.all_chk.toggled.connect(self._set_play_all)
        opts.addWidget(self.all_chk)
        opts.addStretch(1)
        sp = QLabel("Speed")
        theme.mark(sp, role="muted")
        opts.addWidget(sp)
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(0, len(SPEEDS) - 1)
        self.speed_slider.setFixedWidth(90)
        self.speed_slider.setAccessibleName("Demo speed")
        self.speed_slider.setToolTip("The speed of the demos")
        self.speed_slider.setValue(min(range(len(SPEEDS)), key=lambda k: abs(SPEEDS[k] - self.speed)))
        self.speed_slider.valueChanged.connect(self._set_speed)
        opts.addWidget(self.speed_slider)
        self.speed_lab = QLabel()
        self.speed_lab.setMinimumWidth(26)
        opts.addWidget(self.speed_lab)
        self._show_speed()
        self.extra = placed(b, QHBoxLayout())
        row = placed(b, QHBoxLayout())
        row.addStretch(1)
        self.again_btn = QPushButton("Start again")
        self.again_btn.clicked.connect(lambda: self.go_to_step(0))
        row.addWidget(self.again_btn)
        self.back_btn = QPushButton("Back")
        self.back_btn.clicked.connect(lambda: self.go_to_step(self.i - 1))
        self.next_btn = QPushButton("Next")
        theme.mark(self.next_btn, primary=True)
        self.next_btn.clicked.connect(lambda: self.go_to_step(self.i + 1) if self.i + 1 < len(self.steps) else self.end())
        for w in (self.end_btn, self.back_btn, self.next_btn, self.replay_btn, self.pause_btn, self.skip_btn,
                  self.all_chk, self.speed_slider, self.again_btn, self.count_btn):
            w.setFocusPolicy(Qt.NoFocus)
        row.addWidget(self.back_btn)
        row.addWidget(self.next_btn)

    @staticmethod
    def draw_close(label):
        """The close symbol of a window's title bar shown inside the tour (Windows 11's title bars' own, 10 px), in
        the theme's quieter text colour."""
        label.setPixmap(icons.glyph("chrome_close", theme.tokens()["ink2"], size=10).pixmap(QSize(16, 10)))

    def retheme(self):
        """The theme changed while the tour is open: what it draws in its own colours drawn again (the card's
        symbols, the demo's actions, a window's close symbol; the rest follows the stylesheet or is drawn afresh)."""
        for btn in self.bubble.findChildren(QPushButton):
            if btn.property("symbol"):
                _set_symbol(btn, btn.property("symbol"))
        for x in self.findChildren(QLabel, "tourWinClose"):
            Tour.draw_close(x)
        self.step_list.close_list()
        self._show_acts()
        self.update()

    # ---------------------------------------------------------------- the steps
    def available(self, k):
        s = self.steps[k]
        if s.get("ready"):
            try:
                return bool(s["ready"]())
            except (RuntimeError, AttributeError, KeyError):
                return False
        return True

    def _leave_step(self):
        self.stop_demo()
        self.next_timer.stop()
        self.step_list.close_list()
        if 0 <= self.i < len(self.steps) and self.steps[self.i].get("after"):
            self.steps[self.i]["after"]()

    def _prepare(self, k):
        """Step k shown if its control (or its stand-in) is on screen: its before run; else put back, False."""
        st = self.steps[k]
        if st.get("before"):
            st["before"]()
        # (a fold opened or closed, by this step or the one before, a list filled: the page laid out again before it's
        # measured and scrolled. Not yet settled, at the window's smallest size a step scrolled the page past a card
        # that wasn't in sight, 2026-10-23)
        _settle()
        ws = _shown(st.get("target") and st["target"]())
        alt = False
        if not ws and st.get("alt"):
            ws, alt = _shown(st["alt"]()), True
        if ws:
            self.target, self.alt = ws, alt
            return True
        if st.get("after"):
            st["after"]()
        return False

    def go_to_step(self, i):
        if not 0 <= i < len(self.steps):
            return
        d = 1 if i >= self.i else -1
        self._leave_step()
        k = i
        while 0 <= k < len(self.steps) and not self._prepare(k):
            k += d
        if not 0 <= k < len(self.steps):  # (none that way: the nearest the other way)
            k = i - d
            while 0 <= k < len(self.steps) and not self._prepare(k):
                k -= d
            if not 0 <= k < len(self.steps):
                self.end()
                return
        self.i = i = k
        st = self.steps[i]
        from PySide6.QtWidgets import QApplication
        scroll_all_into_view(self.target)
        QApplication.processEvents()
        self.spots = list(self.target)
        self.avoid = []
        text = _val(st["alt_text"] if self.alt and st.get("alt_text") else st["text"])
        self.count_btn.setText(((f"{st['chapter']}  ·  " if st.get("chapter") else "") + f"{i + 1} of {len(self.steps)}")
                               .replace("&", "&&"))  # (a button's & marks its shortcut: shown as one; its chevron: _Count)
        self.badge.setText("Demo · your work does not change")
        self.badge.setToolTip("A demo: it does not change your work")
        self.bar.frac = (i + 1) / len(self.steps)
        self.bar.update()
        self.title.setText(_val(st["title"]))
        self.text.setText(text)
        self.back_btn.setEnabled(i > 0)
        last = i == len(self.steps) - 1
        self.next_btn.setText("Done" if last else "Next")
        self.again_btn.setVisible(last)
        while self.extra.count():
            w = self.extra.takeAt(0).widget()
            if w is not None:
                w.hide()  # (out of sight now: deleteLater waits for the event loop, and it stayed under the card)
                w.deleteLater()
        for label, fn in st.get("buttons") or []:
            b = QPushButton(label)
            b.setFocusPolicy(Qt.NoFocus)
            b.clicked.connect(lambda _=False, fn=fn: (self.end(), fn()))
            self.extra.addWidget(b)
            b.show()  # (now, not when Qt gets to it: the card's height counts its row. It went past the card's foot)
        if st.get("buttons"):
            self.extra.addStretch(1)
        actions = demo_actions(st, self.alt)
        self.acts = [_val(a.get("say", "")) for a in actions if a.get("say")]
        self.act_now = -1
        has_demo = bool(actions)
        self.demo_box.setVisible(has_demo)
        self.badge.setVisible(has_demo)
        self._show_demo_state(False)
        self.holes = self._holes()
        self.place(move_card=True)
        self.setFocus()
        if has_demo:
            QTimer.singleShot(int(450 / self.speed), self, lambda n=i: self.i == n and not self.demo_running
                              and self.isVisible() and self.replay())
        elif self.all_chk.isChecked():
            self._schedule_next()

    def _show_demo_state(self, playing):
        """The card's demo row and actions list as the demo is (playing: only the action playing now)."""
        self.replay_btn.setText("Show the steps" if not self.glide else "Play again" if playing else "Play demo")
        _set_symbol(self.replay_btn, "list" if not self.glide else "refresh" if playing else "play")
        self.pause_btn.setVisible(playing and self.glide)
        self.skip_btn.setVisible(playing)
        if not playing:
            self.paused = self.paused_by_you = False
            self._pause_label("Wait")
        self._show_acts()

    def _pause_label(self, text, tip="Wait or continue the demo (P)"):
        """Wait, or Continue (paused): its words, symbol and tooltip."""
        self.pause_btn.setText(text)
        self.pause_btn.setToolTip(tip)
        _set_symbol(self.pause_btn, "pause" if text == "Wait" else "play")

    def _show_acts(self):
        """The demo's actions, numbered, in the card (while it plays, only the one playing now: on a quiet fill with
        the accent's bar beside it, as Windows 11 marks a chosen row)."""
        t = theme.tokens()
        playing = self.demo_running and self.glide
        rows = []
        for n, text in enumerate(self.acts):
            if playing and n != self.act_now:
                continue
            esc = text.replace("&", "&amp;").replace("<", "&lt;")
            if n == self.act_now:
                rows.append(f"<table width='100%' cellspacing='0' cellpadding='0'><tr>"
                            f"<td width='3' style='background:{t['accent']}'></td>"
                            f"<td style='background:{t['sel']}; color:{t['sel_ink']}; font-weight:600; padding: 3px 6px'>"
                            f"{n + 1}.&nbsp;{esc}</td></tr></table>")
            else:
                rows.append(f"<div style='color:{t['ink2']}'>&nbsp;{n + 1}.&nbsp;{esc}</div>")
        self.acts_lab.setText("".join(rows))
        self.acts_lab.setVisible(bool(rows) and (not self.glide or playing or not self.demo_running))
        self._fit_card()

    def _fit_card(self):
        lay = self.bubble.layout()
        lay.activate()
        self.bubble.resize(CARD_W, lay.totalHeightForWidth(CARD_W))
        lay.activate()

    # ---------------------------------------------------------------- the spotlight
    def _holes(self):
        """The lit rectangles (padded, in the window); ones that overlap are drawn as one shape (paintEvent), not as
        the box around both, and two that touch or overlap edge to edge (one over the other, as wide as each other; or
        side by side, as tall) are one rectangle: drawn as two, their round corners met in a notch on both sides
        (step 1's Target and Measurement cards, 2026-10-23)."""
        out = []
        for w in _shown(self.spots):
            r = self._w_rect(w).toRect().adjusted(-PAD, -PAD, PAD, PAD).intersected(self.rect().adjusted(2, 2, -2, -2))
            if r.width() > 4 and r.height() > 4 and not any(h.contains(r) for h in out):
                out = [h for h in out if not r.contains(h)] + [r]
        return _joined(out)

    def spot_on(self, *ws):
        """During a demo: the spotlight over more at once (e.g. a field and the list it opened)."""
        self.spots += [w for w in ws if w is not None and w not in self.spots]
        self.follow(force=True)

    def spot_to(self, *ws):
        self.spots = [w for w in ws if w is not None]
        self.follow(force=True)

    def keep_clear(self, w):
        self.avoid.append(w)
        self.card_timer.start()

    def follow(self, force=False):
        """The lit parts measured again: what they light moved or changed size (a list filled, the page scrolled).
        The markers too: they can move while the lit rectangles stay as they are (what is lit is out of sight), and
        which of them are drawn changes when the card or the step list moves."""
        if not self.isVisible() and not force:
            return
        hs = self._holes()
        spots = self._marker_spots() if self.markers else []
        seen = ([(p.x(), p.y(), n) for p, n in spots], [n for _p, n in self.marker_points(spots)])
        moved = force or [h.getRect() for h in hs] != [h.getRect() for h in self.holes] or seen[0] != self.marks_seen[0]
        if moved or seen != self.marks_seen:
            self.holes = hs
            self.marks_seen = seen
            self.update()
        if moved:  # (not for the markers drawn alone: placing the card closes the step list, which hides markers)
            self.card_timer.start()

    def place(self, move_card=False):
        """The overlay over the whole window; the card where it covers least."""
        self.setGeometry(self.win.rect())
        self.raise_()
        # (the window resized mid-demo: the kept graph picture laid out again for it, what the demo shows kept inside)
        pin, src = getattr(self, "pin", None), getattr(self, "pin_src", None)
        if pin is not None and src is not None and _alive(pin) and _alive(src):
            pin.setGeometry(self._pin_rect(src))
            self._pin_refresh()
        shown = [pin] + list(getattr(self, "inside", []))
        for w in [x for x in shown if isinstance(x, QWidget) and _alive(x)]:
            g, r = w.geometry(), self.rect().adjusted(8, 8, -8, -8)
            if not r.contains(g):
                ww, wh = min(g.width(), r.width()), min(g.height(), r.height())
                w.setGeometry(max(r.left(), min(g.left(), r.right() - ww)), max(r.top(), min(g.top(), r.bottom() - wh)),
                              ww, wh)
        self.holes = self._holes()
        self.glass.setGeometry(self.rect())
        self._fit_card()
        self.place_card(stay=not move_card)
        self.raise_layer()
        self.update()

    def raise_layer(self):
        self.glass.raise_()
        self.bubble.raise_()
        if self.step_list.isVisible():
            self.step_list.raise_()
        self.layer.setGeometry(self.rect())
        self.layer.raise_()

    def _avoid_rects(self):
        """What the card keeps off, [(rectangle, weight)]: what the demo uses, then the step's own ("avoid"), the last
        of them ×8; a window the demo shows ×8 too (the card beside it, never over it: room kept for the pointer later
        could take the card over the window); the rest ×1."""
        out = []
        for a in self.avoid:
            if isinstance(a, QRect):
                out.append((a, 1))
            elif isinstance(a, QWidget) and _alive(a) and a.isVisible():
                window = a.parentWidget() is self and a.objectName() == "tourWin"
                out.append((a.geometry() if a.parentWidget() is self else _rect(self.win, [a]), 8 if window else 1))
        st = self.steps[self.i] if 0 <= self.i < len(self.steps) else {}
        if st.get("avoid"):
            out += [(_rect(self.win, [w]), 1) for w in _shown(st["avoid"]())]
        if out:
            out[-1] = (out[-1][0], 8)
        return out

    def place_card(self, stay=True):
        """The card where it covers least of what's lit (×3), what the demo uses (the last ×8, a window it shows ×8,
        others ×1) and the pointer (×4): beside, under or over each lit part, then around the window's edges; it stays
        where it is while that's as good. While markers show, the card first covers as few of them as it can, then
        least of the rest (a marker under the card isn't drawn: marker_points), and it also tries the places beside,
        under and over each marker (2026-11-22: the card kept off the lit part only, and markers were drawn on
        it)."""
        if not hasattr(self, "bubble"):
            return
        bw, bh, W, H, m, gap = self.bubble.width(), self.bubble.height(), self.width(), self.height(), 8, 14
        fit = lambda x, y: QRect(int(max(m, min(x, W - bw - m))), int(max(m, min(y, H - bh - m))), bw, bh)
        lit, avoid = self.holes, self._avoid_rects()
        cur = QRect(int(self.cur.x()) - 12, int(self.cur.y()) - 10, 76, 52) if self.cur is not None and self.demo_running else None
        marks = [self._disc(pt, MARK_GAP).toAlignedRect() for pt, _n in self._marker_spots()] if self.markers else []

        def cost(r):
            c = sum(_overlap(r, h) * 3 for h in lit)
            c += sum(_overlap(r, a) * k for a, k in avoid)
            c += sum(MARK_COST for mk in marks if r.intersects(mk))
            return c + (_overlap(r, cur) * 4 if cur is not None else 0)
        tries = []
        for h in lit:
            tries += [(h.right() + gap, h.top()), (h.left() - gap - bw, h.top()), (h.left(), h.bottom() + gap),
                      (h.left(), h.top() - gap - bh), (h.right() + gap, h.bottom() - bh), (h.left() - gap - bw, h.bottom() - bh)]
        edges_x = [m + (W - bw - 2 * m) * fx for fx in (1, 0, 0.5)]
        edges_y = [m + (H - bh - 2 * m) * fy for fy in (1, 0, 0.5)]
        tries += [(x, y) for y in edges_y for x in edges_x]
        for mk in marks:
            tries += [(x, y) for x in (mk.right() + 1, mk.left() - bw) for y in edges_y]
            tries += [(x, y) for y in (mk.bottom() + 1, mk.top() - bh) for x in edges_x]
        best, best_cost = None, None
        for x, y in tries:
            r = fit(x, y)
            c = cost(r)
            if best is None or c < best_cost:
                best, best_cost = r, c
            if c == 0:
                break
        if best is None:
            best = fit((W - bw) / 2, (H - bh) / 2)
            best_cost = cost(best)
        now = fit(self.bubble.x(), self.bubble.y())
        if stay and self.bubble.isVisible() and cost(now) <= best_cost:
            best = now
        self.bubble.move(best.topLeft())
        if self.step_list.isVisible():
            self.step_list.hide()
        if self.markers:  # (which markers are drawn goes with where the card is: all of the layer drawn again)
            self.layer.update()

    def update(self, *a):
        super().update(*a)
        if hasattr(self, "layer"):
            self.layer.update()

    # ---------------------------------------------------------------- inside the tour: lists, windows, notes
    def show_inside(self, w, near=None, below=True, side=False, gap=3):
        """A widget the demo shows (a list, a window), placed under (or over) a control with gap px between them, the
        card kept off it; side: a window at the left, the card's room at the right."""
        if w.parentWidget() is not self:
            w.setParent(self)
        w.adjustSize() if not w.width() or w.width() < 20 else None
        W, H = self.width(), self.height()
        ww, wh = w.width(), w.height()
        if side:
            x = 16
            if near is not None and _alive(near) and near.isVisible():
                r = _rect(self.win, [near])
                y = r.bottom() + 4 if H - r.bottom() - 10 >= wh else r.top() - 4 - wh
            else:
                y = (H - wh) // 2
            y = max(8, min(y, H - wh - 8))
        elif near is not None and _alive(near) and near.isVisible():
            r = _rect(self.win, [near])
            x = max(8, min(r.left(), W - ww - 8))
            room_below = H - r.bottom() - 10
            under, over = r.bottom() + 1 + gap, r.top() - gap - wh
            y = under if (below and room_below >= wh) or over < 8 else over
            if y + wh > H - 8:
                y = max(8, H - 8 - wh)
        else:
            x, y = (W - ww) // 2, (H - wh) // 2
        QWidget.move(w, int(x), int(y))  # (Qt's own: a window of the app may have a move() of its own, e.g. Find…'s)
        w.show()
        self.inside.append(w)
        self.glass.show()
        self.keep_clear(w)
        self.place_card()  # (off it at once: on its timer alone, the card showed over a window as it opened)
        self.raise_layer()
        self.update()

    def note(self, text, near=None, below=True):
        """A message under (below=False: over; "inside": in the top right corner of) a control."""
        n = _Note(self, text)
        W, H = self.width(), self.height()
        if near is not None and _alive(near) and near.isVisible():
            r = self._w_rect(near).toRect()
            x = max(8, min(r.left(), W - n.width() - 8))
            if below == "inside":
                x, y = r.right() - n.width() - 14, r.top() + 12  # (the graph's legend is at its top left)
            else:
                y = r.bottom() + 8 if below and r.bottom() + 8 + n.height() < H - 8 else max(8, r.top() - 8 - n.height())
        else:
            x, y = (W - n.width()) // 2, H - n.height() - 60
        n.move(int(x), int(y))
        n.show()
        self.inside.append(n)
        self.keep_clear(n)
        self.raise_layer()
        return n

    def drop(self, w):
        if w in self.inside:
            self.inside.remove(w)
        if w in self.avoid:
            self.avoid.remove(w)
        if w in self.spots:
            self.spots.remove(w)
        try:
            w.hide()
            w.deleteLater()
        except RuntimeError:
            pass
        if not any(isinstance(x, QWidget) and not isinstance(x, _Note) for x in self.inside):
            self.glass.hide()
        self.follow(force=True)

    def _pin_rect(self, plot):
        """Where the graph's picture goes: at the top of its scrolling page, as wide as it (again when the window is
        resized)."""
        area = next((p for p in self._ancestors(plot) if isinstance(p, QScrollArea)), None)
        vp = _rect(self.win, [area.viewport()]) if area is not None else self.rect()
        w = vp.width() - 24  # (as wide as the page: the graph's picture in the middle)
        h = int(min(plot.height() * w / max(1, plot.width()), self.height() * 0.42))
        return QRect(vp.left() + (vp.width() - w) // 2, vp.top() + 8, w, h)

    def pin_graph(self, plot):
        """The graph kept in sight: a live picture of it at the top of its scrolling page."""
        if self.pin is None:
            self.pin = QLabel(self)
            self.pin.setObjectName("tourPin")  # (its look: theme_sheet.py, #tourPin)
            self.pin.setAlignment(Qt.AlignCenter)
            self.pin.setGeometry(self._pin_rect(plot))
            self.pin_src = plot
            self.pin.show()
            self._pin_refresh()
            self.pin_timer.start()
            self.undos.append(self._unpin)
            self.raise_layer()

    def _unpin(self):
        self.pin_timer.stop()
        if self.pin is not None:
            if self.pin in self.spots:
                self.spots.remove(self.pin)
            self.pin.hide()
            self.pin.deleteLater()
        self.pin = self.pin_src = None

    def _pin_refresh(self):
        if self.pin is None or self.pin_src is None or not _alive(self.pin_src):
            return
        pm = self.pin_src.grab()
        self.pin.setPixmap(pm.scaled(self.pin.size().shrunkBy(QMargins(2, 2, 2, 2)), Qt.KeepAspectRatio,
                                     Qt.SmoothTransformation))

    def below_pin(self, w):
        """The page scrolled so the control is in sight under the kept graph."""
        area = next((p for p in self._ancestors(w) if isinstance(p, QScrollArea)), None)
        if area is None or self.pin is None:
            return
        content = area.widget()
        y = w.mapTo(content, QPoint(0, 0)).y()
        vp_top = _rect(self.win, [area.viewport()]).top()
        want = self.pin.geometry().bottom() + 14 - vp_top  # (its top, in the viewport)
        bar = area.verticalScrollBar()
        bar.setValue(max(bar.minimum(), min(bar.maximum(), y - want)))
        self.follow(force=True)

    @staticmethod
    def _ancestors(w):
        p = w.parentWidget()
        while p is not None:
            yield p
            p = p.parentWidget()

    # ---------------------------------------------------------------- the demo
    def _show_speed(self):
        s = SPEEDS[self.speed_slider.value()]
        self.speed_lab.setText({0.25: "¼×", 0.5: "½×"}.get(s, f"{s:g}×"))

    def _set_speed(self, k):
        self.speed = _kept["speed"] = SPEEDS[k]
        self._show_speed()

    def _set_play_all(self, on):
        _kept["all"] = on
        if on:  # (the demo plays on the card and the window: the list of steps closes, it stayed open over them)
            self.step_list.close_list()
        if on and not self.demo_running:
            if demo_actions(self.steps[self.i], self.alt) if 0 <= self.i < len(self.steps) else False:
                self.replay()
            else:
                self._schedule_next()
        elif not on:
            self.next_timer.stop()

    def _schedule_next(self, ms=None):
        """Play all steps: the next step after time to read this one."""
        if self.i + 1 < len(self.steps):
            words = len(self.text.text().split())
            self.next_timer.start(int((ms if ms is not None else max(2600, 1200 + words * 200)) / self.speed))

    def _auto_next(self):
        if self.all_chk.isChecked() and self.isVisible() and self.i + 1 < len(self.steps):
            self.go_to_step(self.i + 1)

    def replay(self):
        """The step's demo from its start (the last one's effects put back first)."""
        self.stop_demo()
        if not 0 <= self.i < len(self.steps):
            return
        actions = demo_actions(self.steps[self.i], self.alt)
        if not actions:
            return
        if not self.glide:  # (animation effects off: numbered markers, nothing moves)
            return self.show_markers(actions)
        self.demo_running = True
        self.act_now = -1
        self._show_demo_state(True)
        if self.cur is None:
            self.cur = QPointF(self.bubble.geometry().center())
        self.gen = self._play(actions)
        self._tick()

    def show_markers(self, actions):
        """The demo as numbered markers on its controls and the numbered list in the card (Windows' animation effects
        off). A marker keeps its control and where on it, and is drawn where the control is now (marker_points). The
        page moves once at most, before anything is drawn: back to what the step lights (you scrolled away, then
        Show the steps), then to where the most markers show (_page_to_markers); the card then goes off the markers.
        (2026-11-22. Each marker was a point, measured after the page scrolled to its control: the page ended at the
        last control, what was lit could be out of sight, and the markers before the last were where their controls
        had been. A page that never moved was tried first and taken out the same day: "Custom values" then had no
        marker in a window 1000 px wide and 670 px or less high, where it had one before.)"""
        scroll_all_into_view(self.target or [])
        self.markers = []
        for a in actions:
            if not a.get("say"):
                continue
            self.markers.append((_control(a), a.get("x", 0.5), a.get("y", 0.5), len(self.markers) + 1))
        self.markers = [mk for mk in self.markers if mk[0] is not None and mk[0].isVisible()]
        pages = []  # [(a scrolling page, its markers)]: a marker goes with the nearest page that scrolls up and down
        for w, fx, fy, _n in self.markers:
            area = next((p for p in self._ancestors(w) if isinstance(p, QScrollArea) and p.widget() is not None
                         and p.widget().isAncestorOf(w) and p.verticalScrollBar().maximum() > 0), None)
            if area is not None:
                marks = next((ms for a, ms in pages if a is area), None)
                if marks is None:
                    marks = []
                    pages.append((area, marks))
                marks.append((w, fx, fy))
        for area, marks in pages:
            self._page_to_markers(area, marks)
        self.act_now = -1
        self._show_acts()
        self.place(move_card=True)
        if self.all_chk.isChecked():
            self._schedule_next(2600 + 1200 * len(self.markers))

    def _page_to_markers(self, area, marks):
        """A scrolling page moved to where the most of its markers show: marks, [(control, x, y)]. A marker shows
        where its control is all in the page's view, MARK_EDGE px from its top and bottom (of a control taller than
        MARK_STRIP px that much is enough), and its disc is whole in sight. The page goes only where what the step
        lights on it is as much in sight as now; when no marker shows at such a place, where the lit part keeps 60 %
        of what it shows now ("Custom values" in a low window: the tick box of its second marker is above the lit
        settings, and they can't be all in sight together). Of the places with as many markers: the most of the lit
        part, then the nearest. The page stays when no place shows more markers than it does now."""
        bar, vp = area.verticalScrollBar(), area.viewport()
        at = bar.value()
        view = QRect(vp.mapTo(self.win, QPoint(0, 0)), vp.size())
        for _a, r in self._views(area):  # (a page inside another: only what that one shows of it)
            view = view.intersected(r)
        view = view.intersected(self.rect())
        if view.height() < 2 * MARK_R:
            return
        y0, y1, x0, x1 = view.top(), view.top() + view.height(), view.left(), view.left() + view.width()
        ctrls = []  # [(top, height, y)] in the window now: of each control, what scrolling parts inside the page show
        for w, fx, fy in marks:
            r = QRect(w.mapTo(self.win, QPoint(0, 0)), w.size())
            for a, inner in self._views(w):
                if a is area:
                    break
                r = r.intersected(inner)
            left, right = max(r.left(), x0), min(r.left() + r.width(), x1)
            x = left + (right - left) * fx
            if r.height() >= 2 and right - left >= 2 and x - MARK_R >= x0 and x + MARK_R <= x1:
                ctrls.append((r.top(), r.height(), fy))
        lit = []  # [(top, height, width)]: what the step lights on this page
        for w in _shown(self.spots):
            if area.widget().isAncestorOf(w):
                r = QRect(w.mapTo(self.win, QPoint(0, 0)), w.size())
                lit.append((r.top(), r.height(), max(0, min(r.left() + r.width(), x1) - max(r.left(), x0))))

        def lit_at(dv):
            """The area of the lit part in the view with the page dv px further down."""
            return sum(max(0, min(top - dv + h, y1) - max(top - dv, y0)) * width for top, h, width in lit)

        def shown_at(dv):
            """How many markers show with the page dv px further down."""
            n = 0
            for top, h, fy in ctrls:
                top -= dv
                a, b = max(top, y0), min(top + h, y1)  # (the part in the view: the marker is on it, as _point has it)
                y = a + (b - a) * fy
                n += (b - a >= 2 and y - MARK_R >= y0 and y + MARK_R <= y1
                      and min(top + h, y1 - MARK_EDGE) - max(top, y0 + MARK_EDGE) >= min(h, MARK_STRIP))
            return n
        lit_now = lit_at(0)
        # the best place with the lit part as it is now, and with 60 % of it: ((markers, lit area, -distance), place)
        whole = part = None
        for v in range(bar.minimum(), bar.maximum() + 1):
            area_lit = lit_at(v - at)
            if 10 * area_lit < 6 * lit_now:
                continue
            place = ((shown_at(v - at), area_lit, -abs(v - at)), v)
            if part is None or place[0] > part[0]:
                part = place
            if area_lit >= lit_now and (whole is None or place[0] > whole[0]):
                whole = place
        best = whole if whole is not None and whole[0][0] else part
        if best is not None and best[0][0] > shown_at(0):
            bar.setValue(best[1])

    def _views(self, w):
        """The views of the scrolling parts that hold a control, the nearest first: [(part, its view in the window)]."""
        out = []
        p = w.parentWidget()
        while p is not None and p is not self.win:
            if isinstance(p, QAbstractScrollArea) and p.viewport().isAncestorOf(w):
                out.append((p, QRect(p.viewport().mapTo(self.win, QPoint(0, 0)), p.viewport().size())))
            p = p.parentWidget()
        return out

    @staticmethod
    def _disc(pt, more=0):
        r = MARK_R + more
        return QRectF(pt.x() - r, pt.y() - r, 2 * r, 2 * r)

    def _marker_spots(self):
        """The markers in sight now, the card not counted: [(the point in the window, the number)]. A marker is on
        the part of its control that its scrolling parts show (_point), and has no point while the window or one of
        those parts' views would cut its disc: a marker is never drawn half, or over the top bar."""
        out = []
        for w, fx, fy, n in self.markers:
            pt = self._point(w, fx, fy, scroll=False)
            if pt is None:
                continue
            disc = self._disc(pt)
            if QRectF(self.rect()).contains(disc) and all(QRectF(r).contains(disc) for _a, r in self._views(w)):
                out.append((pt, n))
        return out

    def marker_points(self, spots=None):
        """The markers drawn now, [(the point in the window, the number)]: those in sight (_marker_spots; spots: these,
        just measured) whose disc is off the card, and off the step list while it's open. The markers' layer is above
        both, so one drawn there would be on the card's words or buttons. A marker that isn't drawn keeps its line
        in the card's list. Public: the tests read it."""
        spots = self._marker_spots() if spots is None else spots
        if not spots:
            return []
        over = [QRectF(self.bubble.geometry())]
        if self.step_list.isVisible():
            over.append(QRectF(self.step_list.geometry()))
        return [(pt, n) for pt, n in spots if not any(o.intersects(self._disc(pt)) for o in over)]

    def toggle_pause(self):
        if not self.demo_running:
            return
        if self.paused:
            self.resume()
        else:
            self.paused = True
            self.timer.stop()
            self._pause_label("Continue")
            self._show_acts()

    def resume(self):
        """Carry on (after you scrolled away: the page back where the demo was first)."""
        for bar, v in self.scrolled.items():
            try:
                bar.setValue(v)
            except RuntimeError:
                pass
        self.scrolled = {}
        self.paused = self.paused_by_you = False
        self._pause_label("Wait")
        self._show_acts()
        self.follow(force=True)
        self._tick()

    def _pause_for_scroll(self):
        """You scrolled while the demo plays: it pauses there; Continue scrolls back and carries on."""
        if not self.demo_running or self.paused:
            return
        from PySide6.QtWidgets import QScrollBar
        self.scrolled = {b: b.value() for b in self.win.findChildren(QScrollBar)}
        self.paused = self.paused_by_you = True
        self.timer.stop()
        # (its tooltip says it scrolls back: a label that said so too, "Resume (back to the demo)", was cut short at
        # Windows 11's text size)
        self._pause_label("Continue", "The demo waits while you scroll. Continue (P) scrolls the page to the demo, "
                                      "and the demo continues.")
        self._show_acts()
        self._fit_card()

    def skip_demo(self):
        self.stop_demo()
        if self.all_chk.isChecked():
            self._schedule_next(900)

    def stop_demo(self):
        """The demo stopped, and what it showed put back (last first)."""
        self.timer.stop()
        self.markers = []
        self.gen = None
        while self.undos:
            u = self.undos.pop()
            try:
                u()
            except (RuntimeError, AttributeError, ValueError, KeyError, TypeError):
                pass
        for w in list(self.inside):
            self.drop(w)
        if hasattr(self, "glass"):
            self.glass.hide()
        self.demo_running = self.paused = self.paused_by_you = False
        self.scrolled = {}
        self.hot_w = self.ripple = self.trail = self.file_chip = None
        self.typed = []
        self.say = ""
        if 0 <= self.i < len(self.steps) and self.target:
            self.spots = list(self.target)
            self.avoid = []
            if hasattr(self, "acts_lab"):
                self.act_now = -1
                self._show_demo_state(False)
        self.follow(force=True)

    def _finish_demo(self):
        self.gen = None
        self.demo_running = False
        self.hot_w = self.ripple = self.trail = self.file_chip = None
        self.say = ""
        while self.undos:
            u = self.undos.pop()
            try:
                u()
            except (RuntimeError, AttributeError, ValueError, KeyError, TypeError):
                pass
        for w in list(self.inside):
            self.drop(w)
        self.typed = []
        self.spots = list(self.target or [])
        self.avoid = []
        ws = _shown(self.target)
        if ws:
            scroll_into_view(ws[0])
        self.act_now = -1
        self._show_demo_state(False)
        self.follow(force=True)
        self.place_card(stay=True)
        if self.all_chk.isChecked():
            self._schedule_next(900)

    def _tick(self):
        if self.gen is None or self.paused:
            return
        try:
            ms = next(self.gen)
        except StopIteration:
            self._finish_demo()
            return
        except (RuntimeError, AttributeError, KeyError, IndexError, TypeError, ValueError) as e:
            import traceback
            traceback.print_exc()  # (a demo that fails ends as if it had finished: said in the log)
            steps, i = getattr(self, "steps", []), getattr(self, "i", -1)
            title = steps[i].get("title", "?") if 0 <= i < len(steps) else "?"
            self.demo_errors.append(f"{title}: {type(e).__name__}: {e}")
            self._finish_demo()
            return
        self.timer.start(max(0, int((ms or 0) / self.speed)))

    def _point(self, w, fx=0.5, fy=0.5, scroll=True):
        """Where on a control the pointer goes (in the window), or None when it isn't shown. The page scrolls to it
        (or a window the demo shows, when it scrolls inside its frame); scroll=False (a marker's point): nothing
        scrolls, and a control out of sight has no point."""
        if w is None or not _alive(w) or not w.isVisible():
            return None
        if scroll and w.window() is self.win and w is not self:
            scroll_into_view(w)
        r = self._w_rect(w).toRect()
        if r.width() < 2 or r.height() < 2:
            return None
        return QPointF(r.left() + r.width() * fx, r.top() + r.height() * fy)

    def _w_rect(self, w):
        """A control's rectangle in the tour: on the page, or inside what the demo shows (cut to what its scrolling
        parts show)."""
        if w.parentWidget() is self:
            return QRectF(w.geometry())
        if self.isAncestorOf(w):
            return QRectF(_rect(self, [w]))
        return QRectF(_rect(self.win, [w]))

    def _move(self, to, ms=650, also=None):
        """The pointer glides to a point (eased), also(p) called on the way; the card moves off where it goes."""
        if to is None:
            return
        if self.bubble.geometry().adjusted(-24, -24, 24, 24).contains(to.toPoint()):
            self.keep_clear(QRect(int(to.x()) - 70, int(to.y()) - 50, 140, 100))
            self.place_card(stay=False)
        start = QPointF(self.cur) if self.cur is not None else QPointF(to)
        frames = max(1, round(ms / self.speed / 16)) if self.glide else 1
        for n in range(1, frames + 1):
            p = n / frames
            e = 2 * p * p if p < 0.5 else 1 - (-2 * p + 2) ** 2 / 2
            self.cur = start + (to - start) * e
            if also:
                also(p)
            self.update()
            yield 16 * self.speed

    def _click_ripple(self):
        frames = max(1, round(420 / self.speed / 16)) if self.glide else 1
        for n in range(1, frames + 1):
            self.ripple = (self.cur.x(), self.cur.y(), n / frames)
            self.update()
            yield 16 * self.speed
        self.ripple = None

    def _play(self, actions):
        api = Api(self)
        n_say = -1
        for a in actions:
            if a.get("say"):
                n_say += 1
                self.act_now = n_say
                self._show_acts()
            if "wait" in a:
                yield a["wait"]
                continue
            if "run" in a:
                self.say = _val(a.get("say", "")) or self.say
                g = a["run"](api)
                if g is not None:
                    yield from g
                continue
            if "key" in a:
                yield from api.key(a["key"], a.get("hold", 900))
                continue
            w = _control(a)
            kind = next((k for k in ACTIONS if k in a), None)
            if kind is None:
                continue
            self.say = _val(a.get("say", ""))
            if kind == "spot":
                if w is not None:
                    scroll_into_view(w)
                    self.spot_to(w)
                    self.place_card(stay=False)
                yield 150
                continue
            if kind == "note":
                if w is not None:
                    scroll_into_view(w)
                yield from api.note(_val(a["text"]), w, a.get("hold", 1400))
                continue
            if kind == "drag":
                p0, p1 = self._point(w, *a["from"]), self._point(w, *a["to"])
                if p0 is None or p1 is None:
                    yield a.get("hold", 400)
                    continue
                yield from self._move(p0)
                self.hot_w = w
                if a.get("undo"):
                    self.undos.append(a["undo"])
                self.trail = (QPointF(p0), QPointF(p0))

                def along(p, a=a, p0=p0):
                    self.trail = (p0, QPointF(self.cur))
                    if a.get("set"):
                        a["set"](p)
                    if a.get("label"):
                        self.say = a["label"](p)
                yield from self._move(p1, a.get("ms", 900), along)
                yield a.get("hold", 500)
                self.trail = None
                continue
            if w is None:
                yield a.get("hold", 400)
                continue
            if self.spots and not any(s is w or (_alive(s) and s.isAncestorOf(w)) for s in self.spots) \
                    and not self.isAncestorOf(w):
                self.spot_on(w)  # (what the pointer goes to is lit too)
            p = self._point(w, a.get("x", 0.25 if kind == "type" else 0.5), a.get("y", 0.5))
            if p is None:
                yield a.get("hold", 400)
                continue
            yield from self._move(p, a.get("ms", 650))
            self.hot_w = w if a.get("hot", True) else None
            if kind == "click":
                yield from self._click_ripple()
            elif kind == "type":
                yield from self._click_ripple()
                text = str(_val(a["text"]))
                entry = [w, ""]
                self.typed.append(entry)
                for n in range(1, len(text) + 1):
                    entry[1] = text[:n]
                    self.update()
                    yield 75
            if a.get("then"):
                fn = a["then"]
                u = fn(api) if _arg_count(fn) else fn()
                if inspect.isgenerator(u):
                    self.hot_w = None
                    yield from u
                elif callable(u):
                    self.undos.append(u)
            yield a.get("hold", 900 if kind != "click" else 500)
            self.hot_w = None
            if kind == "type" and not a.get("keep"):
                self.typed = [e for e in self.typed if e[0] is not w]
            self.update()
        yield 400

    # ---------------------------------------------------------------- drawing
    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        t = theme.tokens()
        shade = QPainterPath()
        shade.addRect(QRectF(self.rect()))
        lit = QPainterPath()
        for r in self.holes:
            hole = QPainterPath()
            hole.addRoundedRect(QRectF(r), 8, 8)
            lit = lit.united(hole)
        shade = shade.subtracted(lit)
        if self.hot_w is not None and _alive(self.hot_w) and self.hot_w.isVisible() and not self.isAncestorOf(self.hot_w):
            hole = QPainterPath()
            hole.addRoundedRect(self._w_rect(self.hot_w).adjusted(-3, -3, 3, 3), 6, 6)
            shade = shade.subtracted(hole)
        p.fillPath(shade, QColor(0, 0, 0, 140))
        p.setPen(QPen(QColor(t["accent"]), 2))  # (what's lit, outlined in the accent: Windows' own colour)
        p.setBrush(Qt.NoBrush)
        p.drawPath(lit.simplified())

    def paint_demo(self, p):
        """The demo (on the layer above the card): the control pointed at (ringed), what's typed (as a text box being
        typed in), a drag's trail, a click's ripple, the numbered markers, the pointer and its words; the accent
        marks them all (the graph's own colours stay the graph's)."""
        t = theme.tokens()
        for pt, n in self.marker_points():
            p.setPen(QPen(QColor(t["card"]), 2))
            p.setBrush(QColor(t["accent"]))
            p.drawEllipse(pt, 11, 11)
            p.setPen(QColor(t["on_accent"]))
            p.drawText(QRectF(pt.x() - 11, pt.y() - 11, 22, 22), Qt.AlignCenter, str(n))
        if self.hot_w is not None and _alive(self.hot_w) and self.hot_w.isVisible():
            p.setPen(QPen(QColor(t["accent"]), 2, Qt.DashLine))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(self._w_rect(self.hot_w).adjusted(-3, -3, 3, 3), 6, 6)
        for w, text in self.typed:
            if not (_alive(w) and w.isVisible()):
                continue
            r = self._w_rect(w)
            box = r.adjusted(2, 2, -2, -2)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(t["field_focus"]))
            p.drawRoundedRect(box, 3, 3)
            p.setBrush(QColor(t["accent"]))  # (the accent's line under a text box being typed in, as the app's)
            p.drawRect(QRectF(box.left(), box.bottom() - 2, box.width(), 2))
            font = w.font()
            p.setFont(font)
            p.setPen(QColor(t["ink"]))
            fm = QFontMetrics(font)
            x, y = box.left() + 7, box.center().y() + fm.ascent() / 2 - 2
            p.drawText(QPointF(x, y), text)
            cx = x + fm.horizontalAdvance(text) + 1
            p.setPen(QPen(QColor(t["ink"]), 1))
            p.drawLine(QPointF(cx, box.center().y() - fm.ascent() / 2), QPointF(cx, box.center().y() + fm.ascent() / 2))
        if self.file_chip is not None:
            at, name = self.file_chip
            f = QFont(self.font())
            p.setFont(f)
            text = "🗎 " + name
            r = QRectF(at.x() - 10, at.y() + 8, QFontMetrics(f).horizontalAdvance(text) + 18, QFontMetrics(f).height() + 10)
            p.setPen(QPen(QColor(t["stroke"]), 1))
            p.setBrush(QColor(t["menu"]))
            p.drawRoundedRect(r, 8, 8)
            p.setPen(QColor(t["ink"]))
            p.drawText(r, Qt.AlignCenter, text)
        if self.trail is not None:
            p.setPen(QPen(QColor(t["accent"]), 3, Qt.SolidLine, Qt.RoundCap))
            p.drawLine(*self.trail)
        if self.ripple is not None:
            x, y, k = self.ripple
            c, halo = QColor(t["accent"]), QColor(t["card"])  # (the halo: seen on a button filled with the accent)
            c.setAlphaF(max(0.0, 0.8 * (1 - k)))
            halo.setAlphaF(max(0.0, 0.8 * (1 - k)))
            p.setBrush(Qt.NoBrush)
            rad = 6 + 18 * k
            p.setPen(QPen(halo, 1.5))
            p.drawEllipse(QPointF(x, y), rad + 2.25, rad + 2.25)
            p.setPen(QPen(c, 3))
            p.drawEllipse(QPointF(x, y), rad, rad)
        if self.cur is not None and (self.demo_running or self.say):
            self._draw_pointer(p, t)

    def _tag_font(self):
        f = QFont(self.font())
        f.setPointSizeF(max(6.5, f.pointSizeF() * 0.75))
        f.setBold(True)
        return f

    def tag_rect(self):
        """Where the pointer's "demo" tag is drawn (under its tip, to the right)."""
        fm = QFontMetrics(self._tag_font())
        return QRectF(self.cur.x() + 14, self.cur.y() + 20, fm.horizontalAdvance("demo") + 10, fm.height() + 2)

    def _draw_pointer(self, p, t):
        x, y = self.cur.x(), self.cur.y()
        arrow = QPolygonF([QPointF(x + dx * 1.15, y + dy * 1.15) for dx, dy in
                           ((0, 0), (0, 17), (4.5, 13), (7.5, 20), (10, 19), (7, 12.5), (12.5, 12.5))])
        p.setPen(QPen(QColor("#000000"), 1.3))
        p.setBrush(QColor("#ffffff"))
        p.drawPolygon(arrow)
        p.setFont(self._tag_font())
        tag = self.tag_rect()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(t["accent"]))
        p.drawRoundedRect(tag, tag.height() / 2, tag.height() / 2)
        p.setPen(QColor(t["on_accent"]))
        p.drawText(tag, Qt.AlignCenter, "demo")
        box = self.words_box() if self.say else None
        if box is not None:
            p.setFont(QFont(self.font()))
            p.setPen(QPen(QColor(t["accent"]), 1))
            p.setBrush(QColor(t["card"]))
            p.drawRoundedRect(box.adjusted(0.5, 0.5, -0.5, -0.5), 8, 8)
            p.setPen(QColor(t["ink"]))
            p.drawText(box.adjusted(10, 6, -10, -6), Qt.TextWordWrap, self.say)

    def words_box(self):
        """Where the pointer's words go: beside the pointer, in the window, off the card, what the demo shows and what
        is lit (just under or over the lit part when the pointer is in it); else off the card and what the demo shows;
        else off the card only. None where every place would cover the card: the card's line says the same words (the
        UI audit, 2026-11-08: the box covered the card's words; 2026-11-10: it covered the words of the lit controls,
        as Automatic settings' About these settings)."""
        x, y = self.cur.x(), self.cur.y()
        r = QFontMetrics(QFont(self.font())).boundingRect(QRect(0, 0, 260, 400), Qt.TextWordWrap, self.say)
        w, h = r.width() + 20, r.height() + 12
        places = [QRectF(x + 22, y + 40, w, h), QRectF(x + 22, y - 10 - h, w, h), QRectF(x - 10 - w, y + 24, w, h),
                  QRectF(x - 10 - w, y - 10 - h, w, h)]
        lit = [QRectF(hole) for hole in self.holes]
        for hole in lit:
            if hole.contains(self.cur):
                places += [QRectF(x + 22, hole.bottom() + 8, w, h), QRectF(x + 22, hole.top() - 8 - h, w, h)]
        inside = [b for b in places if QRectF(self.rect()).adjusted(8, 8, -8, -8).contains(b)] or places[:1]
        keep = [QRectF(self.bubble.geometry())] + [QRectF(v.geometry()) for v in self.inside
                                                   if _alive(v) and v.isVisible() and isinstance(v, (_Note, Mock))]
        return next((b for b in inside if not any(b.intersects(k) for k in keep + lit)),
                    next((b for b in inside if not any(b.intersects(k) for k in keep)),
                         next((b for b in inside if not b.intersects(keep[0])), None)))

    # ---------------------------------------------------------------- your scrolling, the keys, the end
    def _scroll_area_at(self, pos):
        """The innermost scrolling part of the window under a point (what the wheel would scroll)."""
        best = None
        for a in self.win.findChildren(QAbstractScrollArea):
            if not a.isVisible() or self.step_list.isAncestorOf(a):
                continue
            r = self._w_rect(a)
            if r.contains(QPointF(pos)) and a.verticalScrollBar().maximum() > 0:
                if best is None or r.width() * r.height() < best[1]:
                    best = (a, r.width() * r.height())
        return best[0] if best else None

    def _key_scroll_area(self):
        """What Page Up, Page Down, Up and Down scroll: the scrolling part under the first lit rectangle. When that
        gives none (nothing lit is in sight: you scrolled it away), a scrolling part that holds the step's control:
        the outermost one that has it out of its view, else the nearest. (2026-11-22: with nothing lit in sight the
        keys did nothing, so the keys alone could not bring the lit part back.)"""
        a = self._scroll_area_at(self.holes[0].center()) if self.holes else None
        w = next(iter(_shown(self.target)), None)
        if a is not None or w is None:
            return a
        areas = [p for p in self._ancestors(w) if isinstance(p, QAbstractScrollArea) and p.viewport().isAncestorOf(w)
                 and p.verticalScrollBar().maximum() > 0]
        hiding = [p for p in areas
                  if not p.viewport().rect().intersects(QRect(w.mapTo(p.viewport(), QPoint(0, 0)), w.size()))]
        return hiding[-1] if hiding else areas[0] if areas else None

    def wheelEvent(self, e):
        """The page scrolls under the tour (the spotlight follows); while a demo plays it pauses."""
        a = self._scroll_area_at(e.position())
        if a is None:
            e.accept()
            return
        self._pause_for_scroll()
        bar = a.verticalScrollBar()
        bar.setValue(bar.value() - int(e.angleDelta().y() / 120 * max(bar.singleStep() * 3, 60)))
        self.follow(force=True)
        e.accept()

    def mousePressEvent(self, e):
        self.step_list.close_list()
        e.accept()  # (the tour covers the window: nothing behind it is clicked meanwhile)

    def focusNextPrevChild(self, _next):
        return True  # (Tab stays in the tour: the controls under it can't be reached and worked by the keyboard)

    def _keep_focus(self, _old, new):
        """Focus moved to a control of this window under the tour (a click can't, but a shortcut can), or into what
        a demo shows: back to the tour (the step list keeps it while open)."""
        if not self.isVisible() or new is None or new is self:
            return
        if self.step_list.isVisible() and self.step_list.isAncestorOf(new):
            return
        if new.window() is self.win:
            self.setFocus()

    def _toggle_list(self):
        if self.step_list.isVisible():
            self.step_list.close_list()
        else:
            self.step_list.open()

    def keyPressEvent(self, e):
        k = e.key()
        if k == Qt.Key_Escape:
            self.end()
        elif k in (Qt.Key_Right, Qt.Key_Return, Qt.Key_Enter, Qt.Key_Space):
            self.next_btn.click()
        elif k == Qt.Key_Left:
            if self.i > 0:
                self.go_to_step(self.i - 1)
        elif k == Qt.Key_R and self.demo_box.isVisible():
            self.replay()
        elif k == Qt.Key_P and self.demo_running:
            self.toggle_pause()
        elif k in (Qt.Key_PageUp, Qt.Key_PageDown, Qt.Key_Up, Qt.Key_Down):
            a = self._key_scroll_area()
            if a is not None:
                self._pause_for_scroll()
                bar = a.verticalScrollBar()
                step = bar.pageStep() if k in (Qt.Key_PageUp, Qt.Key_PageDown) else 60
                bar.setValue(bar.value() + (step if k in (Qt.Key_PageDown, Qt.Key_Down) else -step))
                self.follow(force=True)
        else:
            e.accept()

    def end(self):
        if self.i >= len(self.steps):
            return
        self._leave_step()
        self.i = len(self.steps)
        self.follow_timer.stop()
        self.win.removeEventFilter(self.follow_obj)
        from PySide6.QtWidgets import QApplication
        try:
            QApplication.instance().focusChanged.disconnect(self._keep_focus)
        except (RuntimeError, TypeError):
            pass
        self.hide()
        self.deleteLater()
        if self.on_end:
            self.on_end()
        self.end_focus()

    def end_focus(self):
        """The focus when the Guide ends: back on the control that had it before the Guide, when that control is
        there, on and all in sight; else on the first such control in the host's Tab order (the page's, the
        tracer's), else in the window's. Hidden with the focus, the Guide kept it (Tab stays in the Guide:
        focusNextPrevChild), and the keys of the page did nothing (measured after the demo of Calculate,
        2026-11-15). No scroll: the page stays where the last step left it."""
        win = self.win
        if not _alive(win):
            return

        def usable(w):
            if w is None or not _alive(w) or w is self or self.isAncestorOf(w) or w.window() is not win:
                return False
            if not (w.isVisible() and w.isEnabled()):
                return False
            whole = QRect(w.mapTo(win, QPoint(0, 0)), w.size())
            return win.rect().contains(whole) and _rect(win, [w]) == whole
        w = self.had_focus if usable(self.had_focus) else None
        for root in (self.host, win):
            if w is not None or not _alive(root):
                break
            x, n = root.nextInFocusChain(), 0
            while x is not root and n < 5000:  # (the chain is a ring: once round it)
                if ((root is win or root.isAncestorOf(x)) and x.focusPolicy() & Qt.TabFocus
                        and not isinstance(x, QScrollArea) and usable(x)):  # (a page's frame: not a control)
                    w = x
                    break
                x, n = x.nextInFocusChain(), n + 1
        if w is not None:
            w.setFocus(Qt.OtherFocusReason)

    def active(self):
        return self.isVisible()


def problems(host, steps):
    """The steps whose control (or a demo action's) isn't there, can't be seen or lies outside the window:
    [(n, title, why)]. Each step's before and after are run, as the tour does; a step with a stand-in ("alt") is
    checked with whichever is on screen. Each control is measured once the page has settled: straight after a step
    that closed a fold the page wasn't laid out again yet, and at the window's smallest size a card scrolled to went
    out of sight (2026-10-23)."""
    from PySide6.QtWidgets import QApplication
    out = []
    win = host.window()

    def where(t):
        ws = _shown(t)
        if t is None or t == []:
            return "no control"
        if not ws:
            return "not shown"
        _settle()
        scroll_into_view(ws[0])
        QApplication.processEvents()
        r = _rect(win, ws)
        if not win.rect().intersects(r) or r.width() < 4 or r.height() < 4:
            return f"outside the window {r.getRect()}"
        return None
    for n, st in enumerate(steps, 1):
        if st.get("before"):
            st["before"]()
        _settle()
        try:
            alt = False
            if "target" in st and st["target"] is not None:
                why = where(st["target"]())
                if why and st.get("alt"):
                    why2 = where(st["alt"]())
                    alt = not why2
                    why = None if alt else f"{why} (and its stand-in: {why2})"
                if why:
                    out.append((n, _val(st["title"]), why))
            for k, a in enumerate(demo_actions(st, alt), 1):
                if any(x in a for x in ACTIONS):
                    why = where(_control(a))
                    if why:
                        out.append((n, _val(st["title"]), f"demo action {k}: {why}"))
            text = _val(st["alt_text"] if alt and st.get("alt_text") else st["text"])
            if not text.strip():
                out.append((n, _val(st["title"]), "no words"))
        finally:
            if st.get("after"):
                st["after"]()
    return out
