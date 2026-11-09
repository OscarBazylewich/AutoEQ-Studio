"""The main window's top bar in its title bar (the UI audit, 2026-11-08, the user's selection: one row has the name,
the screens, Help, Online and the 3 window buttons, as File Explorer, Edge and Windows Terminal have their tabs in the
title bar; the screens get approximately 30 px more height).

How: the window is frameless for Qt, but Windows keeps its frame styles (WS_CAPTION, WS_THICKFRAME), so it keeps its
shadow, its rounded corners, Snap, its minimize and maximize animations and Mica. Windows' own title bar goes
(WM_NCCALCSIZE: the whole window is client area; maximized, the frame that would be off the screen is taken off).
WM_NCHITTEST tells Windows what each place is: the edges resize the window (not when it is maximized); the empty part
of the top bar is the title bar (drag, double-click, the window menu on a right-click and Alt+Space); the maximize
button is HTMAXBUTTON, so Windows 11 shows its Snap layouts there (a click on it then comes as a non-client message,
handled here too).

caption_buttons(window): Minimize, Maximize / Restore and Close (Windows 11's: 46 px wide, Close red when the pointer
is on it), at the right end of the top bar. install(window, bar): the native part, on Windows only (the tests' and
the pictures' off-screen windows keep the buttons and no native part). With no native part on Windows (it failed),
the buttons hide and Windows' own title bar stays.
"""
import ctypes
from ctypes import wintypes

from PySide6.QtCore import QObject, QPoint, QSize, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QAbstractButton, QFrame, QHBoxLayout, QLayout, QToolButton, QWidget

from ui import theme

WM_NCCALCSIZE, WM_NCHITTEST = 0x0083, 0x0084
WM_NCMOUSEMOVE, WM_NCLBUTTONDOWN, WM_NCLBUTTONUP, WM_NCLBUTTONDBLCLK = 0x00A0, 0x00A1, 0x00A2, 0x00A3
WM_NCMOUSELEAVE = 0x02A2
HTCLIENT, HTCAPTION, HTMAXBUTTON = 1, 2, 9
HTLEFT, HTRIGHT, HTTOP, HTTOPLEFT, HTTOPRIGHT, HTBOTTOM, HTBOTTOMLEFT, HTBOTTOMRIGHT = 10, 11, 12, 13, 14, 15, 16, 17
GWL_STYLE = -16
WS_CAPTION, WS_THICKFRAME, WS_SYSMENU, WS_MINIMIZEBOX, WS_MAXIMIZEBOX = 0x00C00000, 0x00040000, 0x00080000, \
    0x00020000, 0x00010000
SWP_NOSIZE, SWP_NOMOVE, SWP_NOZORDER, SWP_NOACTIVATE, SWP_FRAMECHANGED = 0x1, 0x2, 0x4, 0x10, 0x20
SM_CXSIZEFRAME, SM_CYSIZEFRAME, SM_CXPADDEDBORDER = 32, 33, 92
GLYPHS = {"min": "E921", "max": "E922", "restore": "E923", "close": "E8BB"}  # (Segoe Fluent Icons' caption symbols)


class _NcCalcSizeParams(ctypes.Structure):
    _fields_ = [("rgrc", wintypes.RECT * 3), ("lppos", ctypes.c_void_p)]


def _glyph_font(btn):
    from PySide6.QtGui import QFont, QFontDatabase
    f = QFont("Segoe Fluent Icons" if "Segoe Fluent Icons" in QFontDatabase.families() else "Segoe MDL2 Assets")
    f.setPixelSize(10)
    btn.setFont(f)


def caption_buttons(win):
    """Minimize, Maximize / Restore and Close in a row (no space between them), for the top bar's right end. They
    are win's: win.caption = {"min", "max", "close"}."""
    holder = QWidget()
    row = QHBoxLayout(holder)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(0)
    win.caption = {}
    for key, name, fn in (("min", "Minimize", win.showMinimized),
                          ("max", "Maximize", lambda: toggle_maximized(win)),
                          ("close", "Close", win.close)):
        b = QToolButton()
        b.setObjectName("caption_" + key)
        b.setText(chr(int(GLYPHS[key], 16)))
        _glyph_font(b)
        b.setToolTip(name)
        b.setAccessibleName(name)
        b.setFocusPolicy(Qt.NoFocus)  # (as Windows' own: the keyboard has Alt+Space and Alt+F4: not in the Tab
        b.setProperty("a11y_skip", True)  # order, which the accessibility checks know)
        b.setFixedWidth(46)
        b.setSizePolicy(b.sizePolicy().horizontalPolicy(), b.sizePolicy().Policy.Expanding)
        theme.mark(b, caption=key)
        b.clicked.connect(fn)
        row.addWidget(b)
        win.caption[key] = b
    return holder


def toggle_maximized(win):
    win.showNormal() if win.isMaximized() else win.showMaximized()


def follow_state(win):
    """Maximize's symbol and name after the window's state: Restore when it is maximized."""
    b = getattr(win, "caption", {}).get("max")
    if b is None:
        return
    on = win.isMaximized()
    b.setText(chr(int(GLYPHS["restore" if on else "max"], 16)))
    b.setToolTip("Restore" if on else "Maximize")
    b.setAccessibleName("Restore" if on else "Maximize")


class Native(QObject):
    """The native part on Windows: the frame styles, and the answers to WM_NCCALCSIZE and WM_NCHITTEST (from the
    window's nativeEvent). bar: the top bar (its empty parts are the title bar)."""

    def __init__(self, win, bar):
        super().__init__(win)
        self.win, self.bar = win, bar
        self.hwnd = None
        self._down = False

    def attach(self):
        """The frame styles put back on the native window (Qt made it frameless): once it exists."""
        try:
            self.hwnd = int(self.win.winId())
            u = ctypes.windll.user32
            u.GetWindowLongW.restype = ctypes.c_long
            style = u.GetWindowLongW(wintypes.HWND(self.hwnd), GWL_STYLE)
            u.SetWindowLongW(wintypes.HWND(self.hwnd), GWL_STYLE,
                             ctypes.c_long(style | WS_CAPTION | WS_THICKFRAME | WS_SYSMENU | WS_MINIMIZEBOX
                                           | WS_MAXIMIZEBOX))
            u.SetWindowPos(wintypes.HWND(self.hwnd), None, 0, 0, 0, 0,
                           SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED)
            return True
        except (AttributeError, OSError):
            return False

    def _frame(self, x_axis):
        """The resize frame's thickness in physical pixels (as Windows draws it at the window's DPI)."""
        u = ctypes.windll.user32
        try:
            dpi = u.GetDpiForWindow(wintypes.HWND(self.hwnd))
            m = (SM_CXSIZEFRAME if x_axis else SM_CYSIZEFRAME)
            return u.GetSystemMetricsForDpi(m, dpi) + u.GetSystemMetricsForDpi(SM_CXPADDEDBORDER, dpi)
        except (AttributeError, OSError):
            return u.GetSystemMetrics(SM_CXSIZEFRAME if x_axis else SM_CYSIZEFRAME) + \
                u.GetSystemMetrics(SM_CXPADDEDBORDER)

    def event(self, message):
        """(handled, result) for one native message."""
        msg = wintypes.MSG.from_address(int(message))
        if self.hwnd is None or msg.hWnd != self.hwnd:
            return False, 0
        m = msg.message
        if m == WM_NCCALCSIZE:
            if msg.wParam and self.win.isMaximized():  # (the frame that would be off the screen taken off)
                r = _NcCalcSizeParams.from_address(msg.lParam).rgrc[0]
                fx, fy = self._frame(True), self._frame(False)
                r.left += fx
                r.right -= fx
                r.top += fy
                r.bottom -= fy
            return True, 0
        if m == WM_NCHITTEST:
            return True, self.hit(self._client_point(msg.lParam))
        if m == WM_NCLBUTTONDOWN and msg.wParam == HTMAXBUTTON:
            self._down = True
            self._max_look(down=True)
            return True, 0
        if m == WM_NCLBUTTONUP and msg.wParam == HTMAXBUTTON:
            if self._down:
                toggle_maximized(self.win)
            self._down = False
            self._max_look()
            return True, 0
        if m == WM_NCLBUTTONDBLCLK and msg.wParam == HTMAXBUTTON:
            return True, 0
        if m == WM_NCMOUSEMOVE:
            self._max_look(hover=msg.wParam == HTMAXBUTTON, down=self._down and msg.wParam == HTMAXBUTTON)
            return False, 0
        if m == WM_NCMOUSELEAVE:
            self._down = False
            self._max_look()
            return False, 0
        return False, 0

    def _client_point(self, lparam):
        """The message's screen point (physical pixels) in the window's own coordinates (Qt's, logical)."""
        x, y = ctypes.c_short(lparam & 0xFFFF).value, ctypes.c_short((lparam >> 16) & 0xFFFF).value
        origin = wintypes.POINT(0, 0)
        ctypes.windll.user32.ClientToScreen(wintypes.HWND(self.hwnd), ctypes.byref(origin))
        ratio = self.win.devicePixelRatioF() or 1.0
        return QPoint(int((x - origin.x) / ratio), int((y - origin.y) / ratio))

    def hit(self, p):
        """What the place p (the window's coordinates) is: an edge, the maximize button, the title bar, or the
        window's own."""
        win = self.win
        ratio = win.devicePixelRatioF() or 1.0
        edge = max(4, round(self._frame(True) / ratio))
        if not win.isMaximized() and not win.isFullScreen():
            left, right = p.x() < edge, p.x() >= win.width() - edge
            top, bottom = p.y() < edge, p.y() >= win.height() - edge
            for on, code in ((top and left, HTTOPLEFT), (top and right, HTTOPRIGHT), (bottom and left, HTBOTTOMLEFT),
                             (bottom and right, HTBOTTOMRIGHT), (left, HTLEFT), (right, HTRIGHT), (top, HTTOP),
                             (bottom, HTBOTTOM)):
                if on:
                    return code
        mx = getattr(win, "caption", {}).get("max")
        if mx is not None and mx.isVisible() and mx.rect().contains(mx.mapFrom(win, p)):
            return HTMAXBUTTON
        bar = self.bar
        at = bar.mapFrom(win, p)
        if bar.rect().contains(at):
            child = bar.childAt(at)
            while child is not None and child is not bar and not isinstance(child, QAbstractButton):
                child = child.parentWidget()
            if child is None or child is bar or not isinstance(child, QAbstractButton):
                return HTCAPTION  # (the name and the empty parts of the bar)
        return HTCLIENT

    def _max_look(self, hover=False, down=False):
        b = getattr(self.win, "caption", {}).get("max")
        if b is None:
            return
        state = "down" if down else ("hover" if hover else "")
        if (b.property("nc") or "") != state:
            theme.mark(b, nc=state)


def install(win, bar):
    """The native part (Windows only): returns it, or None (off the screen, as in the tests and the pictures, or when
    Windows refused: then Windows' own title bar stays, and the 3 buttons hide)."""
    if QGuiApplication.platformName() != "windows":
        return None
    native = Native(win, bar)
    if not native.attach():
        return None
    return native


class TopBar(QFrame):
    """The top bar: its own minimum width is the one with only the symbols of its screens (and of Presets and Guide):
    when it has less room than their names need, they show only their symbols, their names in their tooltips (the UI
    audit, 2026-11-08: the window can then fill one half of a screen, also at 125 %). compact(buttons) names the
    buttons that do this."""

    def __init__(self):
        super().__init__()
        self._buttons, self._compact = [], False
        theme.on_change(self._measure)

    def compact(self, buttons):
        self._buttons = list(buttons)
        for b in self._buttons:
            b.setProperty("full_text", b.text())
            b.setProperty("tip", b.toolTip())
            b.setAccessibleName(b.text())
        self.layout().setSizeConstraint(QLayout.SetNoConstraint)  # (the layout must not make it as wide as the names)
        self._measure()

    def _measure(self):
        self.updateGeometry()
        self._fit()

    def _names_need(self):
        """How much wider the bar's layout is with the names than with only the symbols (the shown buttons): each
        name's width, a little less (a button with only its symbol keeps a few px of the space after it): the minimum
        width said with the names then is never less than the true one with only the symbols, so the window never
        becomes wider when the names go."""
        need = 0
        for b in self._buttons:
            if not b.isHidden():
                b.ensurePolished()
                need += max(0, b.fontMetrics().horizontalAdvance(b.property("full_text") or "") - 2)
        return need

    def minimumSizeHint(self):
        hint = super().minimumSizeHint()
        lay = self.layout()
        if lay is None or not self._buttons:
            return hint
        w = lay.minimumSize().width() - (0 if self._compact else self._names_need())
        return QSize(max(0, w), hint.height())

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._fit()

    def showEvent(self, e):
        super().showEvent(e)
        self._fit()

    def _fit(self):
        if not self._buttons or self.layout() is None:
            return
        base = self.layout().minimumSize().width() - (0 if self._compact else self._names_need())
        # (the names back only with some room to spare: they never show squeezed, and it doesn't switch to and fro)
        compact = self.width() < base + self._names_need() + (24 if self._compact else 0)
        if compact != self._compact:
            self._compact = compact
            for b in self._buttons:
                name = b.property("full_text") or ""
                b.setText("" if compact else name)
                b.setToolTip(name if compact else (b.property("tip") or ""))
            self._relayout()

    def _relayout(self):
        """The layouts' sizes measured again now: kept from before, the window took the names' width (or Presets'
        and Guide's) as its minimum for a moment, and became that wide."""
        for w in [*self.findChildren(QWidget), self]:
            if w.layout() is not None:
                w.layout().invalidate()
                w.updateGeometry()

    def refit(self):
        """After a button shows or hides (Presets and Guide, on Make an EQ only)."""
        self._relayout()
        self._fit()

    def is_compact(self):
        return self._compact
