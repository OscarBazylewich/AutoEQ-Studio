"""Devices and Profiles at the window's smallest width, and the window's other corrections of the visual review
(2026-11-10): a long profile name in a device's card ends in "…" (Rename… and the row's ✕ stay whole and in view);
Profiles' "Used by" column has a limit, so the Name column keeps a width to read; the empty device list has the gray
line of every empty list; the line "Wait for Equalizer APO…" is in a note's gray, not a warning's colour; and a window
whose title bar Windows refused is drawn once when it shows, not twice."""
import os

from helpers import qt

KEY = "Headset|EarPods"
OTHER = "Headphones|Buds"
LONG = "Profile name that is long to check the elide of the lists 0123"


def _profile(w, name):
    path = os.path.join(w.top, "fit.txt")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("Preamp: -3 dB\nFilter 1: ON PK Fc 1000 Hz Gain 3 dB Q 1\n")
    return w.sw.import_profile(path, name)


def _cut(win, page):
    """What is cut on a screen: a sideways scroll bar, or a shown button that is not whole in its visible area."""
    from PySide6.QtWidgets import QAbstractButton, QAbstractScrollArea
    root, bad = win.pages[page], []
    for a in [root, *root.findChildren(QAbstractScrollArea)]:  # (Settings is a scroll area itself)
        if isinstance(a, QAbstractScrollArea) and a.isVisibleTo(win) and a.horizontalScrollBar().maximum() > 0:
            bad.append(("sideways scroll bar", a.objectName() or type(a).__name__))
    for b in root.findChildren(QAbstractButton):
        if b.isVisibleTo(win) and b.width() > 0:
            r = b.visibleRegion().boundingRect()
            if not r.isEmpty() and r.width() < b.width() - 1:
                bad.append(("cut", b.text() or b.accessibleName(), r.width(), b.width()))
    return bad


def test_a_long_profile_name_at_the_smallest_width(devices_window, check):
    from PySide6.QtWidgets import QPushButton, QRadioButton, QSplitter, QToolButton
    w = devices_window
    win, sw = w.win, w.sw
    pids = [_profile(w, n) for n in (LONG, "Flat")]
    for pid in pids:
        sw.add_to_device(KEY, pid)
    try:
        win.show()
        win.show_page("devices", remember=False)
        win.selected = KEY
        win.render_all()
        win.resize(300, 700)  # (as small as it can be)
        split = win.pages["devices"].findChild(QSplitter)
        split.setSizes([10000, 1])  # (the device list as wide as it can be: the card beside it at its narrowest)
        qt.pump(20)
        panel = win.dev_panel
        width = win.width()
        cut = _cut(win, "devices")
        rb = next(b for b in panel.findChildren(QRadioButton) if b.text() == LONG)
        ren = next(b for b in panel.findChildren(QPushButton) if b.text() == "Rename…")
        xs = [b for b in panel.findChildren(QToolButton) if b.text() == "✕" and b.isVisibleTo(win)]
        viewport = panel.parentWidget()
        inside = [b.mapTo(viewport, b.rect().topRight()).x() <= viewport.width() for b in [ren, *xs]]
        name = (rb.text(), rb.toolTip(), rb.accessibleName() or rb.text(), rb.width() < rb.sizeHint().width())
    finally:
        for pid in pids:
            sw.remove_profile(pid)
        split.setSizes([316, 540])
        win.resize(1040, 760)
        win.render_all()
        qt.pump(10)
    check("devices: at the window's smallest width a long profile name ends in “…” (its whole name in its tooltip and "
          "for a screen reader); Rename… and each row's ✕ are whole and in view, and nothing needs a sideways scroll "
          "bar", not cut and all(inside) and len(xs) == 2 and name == (LONG, LONG, LONG, True), (width, cut, inside, name))


def test_used_by_has_a_limit(devices_window, check):
    w = devices_window
    win, sw = w.win, w.sw
    pid = _profile(w, "Used by many")
    for k in (KEY, OTHER):
        sw.add_to_device(k, pid)
        sw.set_nickname(k, f"A long name for this device to fill the column {k[:5]}")
    try:
        win.show()
        win.show_page("profiles", remember=False)
        win.render_profiles()
        win.resize(300, 700)
        qt.pump(20)
        t = win.prof_table
        row = next(r for r in range(t.rowCount()) if t.item(r, 0).text() == "Used by many")
        used = t.item(row, 2)
        widths = (t.columnWidth(0), t.columnWidth(2), t.viewport().width(), win.width())
        cut = _cut(win, "profiles")
        tip, text = used.toolTip(), used.text()
    finally:
        for k in (KEY, OTHER):
            sw.set_nickname(k, "")
        sw.remove_profile(pid)
        win.resize(1040, 760)
        win.show_page("devices", remember=False)
        qt.pump(10)
    check("profiles: with a profile used by many devices, “Used by” takes at most 30 % of the table, the Name column "
          "keeps 150 px or more at the window's smallest width, the table needs no sideways scroll bar, and the cell's "
          "tooltip has all the devices", widths[1] <= widths[2] * 0.3 + 1 and widths[0] >= 150 and not cut
          and tip == text and tip.count("A long name") == 2, (widths, cut, tip))


def test_the_wait_line_is_not_a_warning(devices_window, check):
    w = devices_window
    win = w.win
    win.show()
    win.show_page("devices", remember=False)
    win.selected = KEY
    win.render_all()
    qt.wait_for(lambda: not win._checking, 30)
    lab, kept = win.check_label, win._checks.get(KEY)
    roles = []
    try:
        if lab is not None:
            win._checks[KEY] = (win._check_sig(KEY), False, "Equalizer APO is not installed on this device.")
            win._show_check(KEY)
            roles.append(lab.property("role"))
            win._checks.pop(KEY)  # (as Examine again does: asked again, no answer yet)
            win._checking.add(KEY)
            win._show_check(KEY)
            roles += [lab.text(), lab.property("role"), win.check_row.isVisibleTo(win)]
    finally:
        win._checking.discard(KEY)
        if kept is not None:
            win._checks[KEY] = kept
        win.render_all()
    check("devices: while Equalizer APO is asked again after a bad answer, “Wait for Equalizer APO…” is in a note's "
          "gray, not in the warning's colour", roles[:1] == ["warn"] and roles[1:2] and roles[1].startswith("Wait for")
          and roles[2] == "muted" and roles[3], roles)


def test_settings_whole_at_the_smallest_width(devices_window, check):
    w = devices_window
    win = w.win
    win.show()
    win.show_page("settings", remember=False)
    win.render_settings()
    try:
        for height in (760, 480):  # (with and without its scroll bar)
            win.resize(300, height)
            qt.pump(20)
            cut = _cut(win, "settings")
            if cut:
                break
        width = win.width()
    finally:
        win.resize(1040, 760)
        win.show_page("devices", remember=False)
        qt.pump(10)
    check("settings: at the window's smallest width its cards are whole, without a sideways scroll bar (the window "
          "is at least as wide as the Hotkeys card needs)", not cut, (width, height, cut))


def _small_window(tmp_path, stub_app, eps):
    from switcher import core
    from switcher.apo import Apo
    from ui.window import Window
    # (no Equalizer APO folder: the window asks APO nothing in the background)
    sw = core.Switcher(str(tmp_path / "s.json"), Apo(str(tmp_path / "no-apo")), endpoints=lambda: eps,
                       playing=lambda: eps[0].guid if eps else None)
    sw.s["page"] = "devices"
    return Window(sw, stub_app)


def test_the_empty_device_list(qapp, stub_app, tmp_path, check):
    win = _small_window(tmp_path, stub_app, [])
    try:
        win.show()
        win.resize(1040, 760)
        qt.pump(10)
        empty = getattr(win, "dev_empty", None)
        got = (win.dev_list.count(), empty is not None and empty.label.isVisibleTo(win),
               empty.label.text() if empty is not None else "", empty is not None and empty.label.property("role"))
        said_twice = [lab.text() for lab in win.dev_panel.findChildren(type(win.status_text))
                      if "No playback devices" in lab.text()]
    finally:
        qt.close(win)
    check("devices: an empty device list shows one gray line in its middle that tells the next step (UI-RULES 21), "
          "and the panel beside it does not say it again",
          got[0] == 0 and got[1] and got[2].startswith("No playback devices. Connect") and got[3] == "muted"
          and not said_twice, (got, said_twice))


def test_a_refused_title_bar_draws_the_window_once(qapp, stub_app, tmp_path, check, monkeypatch):
    from ui import titlebar
    win = _small_window(tmp_path, stub_app, [])
    drawn = []
    try:
        monkeypatch.setattr(titlebar, "install", lambda *a, **k: None)  # (Windows refuses the title bar)
        monkeypatch.setattr(win, "render_all", lambda: drawn.append(1))
        win._title_mode = "frameless"
        win.show()
        qt.pump(10)
        got = (len(drawn), win._title_mode, win.isVisible(), [b.isVisibleTo(win) for b in win.caption.values()])
    finally:
        monkeypatch.undo()
        qt.close(win)
    check("window: when Windows refuses the title bar, the window shows with Windows' own title bar, without its own "
          "caption buttons, and its screens are drawn once (the show again inside the first one drew them twice)",
          got == (1, None, True, [False, False, False]), got)
