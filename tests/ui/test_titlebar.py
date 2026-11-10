"""The title bar's native part (ui\\titlebar.py), its logic off the screen (the native window itself is on the real
desktop only). 1.5.0's main window was frameless and see-through (Mica), which Qt makes a layered window: a click on
its transparent pixels (the empty top bar, between a button's words) went to the window below it, so a drag on the
title bar activated the window behind, and a maximized window kept its old picture. Now a see-through window has a
resize frame and no title bar (never Qt's frameless flag), Windows answers for its frame, the right-click on the title
bar shows the window menu, Maximize's look goes when the pointer leaves it, and the native handler is not named
QObject's event (Qt called it with its own events)."""
from ctypes import wintypes

import pytest
from PySide6.QtCore import QPoint, Qt

from helpers import qt

FAKE_HWND = 0x5A5A0  # (no window has it: ClientToScreen then leaves the origin at 0, 0)


@pytest.fixture
def win(devices_window):
    w = devices_window.win
    w.show()
    w.show_page("devices", remember=False)
    w.resize(1040, 760)
    qt.pump(20)
    made = []
    yield w, made
    for n in made:
        n._poll.stop()
        n.deleteLater()
    qt.pump(5)


def _native(w, made, framed):
    from ui import titlebar
    n = titlebar.Native(w, w.topbar, framed=framed)
    n.hwnd = FAKE_HWND
    made.append(n)
    return n


def _centre(w, widget):
    return widget.mapTo(w, QPoint(widget.width() // 2, widget.height() // 2))


def _empty_bar(w):
    """A point of the top bar with nothing on it: between the last screen's button and Help."""
    a = w.nav["settings"].mapTo(w, QPoint(w.nav["settings"].width(), 0)).x()
    b = w.help_btn.mapTo(w, QPoint(0, 0)).x()
    return QPoint((a + b) // 2, w.topbar.mapTo(w, QPoint(0, w.topbar.height() // 2)).y())


def _msg(message, wparam=0, point=None, ratio=1.0):
    m = wintypes.MSG()
    m.hWnd, m.message, m.wParam = FAKE_HWND, message, wparam
    if point is not None:
        x, y = round(point.x() * ratio), round(point.y() * ratio)
        m.lParam = (y & 0xFFFF) << 16 | (x & 0xFFFF)
    return m


def test_a_see_through_window_is_never_frameless(check):
    from ui import titlebar
    modes = (titlebar.title_mode("windows", True), titlebar.title_mode("windows", False),
             titlebar.title_mode("offscreen", True))
    frame, frameless, own = (titlebar.flags_for(m) for m in ("frame", "frameless", None))
    check("titlebar: a see-through window (Mica) gets a resize frame and no title bar (Qt's CustomizeWindowHint), never "
          "Qt's frameless flag (Qt makes a frameless see-through window layered: clicks on its transparent pixels went "
          "to the window below); a window that is not see-through stays frameless; off the screen no native part",
          modes == ("frame", "frameless", None) and bool(frame & Qt.CustomizeWindowHint)
          and not frame & Qt.FramelessWindowHint and bool(frameless & Qt.FramelessWindowHint)
          and not own & (Qt.FramelessWindowHint | Qt.CustomizeWindowHint), (modes, frame, frameless, own))


def test_the_frame_styles(win, check):
    from ui import titlebar as T
    w, made = win
    framed, frameless = _native(w, made, True).styles(), _native(w, made, False).styles()
    both = T.WS_THICKFRAME | T.WS_SYSMENU | T.WS_MINIMIZEBOX | T.WS_MAXIMIZEBOX
    check("titlebar: both ways have the resize frame, the window menu and the minimize and maximize boxes; only the "
          "frameless one has WS_CAPTION (with the frame, Windows would draw its own caption buttons over the top bar)",
          framed & both == both and frameless & both == both and not framed & T.WS_CAPTION
          and frameless & T.WS_CAPTION, (hex(framed), hex(frameless)))


def test_what_each_place_is(win, check):
    from ui import titlebar as T
    w, made = win
    framed, frameless = _native(w, made, True), _native(w, made, False)
    places = {"empty part of the bar": _empty_bar(w), "Devices": _centre(w, w.nav["devices"]),
              "Maximize": _centre(w, w.caption["max"]), "Close": _centre(w, w.caption["close"]),
              "inside the left edge": QPoint(1, w.height() // 2), "inside the top-left corner": QPoint(1, 1),
              "the page": QPoint(w.width() // 2, w.height() // 2)}
    got = {k: (framed.hit(p), frameless.hit(p)) for k, p in places.items()}
    want = {"empty part of the bar": (T.HTCAPTION, T.HTCAPTION), "Devices": (T.HTCLIENT, T.HTCLIENT),
            "Maximize": (T.HTMAXBUTTON, T.HTMAXBUTTON), "Close": (T.HTCLIENT, T.HTCLIENT),
            "inside the left edge": (T.HTCLIENT, T.HTLEFT), "inside the top-left corner": (T.HTCAPTION, T.HTTOPLEFT),
            "the page": (T.HTCLIENT, T.HTCLIENT)}
    check("titlebar: the empty part of the top bar is the title bar, Maximize is Windows' maximize button (Snap "
          "layouts), the screens' buttons and Close are the window's own; framed, the edges inside the window are the "
          "window's (Windows' frame is outside it), frameless they resize it", got == want, got)


def test_which_messages_are_answered(win, check):
    from ui import titlebar as T
    w, made = win
    framed, frameless = _native(w, made, True), _native(w, made, False)
    ratio = w.devicePixelRatioF() or 1.0
    outside, bar = QPoint(-4, w.height() // 2), _empty_bar(w)
    seen = {"framed size": framed.handle(_addr(_msg(T.WM_NCCALCSIZE, 1))),
            "framed frame": framed.handle(_addr(_msg(T.WM_NCHITTEST, point=outside, ratio=ratio))),
            "framed bar": framed.handle(_addr(_msg(T.WM_NCHITTEST, point=bar, ratio=ratio))),
            "frameless frame": frameless.handle(_addr(_msg(T.WM_NCHITTEST, point=outside, ratio=ratio))),
            "right button down on the bar": framed.handle(_addr(_msg(T.WM_NCRBUTTONDOWN, T.HTCAPTION))),
            "another window's": framed.handle(_addr(_other(T.WM_NCHITTEST)))}
    check("titlebar: framed, Windows answers for the frame (its size and the places outside the window: an edge or a "
          "corner) and the top bar is the title bar; frameless, the handler answers for both; the right button on the "
          "title bar is the window menu's (not Qt's); another window's messages are not answered",
          seen == {"framed size": (False, 0), "framed frame": (False, 0), "framed bar": (True, T.HTCAPTION),
                   "frameless frame": (True, T.HTLEFT), "right button down on the bar": (True, 0),
                   "another window's": (False, 0)}, seen)


_kept = []


def _addr(m):
    """The address of a message, as Qt gives nativeEvent (the message kept alive until the test ends)."""
    import ctypes
    _kept.append(m)
    return ctypes.addressof(m)


def _other(message):
    m = _msg(message)
    m.hWnd = FAKE_HWND + 16
    return m


def test_the_window_menu(check):
    from ui import titlebar as T
    states = {maximized: dict(T.window_menu_states(maximized)) for maximized in (False, True)}
    check("titlebar: the window menu has Restore only when maximized, Move, Size and Maximize only when not, and "
          "always Minimize and Close, as Windows' own title bar",
          states[False] == {T.SC_RESTORE: False, T.SC_MOVE: True, T.SC_SIZE: True, T.SC_MINIMIZE: True,
                            T.SC_MAXIMIZE: True, T.SC_CLOSE: True}
          and states[True] == {T.SC_RESTORE: True, T.SC_MOVE: False, T.SC_SIZE: False, T.SC_MINIMIZE: True,
                               T.SC_MAXIMIZE: False, T.SC_CLOSE: True}, states)


def test_maximize_look_goes_with_the_pointer(win, monkeypatch, check):
    from PySide6.QtCore import QCoreApplication, QEvent
    from ui import titlebar as T
    w, made = win
    n = _native(w, made, True)
    b = w.caption["max"]
    QCoreApplication.sendEvent(n, QEvent(QEvent.Type.User))  # (Qt's own event: not the native handler's, 1.5.1)
    on = b.mapToGlobal(QPoint(b.width() // 2, b.height() // 2))

    class Pointer:
        at = on

        @classmethod
        def pos(cls):
            return cls.at
    monkeypatch.setattr(T, "QCursor", Pointer)
    n._max_look(hover=True)
    pointed = (b.property("nc"), n._poll.isActive())
    n._pointer_check()
    still = (b.property("nc"), n._poll.isActive())
    Pointer.at = on + QPoint(0, b.height() * 3)
    n._pointer_check()
    left = (b.property("nc"), n._poll.isActive())
    check("titlebar: Maximize has its pointed-at look while the pointer is on it (checked until it is off: Windows "
          "says it late, or too early when Snap layouts opens), and loses it when the pointer leaves; a Qt event to the "
          "native part is not taken for a native message",
          pointed == ("hover", True) and still == ("hover", True) and left == ("", False), (pointed, still, left))


@pytest.mark.parametrize("see_through", [True, False])
def test_the_window_takes_its_mode(see_through, tmp_path, monkeypatch, stub_app, check):
    # (the window as it is made on Windows' own platform, not shown: a see-through window (Mica) with Qt's frameless
    # flag is layered, the 1.5.0 fault; the review of 2026-11-09: the helpers alone did not show it)
    from PySide6.QtCore import QThreadPool
    from PySide6.QtGui import QGuiApplication
    from helpers import apo
    from switcher import core
    from switcher import devices as D
    from switcher.apo import Apo
    from ui import window as window_module
    from ui import winsys

    class OnWindows:
        def __getattr__(self, name):
            return getattr(QGuiApplication, name)

        @staticmethod
        def platformName():
            return "windows"
    monkeypatch.setattr(window_module, "QGuiApplication", OnWindows())
    monkeypatch.setattr(winsys, "supported_effects", lambda platform, build=None: (see_through, False))
    conf = apo.fake_apo(str(tmp_path))
    eps = [D.Endpoint("{5}", "Headset", "EarPods", D.ACTIVE, False)]
    sw = core.Switcher(str(tmp_path / "s.json"), Apo(conf), endpoints=lambda: eps, playing=lambda: "{5}")
    w = window_module.Window(sw, stub_app)
    try:
        flags = w.windowFlags()
        got = (w._title_mode, w.testAttribute(Qt.WA_TranslucentBackground), bool(flags & Qt.FramelessWindowHint),
               bool(flags & Qt.CustomizeWindowHint), bool(flags & Qt.WindowTitleHint))
    finally:
        qt.wait_for(lambda: not w._checking, 30)
        QThreadPool.globalInstance().waitForDone(30000)
        qt.close(w)
    want = ("frame", True, False, True, False) if see_through else ("frameless", False, True, False, False)
    check("titlebar: the main window on Windows, see-through (Mica): a resize frame and no title bar, never the "
          "frameless flag (Qt makes that layered); not see-through: the frameless flag", got == want, (got, want))


def test_the_frame_pixel_next_to_the_window(win, monkeypatch, check):
    # (the review of 2026-11-09: at 125 % the frame's pixel next to the window, -0.8, was taken as the window's own 0:
    # a press there moved the window and did not resize it)
    from ui import titlebar as T
    w, made = win
    n = _native(w, made, True)
    monkeypatch.setattr(w, "devicePixelRatioF", lambda: 1.25)
    y = round(_empty_bar(w).y() * 1.25)

    def at(x):
        m = _msg(T.WM_NCHITTEST)
        m.lParam = (y & 0xFFFF) << 16 | (x & 0xFFFF)
        return n.handle(_addr(m))
    got = (at(-1), at(0))
    check("titlebar: at 125 %, the frame's pixel next to the window (physical -1) is Windows' (an edge), the window's "
          "first pixel is its own (the title bar)", got == ((False, 0), (True, T.HTCAPTION)), got)


def test_maximize_look_through_the_messages(win, monkeypatch, check):
    # (the review of 2026-11-09: the look as the messages and the timer give it, not by calling the check)
    from ui import titlebar as T
    w, made = win
    n = _native(w, made, True)
    b = w.caption["max"]
    on = b.mapToGlobal(QPoint(b.width() // 2, b.height() // 2))

    class Pointer:
        at = on

        @classmethod
        def pos(cls):
            return cls.at
    monkeypatch.setattr(T, "QCursor", Pointer)
    monkeypatch.setattr(T, "_leave_message", lambda hwnd: None)
    n.handle(_addr(_msg(T.WM_NCMOUSEMOVE, T.HTMAXBUTTON)))
    pointed = b.property("nc")
    n.handle(_addr(_msg(T.WM_NCMOUSELEAVE)))  # (as when Snap layouts opens under the pointer)
    after_leave = b.property("nc")
    Pointer.at = on + QPoint(0, b.height() * 3)
    cleared = qt.wait_for(lambda: (b.property("nc") or "") == "", 2)
    check("titlebar: the pointer on Maximize gives its pointed-at look; a leave message while the pointer is still on "
          "it (Snap layouts opened) keeps it; the timer takes it off once the pointer is off",
          pointed == "hover" and after_leave == "hover" and cleared and not n._poll.isActive(),
          (pointed, after_leave, cleared, n._poll.isActive()))



def test_a_bubble_over_the_bar_is_clicked_not_dragged(win, check):
    # (the review of 2026-11-10: a bubble whose control was scrolled out of view went to the window's top, over the
    # bar, and a click on its ✕ moved the window; the Guide's card the same)
    from PySide6.QtWidgets import QWidget
    from ui import bubble
    from ui import titlebar as T
    w, made = win
    n = _native(w, made, True)
    bar_point = _empty_bar(w)
    b = bubble.tell(w.nav["devices"], "Do this first.")
    cover = None
    try:
        b.move(bar_point.x() - b.width() // 2, 0)  # (over the empty part of the bar)
        b.raise_()
        qt.pump(2)
        x = b.close_btn.mapTo(w, QPoint(b.close_btn.width() // 2, b.close_btn.height() // 2))
        words = b.text.mapTo(w, QPoint(4, b.text.height() // 2))
        on_bubble = (n.hit(x), n.hit(words))
        b.close_now()
        qt.pump(2)
        after = n.hit(bar_point)
        # the Guide's cover: a widget as large as the window (its card is a child of it)
        cover = QWidget(w)
        cover.setGeometry(w.rect())
        card = QWidget(cover)
        card.setGeometry(bar_point.x() - 60, 0, 120, 40)
        cover.show()
        cover.raise_()
        qt.pump(2)
        under_cover = n.hit(QPoint(bar_point.x() - 100, bar_point.y()))
        on_card = n.hit(QPoint(bar_point.x(), 20))
    finally:
        b.close_now()
        if cover is not None:
            qt.close(cover)
    check("titlebar: a bubble or the Guide's card over the top bar is the window's own (its ✕ and words are clicked, "
          "not dragged); the bar is the title bar again when the bubble closes, and under the Guide's cover",
          on_bubble == (T.HTCLIENT, T.HTCLIENT) and after == T.HTCAPTION and under_cover == T.HTCAPTION
          and on_card == T.HTCLIENT, (on_bubble, after, under_cover, on_card))


def test_a_maximized_window_moved_to_another_monitor(win, monkeypatch, check):
    # (the review of 2026-11-10: the work area came from the monitor that the window was on, so Win+Shift+Right to the
    # next monitor could pull a maximized window back)
    import ctypes
    from ui import titlebar as T
    w, made = win
    n = _native(w, made, True)
    asked = []
    monkeypatch.setattr(n, "maximized_rect", lambda near=None: asked.append(near) or (0, 0, 10, 10))

    def changing(x, y, cx, cy, flags):
        wp = T._WindowPos()
        wp.x, wp.y, wp.cx, wp.cy, wp.flags = x, y, cx, cy, flags
        n._keep_to_work_area(ctypes.addressof(wp))
        return wp.x, wp.y, wp.cx, wp.cy
    moved = changing(3000, 20, 1900, 1000, 0)
    sized = changing(0, 0, 1900, 1000, T.SWP_NOMOVE)
    minimized = changing(-32000, -32000, 160, 28, 0)
    real = T.Native.maximized_rect(n, (100, 100, 400, 300))  # (Windows' own answer for a place on this PC's monitor)
    check("titlebar: a maximized window that Windows moves gets the work area of the monitor at its new place (not "
          "of the monitor that it was on); a resize only keeps its monitor; a minimize is left alone; the work area "
          "with the frame has the place in it",
          asked == [(3000, 20, 1900, 1000), None] and moved == (0, 0, 10, 10) and minimized == (-32000, -32000, 160, 28)
          and real is not None and real[0] <= 100 and real[1] <= 100 and real[0] + real[2] >= 500
          and real[1] + real[3] >= 400, (asked, moved, sized, minimized, real))


def test_handles_keep_their_64_bits(check):
    # (EnableMenuItem had no argument types: ctypes passed a menu handle as a 32-bit int)
    import ctypes
    from ctypes import wintypes as W
    from ui import titlebar as T
    u = T.user32()
    big = 0x1_0000_0010  # (no menu has it: Windows answers -1 and does nothing)
    try:
        got = u.EnableMenuItem(big, T.SC_CLOSE, 0)
        error = None
    except ctypes.ArgumentError as e:
        got, error = None, str(e)
    shared = ctypes.windll.user32.EnableMenuItem.argtypes
    check("titlebar: the user32 calls with a window, menu or monitor handle have their argument types (a 64-bit handle "
          "goes through whole), on a copy of user32 of its own (other modules' calls are not changed)",
          error is None and u.EnableMenuItem.argtypes[0] is W.HMENU and u.MonitorFromRect.argtypes
          and u.PostMessageW.argtypes[0] is W.HWND and shared is None and u is T.user32(), (got, error, shared))


def test_the_frame_size_is_kept_per_dpi(win, monkeypatch, check):
    # (the frameless window asked Windows for its frame on each WM_NCHITTEST: now once for each DPI)
    from ui import titlebar as T
    w, made = win
    n = _native(w, made, False)
    u = T.user32()
    dpi, asked = [96], []
    monkeypatch.setattr(u, "GetDpiForWindow", lambda hwnd: dpi[0])
    monkeypatch.setattr(u, "GetSystemMetricsForDpi", lambda m, d: asked.append((m, d)) or (4 if d == 96 else 6))
    first = [n._frame(True) for _ in range(3)]
    for _ in range(5):
        n.hit(QPoint(1, w.height() // 2))
    at_96 = len(asked)
    dpi[0] = 144
    second = n._frame(True)
    check("titlebar: the resize frame's size is asked of Windows once for each DPI (not on each WM_NCHITTEST), and "
          "again after a DPI change", first == [8, 8, 8] and at_96 == 2 and second == 12 and len(asked) == 4,
          (first, at_96, second, asked))


def test_the_names_come_back_only_with_room(win, check):
    # (the review of 2026-11-10 thought the names could come back squeezed: measured here, they come back with room)
    w, made = win
    bar = w.topbar
    w.resize(1400, 760)
    qt.pump(10)
    full = bar.layout().minimumSize().width()  # (the bar's true width with the names)
    went = back = None
    try:
        for width in range(1400, 500, -6):
            w.resize(width, 760)
            qt.pump(3)
            if bar.is_compact():
                went = bar.width()
                break
        for width in range(w.width(), 1400, 2):
            w.resize(width, 760)
            qt.pump(3)
            if not bar.is_compact():
                back = bar.width()
                break
        squeezed = [b.accessibleName() for b in bar._buttons if b.isVisible() and b.width() < b.sizeHint().width()]
    finally:
        w.resize(1040, 760)
        qt.pump(10)
    check("titlebar: the screens' names go only when the bar is narrower than they need, and come back only with "
          "room to spare (never squeezed, no switch to and fro)",
          went is not None and went < full and back is not None and back >= full and squeezed == [],
          (full, went, back, squeezed))


def test_a_hidden_bar_is_measured_when_it_shows(win, check):
    # (2026-11-10: as the window was made, its top bar, hidden and 640 px wide, went compact, and came back as it
    # showed: two text changes and two new layouts for each button, for nothing)
    from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget
    from ui import titlebar
    holder = QWidget(win[0])  # (inside the window: never a window of its own)
    try:
        holder.resize(300, 40)
        bar = titlebar.TopBar()
        bar.setParent(holder)
        row = QHBoxLayout(bar)
        names = ["Make an EQ", "Devices", "Profiles", "Settings"]
        buttons = [QPushButton(n, bar) for n in names]
        for b in buttons:
            row.addWidget(b)
        bar.compact(buttons)
        hidden = (bar.is_compact(), [b.text() for b in buttons])
        holder.show()
        bar.resize(300, 40)
        qt.pump(5)
        narrow = bar.is_compact()
        bar.resize(1400, 40)
        qt.pump(5)
        wide = (bar.is_compact(), [b.text() for b in buttons])
    finally:
        qt.close(holder)
    check("titlebar: a hidden top bar keeps its names (it has no width of its own yet); shown, it is measured: narrow, "
          "only the symbols, and with room, the names", hidden == (False, names) and narrow is True
          and wide == (False, names), (hidden, narrow, wide))
