"""The main window's top bar in its title bar (the UI audit, 2026-11-08, the user's selection: one row has the name,
the screens, Help, Online and the 3 window buttons, as File Explorer, Edge and Windows Terminal have their tabs in the
title bar; the screens get approximately 30 px more height).

How (title_mode): two ways, after whether the window is see-through (Mica, Windows 11 22H2 and later):
- "frame", a see-through window: Qt makes it a window with a resize frame and no title bar (Qt::CustomizeWindowHint),
  so Windows keeps its frame on the four sides (invisible, outside the visible border: it resizes the window), its
  shadow and its rounded corners, and Qt counts the same frame as Windows does (its geometry agrees, also maximized
  and after a DPI change). Never Qt::FramelessWindowHint for it: Qt makes a frameless see-through window a layered
  window (WS_EX_LAYERED), and Windows gives a click on its fully transparent pixels (the empty parts of the top bar,
  between a button's words) to the window below it. In 1.5.0 a drag on the title bar so activated the window behind,
  and a maximized window kept its old picture (a layered window's picture must be as large as the whole window).
  Maximized, it is the work area with the frame off the screen (WM_WINDOWPOSCHANGING: Qt would put it at the
  monitor's corner, under a taskbar at the top or left). The trade-off: no WS_CAPTION (with it, Windows draws its own
  caption buttons over the top bar), so Windows animates a minimize and a restore, but not a maximize or a restore
  from maximized (measured 2026-11-09: Windows plays those only for a window with WS_CAPTION).
- "frameless", a window that is not see-through (Windows 10): frameless for Qt (not layered without see-through
  pixels), Windows' frame styles put back (WS_CAPTION, WS_THICKFRAME): its shadow, Snap and the minimize and maximize
  animations; WM_NCCALCSIZE makes the whole window client area (maximized, the frame that would be off the screen is
  taken off), and the edges resize the window (not when it is maximized).
WM_NCHITTEST tells Windows what each place is: the empty part of the top bar is the title bar (drag, double-click, the
window menu on a right-click and Alt+Space); the maximize button is HTMAXBUTTON, so Windows 11 shows its Snap layouts
there (a click on it then comes as a non-client message, handled here too); in "frame" the frame is Windows' own.

caption_buttons(window): Minimize, Maximize / Restore and Close (Windows 11's: 46 px wide, Close red when the pointer
is on it), at the right end of the top bar. install(window, bar, framed): the native part, on Windows only (the tests'
and the pictures' off-screen windows keep the buttons and no native part). With no native part on Windows (it
failed), the buttons hide and Windows' own title bar stays.
"""
import ctypes
import math
from ctypes import wintypes

from PySide6.QtCore import QObject, QPoint, QSize, Qt, QTimer
from PySide6.QtGui import QCursor, QGuiApplication
from PySide6.QtWidgets import QAbstractButton, QFrame, QHBoxLayout, QLayout, QToolButton, QWidget

from ui import theme

WM_NCCALCSIZE, WM_NCHITTEST = 0x0083, 0x0084
WM_NCMOUSEMOVE, WM_NCLBUTTONDOWN, WM_NCLBUTTONUP, WM_NCLBUTTONDBLCLK = 0x00A0, 0x00A1, 0x00A2, 0x00A3
WM_NCRBUTTONDOWN, WM_NCRBUTTONUP = 0x00A4, 0x00A5
WM_NCMOUSELEAVE, WM_SYSCOMMAND = 0x02A2, 0x0112
SC_SIZE, SC_MOVE, SC_MINIMIZE, SC_MAXIMIZE, SC_CLOSE, SC_RESTORE = 0xF000, 0xF010, 0xF020, 0xF030, 0xF060, 0xF120
MF_GRAYED, TPM_RIGHTBUTTON, TPM_RETURNCMD = 0x1, 0x2, 0x100
HTCLIENT, HTCAPTION, HTMAXBUTTON = 1, 2, 9
HTLEFT, HTRIGHT, HTTOP, HTTOPLEFT, HTTOPRIGHT, HTBOTTOM, HTBOTTOMLEFT, HTBOTTOMRIGHT = 10, 11, 12, 13, 14, 15, 16, 17
GWL_STYLE = -16
WS_CAPTION, WS_THICKFRAME, WS_SYSMENU, WS_MINIMIZEBOX, WS_MAXIMIZEBOX = 0x00C00000, 0x00040000, 0x00080000, \
    0x00020000, 0x00010000
SWP_NOSIZE, SWP_NOMOVE, SWP_NOZORDER, SWP_NOACTIVATE, SWP_FRAMECHANGED = 0x1, 0x2, 0x4, 0x10, 0x20
SM_CXSIZEFRAME, SM_CYSIZEFRAME, SM_CXPADDEDBORDER = 32, 33, 92
WM_WINDOWPOSCHANGING, MONITOR_DEFAULTTONEAREST = 0x0046, 2
GLYPHS = {"min": "E921", "max": "E922", "restore": "E923", "close": "E8BB"}  # (Segoe Fluent Icons' caption symbols)


_api = []  # (user32 with the argument types of the calls below, made once: see user32())


def user32():
    """user32's functions that this module calls with window, menu and monitor handles, with their argument types (a
    handle is 64 bits on 64-bit Windows: without the types, ctypes passes a Python int as a 32-bit int). Its own copy
    of user32: the types set here do not change the calls of other modules (ctypes.windll.user32 is shared)."""
    if not _api:
        u = ctypes.WinDLL("user32")
        H, HW, UINT, INT = wintypes.HANDLE, wintypes.HWND, wintypes.UINT, ctypes.c_int
        for name, args, res in (
                ("GetSystemMenu", [HW, wintypes.BOOL], wintypes.HMENU),
                ("EnableMenuItem", [wintypes.HMENU, UINT, UINT], wintypes.BOOL),
                ("TrackPopupMenu", [wintypes.HMENU, UINT, INT, INT, INT, HW, ctypes.c_void_p], wintypes.BOOL),
                ("PostMessageW", [HW, UINT, wintypes.WPARAM, wintypes.LPARAM], wintypes.BOOL),
                ("MonitorFromWindow", [HW, wintypes.DWORD], H),
                ("MonitorFromRect", [ctypes.POINTER(wintypes.RECT), wintypes.DWORD], H),
                ("GetMonitorInfoW", [H, ctypes.c_void_p], wintypes.BOOL),
                ("GetWindowRect", [HW, ctypes.POINTER(wintypes.RECT)], wintypes.BOOL),
                ("IsZoomed", [HW], wintypes.BOOL),
                ("IsIconic", [HW], wintypes.BOOL),
                ("GetDpiForWindow", [HW], UINT),
                ("GetSystemMetricsForDpi", [INT, UINT], INT),
                ("ClientToScreen", [HW, ctypes.POINTER(wintypes.POINT)], wintypes.BOOL)):
            try:
                f = getattr(u, name)
            except AttributeError:  # (GetDpiForWindow, GetSystemMetricsForDpi: Windows 10 1607 and later)
                continue
            f.argtypes, f.restype = args, res
        _api.append(u)
    return _api[0]


def window_menu_states(maximized):
    """The window menu's commands, enabled or not, as Windows' own title bar has them."""
    return ((SC_RESTORE, maximized), (SC_MOVE, not maximized), (SC_SIZE, not maximized), (SC_MINIMIZE, True),
            (SC_MAXIMIZE, not maximized), (SC_CLOSE, True))


def _window_menu(hwnd, x, y, maximized):
    """Windows' window menu (Restore, Move, Size, Minimize, Maximize, Close) at the screen point x, y: the command
    chosen goes to the window as the menu of Windows' own title bar sends it (WM_SYSCOMMAND)."""
    u = user32()
    menu = u.GetSystemMenu(wintypes.HWND(hwnd), False)
    if not menu:
        return
    for cmd, on in window_menu_states(maximized):
        u.EnableMenuItem(menu, cmd, 0 if on else MF_GRAYED)
    cmd = u.TrackPopupMenu(menu, TPM_RETURNCMD | TPM_RIGHTBUTTON, x, y, 0, wintypes.HWND(hwnd), None)
    if cmd:
        u.PostMessageW(wintypes.HWND(hwnd), WM_SYSCOMMAND, cmd, 0)


class _TrackMouseEvent(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("dwFlags", wintypes.DWORD), ("hwndTrack", wintypes.HWND),
                ("dwHoverTime", wintypes.DWORD)]


def _leave_message(hwnd):
    """Windows told to send WM_NCMOUSELEAVE when the pointer leaves the non-client part it is on (it sends it only
    when asked)."""
    t = _TrackMouseEvent(ctypes.sizeof(_TrackMouseEvent), 0x2 | 0x10, wintypes.HWND(hwnd), 0)  # (TME_LEAVE, NONCLIENT)
    ctypes.windll.user32.TrackMouseEvent(ctypes.byref(t))


class _WindowPos(ctypes.Structure):
    _fields_ = [("hwnd", wintypes.HWND), ("hwndInsertAfter", wintypes.HWND), ("x", ctypes.c_int), ("y", ctypes.c_int),
                ("cx", ctypes.c_int), ("cy", ctypes.c_int), ("flags", wintypes.UINT)]


class _MonitorInfo(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", wintypes.RECT), ("rcWork", wintypes.RECT),
                ("dwFlags", wintypes.DWORD)]


class _NcCalcSizeParams(ctypes.Structure):
    _fields_ = [("rgrc", wintypes.RECT * 3), ("lppos", ctypes.c_void_p)]


def _glyph_font(btn):
    from PySide6.QtGui import QFont, QFontDatabase
    f = QFont("Segoe Fluent Icons" if "Segoe Fluent Icons" in QFontDatabase.families() else "Segoe MDL2 Assets")
    f.setPixelSize(10)
    btn.setFont(f)


def title_mode(platform, see_through):
    """How the window has the top bar in its title bar: "frame" (a see-through window: a resize frame and no title
    bar, Qt::CustomizeWindowHint; never frameless, which Qt makes layered), "frameless" (Qt::FramelessWindowHint), or
    None (not on Windows' own platform: the tests' and the pictures' off-screen windows)."""
    if platform != "windows":
        return None
    return "frame" if see_through else "frameless"


def flags_for(mode):
    """The window flags of a title mode (None: Qt's own window, with Windows' title bar)."""
    if mode == "frame":
        return Qt.Window | Qt.CustomizeWindowHint
    if mode == "frameless":
        return Qt.Window | Qt.FramelessWindowHint
    return Qt.Window


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
    window's nativeEvent). bar: the top bar (its empty parts are the title bar). framed: title_mode "frame" (Windows'
    own resize frame on the four sides; no WS_CAPTION, so Windows draws no caption buttons of its own)."""

    def __init__(self, win, bar, framed=False):
        super().__init__(win)
        self.win, self.bar, self.framed = win, bar, framed
        self.hwnd = None
        self._down = False
        self._frames = {}  # (dpi, x_axis) -> the resize frame's thickness (asked on each WM_NCHITTEST: kept)
        # (Maximize's look while the pointer is on it, checked until it is off: Windows tells it late or not at all,
        # and too early when Snap layouts opens under the pointer; Maximize kept its pointed-at look after it left)
        self._poll = QTimer(self, interval=100, timeout=self._pointer_check)

    def styles(self):
        """The frame styles the native window gets: the menu and the minimize and maximize boxes (Win+Up, Win+Down,
        the taskbar); WS_CAPTION too when frameless (not with the frame: Windows would draw its caption buttons over
        the top bar, as the frame is extended into the window for Mica)."""
        return WS_THICKFRAME | WS_SYSMENU | WS_MINIMIZEBOX | WS_MAXIMIZEBOX | (0 if self.framed else WS_CAPTION)

    def attach(self):
        """The frame styles put on the native window: once it exists."""
        try:
            self.hwnd = int(self.win.winId())
            u = ctypes.windll.user32
            u.GetWindowLongW.restype = ctypes.c_long
            style = u.GetWindowLongW(wintypes.HWND(self.hwnd), GWL_STYLE)
            u.SetWindowLongW(wintypes.HWND(self.hwnd), GWL_STYLE, ctypes.c_long(style | self.styles()))
            u.SetWindowPos(wintypes.HWND(self.hwnd), None, 0, 0, 0, 0,
                           SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED)
            return True
        except (AttributeError, OSError):
            return False

    def _zoomed(self):
        """Maximized, for Windows (its style): during a restore that Windows starts (a double-click, a drag down,
        Win+Down) Qt says the window is maximized until its WM_SIZE, after the frame is calculated."""
        return bool(user32().IsZoomed(wintypes.HWND(self.hwnd)))

    def maximized_rect(self, near=None):
        """Framed, maximized: the work area of a monitor, with Windows' frame around it (off the screen), as (x, y,
        width, height) in physical pixels; None if Windows does not say. The monitor: the one with most of the
        rectangle near (x, y, width, height: where Windows puts the window, e.g. Win+Shift+Right to the next monitor),
        else the window's monitor now. Qt puts a window without a title bar at the monitor's own corner: under a
        taskbar or another app bar at the top or at the left."""
        u = user32()
        if near is not None:
            x, y, w, h = near
            mon = u.MonitorFromRect(ctypes.byref(wintypes.RECT(x, y, x + w, y + h)), MONITOR_DEFAULTTONEAREST)
        else:
            mon = u.MonitorFromWindow(wintypes.HWND(self.hwnd), MONITOR_DEFAULTTONEAREST)
        info = _MonitorInfo()
        info.cbSize = ctypes.sizeof(_MonitorInfo)
        if not mon or not u.GetMonitorInfoW(mon, ctypes.byref(info)):
            return None
        bx, by, work = self._frame(True), self._frame(False), info.rcWork
        return work.left - bx, work.top - by, work.right - work.left + 2 * bx, work.bottom - work.top + 2 * by

    def _frame(self, x_axis):
        """The resize frame's thickness in physical pixels (as Windows draws it at the window's DPI), kept per DPI."""
        u = user32()
        try:
            dpi = u.GetDpiForWindow(wintypes.HWND(self.hwnd))
        except (AttributeError, OSError):
            dpi = 0
        got = self._frames.get((dpi, x_axis))
        if got is None:
            m = (SM_CXSIZEFRAME if x_axis else SM_CYSIZEFRAME)
            try:
                if not dpi:
                    raise OSError("no DPI of the window")
                got = u.GetSystemMetricsForDpi(m, dpi) + u.GetSystemMetricsForDpi(SM_CXPADDEDBORDER, dpi)
            except (AttributeError, OSError):
                got = u.GetSystemMetrics(m) + u.GetSystemMetrics(SM_CXPADDEDBORDER)
            self._frames[(dpi, x_axis)] = got
        return got

    def handle(self, message):
        """(handled, result) for one native message (not named event: that is QObject's, which Qt calls with its own
        events, e.g. a child added)."""
        msg = wintypes.MSG.from_address(int(message))
        if self.hwnd is None or msg.hWnd != self.hwnd:
            return False, 0
        m = msg.message
        if m == WM_NCCALCSIZE:
            if self.framed:
                return False, 0  # (Windows' own: the frame on the four sides, as Qt counts it)
            if msg.wParam and self._zoomed():  # (the frame that would be off the screen taken off)
                r = _NcCalcSizeParams.from_address(msg.lParam).rgrc[0]
                fx, fy = self._frame(True), self._frame(False)
                r.left += fx
                r.right -= fx
                r.top += fy
                r.bottom -= fy
            return True, 0
        if m == WM_WINDOWPOSCHANGING and self.framed and self._zoomed():
            self._keep_to_work_area(msg.lParam)
            return False, 0
        if m == WM_NCHITTEST:
            p = self._client_point(msg.lParam)
            if self.framed and not self.win.rect().contains(p):
                return False, 0  # (the frame: Windows' own answer, an edge or a corner)
            return True, self.hit(p)
        # a right-click on the title bar: Windows' window menu, as on its own title bar (Qt keeps the right button's
        # non-client messages, so Windows never showed it; Alt+Space is Windows' own)
        if m == WM_NCRBUTTONDOWN and msg.wParam == HTCAPTION:
            return True, 0
        if m == WM_NCRBUTTONUP and msg.wParam == HTCAPTION:
            x, y = ctypes.c_short(msg.lParam & 0xFFFF).value, ctypes.c_short((msg.lParam >> 16) & 0xFFFF).value
            _window_menu(self.hwnd, x, y, self.win.isMaximized())
            return True, 0
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
            if msg.wParam == HTMAXBUTTON:
                _leave_message(self.hwnd)
            self._max_look(hover=msg.wParam == HTMAXBUTTON, down=self._down and msg.wParam == HTMAXBUTTON)
            return False, 0
        if m == WM_NCMOUSELEAVE:
            self._pointer_check()
            return False, 0
        return False, 0

    def _keep_to_work_area(self, lparam):
        """Framed and maximized: a move or a resize changed to the work area and its frame (see maximized_rect). Not
        for a minimize (Windows puts the window far off the screen) or a change of the stacking order only."""
        wp = _WindowPos.from_address(lparam)
        if user32().IsIconic(wintypes.HWND(self.hwnd)) or wp.x <= -30000:
            return
        if wp.flags & SWP_NOMOVE and wp.flags & SWP_NOSIZE:
            return
        # (a new position: the monitor that it is on. Win+Shift+Left or Right moves a maximized window to the next
        # monitor, and the window's monitor now would pull it back)
        want = self.maximized_rect(None if wp.flags & SWP_NOMOVE else self.proposed(wp))
        if want and (wp.x, wp.y, wp.cx, wp.cy) != want:
            wp.x, wp.y, wp.cx, wp.cy = want
            wp.flags &= ~(SWP_NOMOVE | SWP_NOSIZE)

    def proposed(self, wp):
        """Where a WM_WINDOWPOSCHANGING puts the window: (x, y, width, height), with its size now when it keeps it."""
        if wp.flags & SWP_NOSIZE:
            r = wintypes.RECT()
            user32().GetWindowRect(wintypes.HWND(self.hwnd), ctypes.byref(r))
            return wp.x, wp.y, r.right - r.left, r.bottom - r.top
        return wp.x, wp.y, wp.cx, wp.cy

    def _client_point(self, lparam):
        """The message's screen point (physical pixels) in the window's own coordinates (Qt's, logical)."""
        x, y = ctypes.c_short(lparam & 0xFFFF).value, ctypes.c_short((lparam >> 16) & 0xFFFF).value
        origin = wintypes.POINT(0, 0)
        user32().ClientToScreen(wintypes.HWND(self.hwnd), ctypes.byref(origin))
        ratio = self.win.devicePixelRatioF() or 1.0
        # (down, not toward 0: at 125 % the frame's pixel next to the window, -0.8, was the window's own 0)
        return QPoint(math.floor((x - origin.x) / ratio), math.floor((y - origin.y) / ratio))

    def hit(self, p):
        """What the place p (the window's coordinates) is: an edge (frameless only: framed, the edges are Windows'
        frame, outside the window's own area), the maximize button, the title bar, or the window's own."""
        win = self.win
        if not self.framed and not win.isMaximized() and not win.isFullScreen():
            ratio = win.devicePixelRatioF() or 1.0
            edge = max(4, round(self._frame(True) / ratio))
            left, right = p.x() < edge, p.x() >= win.width() - edge
            top, bottom = p.y() < edge, p.y() >= win.height() - edge
            for on, code in ((top and left, HTTOPLEFT), (top and right, HTTOPRIGHT), (bottom and left, HTBOTTOMLEFT),
                             (bottom and right, HTBOTTOMRIGHT), (left, HTLEFT), (right, HTRIGHT), (top, HTTOP),
                             (bottom, HTBOTTOM)):
                if on:
                    return code
        if self._covered(p):  # (a bubble or the Guide's card over the bar: its ✕ and links are clicked, not dragged)
            return HTCLIENT
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

    def _covered(self, p):
        """True when a control that is not the top bar's is drawn at p (a bubble, the Guide's card). The Guide's
        cover itself (a widget as large as the window, under its card) does not count: the bar under it stays the
        title bar, so the window still moves during the Guide."""
        win, bar = self.win, self.bar
        over = win.childAt(p)
        if over is None or over is bar or bar.isAncestorOf(over):
            return False
        return not (over.parentWidget() is win and over.size() == win.size())

    def _max_look(self, hover=False, down=False):
        b = getattr(self.win, "caption", {}).get("max")
        if b is None:
            return
        state = "down" if down else ("hover" if hover else "")
        if (b.property("nc") or "") != state:
            theme.mark(b, nc=state)
        self._poll.start() if state else self._poll.stop()

    def _pointer_check(self):
        """Maximize's look taken off once the pointer is off it."""
        b = getattr(self.win, "caption", {}).get("max")
        if b is None or not b.isVisible() or not b.rect().contains(b.mapFromGlobal(QCursor.pos())):
            self._down = False
            self._max_look()


def install(win, bar, framed=False):
    """The native part (Windows only): returns it, or None (off the screen, as in the tests and the pictures, or when
    Windows refused: then Windows' own title bar stays, and the 3 buttons hide)."""
    if QGuiApplication.platformName() != "windows":
        return None
    native = Native(win, bar, framed)
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
