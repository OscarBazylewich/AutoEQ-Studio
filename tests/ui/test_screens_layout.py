"""The layout of Devices, Profiles and Settings after the UI audit (2026-11-08, the user's selections): the device's
name, condition and Rename… in one card; each profile on two lines; a 5-minute EQ as a selected row of the device's
card (the user's answer: the tray marks it too); Make an EQ in Add a profile's menu; Profiles' general commands first,
a line, then those for a profile, and a gray line in its empty table; Settings at most about 900 px wide, the APO
card's condition first with its symbol, Add AutoEQ Studio to APO… in the accent."""
import os
import time

from helpers import qt

KEY = "Headset|EarPods"


def _profile(w, name):
    path = os.path.join(w.top, name + ".txt")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("Preamp: -3 dB\nFilter 1: ON PK Fc 1000 Hz Gain 3 dB Q 1\n")
    return w.sw.import_profile(path, name)


def test_the_device_card_and_its_rows(devices_window, check):
    from PySide6.QtCore import QPoint
    from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QRadioButton
    w = devices_window
    win, sw = w.win, w.sw
    pid = _profile(w, "Layout check")
    sw.add_to_device(KEY, pid, switch_on=True)
    try:
        win.show()
        win.show_page("devices", remember=False)
        win.selected = KEY
        win.render_all()
        qt.pump(10)
        panel = win.dev_panel
        title = next(lab for lab in panel.findChildren(QLabel) if lab.property("role") == "heading")
        ren = next(b for b in panel.findChildren(QPushButton) if b.text() == "Rename…")
        card = title.parentWidget()
        same_card = isinstance(card, QFrame) and card.property("card") == "true" and ren.parentWidget() is card
        rb = next(b for b in panel.findChildren(QRadioButton) if b.text() == "Layout check")
        data = next(lab for lab in panel.findChildren(QLabel) if lab.text().startswith("1 filter"))
        below = data.mapTo(panel, QPoint(0, 0)).y() >= rb.mapTo(panel, QPoint(0, 0)).y() + rb.height() - 2
        small = data.property("small") == "true"
        add = next(b for b in panel.findChildren(QPushButton) if b.text() == "Add a profile")
        items = [a.text() for a in add.menu().actions() if not a.isSeparator()]
        sw.trial = {"key": KEY, "name": "Bright", "until": time.time() + 200}
        win.render_all()
        qt.pump(10)
        radios = {b.text(): b.isChecked() for b in win.dev_panel.findChildren(QRadioButton)}
    finally:
        sw.trial = None
        sw.remove_profile(pid)
        win.render_all()
    check("devices: the name, its condition and Rename… are in one card; a profile's data is under its name in small "
          "gray text; Add a profile's menu ends with Import EQ files… and Make an EQ; during a 5-minute EQ the card "
          "selects it, not the usual profile",
          same_card and below and small and items[-2:] == ["Import EQ files…", "Make an EQ"]
          and radios.get("For 5 minutes: Bright") is True and radios.get("Layout check") is False
          and radios.get("Off") is False, (same_card, below, small, items, radios))


def test_profiles_commands_and_its_empty_table(devices_window, check):
    from PySide6.QtWidgets import QFrame, QPushButton
    w = devices_window
    win = w.win
    win.show()
    win.show_page("profiles", remember=False)
    win.render_profiles()
    qt.pump(10)
    page = win.pages["profiles"]
    row = [b for b in page.findChildren(QPushButton) if b.isVisibleTo(win)] +         [f for f in page.findChildren(QFrame) if f.property("vline") == "true"]
    order = sorted(row, key=lambda b: b.mapTo(win, b.rect().topLeft()).x())
    names = ["|" if not isinstance(b, QPushButton) else b.text() for b in order]
    empty = (win.prof_table.rowCount() == 0, win.prof_empty.label.isVisibleTo(win), win.prof_empty.label.text())
    win.show_page("devices", remember=False)
    check("profiles: Import EQ files… and Open the profiles folder first, a line, then Edit in Make an EQ, Rename… and "
          "Delete… last; an empty table tells the next step in one gray line",
          names == ["Import EQ files…", "Open the profiles folder", "|", "Edit in Make an EQ", "Rename…", "Delete…"]
          and empty[0] and empty[1] and "Import EQ files" in empty[2], (names, empty))


def test_settings_width_and_the_apo_card(devices_window, check):
    w = devices_window
    win = w.win
    win.show()
    win.resize(1500, 800)
    win.show_page("settings", remember=False)
    win.render_settings()
    qt.pump(10)
    cards = win.chk_autostart.parentWidget()
    width, left = cards.width(), cards.mapTo(win, cards.rect().topLeft()).x()
    state = (win.apo_state.text(), win.apo_state.property("role"), win.apo_mark.isVisibleTo(win),
             win.btn_setup.property("primary"), win.apo_path.text())
    win.resize(1040, 760)
    win.show_page("devices", remember=False)
    check("settings: on a wide window the cards are at most 900 px wide, at the left; the APO card says its condition "
          "first (a warning while APO does not use AutoEQ Studio), the folder under it, Add… in the accent",
          width <= 900 and left <= 20 and state[0] == "APO does not use AutoEQ Studio." and state[1] == "warn"
          and state[2] and state[3] == "true" and state[4].startswith("Its config folder:"), (width, left, state))
