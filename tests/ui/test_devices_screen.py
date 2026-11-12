"""Devices (the window's device screen, ui\\window.py; ui\\devices_screen.py once the window is split): the banner
asking to set APO up, the device playing chosen and APO missing on it said, the device's line saying whether its EQ
applies (Equalizer APO asked, by itself or with Check again: a stand-in answers for APO's Benchmark here), your name
for a device, trying an EQ for 5 minutes, and the device's choices. Moved from selftest.py's qt_checks.

One window for the whole file (tests\\ui\\conftest.py's devices_window, then set_up_window: the same window after
Set up), its tests in the old checks' order: each one starts from the state the one before left, as the old checks
did (the device's line keeps the last answer; the EQ choices count on the earlier tests putting things back).
Then the screen's look in Windows 11's (the restyle, 2026-10-23): its rows, a profile's quiet ✕ (drawn in a Python of
its own, themed), and the symbols beside its buttons' words. Last, Remove in a device's card (2026-11-12): it removes
only a device that is not connected (for a connected one, a bubble at it tells why), Undo, the row selected after
it, the lists of devices in agreement, and pictures of the card, the bubble and the message (in a Python of its own,
themed). It is in this file, not in a file of its own, so a change
to ui\\devices_screen.py chooses fewer than 25 test files (tests\\infra\\test_relevant.py).
"""
import os
import threading
import types

from helpers import qt, session, subproc

KEY = "Headset|EarPods"

# (after tests\ui\conftest.py's THEMED_WINDOW: a profile on the playing device, then the list's first row and the
# profile's ✕ read back from the screen's picture)
ROWS = r'''
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QToolButton
pid = sw.import_profile(os.path.join(conf, "EarPods.txt"))
sw.add_to_device(KEY, pid)
win.render_all()
for _ in range(5):
    qapp.processEvents()
lst = win.dev_list
r = lst.visualItemRect(lst.item(0))
img = lst.viewport().grab().toImage()


def brightest(y0, y1):  # (the text's own colour: its fullest pixel, dark theme)
    return max(max(img.pixelColor(x, y).getRgb()[:3]) for x in range(r.left() + 30, r.right() - 4)
               for y in range(y0, y1))


mid = r.center().y()
xs = [b for b in win.dev_panel.findChildren(QToolButton) if b.text() == "✕" and b.isVisible()]
fill = None
if xs:
    panel = win.dev_panel.grab().toImage()
    fill = panel.pixelColor(xs[0].mapTo(win.dev_panel, QPoint(5, 5))).name()
out = {"first": brightest(r.top() + 2, mid - 1), "second": brightest(mid + 2, r.bottom() - 2),
       "text": lst.item(0).text(), "ink2": t["ink2"], "fill": fill, "card": t["card"], "xs": len(xs)}
theme.apply(qapp, dark=False, contrast=False)  # (Windows switched to light: the rows are drawn again in its colours)
for _ in range(5):
    qapp.processEvents()
img = lst.viewport().grab().toImage()
out.update(light_second=min(min(img.pixelColor(x, y).getRgb()[:3]) for x in range(r.left() + 30, r.right() - 4)
                            for y in range(mid + 2, r.bottom() - 2)), light_ink2=theme.tokens()["ink2"])
print(json.dumps(out))
'''


# (after THEMED_WINDOW: a third device, connected; then each row's dot read back from the list's picture, dark, then
# light, then light with Windows' green accent, then a contrast theme (with each row's fill: the device playing is the
# chosen row), beside the colours the theme has for each)
DOTS = r'''
eps.append(D.Endpoint("{3}", "Speakers", "Realtek(R) Audio", D.ACTIVE, True))
sw.refresh()
win.render_all()
for _ in range(5):
    qapp.processEvents()
''' + "{shapes}" + r'''
KINDS = {"Active": "playing", "Connected": "connected", "Not connected": "away"}


def dots(fills=False):  # (each row's dot, by its row's words: the colour in its middle; with fills, [that colour,
    # the row's own fill, whether it's the chosen row])
    lst = win.dev_list
    img = lst.viewport().grab().toImage()
    got = {}
    for i in range(lst.count()):
        it = lst.item(i)
        r = lst.visualItemRect(it)
        y = r.center().y()
        bg = img.pixelColor(r.left() + 6, r.top() + 3)
        found = runs(img, r.left() + 4, r.left() + 40, y - 1, y + 2, bg)
        kind = KINDS.get(it.text().split("\n")[1].split(" · ")[0])
        got[kind] = img.pixelColor((found[0][0] + found[0][1]) // 2, y).name() if found else None
        if fills:
            got[kind] = [got[kind], bg.name(), it.isSelected()]
    return got


def wanted(blue=False):
    t = theme.tokens()
    return {"playing": t["good"], "connected": theme_tokens.LIGHT["accent"] if blue else t["accent"], "away": t["muted"],
            "card": t["card"]}


out = {"dark": [dots(), wanted()]}
theme.apply(qapp, dark=False, contrast=False)  # (Windows switched to light)
for _ in range(5):
    qapp.processEvents()
out["light"] = [dots(), wanted()]
theme.accent_palette = lambda: ("#9ff0a4", "#6ccb5f", "#3aa53b", "#107c10", "#0e6b0e", "#0b5a08", "#073f05")
theme.apply(qapp, dark=False, contrast=False)  # (Windows' accent changed to its green)
for _ in range(5):
    qapp.processEvents()
out["green accent"] = [dots(), wanted(blue=True)]
# a contrast theme, Windows 11's Aquatic (its colours as Windows gives them, stood in): the device playing is the chosen
# row, filled with Windows' highlight colour, which is the playing dot's colour there too
import ctypes
AQUATIC = {5: "#202020", 8: "#ffffff", 13: "#8ee3f0", 14: "#263b50", 17: "#a6a6a6", 26: "#75e9fc", 15: "#202020",
           18: "#ffffff"}  # (window, text, highlight, its text, grey text, links, button face, button text)
user32 = ctypes.windll.user32
real = user32.GetSysColor
user32.GetSysColor = lambda i: int(AQUATIC[i][5:7], 16) << 16 | int(AQUATIC[i][3:5], 16) << 8 | int(AQUATIC[i][1:3], 16)
try:
    hc = theme.system_tokens()
finally:
    user32.GetSysColor = real
theme.apply(qapp, dark=False, contrast=hc)
for _ in range(5):
    qapp.processEvents()
out["contrast, chosen row"] = [dots(fills=True), {"playing": hc["sel_ink"], "connected": hc["accent_text"],
                                                  "away": hc["muted"], "sel": hc["sel"]}]
print(json.dumps(out))
'''


def _near(a, b, most=2):
    """Two colours (#rrggbb) the same to within `most` in each of red, green and blue."""
    return bool(a and b) and all(abs(int(a[i:i + 2], 16) - int(b[i:i + 2], 16)) <= most for i in (1, 3, 5))


def _read(path):
    """A file's text (APO's switcher.txt: the app writes it as UTF-8)."""
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def test_banner_asks_to_set_apo_up(devices_window, check):
    win = devices_window.win
    # was selftest.py:373
    check("window: the banner asks to set APO up", win.banner.isVisible() and "does not use AutoEQ Studio" in win.banner_text.text(),
          (win.banner.isVisible(), win.banner_text.text()))


def test_playing_device_chosen_and_apo_missing_said(devices_window, check):
    win = devices_window.win
    labels = [w.text() for w in win.dev_panel.findChildren(type(win.banner_text))]
    # was selftest.py:374
    check("window: the device playing is chosen, and APO missing on it is said",
          win.selected == "Headset|EarPods" and any("is not installed on this device" in t for t in labels),
          (win.selected, labels))


def test_check_again(set_up_window, check, monkeypatch):
    # Is the EQ playing? Benchmark's answer (a stand-in for it here) on the device's line and, with Check again, said
    # in full
    from PySide6.QtWidgets import QMessageBox, QPushButton
    from switcher import check as apo_check
    w = set_up_window
    win, sw = w.win, w.sw
    rec = sw.record(KEY)
    win._checks.clear()
    chk = [b for b in win.dev_panel.findChildren(QPushButton) if b.text() == "Examine again" and b.isVisibleTo(win)]
    pfile = os.path.join(sw.apo.profiles, sw.profiles()[rec["active"]]["file"])
    told = []
    monkeypatch.setattr(apo_check, "run", lambda apo, guid, timeout=60: (told.append(guid), {
        "loaded": [apo.config_txt, os.path.join(apo.config, "AutoEQ Studio", "switcher.txt"), pfile],
        "matched": ["{5}"]})[1])
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: told.append(("ok", a[2]))))
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: told.append(("not", a[2]))))
    if chk:
        chk[0].click()
        qt.wait_for(lambda: len(told) >= 2, 10)
    monkeypatch.undo()  # (put back before the line is read, as the old check did)
    line = win.check_label.text() if win.check_label is not None else ""
    bar = (win.check_warn is not None and win.check_warn.isVisibleTo(win), win.check_warn_text.text()
           if win.check_warn is not None else "", win.check_row is not None and win.check_row.isVisibleTo(win))
    # was selftest.py:424 (the UI audit, 2026-11-08: a bad answer is Windows 11's warning bar, with Examine again in it)
    check("window: Check again asks APO for the device's endpoint and says all it found (its EQ applies, but APO "
          "isn't on the device); the device's line says it too, as a warning bar",
          len(chk) == 1 and "{5}" in told and any(isinstance(x, tuple) and x[0] == "not" and "on this device: APO finds the section"
                                                   in x[1] and "is not installed on this device" in x[1] for x in told)
          and line.startswith("Equalizer APO is not installed on this device") and bar[0] and bar[1] == line
          and not bar[2], (told, line, bar))


def test_line_asked_once_per_change(set_up_window, check, monkeypatch, qapp):
    # the line asks by itself, once per change (the answer kept while nothing it depends on changes: here the one
    # Check again got, just before)
    from switcher import check as apo_check
    win = set_up_window.win
    asked = []
    monkeypatch.setattr(apo_check, "run", lambda apo, guid, timeout=60: (asked.append(guid), {"loaded": [], "matched": []})[1])
    win.render_device_panel()
    win.render_device_panel()
    qapp.processEvents()
    again = list(asked)
    win._checks.clear()
    win.render_device_panel()
    qt.wait_for(lambda: asked and not win._checking, 10)
    monkeypatch.undo()
    # was selftest.py:477
    check("window: the device's line isn't asked again while nothing changed; asked by itself after a change "
          "(a warning bar: APO doesn't read AutoEQ Studio's file)", again == [] and asked == ["{5}"]
          and win.check_warn.isVisibleTo(win) and "does not read" in win.check_warn_text.text(), (again, asked,
                                                                                         win.check_label.text()))


def test_line_keeps_a_profiles_name_whole(check):
    # (the one-line answer kept a profile's name whole: "Truthear GATe (Diffuse field)" was cut at its bracket)
    from ui.window import check_line
    lines = [check_line(True, "APO uses “Truthear GATe (Diffuse field)” on this device: APO finds the section of the "
                              "device and loads the file of the EQ. config.txt also loads these files for this device: "
                              "x.txt."),
             check_line(False, "AutoEQ Studio selected “A. B (C)”, but APO does not load its file for this device (the "
                               "file is missing from APO's folder)."),
             check_line(True, "AutoEQ Studio's EQ is off for this device (APO finds its section, with no EQ in it)."),
             check_line(None, "AutoEQ Studio cannot get data from Equalizer APO: Benchmark is not there.")]
    # was selftest.py:489
    check("window: the device's line keeps a profile's name whole (brackets, a full stop) and drops the rest",
          lines == ["APO uses “Truthear GATe (Diffuse field)” on this device.",
                    "AutoEQ Studio selected “A. B (C)”, but APO does not load its file for this device.",
                    "AutoEQ Studio's EQ is off for this device.", "AutoEQ Studio cannot get data from Equalizer APO"],
          lines)


def test_eq_switched_while_apo_is_asked(set_up_window, check, monkeypatch, qapp):
    # (the EQ switched while APO is still being asked: the line is about the new one, not the one asked about)
    from switcher import check as apo_check
    w = set_up_window
    win, sw, key = w.win, w.sw, KEY
    first = sw.record(key)["active"]
    other = next(p for p in sw.profiles() if p != first)
    sw.add_to_device(key, other, switch_on=False)
    asked = []
    switched = threading.Event()

    def slow(apo, guid, timeout=60):
        # (APO slow to answer: the first question lasts until the EQ has been switched; the old stand-in slept 0.4 s,
        # which a busy PC can outlast before the switch)
        pid = sw.record(key)["active"]
        asked.append(sw.profile_name(pid))
        switched.wait(qt.time_limit(10))
        return {"loaded": [apo.config_txt, os.path.join(apo.config, "AutoEQ Studio", "switcher.txt"),
                           os.path.join(apo.profiles, sw.profiles()[pid]["file"])], "matched": [guid]}
    monkeypatch.setattr(apo_check, "run", slow)
    try:
        win._checks.clear()
        win.render_device_panel()
        qt.wait_for(lambda: asked, 5)
        sw.set_active(key, other)
        switched.set()
        qt.wait_for(lambda: not win._checking and key in win._checks, 10)
    finally:
        switched.set()
        monkeypatch.undo()
    told = win.check_label.toolTip() if win.check_label is not None else ""  # (all of the answer; this test device
    # has no APO, so its short line says that)
    try:
        # was selftest.py:523
        check("window: the EQ switched while APO is asked: it's asked again, and the answer is about the EQ on now",
              asked == [sw.profile_name(first), sw.profile_name(other)] and sw.profile_name(other) in told
              and sw.profile_name(first) not in told, (asked, told))
    finally:  # (as the old check left it, lines 526-528: EarPods on again, Samson off the device)
        sw.set_active(key, first)
        sw.remove_from_device(key, other)
        qapp.processEvents()


def test_device_nickname(set_up_window, check):
    # your name for a device: shown in the list, the panel and the tray; Windows' name kept; empty gives it back
    from switcher.core import shown
    w = set_up_window
    win, sw = w.win, w.sw
    sw.set_nickname("Headset|EarPods", "  Dongle – KZ  ")
    try:
        win.render_all()
        item = win.dev_list.currentItem().text()
        kept = w.switcher()  # (a second Switcher on the saved settings: as at the next start)
        named = (item.startswith("Dongle – KZ"), shown(sw.record("Headset|EarPods")),
                 kept.record("Headset|EarPods").get("nickname"), sw.record("Headset|EarPods")["label"])
    finally:
        sw.set_nickname("Headset|EarPods", "")
    # was selftest.py:538
    check("window: a device's own name (Rename…) shown in the list, kept, Windows' name under it; empty: Windows' "
          "name again", named == (True, "Dongle – KZ", "Dongle – KZ", "Headset (EarPods)")
          and shown(sw.record("Headset|EarPods")) == "Headset (EarPods)", named)


def test_trying_an_eq_for_5_minutes(set_up_window, check, qapp):
    # trying an EQ: in APO's file for that device only, the bar says it, Keep it makes it a profile; a hand switch or
    # the time up ends it; a trial left by a crash is gone at the next start
    from ui import app as app_mod
    w = set_up_window
    win, sw = w.win, w.sw
    swt = os.path.join(w.conf, "AutoEQ Studio", "switcher.txt")
    before = sw.record("Headset|EarPods")["active"]
    pid = None
    try:
        sw.try_eq("Headset|EarPods", "Preamp: -3 dB\r\nFilter 1: ON PK Fc 1000 Hz Gain -3 dB Q 1\r\n", "Trial EQ", 5)
        win.render_trial()
        trying = (_read(swt).count("_trying.txt"), win.trial_holder.isVisible() or not win.isVisible(),
                  "Trial EQ" in win.trial_text.text(), win._device_state("Headset|EarPods")[1])
        leftover = w.switcher()  # (the next start, after a crash: the trial still in APO's file)
        after_crash = (os.path.exists(sw.trial_path()), "_trying" in _read(swt))
        sw.try_eq("Headset|EarPods", "Preamp: -3 dB\r\nFilter 1: ON PK Fc 1000 Hz Gain -3 dB Q 1\r\n", "Trial EQ", 5)
        pid = sw.end_trial(keep=True)
        rec2 = sw.record("Headset|EarPods")
        kept_it = (sw.profile_name(pid), rec2["active"] == pid, sw.trial, os.path.exists(sw.trial_path()))
        sw.try_eq("Headset|EarPods", "Preamp: -1 dB\r\n", "Second", 5)
        sw.set_active("Headset|EarPods", before)
        by_hand = (sw.trial, "_trying" in _read(swt), rec2["active"] == before)
        sw.try_eq("Headset|EarPods", "Preamp: -1 dB\r\n", "Third", 5)
        sw.trial["until"] = 0
        # (the app's 1.5 s poll, with a stand-in for the app: what poll uses of it, the switcher and ending a trial)
        app_mod.App.poll(type("A", (), {"sw": sw, "hotkey_problem": "", "onoff_problem": "",
                                        "end_trial": staticmethod(lambda keep=False: sw.end_trial(keep))})())
        # was selftest.py:562
        check("devices: Try for 5 minutes plays the EQ on that device only (APO's file, the bar, the status), Keep it "
              "makes it a profile switched on; a hand switch or the time up ends it; one left by a crash is gone at the "
              "next start",
              trying == (1, True, True, "For 5 minutes: Trial EQ") and after_crash == (False, False) and leftover.trial is None
              and kept_it == ("Trial EQ", True, None, False) and by_hand == (None, False, True) and sw.trial is None
              and "_trying" not in _read(swt), (trying, after_crash, kept_it, by_hand, sw.trial))
    finally:  # (as the old check left it, line 567: the profile it kept removed)
        if sw.trial:
            sw.end_trial(False)
        if pid:
            sw.remove_profile(pid)
        qapp.processEvents()


def test_device_choices(set_up_window, check, qapp):
    from PySide6.QtWidgets import QRadioButton
    win = set_up_window.win
    qapp.processEvents()
    radios = [r for r in win.dev_panel.findChildren(QRadioButton) if r.isVisible()]
    # was selftest.py:571
    check("window: the device's choices are Off and its profile, the profile on",
          [r.text() for r in radios] == ["Off", "EarPods"] and radios[1].isChecked(), [r.text() for r in radios])


def test_off_switches_the_eq_off_and_one_panel_at_a_time(set_up_window, check, qapp):
    # (one action, two checks: choosing Off draws the panel again, and the old one's parts must be gone at once)
    from PySide6.QtWidgets import QRadioButton
    win, sw = set_up_window.win, set_up_window.sw
    radios = [r for r in win.dev_panel.findChildren(QRadioButton) if r.isVisible()]
    if radios:
        radios[0].setChecked(True)  # ("Off": the first choice)
    qapp.processEvents()
    # was selftest.py:575
    check("window: choosing Off switches the EQ off", sw.record("Headset|EarPods")["active"] is None,
          [r.text() for r in radios])
    # was selftest.py:576
    check("window: one device panel at a time (the old one's parts are gone at once)",
          len([r for r in win.dev_panel.findChildren(QRadioButton) if r.parent() is not None and r.isVisible()]) == 2,
          [r.text() for r in win.dev_panel.findChildren(QRadioButton)])


def test_device_rows_and_a_quiet_take_off(themed_window, check, fake_apo, tmp_path):
    out = subproc.run_python(themed_window + ROWS, session.SESSION.app, str(tmp_path))
    d = out.data or {}
    second = int((d.get("ink2") or "#000000")[1:3], 16)  # (dark: ink2 is a grey, the same in red, green and blue)
    check("devices: each row says the device in the text colour and, under it, where it is and its EQ, smaller, in "
          "the secondary colour (as Windows 11 lists devices); the row's words unchanged",
          (d.get("first") or 0) >= 245 and abs((d.get("second") or 0) - second) <= 8
          and "\n" in (d.get("text") or ""), d or out.stderr[-300:])
    check("devices: a profile's ✕ is a quiet button (the card shows through it until it's pointed at)",
          d.get("xs") == 1 and d.get("fill") == d.get("card"), d and (d.get("xs"), d.get("fill"), d.get("card"))
          or out.stderr[-300:])
    light = int((d.get("light_ink2") or "#ffffff")[1:3], 16)
    check("devices: the rows, drawn by the screen itself, follow Windows switching from dark to light (the second "
          "line in light's secondary colour)", abs((d.get("light_second") or 999) - light) <= 8,
          d and (d.get("light_second"), d.get("light_ink2")) or out.stderr[-300:])


def test_device_dots_in_the_themes_colours(themed_window, check, fake_apo, tmp_path, shapes):
    # (2026-10-23: EQ Switcher's own colours, #1f9d55, #2f6fde and #9aa0a6, whatever the theme: the grey 2.5:1 on the
    # light list, and neither Windows' accent nor its contrast themes followed)
    from ui import theme_tokens
    out = subproc.run_python(themed_window + DOTS.replace("{shapes}", shapes), session.SESSION.app, str(tmp_path))
    d = out.data or {}

    def right(case):
        got, want = (d.get(case) or [{}, {}])
        return all(_near(got.get(k), want.get(k)) and theme_tokens.contrast(got[k], want["card"]) >= 3
                   for k in ("playing", "connected", "away")) and len(set(got.values())) == 3

    def on_chosen_row():
        # (2026-10-23: in a contrast theme the playing dot is Windows' highlight colour, the chosen row's fill too, and
        # the device playing is the one chosen when Devices opens: its dot was gone there. On the chosen row it's in
        # the row's text colour now)
        got, want = (d.get("contrast, chosen row") or [{}, {}])
        rows = [got.get(k) or [None, None, None] for k in ("playing", "connected", "away")]
        return got.get("playing", [0, 0, False])[2] is True and rows[0][1] == want.get("sel") \
            and all(_near(dot, want.get(k)) and theme_tokens.contrast(dot, fill) >= 3
                    for k, (dot, fill, _chosen) in zip(("playing", "connected", "away"), rows)) \
            and len({dot for dot, _f, _c in rows}) == 3
    check("devices: the list's dots in the theme's colours (playing: its green; connected: Windows' accent, its default "
          "blue a green accent's stand-in; not connected: its grey), drawn again when Windows switches light or dark or "
          "its accent, each 3:1 on the list and the three told apart",
          all(right(c) for c in ("dark", "light", "green accent")) and on_chosen_row(), d or out.stderr[-300:])


def test_symbols_beside_the_device_screens_words(set_up_window, check, qapp):
    from PySide6.QtWidgets import QLabel, QPushButton
    win = set_up_window.win
    win.render_device_panel()
    qapp.processEvents()  # (the panel's new parts are shown on Qt's next turn)
    buttons = {b.text(): b for b in win.dev_panel.findChildren(QPushButton) if b.isVisible()}
    want = ("Rename…", "Add a profile", "Examine again")
    signs = [(lab.accessibleName(), lab.property("role")) for lab in win.dev_panel.findChildren(QLabel)
             if lab.property("glyph") == "true" and lab.isVisible()]
    # (the playing device has no APO on it: its card says so)
    check("devices: Windows 11's symbols beside Rename…, Add a profile and Check again (their words unchanged), and "
          "the warning sign on the card saying APO isn't on the device",
          all(w in buttons and not buttons[w].icon().isNull() for w in want) and signs == [("Warning", "warn")],
          (sorted(buttons), [w for w in want if w in buttons and buttons[w].icon().isNull()], signs))


def test_add_a_profile_menu_sorts_numbers_as_numbers(set_up_window, check, qapp, tmp_path):
    """The menu of Add a profile lists the profiles A to Z with numbers as numbers (UI-RULES 22): EQ 2 before EQ 10.
    The three profiles are removed at the end (the window is the file's own)."""
    from PySide6.QtWidgets import QPushButton
    win, sw = set_up_window.win, set_up_window.sw
    made, rows = [], []
    try:
        for name in ("EQ 10", "EQ 2", "EQ 1"):
            path = tmp_path / f"{name}.txt"
            path.write_text("Preamp: -1 dB\nFilter 1: ON PK Fc 100 Hz Gain -2 dB Q 1\n", encoding="utf-8")
            made.append(sw.import_profile(str(path), name))
        win.render_device_panel()
        qapp.processEvents()
        add = [b for b in win.dev_panel.findChildren(QPushButton) if b.text() == "Add a profile" and b.isVisible()]
        rows = [a.text() for a in add[-1].menu().actions()] if add else []
    finally:
        for pid in made:
            sw.remove_profile(pid)
        win.render_all()
        qapp.processEvents()
    check("devices: the menu of Add a profile sorts the profiles A to Z with numbers as numbers (EQ 2 before EQ 10)",
          [r for r in rows if r.startswith("EQ ")] == ["EQ 1", "EQ 2", "EQ 10"], rows)


# ---------------------------------------------------------------- Remove (a device), 2026-11-12
# (after an update of Equalizer APO or a driver, Windows can give a device a new entry, and the old one stayed in
# Devices for good: Remove removes only a device that is not connected, with Undo; the lists of devices agree.
# For a connected device Remove stays on and a bubble at it tells why: UI-RULES 25)
AWAY = "Headphones|Buds"  # (in Windows' list, not connected)
GONE = "Headset|USB-C to 3.5mm Headphone Jack Adapter"  # (no longer in Windows' list)
TIP = "Removes this device from Devices. Its profiles stay in Profiles."
CONNECTED = "You can remove a device only when it is not connected."


def _remove_profile(w, name):
    path = os.path.join(w.top, name + ".txt")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("Preamp: -3 dB\nFilter 1: ON PK Fc 1000 Hz Gain 3 dB Q 1\n")
    return w.sw.import_profile(path, name)


def _remove_button(win):
    from PySide6.QtWidgets import QPushButton
    return next((b for b in win.dev_panel.findChildren(QPushButton) if b.text() == "Remove" and b.isVisibleTo(win)),
                None)


def _select(win, qapp, key):
    win.selected = key
    win.render_devices()
    qapp.processEvents()


def _rows(win):
    from PySide6.QtCore import Qt
    return [win.dev_list.item(i).data(Qt.UserRole) for i in range(win.dev_list.count())]


def _tell_bubble():
    from ui import bubble
    b = bubble.last("tell")
    return b if b is not None and b.isVisible() else None


def test_the_button_on_with_its_tooltip(devices_window, qapp, check):
    w = devices_window
    win = w.win
    got = {}
    for key in (KEY, AWAY):
        _select(win, qapp, key)
        b = _remove_button(win)
        got[key] = b and (b.isEnabled(), b.toolTip().split("\n")[0], b.accessibleName(), b.property("help_key"))
    check("devices: Remove is in the device's card, on for a connected device too (UI-RULES 25: a disabled button "
          "cannot be reached with the keyboard), with one tooltip; its name for a screen reader names the device; F1 "
          "opens its Help",
          got == {KEY: (True, TIP, "Remove Headset (EarPods) from Devices", "#dev-remove"),
                  AWAY: (True, TIP, "Remove Headphones (Buds) from Devices", "#dev-remove")}, got)


def test_the_help_of_remove_in_ste_limits(check):
    # (2026-11-12: a sentence of 31 words, "…not connected: a device that…", and a source line of 121 characters)
    import re
    from ui import help_text_devices as H
    entry = next(i for s in H.SETTINGS_DEVICES for i in s["items"] if i["key"] == "#dev-remove")
    texts = entry["body"] + [H.HELP_DEVICES["#dev-remove"]]
    long = [s for t in texts for s in re.split(r"(?<=[.!?])\s+", t) if len(re.findall(r"[\w“”…'-]+", s)) > 25]
    with open(H.__file__, encoding="utf-8") as fh:
        source = fh.read()
    part = source[source.index("'#dev-remove'"):]
    part = part[:part.index("\n")] + "\n" + part[part.index("{'key': '#dev-remove'"):part.index("{'key': '#use-device'")]
    wide = [line for line in part.split("\n") if len(line) > 120]
    check("devices: each sentence of the Help of Remove has 25 words or fewer, and its source lines 120 characters or "
          "fewer; the words say \"from Devices\" (one name), not \"from the list\"",
          not long and not wide and "from the list" not in " ".join(texts)
          and H.HELP_DEVICES["#dev-remove"] == "Removes a device that is not connected from Devices. Its profiles stay "
                                               "in Profiles.", (long, wide))


def test_a_connected_device_stays_and_a_bubble_tells_why(devices_window, qapp, check):
    from PySide6.QtCore import Qt
    from switcher import devices as D
    from ui.devices_screen import DOT
    w = devices_window
    win, sw = w.win, w.sw
    got = {}
    try:
        # (a connected device; then one that was connected after the last poll: its row said "Not connected")
        for case, key in (("connected", KEY), ("connected since the poll", AWAY)):
            _select(win, qapp, key)
            row_before = win.dev_list.currentItem().data(DOT)
            if case == "connected since the poll":
                w.eps[1] = D.Endpoint("{1}", "Headphones", "Buds", D.ACTIVE, True)  # (plugged in, not polled yet)
            _remove_button(win).click()
            qt.pump(50)
            tell = _tell_bubble()
            current = win.dev_list.currentItem()
            got[case] = (row_before, sw.record(key) is not None, key in _rows(win), sw.s["hidden_devices"],
                         win.selected, current.data(Qt.UserRole) if current else None,
                         current.data(DOT) if current else None, tell.text.text() if tell else None,
                         tell is not None and tell.anchor is _remove_button(win))
            if tell is not None:
                tell.close_now()
    finally:
        w.eps[1] = D.Endpoint("{1}", "Headphones", "Buds", D.NOT_PRESENT, True)
        sw.refresh()
        win.render_all()
    check("devices: a click on Remove for a connected device removes nothing, the device stays selected, and a "
          "bubble at Remove tells why; the same for a device that was connected after the last poll (its row then "
          "shows it connected)",
          got == {"connected": ("playing", True, True, [], KEY, KEY, "playing", CONNECTED, True),
                  "connected since the poll": ("away", True, True, [], AWAY, AWAY, "connected", CONNECTED, True)},
          got)


def test_remove_is_last_and_apart_in_the_card(devices_window, qapp, check):
    from PySide6.QtWidgets import QPushButton
    w = devices_window
    win = w.win
    _select(win, qapp, AWAY)
    rem = _remove_button(win)
    ren = next((b for b in win.dev_panel.findChildren(QPushButton) if b.text() == "Rename…"), None)
    head = rem.parentWidget() if rem else None
    got = rem and ren and (ren.parentWidget() is head, rem.geometry().left() - ren.geometry().right() - 1,
                           head.layout().indexOf(rem) == head.layout().count() - 1)
    check("devices: Remove comes after Rename… in the card, last and 12 px apart (UI-RULES 14)",
          bool(got) and got[0] and got[1] == 12 and got[2], got)


def test_a_click_removes_and_undo_puts_it_back(devices_window, qapp, check):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication
    w = devices_window
    win, sw = w.win, w.sw
    pid = _remove_profile(w, "Buds EQ")
    sw.add_to_device(AWAY, pid)
    sw.set_nickname(AWAY, "My buds")
    rec = dict(sw.record(AWAY))
    try:
        _select(win, qapp, AWAY)
        _remove_button(win).click()
        qapp.processEvents()
        off = (sw.record(AWAY), AWAY in _rows(win), win.selected, win.message.text.text(),
               win.message.undo_btn.isVisibleTo(win), pid in sw.profiles(), list(sw.s["hidden_devices"]),
               QApplication.focusWidget() is win.dev_list)  # (the clicked button went with the old panel)
        win.message.undo_btn.click()
        qapp.processEvents()
        current = win.dev_list.currentItem()
        back = (sw.record(AWAY) == rec, AWAY in _rows(win), win.selected,
                current.data(Qt.UserRole) if current else None, list(sw.s["hidden_devices"]))
    finally:
        sw.remove_profile(pid)
        sw.set_nickname(AWAY, "")
        win.render_all()
    check("devices: a click on Remove removes the device (its profile stays in Profiles) and selects the row at the "
          "same place, with the keyboard in the list; the message names it, tells that it shows again when you "
          "connect it, and has Undo; Undo puts it back as it was and selects it",
          off == (None, False, KEY, "Removed “My buds” from Devices. It shows again when you connect it.", True, True,
                  [AWAY], True) and back == (True, True, AWAY, AWAY, []), (off, back))


def test_the_list_selects_the_row_at_the_same_place_or_the_last(devices_window, qapp, check):
    w = devices_window
    win, sw = w.win, w.sw
    pid = _remove_profile(w, "Old dongle")
    sw.s["devices"][GONE] = {"label": "Headset (USB-C to 3.5mm Headphone Jack Adapter)", "guids": ["{9}"],
                             "profiles": [], "active": None}
    sw.add_to_device(GONE, pid)
    try:
        win.render_all()
        order = _rows(win)
        _select(win, qapp, AWAY)
        _remove_button(win).click()
        qapp.processEvents()
        middle = (win.selected, _rows(win), win.message.text.text())
        _remove_button(win).click()  # (the row selected after it: now the last row)
        qapp.processEvents()
        last = (win.selected, _rows(win), win.message.text.text(), sw.record(GONE))
    finally:
        sw.remove_profile(pid)
        sw.s["hidden_devices"].clear()
        sw.refresh()
        win.render_all()
    check("devices: after a removal the list selects the row at the same place (or the last row) and the panel shows "
          "it; a device that Windows does not list shows no more (the message has no more words for it)",
          order == [KEY, AWAY, GONE] and middle == (GONE, [KEY, GONE], "Removed “Headphones (Buds)” from Devices. It "
                                                                       "shows again when you connect it.")
          and last == (KEY, [KEY], "Removed “Headset (USB-C to 3.5mm Headphone Jack Adapter)” from Devices.", None),
          (order, middle, last))


def test_undo_after_the_device_connected_again(devices_window, qapp, check):
    from PySide6.QtCore import Qt
    from switcher import devices as D
    w = devices_window
    win, sw = w.win, w.sw
    _select(win, qapp, AWAY)
    _remove_button(win).click()
    qapp.processEvents()
    w.eps[1] = D.Endpoint("{1}", "Headphones", "Buds", D.ACTIVE, True)  # (plugged in)
    try:
        sw.refresh()
        win.message.undo_btn.click()
        qapp.processEvents()
        said = win.message.text.text()
        current = win.dev_list.currentItem()
        got = (said, sw.record(AWAY)["profiles"], AWAY in _rows(win), win.selected,
               current.data(Qt.UserRole) if current else None)
    finally:
        w.eps[1] = D.Endpoint("{1}", "Headphones", "Buds", D.NOT_PRESENT, True)
        sw.refresh()
        win.render_all()
    check("devices: Undo after the device was connected again (a new device) changes nothing and tells why; the list "
          "selects that device (its row, not only the panel)",
          got == ("You connected “Headphones (Buds)” again: Undo is not possible.", [], True, AWAY, AWAY), got)


def test_use_on_device_and_the_tray_do_not_list_a_removed_device(devices_window, qapp, check):
    from PySide6.QtCore import QCoreApplication, QEvent
    from PySide6.QtWidgets import QMenu
    from ui.app import App
    from ui.eq_page_parts import use_menu_order
    w = devices_window
    win, sw = w.win, w.sw
    sw.s["devices"]["Speakers|Old"] = {"label": "Speakers (Old)", "guids": ["{8}"], "profiles": [], "active": None}
    win.render_all()
    agree = (use_menu_order(sw)[0], _rows(win))  # (a device that Windows does not list, with no profiles: in neither)
    _select(win, qapp, AWAY)
    _remove_button(win).click()
    qapp.processEvents()
    keys, _ = use_menu_order(sw)
    fake = types.SimpleNamespace(sw=sw, menu=QMenu(), win=win, on_onoff=lambda: None,
                                 end_trial=lambda keep=False: None, quit=lambda: None)
    try:
        App.build_menu(fake)
        tray = [a.text() for a in fake.menu.actions()]
    finally:
        fake.menu.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        del sw.s["devices"]["Speakers|Old"]
        sw.s["hidden_devices"].clear()
        sw.refresh()
        win.render_all()
    check("devices: Use on device lists the devices that the Devices screen lists, in its sequence (a device that "
          "Windows does not list, with no profiles, in neither); a removed device is in neither, nor in the tray menu",
          agree == ([KEY, AWAY], [KEY, AWAY]) and keys == [KEY] and "Headphones (Buds)" not in tray
          and "Headset (EarPods)" in tray, (agree, keys, tray))


# (after tests\ui\conftest.py's THEMED_WINDOW: a device that Windows does not list, with a long name and a profile;
# its card and the window at the usual size and at the smallest size, the bubble after a click on Remove for the
# connected device at the two sizes, then the message after Remove, dark and light)
PICTURES = r'''
from PySide6.QtWidgets import QPushButton
from ui import bubble
path = os.path.join(top, "Old.txt")
with open(path, "w", encoding="utf-8") as fh:
    fh.write("Preamp: -3 dB\n")
pid = sw.import_profile(path, "Old dongle")
GONE = "Headset|USB-C to 3.5mm Headphone Jack Adapter (a long name for a test of the width of the card)"
sw.s["devices"][GONE] = {"label": "Headset (USB-C to 3.5mm Headphone Jack Adapter, a long name for a test of the "
                                  "width of the card)", "guids": ["{9}"], "profiles": [], "active": None}
sw.add_to_device(GONE, pid)
pics = os.path.join(top, "pictures")
os.makedirs(pics, exist_ok=True)
out = {}


def pump():
    for _ in range(8):
        qapp.processEvents()


def button():
    return next((b for b in win.dev_panel.findChildren(QPushButton) if b.text() == "Remove" and b.isVisibleTo(win)),
                None)


def inside(b):  # (the button whole: in its card, and in the window's sight)
    head = b.parentWidget()
    r = b.geometry()
    at = b.mapTo(win, b.rect().topLeft())
    return head.rect().contains(r) and 0 <= at.x() and at.x() + b.width() <= win.width()


for mode in ("dark", "light"):
    theme.apply(qapp, dark=mode == "dark", contrast=False)
    for size, (wd, ht) in (("usual", (1180, 900)), ("smallest", (300, 300))):
        win.resize(wd, ht)
        win.selected = GONE
        win.render_all()
        pump()
        b = button()
        win.grab().save(os.path.join(pics, f"window-{mode}-{size}.png"))
        if b is not None:
            b.parentWidget().grab().save(os.path.join(pics, f"card-{mode}-{size}.png"))
        ren = next(x for x in win.dev_panel.findChildren(QPushButton) if x.text() == "Rename…" and x.isVisible())
        out[f"{mode} {size}"] = {"size": [win.width(), win.height()], "button": b is not None and inside(b),
                                 "enabled": b is not None and b.isEnabled(),
                                 "gap": b.geometry().left() - ren.geometry().right() - 1 if b else None}
        win.selected = KEY  # (the connected device: Remove on, and a click tells why in a bubble at it)
        win.render_all()
        pump()
        button().click()
        pump()
        tell = bubble.last("tell")
        win.grab().save(os.path.join(pics, f"bubble-{mode}-{size}.png"))
        shows = tell is not None and tell.isVisible()
        out[f"{mode} {size} bubble"] = [tell.text.text() if shows else None, shows and tell.anchor is button(),
                                        shows and win.rect().contains(tell.geometry()), sw.record(KEY) is not None]
        if shows:
            tell.close_now()
    win.resize(1180, 900)
    win.selected = GONE
    win.render_all()
    pump()
    button().click()
    pump()
    win.grab().save(os.path.join(pics, f"message-{mode}.png"))
    out[f"{mode} message"] = [win.message.text.text(), win.message.bubble.isVisible()]
    win.message.undo_btn.click()
    pump()
    out[f"{mode} undo"] = [sw.record(GONE) is not None, win.selected == GONE]
print(json.dumps(out))
'''


def test_pictures_of_the_card_and_the_message(themed_window, check, fake_apo, tmp_path):
    out = subproc.run_python(themed_window + PICTURES, session.SESSION.app, str(tmp_path))
    d = out.data or {}
    pics = sorted(os.listdir(os.path.join(tmp_path, "pictures"))) if os.path.isdir(tmp_path / "pictures") else []
    message = ("Removed “Headset (USB-C to 3.5mm Headphone Jack Adapter, a long name for a test of the width of the "
               "card)” from Devices.")
    check("devices: in dark and light, at the usual size and at the smallest size, Remove is whole in the card and in "
          "the window with a long device name, 12 px after Rename…; for the connected device a click on it shows the "
          "bubble at it, in the window, and removes nothing; the message after a removal shows its words; Undo puts "
          "the device back and selects it; the pictures are saved",
          all(d.get(f"{m} {s}", {}).get("button") and d[f"{m} {s}"]["enabled"] and d[f"{m} {s}"]["gap"] == 12
              and d.get(f"{m} {s} bubble") == [CONNECTED, True, True, True]
              for m in ("dark", "light") for s in ("usual", "smallest"))
          and all(d.get(f"{m} message") == [message, True] and d.get(f"{m} undo") == [True, True]
                  for m in ("dark", "light")) and len(pics) == 14, d or out.stderr[-600:])
