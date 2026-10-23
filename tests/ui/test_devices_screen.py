"""Devices (the window's device screen, ui\\window.py; ui\\devices_screen.py once the window is split): the banner
asking to set APO up, the device playing chosen and APO missing on it said, the device's line saying whether its EQ
applies (Equalizer APO asked, by itself or with Check again: a stand-in answers for APO's Benchmark here), your name
for a device, trying an EQ for 5 minutes, and the device's choices. Moved from selftest.py's qt_checks.

One window for the whole file (tests\\ui\\conftest.py's devices_window, then set_up_window: the same window after
Set up), its tests in the old checks' order: each one starts from the state the one before left, as the old checks
did (the device's line keeps the last answer; the EQ choices count on the earlier tests putting things back).
Then the screen's look in Windows 11's (the restyle, 2026-10-23): its rows, a profile's quiet ✕ (drawn in a Python of
its own, themed), and the symbols beside its buttons' words.
"""
import os
import threading

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
# light, then light with Windows' green accent, beside the colours the theme has for each)
DOTS = r'''
eps.append(D.Endpoint("{3}", "Speakers", "Realtek(R) Audio", D.ACTIVE, True))
sw.refresh()
win.render_all()
for _ in range(5):
    qapp.processEvents()
''' + "{shapes}" + r'''
KINDS = {"Playing now": "playing", "Connected": "connected", "Not connected": "away"}


def dots():  # (each row's dot, by its row's words: the colour in its middle)
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
    check("window: the banner asks to set APO up", win.banner.isVisible() and "isn't using" in win.banner_text.text(),
          (win.banner.isVisible(), win.banner_text.text()))


def test_playing_device_chosen_and_apo_missing_said(devices_window, check):
    win = devices_window.win
    labels = [w.text() for w in win.dev_panel.findChildren(type(win.banner_text))]
    # was selftest.py:374
    check("window: the device playing is chosen, and APO missing on it is said",
          win.selected == "Headset|EarPods" and any("isn't installed on this device" in t for t in labels),
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
    chk = [b for b in win.dev_panel.findChildren(QPushButton) if b.text() == "Check again"]
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
    # was selftest.py:424
    check("window: Check again asks APO for the device's endpoint and says all it found (its EQ applies, but APO "
          "isn't on the device); the device's line says it too",
          len(chk) == 1 and "{5}" in told and any(isinstance(x, tuple) and x[0] == "not" and "applies on this device"
                                                   in x[1] and "isn't installed on this device" in x[1] for x in told)
          and line.startswith("✕ Equalizer APO isn't installed on this device"), (told, line))


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
          "(✕: APO doesn't read AutoEQ Studio's file)", again == [] and asked == ["{5}"]
          and "✕" in win.check_label.text() and "doesn't read" in win.check_label.text(), (again, asked,
                                                                                         win.check_label.text()))


def test_line_keeps_a_profiles_name_whole(check):
    # (the one-line answer kept a profile's name whole: "Truthear GATe (Diffuse field)" was cut at its bracket)
    from ui.window import check_line
    lines = [check_line(True, "“Truthear GATe (Diffuse field)” applies on this device: APO finds its section and "
                              "loads its file. config.txt also loads, on top: x.txt."),
             check_line(False, "AutoEQ Studio chose “A. B (C)”, but APO doesn't load its file for this device (the "
                               "file is missing from APO's folder)."),
             check_line(True, "AutoEQ Studio's EQ is off for this device (APO finds its section, with no EQ in it)."),
             check_line(None, "Couldn't ask Equalizer APO: Benchmark isn't there.")]
    # was selftest.py:489
    check("window: the device's line keeps a profile's name whole (brackets, a full stop) and drops the rest",
          lines == ["“Truthear GATe (Diffuse field)” applies on this device.",
                    "AutoEQ Studio chose “A. B (C)”, but APO doesn't load its file for this device.",
                    "AutoEQ Studio's EQ is off for this device.", "Couldn't ask Equalizer APO"], lines)


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
                  "Trial EQ" in win.trial_text.text(), win._status("Headset|EarPods")[1])
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
        app_mod.App.poll(type("A", (), {"sw": sw, "hotkey_problem": "",
                                        "end_trial": staticmethod(lambda keep=False: sw.end_trial(keep))})())
        # was selftest.py:562
        check("devices: Try for 5 minutes plays the EQ on that device only (APO's file, the bar, the status), Keep it "
              "makes it a profile switched on; a hand switch or the time up ends it; one left by a crash is gone at the "
              "next start",
              trying == (1, True, True, "Trying: Trial EQ") and after_crash == (False, False) and leftover.trial is None
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
    check("devices: the list's dots in the theme's colours (playing: its green; connected: Windows' accent, its default "
          "blue a green accent's stand-in; not connected: its grey), drawn again when Windows switches light or dark or "
          "its accent, each 3:1 on the list and the three told apart",
          all(right(c) for c in ("dark", "light", "green accent")), d or out.stderr[-300:])


def test_symbols_beside_the_device_screens_words(set_up_window, check, qapp):
    from PySide6.QtWidgets import QLabel, QPushButton
    win = set_up_window.win
    win.render_device_panel()
    qapp.processEvents()  # (the panel's new parts are shown on Qt's next turn)
    buttons = {b.text(): b for b in win.dev_panel.findChildren(QPushButton) if b.isVisible()}
    want = ("Rename…", "Add a profile", "Check again")
    signs = [(lab.accessibleName(), lab.property("role")) for lab in win.dev_panel.findChildren(QLabel)
             if lab.property("glyph") == "true" and lab.isVisible()]
    # (the playing device has no APO on it: its card says so)
    check("devices: Windows 11's symbols beside Rename…, Add a profile and Check again (their words unchanged), and "
          "the warning sign on the card saying APO isn't on the device",
          all(w in buttons and not buttons[w].icon().isNull() for w in want) and signs == [("Warning", "warn")],
          (sorted(buttons), [w for w in want if w in buttons and buttons[w].icon().isNull()], signs))
