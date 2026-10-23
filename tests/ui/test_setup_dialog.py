"""Set up (ui\\window.py's SetUpDialog; ui\\setup_dialog.py once the window is split): config.txt's EQ files added as
profiles, the one on now becoming the playing device's EQ, and EQ Switcher's Start with Windows turned off and EQ
Switcher asked to quit (both stand-ins here: tests\\ui\\conftest.py's set_up_window, which runs the dialog once for
this file). Moved from selftest.py's qt_checks. Then its look in Windows 11's (the restyle, 2026-10-23), in a Python of
its own, themed: its words wrap, nothing is cut or squeezed, Set up is the main action on a band of buttons."""
from helpers import session, subproc

KEY = "Headset|EarPods"

# (after tests\ui\conftest.py's THEMED_WINDOW: config.txt with lines on, EQ Switcher's among them, and two EQ files,
# so the dialog has all it can show; EQ Switcher's side stood in, never this PC's)
DIALOG = r'''
from PySide6.QtWidgets import QCheckBox, QFrame, QListWidget
with open(os.path.join(conf, "config.txt"), "w") as fh:
    fh.write("Preamp: -3 dB\nInclude: EQ Switcher\\switcher.txt\nInclude: EarPods.txt\n# Include: Samson.txt\n")
from ui import winsys
winsys.eq_switcher_autostart = lambda: True
winsys.eq_switcher_running = lambda: True
from ui.setup_dialog import SetUpDialog
dlg = SetUpDialog(sw, win)
dlg.show()
for _ in range(5):
    qapp.processEvents()
boxes = [b for b in dlg.findChildren(QCheckBox) if b.isVisible()]
go = getattr(dlg, "go_btn", None)


def hidden(lst):  # (rows not wholly in sight)
    return sum(1 for i in range(lst.count()) if lst.visualItemRect(lst.item(i)).bottom() >= lst.viewport().height())


print(json.dumps({"size": [dlg.width(), dlg.height()], "boxes": len(boxes),
                  "cut": [b.text()[:40] for b in boxes if b.width() < b.sizeHint().width()],
                  "lists": [(lst.count(), hidden(lst)) for lst in dlg.findChildren(QListWidget)],
                  "go": go and [go.text(), go.property("primary"), go.isDefault()],
                  "band": dlg.findChild(QFrame, "dialogFooter") is not None and go is not None
                  and go.parent().objectName() == "dialogFooter"}))
'''


def test_setting_up_adds_the_eq_files(set_up_window, check):
    w = set_up_window
    sw, rec = w.sw, w.sw.record(KEY)
    # was selftest.py:394
    check("window: setting up adds config.txt's EQ files, the one on now becoming the playing device's",
          len(sw.profiles()) == 2 and [sw.profile_name(i) for i in rec["profiles"]] == ["EarPods"]
          and rec["active"] == rec["profiles"][0] and sw.apo.set_up() and not w.win.banner.isVisible(),
          (sw.profiles(), rec, w.warnings))


def test_eq_switcher_turned_off_and_quit(set_up_window, check):
    w = set_up_window
    # was selftest.py:398
    check("window: Set up offers to turn off EQ Switcher's Start with Windows and to quit it (both ticked), and does "
          "both", w.offered == (True, True) and w.done_es == ["Start with Windows off", "quit"], (w.offered, w.done_es))


def test_the_set_up_dialog_as_windows_11(themed_window, check, fake_apo, tmp_path):
    # (its first line didn't wrap: the dialog was a thousand pixels wide; once it wrapped, Windows' limit of two
    # thirds of the screen cut its tick boxes' words and squeezed its lists to a row and a half)
    out = subproc.run_python(themed_window + DIALOG, session.SESSION.app, str(tmp_path))
    d = out.data or {}
    check("set up: its words wrap (no wider than 800 px), every tick box's words whole, and its lists show all their "
          "rows", 0 < (d.get("size") or [0])[0] <= 800 and (d.get("boxes") or 0) >= 3 and d.get("cut") == []
          and d.get("lists") == [[3, 0], [2, 0]], d or out.stderr[-300:])
    check("set up: Set up is its main action (in the accent, Enter's), on Windows 11's band of buttons below the words",
          d.get("go") == ["Set up", "true", True] and d.get("band") is True, d and (d.get("go"), d.get("band"))
          or out.stderr[-300:])
