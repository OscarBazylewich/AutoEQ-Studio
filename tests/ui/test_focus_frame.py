"""The focus frame (ui\\focus_frame.py; the user's decision, 2026-11-16: no button showed clearly that it has the
focus): a frame round the control with the focus, only while the keyboard is in use. Real keys and clicks (QTest, on
the window's native part, as Windows sends them) on a window made as the app's (a button on the window, a scroll area
with a card of controls, a list with a button in each row), light and dark, and what shows is read from the pixels
of the window's picture: Tab, Shift+Tab and the arrow keys show the frame, in its two colours, on a push button, the
accent button and a ✕ button; a click shows none and takes it off, a click in a button's menu too; a notch of the
mouse wheel on a drop-down list (it gives the list the focus) shows none, and one on the page leaves the frame; a key
on a control that a click gave the focus shows it; it follows the focus that the code moves while the keyboard is in
use; it changes no control's size, place or pixels; it goes with its control (a scroll area, a list that scrolls,
hidden, moved, deleted); it is not there while another window is active, and a window that opens shows it from the
first key in it; one move of the focus takes less than 1 ms, and the frame's code does not run for the events of
other controls.

The theme is applied in a Python of its own, as in test_theme.py (applied here, it would stay for the other tests of
this folder). FRAME is that Python's code: it prints what it saw as one JSON line, and the checks below read it. On
the code before the focus frame it runs too (no ui.focus_frame there), and each check fails with what was seen.
"""
import pytest

from helpers import qt, session, subproc

COVERS = ("ui.focus_frame", "ui.theme", "ui.theme_tokens", "ui.theme_sheet")

FRAME = r'''
import json, sys, time
sys.path.insert(0, sys.argv[1])
from PySide6.QtCore import QEvent, QPoint, QPointF, QRect, Qt, QTimer
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (QApplication, QCheckBox, QDialog, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
                               QListWidget, QListWidgetItem, QMenu, QPushButton, QRadioButton, QScrollArea, QSlider,
                               QToolButton, QVBoxLayout, QWidget)
qapp = QApplication([])
from ui import theme, theme_tokens
from ui.search_combo import SearchCombo
try:
    from ui import focus_frame
except ImportError:  # (the code before the focus frame: every check of it then fails, with what was seen)
    focus_frame = None
theme.accent_palette = lambda: theme_tokens.DEFAULT_ACCENT


def build():
    """A window as the app's: a button and a label on the window itself, then a scroll area with a card of controls,
    a list with a button in each row, a button at the right edge of the scroll area's view, and buttons further
    down; last (in the Tab order too), a button with a menu, whose first item moves the focus as the app does."""
    w = {}
    win = w["win"] = QWidget()
    outer = QVBoxLayout(win)
    top = QHBoxLayout()
    outer.addLayout(top)
    w["top"] = QPushButton("Help")
    w["label"] = QLabel("A label: a click here moves no focus")
    top.addWidget(w["top"])
    top.addWidget(w["label"])
    top.addStretch(1)
    area = w["area"] = QScrollArea()
    area.setWidgetResizable(True)
    area.setFocusPolicy(Qt.NoFocus)
    outer.addWidget(area)
    inner = QWidget()
    area.setWidget(inner)
    lay = w["lay"] = QVBoxLayout(inner)
    card = QGroupBox("A card")
    lay.addWidget(card)
    g = w["card"] = QVBoxLayout(card)
    row = QHBoxLayout()
    g.addLayout(row)
    w["accent"] = QPushButton("Calculate")
    theme.mark(w["accent"], primary=True)
    w["push"] = QPushButton("Find…")
    w["x"] = QToolButton()
    w["x"].setText("✕")
    theme.mark(w["x"], quiet=True)
    w["more"] = QPushButton("Queue…")
    for k in ("accent", "push", "x", "more"):
        row.addWidget(w[k])
    row.addStretch(1)
    w["tick"], w["round1"], w["round2"] = QCheckBox("Tick box"), QRadioButton("One"), QRadioButton("Two")
    w["round1"].setChecked(True)
    w["combo"] = SearchCombo()
    w["combo"].addItems(["One", "Two"])
    w["slider"] = QSlider(Qt.Horizontal)
    w["own"] = QSlider(Qt.Horizontal)
    w["own"].setProperty("ownFocus", True)  # (a control that draws its own keyboard focus)
    w["edit"] = QLineEdit("a text box")
    for k in ("tick", "round1", "round2", "combo", "slider", "own", "edit"):
        g.addWidget(w[k], 0, Qt.AlignLeft)
    lst = w["list"] = QListWidget()
    lst.setFixedHeight(110)
    lst.setFocusPolicy(Qt.NoFocus)
    w["rows"] = []
    for i in range(8):
        it = QListWidgetItem(lst)
        rw = QWidget()
        rl = QHBoxLayout(rw)
        rl.setContentsMargins(8, 4, 8, 4)
        rl.addWidget(QLabel("Row %d" % i))
        rl.addStretch(1)
        rb = QPushButton("Use")
        rl.addWidget(rb)
        it.setSizeHint(rw.sizeHint())
        lst.setItemWidget(it, rw)
        w["rows"].append(rb)
    g.addWidget(lst)
    edge_row = QHBoxLayout()
    edge_row.setContentsMargins(0, 0, 0, 0)
    lay.addLayout(edge_row)
    edge_row.addStretch(1)
    w["edge"] = QPushButton("At the edge")
    edge_row.addWidget(w["edge"])
    w["low"] = [QPushButton("Lower button %d" % i) for i in range(10)]
    for b in w["low"]:
        lay.addWidget(b, 0, Qt.AlignLeft)
    lay.setContentsMargins(12, 12, 0, 12)
    w["menu button"] = QPushButton("Use on device")
    w["menu"] = QMenu(w["menu button"])
    w["item"] = w["menu"].addAction("An item")
    w["item"].triggered.connect(lambda: w["top"].setFocus(Qt.OtherFocusReason))
    w["menu"].addAction("Another item")
    w["menu button"].setMenu(w["menu"])
    top.addWidget(w["menu button"])
    win.resize(560, 640)
    win.show()
    win.activateWindow()
    QTest.qWaitForWindowActive(win, 3000)
    for _ in range(5):
        qapp.processEvents()
    return w


def run(look):
    theme.apply(qapp, dark=look == "dark", contrast=False)
    t = theme.tokens()
    outer_c = t.get("focus_outer", t["ink"])
    inner_c = t.get("focus_inner", "#ffffff" if look == "light" else "#000000")
    w = build()
    win, handle = w["win"], w["win"].windowHandle()
    d = {"colours": [outer_c, inner_c, t["ink"], t["card"], t["accent"]]}

    def box(c):
        return QRect(c.mapTo(win, QPoint(0, 0)), c.size())

    def picture():
        qapp.processEvents()
        return win.grab().toImage()

    def sides(c, img=None):
        """The picture's colours where the frame of c has its two lines, at the middle of each side: the outer line
        (2 px: both read), then the inner one. For the left, top, right and bottom side."""
        img = img or picture()
        b = box(c)
        cx, cy, l, tp, r, bt = b.center().x(), b.center().y(), b.left(), b.top(), b.right(), b.bottom()
        pts = (((l - 3, cy), (l - 2, cy), (l - 1, cy)), ((cx, tp - 3), (cx, tp - 2), (cx, tp - 1)),
               ((r + 3, cy), (r + 2, cy), (r + 1, cy)), ((cx, bt + 3), (cx, bt + 2), (cx, bt + 1)))
        return [[img.pixelColor(x, y).name() if img.rect().contains(x, y) else None for x, y in side] for side in pts]

    def framed(c, img=None):
        return all(s == [outer_c, outer_c, inner_c] for s in sides(c, img))

    def rings():
        return [r for r in win.findChildren(QWidget, "focusFrame") if r.isVisible() and r.window() is win]

    def none(c, img=None):
        """No line of a frame at c, and no frame anywhere in the window."""
        return not any(s == [outer_c, outer_c, inner_c] for s in sides(c, img)) and not rings()

    def on():
        f = focus_frame.framed() if focus_frame is not None else None
        return next((k for k, v in w.items() if v is f), None if f is None else "?")

    def differ(a, b, rect=None, corners=0):
        """How many pixels differ between two pictures (in rect, without its four corners when asked)."""
        r = rect or a.rect()
        n = 0
        for y in range(r.top(), r.bottom() + 1):
            for x in range(r.left(), r.right() + 1):
                if corners and min(x - r.left(), r.right() - x) < corners and min(y - r.top(), r.bottom() - y) < corners:
                    continue
                n += a.pixel(x, y) != b.pixel(x, y)
        return n

    def key(k, mod=Qt.NoModifier):
        QTest.keyClick(handle, k, mod)
        qapp.processEvents()

    def click(c, at=None):
        QTest.mouseClick(handle, Qt.LeftButton, Qt.NoModifier, c.mapTo(win, at or QPoint(5, 5)))
        qapp.processEvents()

    def focus():
        f = QApplication.focusWidget()
        return next((k for k, v in w.items() if v is f), type(f).__name__ if f is not None else None)

    def by_code(c):
        c.setFocus(Qt.OtherFocusReason)
        qapp.processEvents()

    def places():
        return {k: (v.geometry().getRect(), v.sizeHint().toTuple()) for k, v in w.items()
                if isinstance(v, QWidget) and k != "win"}

    # ---- the start: a click (the mouse in use), then the focus put on a button by the code
    click(w["label"])
    by_code(w["top"])
    start = picture()
    geometry = places()
    d["start"] = {"focus": focus(), "no frame": none(w["top"], start)}
    # ---- Tab: the accent button, a push button, a ✕ button
    tabbed = {}
    for want in ("accent", "push", "x"):
        key(Qt.Key_Tab)
        tabbed[want] = {"focus": focus(), "frame": framed(w[want]), "left side": sides(w[want])[0], "on": on()}
    d["tab"] = tabbed
    d["places kept"] = places() == geometry
    d["frames in the window"] = len(rings())
    # ---- a click on a label (it takes no focus): the frame goes, and the picture is the one of the start
    before = framed(w["x"])
    click(w["label"])
    after = picture()
    d["click on a label"] = {"frame before": before, "focus": focus(), "no frame": none(w["x"], after),
                             "pixels different from the start": differ(start, after)}
    # ---- a key on the control that has the focus without the keyboard: the frame shows on it
    key(Qt.Key_Space)
    d["a key after a click"] = {"focus": focus(), "frame": framed(w["x"]), "on": on()}
    before = framed(w["x"])
    click(w["x"])
    d["click on the framed control"] = {"frame before": before, "focus": focus(), "no frame": none(w["x"])}
    key(Qt.Key_Shift)
    key(Qt.Key_C, Qt.ControlModifier)
    d["Shift alone, then Ctrl+C"] = {"no frame": none(w["x"])}
    # ---- Shift+Tab; then a click on another button gives it the focus and no frame; the code then moves the focus
    key(Qt.Key_Tab, Qt.ShiftModifier)
    d["Shift+Tab"] = {"focus": focus(), "frame": framed(w["push"]), "on": on()}
    before = framed(w["push"])
    click(w["accent"])
    d["click on another button"] = {"frame before": before, "focus": focus(), "no frame": none(w["accent"])}
    by_code(w["push"])
    d["the code moves the focus, mouse in use"] = {"focus": focus(), "no frame": none(w["push"])}
    # ---- with the keyboard in use, the frame follows the focus that the code moves
    key(Qt.Key_Tab)
    by_code(w["accent"])
    d["the code moves the focus, keyboard in use"] = {"focus": focus(), "frame": framed(w["accent"]), "on": on()}
    w["accent"].clearFocus()
    qapp.processEvents()
    d["nothing has the focus"] = {"focus": focus(), "no frame": none(w["accent"])}
    # ---- the arrow keys (round buttons), after a click
    click(w["round1"])
    by_click = none(w["round1"])
    key(Qt.Key_Down)
    d["arrow key"] = {"no frame after the click": by_click, "focus": focus(), "frame": framed(w["round2"]),
                      "on": on()}
    # ---- the other types that get the frame, and the two that do not
    kinds = {}
    for k in ("tick", "combo", "slider", "own", "edit"):
        by_code(w[k])
        kinds[k] = {"focus": focus(), "frame": framed(w[k]), "frames": len(rings())}
    e = box(w["edit"])
    kinds["edit"]["its own line"] = picture().pixelColor(e.center().x(), e.bottom()).name() == t["accent"]
    d["kinds"] = kinds
    # ---- the frame changes no pixel of the control itself (its rounded corners left out: the frame goes round them):
    # each control reached with Tab, against the window's picture with no keyboard focus
    click(w["label"])
    by_code(w["top"])
    plain = picture()
    inside = {}
    for _ in range(8):
        key(Qt.Key_Tab)
        k = focus()
        inside[k] = differ(plain, picture(), box(w[k]), corners=4) if isinstance(w.get(k), QWidget) else None
    d["pixels changed in the control"] = inside
    # ---- in a list: the button of a row, and the list scrolled (the view moves all that is in it)
    by_code(w["rows"][1])
    ring = rings()[0] if rings() else None
    in_list = {"frame": framed(w["rows"][1]),
               "in the list's view": ring is not None and ring.parentWidget() is w["list"].viewport()}
    w["list"].verticalScrollBar().setValue(w["list"].verticalScrollBar().value() + 1)
    qapp.processEvents()
    in_list["frame after the scroll"] = framed(w["rows"][1])
    d["list"] = in_list
    # ---- in a scroll area: the frame goes with its control, and the view cuts it
    low, bar, view = w["more"], w["area"].verticalScrollBar(), w["area"].viewport()
    by_code(low)
    ring = rings()[0] if rings() else None
    sc = {"frame": framed(low), "in the view": ring is not None and ring.parentWidget() is view}
    was = box(low).top()
    bar.setValue(23)
    qapp.processEvents()
    sc["frame after a scroll of 23"] = box(low).top() == was - 23 and framed(low)
    vp_top = view.mapTo(win, QPoint(0, 0)).y()
    bar.setValue(bar.value() + (box(low).top() - vp_top) + 12)  # (its top 12 px above the view)
    qapp.processEvents()
    img, b = picture(), box(low)
    sc["cut by the view"] = {
        "the control's top is out": b.top() == vp_top - 12,
        "lines at its left in the view": [img.pixelColor(b.left() - k, vp_top + 6).name() for k in (3, 2, 1)],
        "pixels of the frame above the view": sum(img.pixel(x, y) != start.pixel(x, y)
                                                  for x in range(b.left() - 3, b.right() + 4)
                                                  for y in range(vp_top - 6, vp_top))}
    bar.setValue(0)
    qapp.processEvents()
    d["scroll area"] = sc
    # ---- at the edge of the view: no room for the frame at the right, it comes in to the edge
    by_code(w["edge"])
    w["area"].ensureWidgetVisible(w["edge"], 0, 60)
    qapp.processEvents()
    img, b = picture(), box(w["edge"])
    vp = QRect(view.mapTo(win, QPoint(0, 0)), view.size())
    all_sides = sides(w["edge"], img)
    d["edge"] = {"room at the right": vp.right() - b.right(),
                 "line at the view's edge": [img.pixelColor(vp.right() - k, b.center().y()).name() for k in (0, 1)],
                 "the other sides": all_sides[:2] + all_sides[3:]}
    bar.setValue(0)
    qapp.processEvents()
    # ---- the control changes its size, moves, hides, shows, is deleted
    c = w["push"]
    by_code(c)
    life = {"frame": framed(c)}
    c.setFixedWidth(c.width() + 40)
    qapp.processEvents()
    life["frame after it got wider"] = framed(c)
    was = box(c).top()
    w["card"].insertSpacing(0, 17)
    qapp.processEvents()
    life["frame after it moved"] = box(c).top() == was + 17 and framed(c)
    c.hide()
    qapp.processEvents()
    f = QApplication.focusWidget()
    life["hidden"] = {"the focus went to": focus(), "one frame, on the control with the focus now":
                      len(rings()) == 1 and f is not None and f is not c and framed(f)}
    c.show()
    by_code(c)
    life["frame when it shows again"] = framed(c)
    c.deleteLater()
    w["push"] = None
    qapp.processEvents()
    qapp.processEvents()
    f = QApplication.focusWidget()
    life["deleted"] = {"the focus went to": focus(), "one frame at most, on the control with the focus now":
                       not rings() if f is None else (len(rings()) == 1 and framed(f))}
    d["life"] = life
    # ---- another window of the app active: no frame here; that window shows the frame after a key in it; this one
    # active again: its frame is back
    by_code(w["accent"])
    act = {"frame": framed(w["accent"])}
    dlg = QDialog(win)
    dl = QVBoxLayout(dlg)
    d_ok, d_no = QPushButton("OK"), QPushButton("Cancel")
    dl.addWidget(QLabel("A question"))
    dl.addWidget(d_ok)
    dl.addWidget(d_no)
    dlg.show()
    dlg.activateWindow()
    QTest.qWaitForWindowActive(dlg, 3000)
    qapp.processEvents()
    def in_dialog(c):
        dimg = dlg.grab().toImage()
        b = QRect(c.mapTo(dlg, QPoint(0, 0)), c.size())
        cx, cy = b.center().x(), b.center().y()
        return [dimg.pixelColor(x, y).name() for x, y in ((b.left() - 3, cy), (b.left() - 1, cy), (cx, b.top() - 3),
                                                          (cx, b.bottom() + 3), (b.right() + 3, cy))]
    f = QApplication.focusWidget()
    other = {"no frame in the window behind": none(w["accent"]),
             "no frame in the dialog before a key in it": f in (d_ok, d_no) and not [
                 r for r in dlg.findChildren(QWidget, "focusFrame") if r.isVisible()]}
    QTest.keyClick(dlg.windowHandle(), Qt.Key_Tab)
    qapp.processEvents()
    f = QApplication.focusWidget()
    other["the frame of the dialog's button with the focus, after Tab in it"] = (in_dialog(f) if f in (d_ok, d_no)
                                                                               else None)
    act["another window active"] = other
    dlg.close()
    win.activateWindow()
    QTest.qWaitForWindowActive(win, 3000)
    qapp.processEvents()
    act["active again"] = {"focus": focus(), "frame": framed(w["accent"])}
    dlg.deleteLater()
    qapp.processEvents()
    d["windows"] = act
    # ---- a menu that a button opens: it takes the keys and the clicks itself, and moves no focus
    menu, mb = w["menu"], w["menu button"]

    def in_menu(open_it, act):
        """open_it() opens the menu (Qt stays in the menu until it closes); act() is called once while it shows.
        Whether the menu showed."""
        done = []

        def poll(n=0):
            if menu.isVisible():
                act()
                done.append(True)
            elif n < 150:
                QTimer.singleShot(20, lambda: poll(n + 1))
            else:
                done.append(False)
        QTimer.singleShot(20, poll)
        open_it()
        end = time.perf_counter() + 6
        while (not done or menu.isVisible()) and time.perf_counter() < end:
            QTest.qWait(20)
        qapp.processEvents()
        return bool(done and done[0])

    def tab_to_menu_button():
        by_code(w["low"][-1])
        key(Qt.Key_Tab)
        return {"focus": focus(), "frame": framed(mb)}
    in_it = menu.windowHandle  # (the menu's native part, made when it first shows)
    m = {"Tab to the button": tab_to_menu_button()}
    showed = in_menu(lambda: key(Qt.Key_Space), lambda: QTest.mouseClick(
        in_it(), Qt.LeftButton, Qt.NoModifier, menu.actionGeometry(w["item"]).center()))
    m["a click on an item"] = {"the menu showed": showed, "focus": focus(), "no frame": none(w["top"])}
    again = tab_to_menu_button()
    showed = in_menu(lambda: key(Qt.Key_Space), lambda: QTest.mouseClick(
        in_it(), Qt.LeftButton, Qt.NoModifier, QPoint(-30, -30)))
    m["a click outside the menu"] = {"frame before": again["frame"], "the menu showed": showed, "focus": focus(),
                                     "no frame": none(mb)}
    showed = in_menu(lambda: click(mb), lambda: (QTest.keyClick(handle, Qt.Key_Down),
                                                 QTest.keyClick(handle, Qt.Key_Return)))
    m["keys in a menu that a click opened"] = {"the menu showed": showed, "focus": focus(),
                                               "frame": framed(w["top"])}
    again = tab_to_menu_button()
    showed = in_menu(lambda: key(Qt.Key_Space), lambda: QTest.keyClick(in_it(), Qt.Key_Escape))
    m["Esc in the menu"] = {"frame before": again["frame"], "the menu showed": showed, "focus": focus(),
                            "frame": framed(mb)}
    d["menu"] = m
    # ---- the mouse wheel: a notch on the page moves no focus; a notch on a drop-down list gives the list the focus,
    # with no mouse button down
    def wheel(c, at=None, events=True):
        """One notch of the mouse wheel towards the person, the pointer on c (to the window's native part)."""
        QTest.wheelEvent(handle, QPointF(c.mapTo(win, at or c.rect().center())), QPoint(0, -120))
        if events:
            qapp.processEvents()

    def no_keyboard():
        return focus_frame is not None and not focus_frame.keyboard_in_use()
    nothing_there = QPoint(view.width() - 30, 40)  # (in the card, right of its buttons: only the page takes the wheel)
    bar.setValue(0)
    click(w["label"])
    by_code(w["combo"])
    key(Qt.Key_Tab)
    whl = {"Tab": {"focus": focus(), "frame": framed(w["slider"])}}
    was, top = box(w["slider"]).top(), bar.value()
    wheel(view, nothing_there)
    moved = bar.value() - top
    whl["a notch on the page"] = {"the page moved": moved > 0, "focus": focus(),
                                  "frame, moved with its control": box(w["slider"]).top() == was - moved
                                  and framed(w["slider"])}
    bar.setValue(0)
    by_code(w["tick"])
    whl["the code moves the focus after it"] = {"focus": focus(), "frame": framed(w["tick"])}
    wheel(w["combo"])
    whl["a notch on a drop-down list"] = {"focus": focus(), "no frame": none(w["combo"]),
                                          "the keyboard is not in use": no_keyboard()}
    key(Qt.Key_Tab)
    whl["Tab after it"] = {"focus": focus(), "frame": framed(w["slider"])}
    w["slider"].clearFocus()
    qapp.processEvents()
    wheel(w["combo"])
    whl["a notch on the list while nothing has the focus"] = {"focus": focus(), "no frame": none(w["combo"]),
                                                              "the keyboard is not in use": no_keyboard()}
    # (no pass of the event loop between the notch and the key, as when the two waited while the app was busy)
    by_code(w["tick"])
    key(Qt.Key_Tab)
    before = framed(w["round2"])
    wheel(view, nothing_there, events=False)
    key(Qt.Key_Tab)
    whl["a notch on the page, then Tab at once"] = {"frame before": before, "focus": focus(),
                                                    "frame": framed(w["combo"])}
    bar.setValue(0)
    qapp.processEvents()
    d["wheel"] = whl
    # ---- the time of one move of the focus, and what the frame's code runs on
    if focus_frame is not None:
        a, b2, far = w["accent"], w["more"], w["top"]
        key(Qt.Key_Tab)
        times = {}
        for name, pair in (("in one parent", (a, b2)), ("to another parent", (far, b2))):
            took = []
            for i in range(200):
                t0 = time.perf_counter()
                pair[i % 2].setFocus(Qt.OtherFocusReason)
                took.append(time.perf_counter() - t0)
            times[name] = round(sorted(took)[len(took) // 2] * 1e6, 1)
        click(w["label"])
        took = []
        for i in range(200):
            t0 = time.perf_counter()
            (a, b2)[i % 2].setFocus(Qt.OtherFocusReason)
            took.append(time.perf_counter() - t0)
        times["mouse in use"] = round(sorted(took)[len(took) // 2] * 1e6, 1)
        d["microseconds for one move of the focus"] = times
        calls = []

        def prof(frame, event, arg):
            if event == "call" and frame.f_code.co_filename.replace("\\", "/").endswith("ui/focus_frame.py"):
                calls.append(frame.f_code.co_name)

        def events(n):
            """n times three events that have nothing to do with the focus, for controls that the frame does not
            watch: a plain event, a mouse move and a paint."""
            other = w["low"][5]
            for i in range(n):
                QApplication.sendEvent(w["label"], QEvent(QEvent.User))
                QApplication.sendEvent(other, QMouseEvent(QEvent.MouseMove, QPointF(3 + i % 5, 3),
                                                          QPointF(other.mapToGlobal(QPoint(3 + i % 5, 3))),
                                                          Qt.NoButton, Qt.NoButton, Qt.NoModifier))
                w["label"].repaint()
            qapp.processEvents()
        ran = {}
        by_code(a)  # (the mouse in use: only the control with the focus is watched, for a key)
        sys.setprofile(prof)
        events(300)
        QTest.mouseMove(handle, w["label"].mapTo(win, QPoint(9, 9)))  # (the mouse moves over the window)
        QTest.mouseMove(handle, w["label"].mapTo(win, QPoint(19, 9)))
        qapp.processEvents()
        sys.setprofile(None)
        ran["mouse in use"] = len(calls)
        calls.clear()
        key(Qt.Key_Tab)
        ran["frame shown meanwhile"] = framed(QApplication.focusWidget())
        sys.setprofile(prof)
        events(300)
        sys.setprofile(None)
        ran["keyboard in use"] = len(calls)
        d["calls of the frame's code for 900 events of other controls"] = ran
    win.close()
    win.deleteLater()
    qapp.processEvents()
    return d


print(json.dumps({look: run(look) for look in ("light", "dark")}))
'''


@pytest.fixture(scope="module")
def seen():
    """What FRAME saw, in light and in dark (run once for the file)."""
    out = subproc.run_python(FRAME, session.SESSION.app, timeout=240)
    return out.data or {}, out.stderr[-600:]


def _both(seen, part):
    data, err = seen
    return {look: (data.get(look) or {}).get(part) for look in ("light", "dark")}, err


def _colours(seen, look):
    c = ((seen[0].get(look) or {}).get("colours") or [None] * 5)
    return {"outer": c[0], "inner": c[1], "ink": c[2], "card": c[3], "accent": c[4]}


def test_tab_shows_the_frame_in_its_colours(seen, check):
    tab, err = _both(seen, "tab")
    want = {look: {k: {"focus": k, "frame": True, "left side": [_colours(seen, look)["outer"]] * 2
                       + [_colours(seen, look)["inner"]], "on": k} for k in ("accent", "push", "x")}
            for look in ("light", "dark")}
    check("focus frame: Tab shows the frame on the accent button, on a push button and on a ✕ button: a 2 px line in "
          "the frame's outer colour and a 1 px line in its inner colour, on all four sides, light and dark (no button "
          "showed clearly that it has the focus)", tab == want and all(tab.values()), tab if any(tab.values()) else err)
    from ui import theme_tokens
    low = []
    for dark in (False, True):
        t = theme_tokens.build(dark)
        if "focus_outer" not in t:
            low.append("no colours for the frame")
            continue
        low += [(dark, a, b, round(theme_tokens.contrast(t[a], t[b]), 2))
                for a, b in (("focus_outer", "card"), ("focus_outer", "bg"), ("focus_inner", "accent"),
                             ("focus_outer", "focus_inner")) if theme_tokens.contrast(t[a], t[b]) < 3]
    check("focus frame: its outer line keeps 3:1 on a card and on the window, and its inner line 3:1 on the accent "
          "button and against the outer line, light and dark (clear on the accent button too)", not low, low)
    start, _ = _both(seen, "start")
    check("focus frame: the focus put on a button by the code, after a click, shows no frame",
          all(v == {"focus": "top", "no frame": True} for v in start.values()), start)


def test_a_click_shows_none_and_takes_it_off(seen, check):
    parts = {name: _both(seen, name)[0] for name in ("click on a label", "click on the framed control",
                                                     "click on another button",
                                                     "the code moves the focus, mouse in use",
                                                     "Shift alone, then Ctrl+C")}
    want = {"click on a label": {"frame before": True, "focus": "x", "no frame": True,
                                 "pixels different from the start": 0},
            "click on the framed control": {"frame before": True, "focus": "x", "no frame": True},
            "click on another button": {"frame before": True, "focus": "accent", "no frame": True},
            "the code moves the focus, mouse in use": {"focus": "push", "no frame": True},
            "Shift alone, then Ctrl+C": {"no frame": True}}
    bad = {k: v for k, v in parts.items() if any(v[look] != want[k] for look in v)}
    check("focus frame: a click takes the frame off (on a label that takes no focus: the window's picture is then, "
          "pixel for pixel, the one before the keyboard was used; on the control with the frame), a click on a "
          "button gives it the focus and no frame, the focus that the code moves after a click shows none, and "
          "Shift by itself or a key with Ctrl (Ctrl+C) shows none", not bad, bad or seen[1])


def test_keys_show_it(seen, check):
    parts = {name: _both(seen, name)[0] for name in ("a key after a click", "Shift+Tab", "arrow key",
                                                     "the code moves the focus, keyboard in use",
                                                     "nothing has the focus")}
    want = {"a key after a click": {"focus": "x", "frame": True, "on": "x"},
            "Shift+Tab": {"focus": "push", "frame": True, "on": "push"},
            "arrow key": {"no frame after the click": True, "focus": "round2", "frame": True, "on": "round2"},
            "the code moves the focus, keyboard in use": {"focus": "accent", "frame": True, "on": "accent"},
            "nothing has the focus": {"focus": None, "no frame": True}}
    bad = {k: v for k, v in parts.items() if any(v[look] != want[k] for look in v)}
    check("focus frame: Shift+Tab and an arrow key that moves the focus (round buttons, after a click) show the "
          "frame; a key pressed on a control that a click gave the focus (Space on a ✕ button) shows it there; with "
          "the keyboard in use it follows the focus that the code moves, and it goes when nothing has the focus",
          not bad, bad or seen[1])


def test_which_controls_get_it(seen, check):
    kinds, err = _both(seen, "kinds")
    want = {"tick": {"focus": "tick", "frame": True, "frames": 1},
            "combo": {"focus": "combo", "frame": True, "frames": 1},
            "slider": {"focus": "slider", "frame": True, "frames": 1},
            "own": {"focus": "own", "frame": False, "frames": 0},
            "edit": {"focus": "edit", "frame": False, "frames": 0, "its own line": True}}
    check("focus frame: a tick box, a drop-down list and a slider get the frame too; a text box keeps its own focus "
          "style (the accent's line under it) and gets none, and a control that draws its own keyboard focus (the "
          "property ownFocus) gets none", all(v == want for v in kinds.values()), kinds if any(kinds.values()) else err)


def test_no_control_changes(seen, check):
    kept, err = _both(seen, "places kept")
    inside, _ = _both(seen, "pixels changed in the control")
    count, _ = _both(seen, "frames in the window")
    want = dict.fromkeys(("accent", "push", "x", "more", "tick", "round2", "combo", "slider"), 0)
    check("focus frame: with the frame shown, every control of the window keeps its place, its size and its size "
          "hint, and each control that Tab gives the focus keeps its own pixels (the frame is drawn round it; "
          "Fusion's own focus box, drawn in a button, a tick box and a round button after a key, is gone): one frame "
          "in the window", all(kept.values()) and all(v == want for v in inside.values())
          and all(v == 1 for v in count.values()), (kept, inside, count) if any(inside.values()) else err)


def test_it_goes_with_its_control(seen, check):
    lst, err = _both(seen, "list")
    check("focus frame: the frame of a button in a list's row is in the list's view, and stays on its button when "
          "the list scrolls (the view moves all that is in it)",
          all(v == {"frame": True, "in the list's view": True, "frame after the scroll": True} for v in lst.values()),
          lst if any(lst.values()) else err)
    sc, _ = _both(seen, "scroll area")
    want = {look: {"frame": True, "in the view": True, "frame after a scroll of 23": True,
                   "cut by the view": {"the control's top is out": True,
                                       "lines at its left in the view": [_colours(seen, look)["outer"]] * 2
                                       + [_colours(seen, look)["inner"]],
                                       "pixels of the frame above the view": 0}} for look in sc}
    check("focus frame: in a scroll area the frame is in the area's view: it moves with its control when the page "
          "scrolls, and a control half out of the view has its frame cut with it (no pixel of it out of the view)",
          sc == want and all(sc.values()), sc)
    edge, _ = _both(seen, "edge")
    want = {look: {"room at the right": 0, "line at the view's edge": [_colours(seen, look)["outer"]] * 2,
                   "the other sides": [[_colours(seen, look)["outer"]] * 2 + [_colours(seen, look)["inner"]]] * 3}
            for look in edge}
    check("focus frame: a button at the right edge of a scroll area's view, with no room for the frame there, has "
          "its frame's line at the view's edge, and the three other sides as everywhere (a table's first row and a "
          "button at the edge of a page had no line there)", edge == want and all(edge.values()), edge)
    life, _ = _both(seen, "life")
    want = {"frame": True, "frame after it got wider": True, "frame after it moved": True,
            "hidden": {"one frame, on the control with the focus now": True}, "frame when it shows again": True,
            "deleted": {"one frame at most, on the control with the focus now": True}}

    def without_names(v):  # (which control Qt gives the focus then is Qt's own choice: only told in the detail)
        return {k: ({a: b for a, b in x.items() if a != "the focus went to"} if isinstance(x, dict) else x)
                for k, x in (v or {}).items()}
    check("focus frame: the frame stays on a control that gets wider or moves; when the control hides or is "
          "deleted, the frame goes to the control that gets the focus (none is left behind), and it is back on a "
          "control that shows again with the focus", all(without_names(v) == want for v in life.values()), life)


def test_only_in_the_active_window(seen, check):
    act, err = _both(seen, "windows")
    want = {look: {"frame": True,
                   "another window active": {
                       "no frame in the window behind": True,
                       "no frame in the dialog before a key in it": True,
                       "the frame of the dialog's button with the focus, after Tab in it":
                           [_colours(seen, look)[k] for k in ("outer", "inner", "outer", "outer", "outer")]},
                   "active again": {"focus": "accent", "frame": True}} for look in act}
    check("focus frame: while a dialog of the window is active, the window behind shows no frame; the dialog shows "
          "none before a key is pressed in it (a window that the app opens shows the frame from its first key), and "
          "after Tab in it its button with the focus has the frame; the first window active again, its frame is "
          "back", act == want and all(act.values()), act if any(act.values()) else err)


def test_a_menu_of_a_button(seen, check):
    menu, err = _both(seen, "menu")
    want = {"Tab to the button": {"focus": "menu button", "frame": True},
            "a click on an item": {"the menu showed": True, "focus": "top", "no frame": True},
            "a click outside the menu": {"frame before": True, "the menu showed": True, "focus": "menu button",
                                         "no frame": True},
            "keys in a menu that a click opened": {"the menu showed": True, "focus": "top", "frame": True},
            "Esc in the menu": {"frame before": True, "the menu showed": True, "focus": "menu button", "frame": True}}
    check("focus frame: a button's menu opened with Space: a click on one of its items, which moves the focus as "
          "the app does, leaves no frame, and a click outside the menu takes the frame off its button (a menu takes "
          "the clicks itself and moves no focus: the frame stayed); a menu opened with a click and used with the "
          "keys (Down, Enter) leaves the frame where the focus goes; after Esc the frame is on the button again",
          all(v == want for v in menu.values()), menu if any(menu.values()) else err)


def test_the_mouse_wheel(seen, check):
    whl, err = _both(seen, "wheel")
    want = {"Tab": {"focus": "slider", "frame": True},
            "a notch on the page": {"the page moved": True, "focus": "slider", "frame, moved with its control": True},
            "the code moves the focus after it": {"focus": "tick", "frame": True},
            "a notch on a drop-down list": {"focus": "combo", "no frame": True, "the keyboard is not in use": True},
            "Tab after it": {"focus": "slider", "frame": True},
            "a notch on the list while nothing has the focus": {"focus": "combo", "no frame": True,
                                                                "the keyboard is not in use": True},
            "a notch on the page, then Tab at once": {"frame before": True, "focus": "combo", "frame": True}}
    check("focus frame: with the frame on a control, a notch of the mouse wheel on a drop-down list gives the list "
          "the focus and no frame (the wheel moves the focus with no mouse button down: the frame went to the list), "
          "also while nothing has the focus, and Tab then shows the frame again; a notch on the page, where no "
          "control takes it, scrolls the page and the frame stays on its control, the focus that the code moves "
          "after it has the frame, and Tab pressed at once after it too",
          all(v == want for v in whl.values()), whl if any(whl.values()) else err)


def test_its_cost(seen, check):
    times, err = _both(seen, "microseconds for one move of the focus")
    limit = qt.time_limit(1000)  # (1 ms, in microseconds)
    check("focus frame: one move of the focus takes less than 1 ms with the frame (the median of 200 moves): in one "
          "parent, to another parent (the frame goes from the window to a scroll area's view and back), and with "
          "the mouse in use", all(v and all(0 < x < limit for x in v.values()) and len(v) == 3
                                  for v in times.values()), times if any(times.values()) else err)
    ran, _ = _both(seen, "calls of the frame's code for 900 events of other controls")
    want = {"mouse in use": 0, "frame shown meanwhile": True, "keyboard in use": 0}
    check("focus frame: its code does not run for the events of controls that it does not watch (900 plain events, "
          "mouse moves and paints, with the mouse in use and with the frame shown): it is no event filter on the "
          "application", all(v == want for v in ran.values()), ran)
