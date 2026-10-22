"""The App (ui\\app.py: the tray, the window, the hotkey, Online / Offline) in a Python of its own, on a stand-in APO
folder, data folder and EQ Switcher settings in the test's folder: EQ Switcher's profiles brought over on the first
start, Offline kept for the next start. Moved from selftest.py's app_checks."""
import json
import os

from helpers import apo, session, subproc

COVERS = ("ui.app", "switcher.core", "net", "paths", "ui.window")

# (two starts of the app in one Python, without an event loop: the App's delayed message boxes never show, and no
# hotkey is registered: the one brought over is empty)
CODE = ("import sys; sys.path.insert(0, sys.argv[1])\n"
        "from PySide6.QtWidgets import QApplication\n"
        "qapp = QApplication([])\n"
        "import net\n"
        "from ui.app import App\n"
        "a = App(qapp, show=False)\n"
        "print('brought', a.brought, sorted(p['name'] for p in a.sw.s['profiles'].values()))\n"
        "a.set_offline(True)\n"
        "a.tray.hide(); a.win.close(); net.set_offline(False)\n"
        "b = App(qapp, show=False)\n"
        "print('offline', net.offline(), b.sw.s.get('offline'), b.brought)\n"
        "b.tray.hide()\n")


def test_first_start_brings_eq_switcher_over_and_offline_is_kept(check, fake_apo, tmp_path):
    conf, top = fake_apo, str(tmp_path)
    old_dir = os.path.join(conf, "EQ Switcher", "profiles")
    os.makedirs(old_dir)
    with open(os.path.join(old_dir, "EarPods.txt"), "wb") as fh:
        fh.write(apo.EARPODS)
    old = os.path.join(top, "eqswitcher.json")
    with open(old, "w") as fh:
        json.dump({"profiles": {"p1": {"name": "EarPods", "file": "EarPods.txt"}}, "devices": {}, "hotkey": ""}, fh)
    out = subproc.run_python(CODE, session.SESSION.app, env={
        "AUTOEQSTUDIO_APO_CONFIG": conf, "AUTOEQSTUDIO_OLD_SETTINGS": old,
        "AUTOEQSTUDIO_DATA": os.path.join(top, "data"), "AUTOEQSTUDIO_ROOT": os.path.join(top, "root")})
    lines = [line for line in out.stdout.strip().splitlines() if line.startswith(("brought ", "offline "))]
    # was selftest.py:977
    check("app: the first start brings EQ Switcher's profiles over; Offline is kept for the next start",
          lines == ["brought 1 ['EarPods']", "offline True True 0"], lines or out.stderr[-400:])
