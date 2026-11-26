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

import pytest

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
    check("window: the banner asks to set APO up", win.banner.isVisible()
          and win.banner_text.text() == "Equalizer APO isn't loading AutoEQ Studio. Check config.txt.",
          (win.banner.isVisible(), win.banner_text.text()))


def test_playing_device_chosen_and_apo_missing_said(devices_window, check):
    win = devices_window.win
    labels = [w.text() for w in win.dev_panel.findChildren(type(win.banner_text))]
    # was selftest.py:374
    check("window: the device playing is chosen, and APO missing on it is said",
          win.selected == "Headset|EarPods" and any("isn't installed on this device" in t for t in labels),
          (win.selected, labels))


@pytest.fixture
def apo_on(set_up_window):
    """The window after Set up, with Equalizer APO on the playing device while the test runs
    (tests\\ui\\conftest.py's apo_on_playing_device)."""
    with set_up_window.apo_on_playing_device():
        yield set_up_window


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
    name = sw.profiles()[rec["active"]]["name"]
    # was selftest.py:424. (The owner, 2026-11-25: the card's own warning bar says that APO isn't installed on the
    # device, so the line shows the rest of the answer, a gray note with no ✓, not a second warning bar)
    check("window: Check again asks APO for the device's endpoint and says all it found (its EQ applies, but APO "
          "isn't on the device); the device's line shows the rest, not a second warning bar",
          len(chk) == 1 and "{5}" in told and any(isinstance(x, tuple) and x[0] == "not" and "device section found and EQ file loaded"
                                                   in x[1] and "isn't installed on this device" in x[1] for x in told)
          and line == f"APO is using “{name}”" and win.check_label.property("role") == "muted"
          and "device section found and EQ file loaded" in win.check_label.toolTip()
          and not bar[0] and bar[2] and _visible_not_installed(win) == 1, (told, line, bar, _visible_not_installed(win)))


def _visible_not_installed(win):
    """How many labels that the device's card shows say that Equalizer APO isn't installed on the device."""
    from PySide6.QtWidgets import QLabel
    return sum("isn't installed on this device" in lab.text() for lab in win.dev_panel.findChildren(QLabel)
               if lab.isVisibleTo(win))


def test_one_not_installed_sentence_on_a_device_without_apo(set_up_window, check, monkeypatch):
    # (the owner, 2026-11-25: on a device without Equalizer APO, the card's warning bar says so; a problem of the
    # configuration still shows as the line's warning bar, with Examine again, but without "Also, Equalizer APO isn't
    # installed …", and every other finding stays; the message box of Examine again has all of the answer)
    from PySide6.QtWidgets import QMessageBox
    from switcher import check as apo_check
    w = set_up_window
    win, sw = w.win, w.sw
    name = sw.profiles()[sw.record(KEY)["active"]]["name"]
    other = os.path.join(sw.apo.config, "Loudness.txt")
    told = []
    monkeypatch.setattr(apo_check, "run", lambda apo, guid, timeout=60: {
        "loaded": [apo.config_txt, other, os.path.join(apo.config, "AutoEQ Studio", "switcher.txt")],
        "matched": ["{5}"]})
    for kind in ("information", "warning"):
        monkeypatch.setattr(QMessageBox, kind, staticmethod(lambda *a, **k: told.append(a[2])))
    try:
        win._checks.clear()
        win.check_device(KEY)
        qt.wait_for(lambda: told, 10)
    finally:
        monkeypatch.undo()
    bar_text, tip = win.check_warn_text.text(), win.check_warn_text.toolTip()
    shown = (win.check_warn.isVisibleTo(win), win.check_row.isVisibleTo(win), _visible_not_installed(win))
    check("devices: a device without APO with a problem in the configuration: its line is a warning bar with the "
          "problem and the other findings, without the card's sentence that APO isn't installed; one label says that",
          bar_text == f"“{name}” is selected, but APO isn't loading it" and shown == (True, False, 1)
          and "config.txt also loads these files for this device: Loudness.txt" in tip
          and "isn't installed" not in tip
          and len(told) == 1 and "Also, Equalizer APO isn't installed on this device" in told[0]
          and f"“{name}” is selected, but APO isn't loading it" in told[0], (bar_text, tip, shown, told))


def test_check_again_on_a_device_with_apo(apo_on, check, monkeypatch):
    # (as test_check_again, with Equalizer APO on the device; its answer is bad: the profile's file is not loaded)
    from PySide6.QtWidgets import QMessageBox, QPushButton
    from switcher import check as apo_check
    w = apo_on
    win, sw = w.win, w.sw
    rec = sw.record(KEY)
    win._checks.clear()
    chk = [b for b in win.dev_panel.findChildren(QPushButton) if b.text() == "Examine again" and b.isVisibleTo(win)]
    name = sw.profiles()[rec["active"]]["name"]
    told = []
    monkeypatch.setattr(apo_check, "run", lambda apo, guid, timeout=60: (told.append(guid), {
        "loaded": [apo.config_txt, os.path.join(apo.config, "AutoEQ Studio", "switcher.txt")],
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
    check("window: Check again asks APO for the device's endpoint and says all it found (the profile is selected, but "
          "APO isn't loading its file); the device's line says it too, as a warning bar in the line's place",
          len(chk) == 1 and "{5}" in told and any(isinstance(x, tuple) and x[0] == "not"
                                                  and f"“{name}” is selected, but APO isn't loading it" in x[1]
                                                  for x in told)
          and line == f"“{name}” is selected, but APO isn't loading it" and bar[0] and bar[1] == line
          and not bar[2], (told, line, bar))


def test_examine_again_shows_no_wait_message(apo_on, check, monkeypatch):
    # (the text survey, area 27, 2026-11-24: Examine again shows no message while it waits; the line beside it says
    # "Checking Equalizer APO…", and then the message box shows all the results)
    from PySide6.QtWidgets import QMessageBox
    from switcher import check as apo_check
    win = apo_on.win
    win._checks.clear()
    said, boxes, line = [], [], []
    monkeypatch.setattr(win, "status", lambda *a, **k: said.append(a[0] if a else k))
    monkeypatch.setattr(apo_check, "run", lambda apo, guid, timeout=60: {"loaded": [], "matched": []})
    for kind in ("information", "warning"):
        monkeypatch.setattr(QMessageBox, kind, staticmethod(lambda *a, **k: boxes.append(a[2])))
    real = win._show_check
    monkeypatch.setattr(win, "_show_check", lambda key: (real(key), line.append(win.check_label.text()))[0])
    win.check_device(KEY)
    qt.wait_for(lambda: boxes, 10)
    monkeypatch.undo()
    check("devices: Examine again shows no message while it waits; the line says “Checking Equalizer APO…”, then the "
          "message box shows the result", said == [] and "Checking Equalizer APO…" in line and len(boxes) == 1
          and boxes[0].startswith("Equalizer APO isn't loading AutoEQ Studio"), (said, line, boxes))


def test_line_asked_once_per_change(apo_on, check, monkeypatch, qapp):
    # the line asks by itself, once per change (the answer kept while nothing it depends on changes: here the one
    # the line got when Equalizer APO came on the device, apo_on)
    from switcher import check as apo_check
    win = apo_on.win
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
          and win.check_warn.isVisibleTo(win) and "isn't loading" in win.check_warn_text.text(), (again, asked,
                                                                                         win.check_label.text()))


def test_line_keeps_a_profiles_name_whole(check):
    # (the one-line answer kept a profile's name whole: "Truthear GATe (Diffuse field)" was cut at its bracket)
    from ui.window import check_line
    lines = [check_line(True, "APO is using “Truthear GATe (Diffuse field)”: device section found and EQ file "
                              "loaded. config.txt also loads these files for this device: x.txt"),
             check_line(False, "“A. B (C)” is selected, but APO isn't loading it (file missing from APO folder)"),
             check_line(True, "EQ is off for this device (APO sees its section with no active profile)"),
             check_line(None, "Couldn't read Equalizer APO status: Benchmark tool not found. Install Equalizer APO "
                              "1.3 or newer."),
             check_line(False, "Equalizer APO isn't installed on this device, so EQ won't apply. Enable it in APO "
                               "Configurator, then restart Windows.")]
    # was selftest.py:489. (2026-11-24, the text survey, area 27: the line is one sentence or fragment, so it has no end
    # period (style.md, rule 4 of the checklist), as the owner typed these texts; check_line added one)
    check("window: the device's line keeps a profile's name whole (brackets, a full stop) and drops the rest, with no "
          "end period",
          lines == ["APO is using “Truthear GATe (Diffuse field)”",
                    "“A. B (C)” is selected, but APO isn't loading it",
                    "EQ is off for this device", "Couldn't read Equalizer APO status",
                    "Equalizer APO isn't installed on this device, so EQ won't apply"],
          lines)


def test_eq_switched_while_apo_is_asked(apo_on, check, monkeypatch, qapp):
    # (the EQ switched while APO is still being asked: the line is about the new one, not the one asked about)
    from switcher import check as apo_check
    w = apo_on
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
    told = win.check_label.toolTip() if win.check_label is not None else ""  # (all of the answer)
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
              trying == (1, True, True, "5-min preview: Trial EQ") and after_crash == (False, False) and leftover.trial is None
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


def _card_focus(win):
    """The control with the focus, as the checks name it: its words or its name for a screen reader, and whether it is
    in the device's card."""
    from PySide6.QtWidgets import QApplication
    f = QApplication.focusWidget()
    if f is None:
        return None
    words = f.accessibleName() or (f.text() if callable(getattr(f, "text", None)) else "")
    return words if win.dev_panel.isAncestorOf(f) and f.isVisible() else f"out of the card: {words}"


def test_the_card_keeps_the_focus_in_its_place(set_up_window, check, qapp, tmp_path):
    # (2026-11-13, measured with the fault of Calculate: Off, a profile and a profile's ✕ make the card again, and the
    # focus went to the window's Make an EQ button, where Space opened Make an EQ. Now the focus stays at the same place
    # in the new card: the same control, or the row in the place of a removed row, else Add a profile)
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QRadioButton, QToolButton
    win, sw = set_up_window.win, set_up_window.sw
    rec = sw.record(KEY)
    was = (list(rec["profiles"]), rec["active"])
    made = []
    seen = {}

    def named(kind, words):
        return next(w for w in win.dev_panel.findChildren(kind) if w.isVisible()
                    and words in (w.text(), w.accessibleName()))

    def press(w, key=Qt.Key_Space):
        w.setFocus(Qt.TabFocusReason)  # (as Tab puts it there: a keyboard user's way)
        QTest.keyClick(w, key)
        for _ in range(5):
            qapp.processEvents()
        return _card_focus(win)
    try:
        for pid in was[0]:  # (the file's own profiles off the device for the test: put back after)
            sw.remove_from_device(KEY, pid)
        for name in ("Card A", "Card B", "Card C"):
            path = tmp_path / f"{name}.txt"
            path.write_text("Preamp: -1 dB\nFilter 1: ON PK Fc 100 Hz Gain -2 dB Q 1\n", encoding="utf-8")
            pid = sw.import_profile(str(path), name)
            made.append(pid)
            sw.add_to_device(KEY, pid, switch_on=False)
        sw.set_active(KEY, made[2])
        win.selected = KEY
        win.show_page("devices", remember=False)
        win.render_all()
        win.activateWindow()
        for _ in range(5):
            qapp.processEvents()
        seen["Off"] = press(named(QRadioButton, "Off"))
        seen["Down from Off"] = press(named(QRadioButton, "Off"), Qt.Key_Down)
        seen["Card B"] = press(named(QRadioButton, "Card B"))
        seen["✕ of Card B"] = press(named(QToolButton, "Remove Card B from this device"))
        seen["✕ of the last row"] = press(named(QToolButton, "Remove Card C from this device"))
        seen["✕ of the only row"] = press(named(QToolButton, "Remove Card A from this device"))
        rows = [r.text() for r in win.dev_panel.findChildren(QRadioButton) if r.isVisible()]
    finally:
        for pid in made:
            sw.remove_profile(pid)
        for pid in was[0]:
            if pid not in sw.record(KEY)["profiles"]:
                sw.add_to_device(KEY, pid, switch_on=False)
        sw.set_active(KEY, was[1])
        win.render_all()
        qapp.processEvents()
    check("devices: Off, a profile and a profile's ✕ with the keyboard keep the focus at the same place in the "
          "device's card: the same control, the row now in the removed row's place, else the row before it, else Add "
          "a profile (it went to the window's Make an EQ button)",
          seen == {"Off": "Off", "Down from Off": "Card A", "Card B": "Card B",
                   "✕ of Card B": "Remove Card C from this device",
                   "✕ of the last row": "Remove Card A from this device", "✕ of the only row": "Add a profile"}
          and rows == ["Off"], (seen, rows))


def test_the_card_keeps_its_place_in_a_small_window(set_up_window, check, qapp, tmp_path):
    # (2026-11-15, the verifier of round 2: the old parts hid one by one with the focus, and each gave it to the next
    # control of the card: the card scrolled to its end, and a profile at the top of the view went out of sight)
    from PySide6.QtCore import QPoint, QRect, Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication, QRadioButton, QScrollArea, QToolButton
    win, sw = set_up_window.win, set_up_window.sw
    rec = sw.record(KEY)
    was, size = (list(rec["profiles"]), rec["active"]), win.size()
    made, seen = [], {}
    area = next(a for a in win.findChildren(QScrollArea) if a.widget() is win.dev_panel)
    bar, vp = area.verticalScrollBar(), area.viewport()

    def pump():
        for _ in range(8):
            qapp.processEvents()
    try:
        for pid in was[0]:
            sw.remove_from_device(KEY, pid)
        for i in range(14):
            path = tmp_path / f"Row {i:02d}.txt"
            path.write_text("Preamp: -1 dB\nFilter 1: ON PK Fc 100 Hz Gain -2 dB Q 1\n", encoding="utf-8")
            made.append(sw.import_profile(str(path), f"Row {i:02d}"))
            sw.add_to_device(KEY, made[-1], switch_on=False)
        sw.set_active(KEY, made[0])
        win.resize(1040, 560)
        win.selected = KEY
        win.show_page("devices", remember=False)
        win.render_all()
        win.activateWindow()
        pump()
        for kind, words in ((QRadioButton, "Row 02"), (QToolButton, "Remove Row 03 from this device")):
            w = next(x for x in win.dev_panel.findChildren(kind) if x.isVisible()
                     and words in (x.text(), x.accessibleName()))
            bar.setValue(w.mapTo(win.dev_panel, QPoint(0, 0)).y() - 4)  # (the row at the top of the view)
            pump()
            w.setFocus(Qt.TabFocusReason)
            at = bar.value()
            QTest.keyClick(w, Qt.Key_Space)
            pump()
            f = QApplication.focusWidget()
            seen[words] = (at > 0, bar.value() == min(at, bar.maximum()), f is not None
                           and win.dev_panel.isAncestorOf(f) and vp.rect().contains(QRect(f.mapTo(vp, QPoint(0, 0)),
                                                                                          f.size())))
    finally:
        for pid in made:
            sw.remove_profile(pid)
        for pid in was[0]:
            if pid not in sw.record(KEY)["profiles"]:
                sw.add_to_device(KEY, pid, switch_on=False)
        sw.set_active(KEY, was[1])
        win.resize(size)
        win.render_all()
        qapp.processEvents()
    check("devices: in a card that scrolls, Space on a profile or on a profile's ✕ at the top of the view keeps the "
          "card where it is, and the focus in sight (the card scrolled to its end, the focus out of sight)",
          seen == {"Row 02": (True, True, True), "Remove Row 03 from this device": (True, True, True)}, seen)


def test_a_selection_before_does_not_move_the_focus_later(set_up_window, check, qapp, tmp_path):
    # (2026-11-15, round 3 of the fault of Calculate: the card keeps the round button that a selection with the
    # keyboard selected only while it makes the card for that selection, _card_choose. Kept after it, the next card,
    # made for another reason with the focus on Off, gave the focus to that profile)
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QRadioButton
    win, sw = set_up_window.win, set_up_window.sw
    rec = sw.record(KEY)
    was = (list(rec["profiles"]), rec["active"])
    made = []

    def named(words):
        return next(w for w in win.dev_panel.findChildren(QRadioButton) if w.isVisible() and w.text() == words)

    def pump():
        for _ in range(5):
            qapp.processEvents()
    try:
        for pid in was[0]:
            sw.remove_from_device(KEY, pid)
        for name in ("Card A", "Card B"):
            path = tmp_path / f"{name}.txt"
            path.write_text("Preamp: -1 dB\nFilter 1: ON PK Fc 100 Hz Gain -2 dB Q 1\n", encoding="utf-8")
            made.append(sw.import_profile(str(path), name))
            sw.add_to_device(KEY, made[-1], switch_on=False)
        sw.set_active(KEY, None)
        win.selected = KEY
        win.show_page("devices", remember=False)
        win.render_all()
        win.activateWindow()
        pump()
        b = named("Card B")
        b.setFocus(Qt.TabFocusReason)
        QTest.keyClick(b, Qt.Key_Space)  # (Card B selected: the card is made again, the focus on Card B)
        pump()
        after_space = _card_focus(win)
        named("Off").setFocus(Qt.TabFocusReason)  # (Shift+Tab's way: the focus on Off, nothing selected)
        pump()
        win.render_all()  # (the card made again for another reason, as when the window shows again)
        pump()
        again = _card_focus(win)
    finally:
        for pid in made:
            sw.remove_profile(pid)
        for pid in was[0]:
            if pid not in sw.record(KEY)["profiles"]:
                sw.add_to_device(KEY, pid, switch_on=False)
        sw.set_active(KEY, was[1])
        win.render_all()
        qapp.processEvents()
    check("devices: after a profile selected with the keyboard, the focus moved to Off stays on Off when the card is "
          "made again for another reason (the selection before gave the focus to that profile)",
          (after_space, again) == ("Card B", "Off"), (after_space, again))


def test_the_device_list_keeps_the_focus_when_the_card_is_made_again(set_up_window, check, qapp):
    # (2026-11-15, the verifier of round 3: the card's panel takes the focus before its old parts hide only when a
    # control of the card has it. Always, it took the focus from the device list. No test found that)
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication
    win = set_up_window.win
    win.selected = KEY
    win.show_page("devices", remember=False)
    win.render_all()
    win.activateWindow()
    qapp.processEvents()
    win.dev_list.setFocus(Qt.TabFocusReason)
    qapp.processEvents()
    win.render_all()  # (the card made again, as for a change of the device's EQ)
    for _ in range(5):
        qapp.processEvents()
    f = QApplication.focusWidget()
    check("devices: the device list keeps the focus when the card is made again (the card's panel took it)",
          f is win.dev_list, f)


def _examine_again(w, monkeypatch, start, new, how):
    """Examine again pressed (how: "Space" or "click") in the card of the playing device, with a stand-in for
    Equalizer APO's Benchmark tool: its answer `start` ("bad": the warning bar shows; "good": the line shows) is on
    the card, then it answers `new`, only when the test lets it (so the card is seen while it waits). What was seen
    while it waited and after the answer: [the control with the focus, the line shows, the warning bar shows]; then
    what the next Space did: [how many times it asked Equalizer APO, the screens it opened]."""
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton
    from switcher import check as apo_check
    win, sw = w.win, w.sw
    rec = sw.record(KEY)
    p = sw.profiles().get(rec["active"]) if rec["active"] else None
    good = {"loaded": [sw.apo.config_txt, os.path.join(sw.apo.config, "AutoEQ Studio", "switcher.txt")]
            + ([os.path.join(sw.apo.profiles, p["file"])] if p else []), "matched": ["{5}"]}
    answer, asked, opened, go = [start], [], [], threading.Event()

    def run(apo, guid, timeout=60):
        go.wait(20)
        asked.append(guid)
        return good if answer[0] == "good" else {"loaded": [], "matched": []}

    def seen():
        f = QApplication.focusWidget()
        words = f.text() if isinstance(f, QPushButton) else type(f).__name__
        in_card = f is not None and f.isVisible() and win.dev_panel.isAncestorOf(f)
        return [words if in_card else f"out of the card: {words}", win.check_row.isVisibleTo(win),
                win.check_warn.isVisibleTo(win)]
    monkeypatch.setattr(apo_check, "run", run)
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: None))
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: None))
    # (the window's Make an EQ button, where the focus went: its click is recorded, the screen never opened)
    monkeypatch.setattr(win, "show_page", lambda key, remember=True: opened.append(key))
    qt.wait_for(lambda: not win._checking, 20)  # (an answer asked for before: in, so the card asks the stand-in now)
    go.set()
    win._checks.clear()
    win.render_all()
    qt.wait_for(lambda: not win._checking, 20)
    qt.pump(50)
    again = next(b for b in win.dev_panel.findChildren(QPushButton) if b.text() == "Examine again"
                 and b.isVisibleTo(win))
    out = {"start": seen()[1:]}
    answer[0] = new
    go.clear()
    if how == "Space":
        again.setFocus(Qt.TabFocusReason)  # (as Tab puts it there: a keyboard user's way)
        QTest.keyClick(again, Qt.Key_Space)
    else:
        QTest.mouseClick(again, Qt.LeftButton)
    qt.pump(50)
    out["wait"] = seen()
    go.set()
    qt.wait_for(lambda: not win._checking, 20)
    qt.pump(50)
    out["after"] = seen()
    before = len(asked)
    QTest.keyClick(QApplication.focusWidget(), Qt.Key_Space)  # (the person's next key)
    qt.wait_for(lambda: not win._checking, 20)
    qt.pump(50)
    out["next Space"] = [len(asked) - before, opened]
    monkeypatch.undo()
    return out


def test_examine_again_keeps_the_focus_in_the_card(set_up_window, check, qapp, monkeypatch):
    # (2026-11-16, the verifier of the merged focus work: Examine again asks Equalizer APO again. While it waits, the
    # line shows in the place of the warning bar, and a bad answer puts the bar in the place of the line. The part
    # that hid had the focus on its Examine again: the focus went to the window's Make an EQ button, where the next
    # Space opened Make an EQ. Now the Examine again of the part that shows takes it)
    import dataclasses
    w = set_up_window
    win, sw = w.win, w.sw
    headset = w.eps[0]
    win.selected = KEY
    win.show_page("devices", remember=False)
    win.activateWindow()
    got = {}
    try:
        # (Equalizer APO on the device: then the Benchmark tool's answer alone decides between the line and the bar)
        w.eps[0] = dataclasses.replace(headset, apo=True)
        sw.refresh()
        for how in ("Space", "click"):
            for start in ("bad", "good"):
                for new in ("bad", "good"):
                    got[(how, start, new)] = _examine_again(w, monkeypatch, start, new, how)
    finally:
        monkeypatch.undo()
        w.eps[0] = headset
        sw.refresh()
        win._checks.clear()
        win.render_all()
        qt.wait_for(lambda: not win._checking, 20)
    line, bar = [True, False], [False, True]

    def wrong(how):
        """The cases of this way that are not as wanted (none: all 4 were seen, each as wanted)."""
        want = {(how, start, new): {"start": bar if start == "bad" else line, "wait": ["Examine again", *line],
                                    "after": ["Examine again", *(bar if new == "bad" else line)],
                                    "next Space": [1, []]}
                for start in ("bad", "good") for new in ("bad", "good")}
        return {k: got.get(k) for k in want if got.get(k) != want[k]}
    check("devices: Space on Examine again in the device's card keeps the focus on the Examine again that shows, "
          "while Equalizer APO is asked and after its answer, and the next Space asks again: with the warning bar or "
          "the line at the start, and a bad or a good new answer (the part that hid gave the focus to the window's "
          "Make an EQ button, where the next Space opened Make an EQ)", not wrong("Space"), wrong("Space"))
    check("devices: a click on Examine again in the device's card keeps the focus on the Examine again that shows, "
          "while Equalizer APO is asked and after its answer, and the next Space asks again: with the warning bar or "
          "the line at the start, and a bad or a good new answer (the part that hid gave the focus to the window's "
          "Make an EQ button, where the next Space opened Make an EQ)", not wrong("click"), wrong("click"))


def test_examine_again_keeps_the_focus_when_the_card_is_made_again(apo_on, check, qapp, monkeypatch):
    # (2026-11-16: the EQ hotkey changes the device's EQ while Examine again in the warning bar has the focus. The
    # card is made again and asks Equalizer APO again: the line shows, with its own Examine again. The two buttons
    # had different places in the card, so the focus went to Add a profile, where Space opened its menu)
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication, QPushButton
    from switcher import check as apo_check
    win, sw = apo_on.win, apo_on.sw
    was = sw.record(KEY)["active"]
    go = threading.Event()
    go.set()
    monkeypatch.setattr(apo_check, "run", lambda apo, guid, timeout=60: (go.wait(20), {"loaded": [], "matched": []})[1])

    def seen():
        f = QApplication.focusWidget()
        return [f.text() if isinstance(f, QPushButton) else type(f).__name__, win.check_row.isVisibleTo(win),
                win.check_warn.isVisibleTo(win)]
    try:
        qt.wait_for(lambda: not win._checking, 20)
        win._checks.clear()
        win.selected = KEY
        win.show_page("devices", remember=False)
        win.render_all()
        win.activateWindow()
        qt.wait_for(lambda: not win._checking, 20)
        qt.pump(50)
        again = next(b for b in win.dev_panel.findChildren(QPushButton) if b.text() == "Examine again"
                     and b.isVisibleTo(win))
        again.setFocus(Qt.TabFocusReason)
        qt.pump(20)
        start = seen()
        go.clear()
        sw.cycle(KEY)  # (what the EQ hotkey does: on_hotkey in ui/app.py)
        qt.pump(50)
        wait = seen()
        go.set()
        qt.wait_for(lambda: not win._checking, 20)
        qt.pump(50)
        after = seen()
    finally:
        go.set()
        monkeypatch.undo()
        sw.set_active(KEY, was)
        win._checks.clear()
        win.render_all()
        qt.wait_for(lambda: not win._checking, 20)
    check("devices: Examine again keeps the focus when the EQ hotkey changes the device's EQ while Examine again in "
          "the warning bar has the focus: on the Examine again of the line while Equalizer APO is asked again, then "
          "on the one of the warning bar (the focus went to Add a profile)",
          (start, wait, after) == (["Examine again", False, True], ["Examine again", True, False],
                                   ["Examine again", False, True]), (start, wait, after))


# ---------------------------------------------------------------- Remove (a device), 2026-11-12
# (after an update of Equalizer APO or a driver, Windows can give a device a new entry, and the old one stayed in
# Devices for good: Remove removes only a device that is not connected, with Undo; the lists of devices agree.
# For a connected device Remove stays on and a bubble at it tells why: UI-RULES 25)
AWAY = "Headphones|Buds"  # (in Windows' list, not connected)
GONE = "Headset|USB-C to 3.5mm Headphone Jack Adapter"  # (no longer in Windows' list)
TIP = "Remove from Devices. Its profiles stay in Profiles."
CONNECTED = "Disconnect this device before removing it"


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


def test_the_help_of_remove_says_from_devices(check):
    # (2026-11-12: a source line of 121 characters. The 120-character limit stays: the commit c611474 of 2026-11-23
    # kept it. The test audit of 2026-11-25 took out two parts: the lines were cut at the text {'key': '#use-device'
    # (the next entry, with these quotes), so a change of the quotes or of the order of the entries broke the check;
    # they are now the lines from the entry's key to the next key, in either quotes. And the empty line of
    # "#dev-remove" in HELP: tests\eq_screen\test_help_tags.py's test_controls_without_a_tooltip checks it with the
    # other empty lines, NO_TOOLTIP)
    import re
    from ui import help_text_devices as H
    entry = next(i for s in H.SETTINGS_DEVICES for i in s["items"] if i["key"] == "#dev-remove")
    texts = entry["body"] + [H.HELP_DEVICES["#dev-remove"]]
    with open(H.__file__, encoding="utf-8") as fh:
        lines = fh.read().split("\n")
    key = re.compile(r"""["']key["']\s*:""")
    first = next(i for i, line in enumerate(lines) if key.search(line) and "#dev-remove" in line)
    end = next((i for i in range(first + 1, len(lines)) if key.search(lines[i])), len(lines))
    part = lines[first:end] + [line for line in lines[:first] if "#dev-remove" in line]  # (and its line in HELP)
    wide = [line for line in part if len(line) > 120]
    check("devices: the source lines of the Help of Remove have 120 characters or fewer; the words say \"from "
          "Devices\" (one name), not \"from the list\"",
          not wide and "from the list" not in " ".join(texts), (wide, texts))


def test_rename_and_examine_again_without_a_help_line(apo_on, check, monkeypatch):
    # (2026-11-24, the text survey, area 30: the Help lines of "#dev-rename" and "#dev-check" removed. Rename… and the
    # two Examine again buttons keep the tooltips that their own code gives them, and a screen reader reads their
    # name (the title of their Help entry), then their tooltip (the owner's rule of 2026-11-24); the line about
    # Equalizer APO keeps its tag for F1, and a screen reader reads its tooltip, all of the answer, after its name)
    from PySide6.QtWidgets import QPushButton
    from switcher import check as apo_check
    win = apo_on.win
    monkeypatch.setattr(apo_check, "run", lambda apo, guid, timeout=60: {"loaded": [], "matched": []})
    win._checks.clear()
    win.render_device_panel()
    qt.wait_for(lambda: not win._checking, 10)
    buttons = win.dev_panel.findChildren(QPushButton)
    ren = next(b for b in buttons if b.text() == "Rename…")
    again = [b for b in buttons if b.text() == "Examine again"]
    got = {"Rename…": (ren.toolTip(), ren.accessibleName(), qt.description(ren), ren.property("help_key"))}
    got.update({f"Examine again {i}": (b.toolTip(), b.accessibleName(), qt.description(b),
                                       b.property("help_key")) for i, b in enumerate(again)})
    lab = win.check_label
    got["line"] = (lab.accessibleName(), qt.description(lab), lab.property("help_key"))
    answer = lab.toolTip()
    monkeypatch.undo()
    exam_tip = "Re-check with Equalizer APO's read-only Benchmark tool and show full results"
    exam = (exam_tip, "Does Equalizer APO use the EQ? (Examine again)", exam_tip, "#dev-check")
    rename_tip = "Set a custom name for this device (e.g., your headphone or IEM)"
    check("devices: Rename… and Examine again keep their own tooltips, which a screen reader reads after their name; "
          "the line about Equalizer APO keeps its name and its tag for F1, and a screen reader reads its tooltip",
          answer.startswith("Equalizer APO isn't loading AutoEQ Studio")
          and got == {"Rename…": (rename_tip, "Rename… (a device)", rename_tip, "#dev-rename"),
                      "Examine again 0": exam, "Examine again 1": exam,
                      "line": ("Does Equalizer APO use the EQ? (Examine again)", answer, "#dev-check")}, got)



def test_every_tagged_control_reads_its_tooltip(apo_on, check):
    # (the owner's rule of 2026-11-24: the line a screen reader reads after a control's name is its tooltip. A review
    # of the text survey found help_window.tag giving the Help line as the description, which stayed when the
    # control's own code gave it a different tooltip: Remove (a device) was the first case found, and its own test
    # went in the test audit of 2026-11-25, as this one fails for it too. Every control of the window tagged for F1,
    # on each screen)
    from PySide6.QtWidgets import QWidget
    win = apo_on.win
    tagged = [w for w in win.findChildren(QWidget) if w.property("help_key")]
    differ = [(w.property("help_key"), type(w).__name__, w.toolTip(), qt.description(w)) for w in tagged
              if qt.description(w) != w.toolTip()]
    check("devices: a screen reader reads the tooltip of each control of the window tagged for F1",
          len(tagged) > 10 and not differ, (len(tagged), differ))


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
          off == (None, False, KEY, "Removed “My buds” from Devices. It will reappear when reconnected.", True, True,
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
                                                                       "will reappear when reconnected.")
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
          got == ("Can't undo: “Headphones (Buds)” was reconnected", [], True, AWAY, AWAY), got)


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
