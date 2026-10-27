"""The App (ui\\app.py: the tray, the window, the hotkey, Online / Offline) in a Python of its own, on a stand-in APO
folder, data folder and EQ Switcher settings in the test's folder: EQ Switcher's profiles brought over on the first
start, Offline kept for the next start. Moved from selftest.py's app_checks. Then the tray icon's menu in Windows 11's
look (the restyle, 2026-10-23): its headings readable."""
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
        json.dump({"profiles": {"p1": {"name": "EarPods", "file": "EarPods.txt"}}, "devices": {}, "hotkey": "", "onoff_hotkey": ""}, fh)
    out = subproc.run_python(CODE, session.SESSION.app, env={
        "AUTOEQSTUDIO_APO_CONFIG": conf, "AUTOEQSTUDIO_OLD_SETTINGS": old,
        "AUTOEQSTUDIO_DATA": os.path.join(top, "data"), "AUTOEQSTUDIO_ROOT": os.path.join(top, "root")})
    lines = [line for line in out.stdout.strip().splitlines() if line.startswith(("brought ", "offline "))]
    # was selftest.py:977
    check("app: the first start brings EQ Switcher's profiles over; Offline is kept for the next start",
          lines == ["brought 1 ['EarPods']", "offline True True 0"], lines or out.stderr[-400:])


# (the app made once, then drawn light: its tray icon's menu, built as when it's right-clicked, read back from its
# picture: the first heading's darkest pixel, its words' own colour)
TRAY = ("import json, sys; sys.path.insert(0, sys.argv[1])\n"
        "from PySide6.QtWidgets import QApplication\n"
        "qapp = QApplication([])\n"
        "from ui import theme, theme_tokens\n"
        "theme.accent_palette = lambda: theme_tokens.DEFAULT_ACCENT\n"
        "from ui.app import App\n"
        "a = App(qapp, show=False)\n"
        "theme.apply(qapp, dark=False, contrast=False)\n"
        "a.build_menu()\n"
        "m = a.menu\n"
        "m.ensurePolished()\n"
        "m.resize(m.sizeHint())\n"
        "head = next(x for x in m.actions() if not x.isEnabled() and not x.isSeparator())\n"
        "r = m.actionGeometry(head)\n"
        "img = m.grab().toImage()\n"
        "darkest = min(min(img.pixelColor(x, y).getRgb()[:3]) for x in range(r.left(), r.right())\n"
        "              for y in range(r.top(), r.bottom()))\n"
        "t = theme.tokens()\n"
        "def ink(menu, act):  # (how much of its row is dark: the words' weight)\n"
        "    g = menu.actionGeometry(act)\n"
        "    pic = menu.grab().toImage()\n"
        "    return sum(1 for x in range(g.left(), g.right()) for y in range(g.top(), g.bottom())\n"
        "               if min(pic.pixelColor(x, y).getRgb()[:3]) < 110)\n"
        "from PySide6.QtWidgets import QMenu\n"
        "dft = m.defaultAction()\n"
        "plain = QMenu()\n"
        "same = plain.addAction(dft.text() if dft else '')\n"
        "plain.ensurePolished()\n"
        "plain.resize(plain.sizeHint())\n"
        "print(json.dumps({'name': m.objectName(), 'head': head.text(), 'darkest': darkest,\n"
        "                  'muted': int(t['muted'][1:3], 16), 'disabled': int(t['disabled'][1:3], 16),\n"
        "                  'default': dft.text() if dft else None, 'first': m.actions()[0].text(),\n"
        "                  'ink': ink(m, dft) if dft else 0, 'plain_ink': ink(plain, same)}))\n"
        "a.tray.hide(); a.win.close()\n")


def test_the_tray_menus_headings_readable(check, fake_apo, tmp_path):
    # (its headings, the device playing or "No device playing", are items that can't be chosen: they were drawn in
    # the grey of an unavailable item, 2.7:1 on the menu)
    top = str(tmp_path)
    out = subproc.run_python(TRAY, session.SESSION.app, env={
        "AUTOEQSTUDIO_APO_CONFIG": fake_apo, "AUTOEQSTUDIO_OLD_SETTINGS": os.path.join(top, "no-eqswitcher.json"),
        "AUTOEQSTUDIO_DATA": os.path.join(top, "data"), "AUTOEQSTUDIO_ROOT": os.path.join(top, "root")})
    d = out.data or {}
    check("tray: the menu's headings (the device playing, the EQ being tried) in the readable secondary colour, not "
          "the grey of an item that can't be chosen", d.get("name") == "tray" and d.get("muted") is not None
          and abs(d.get("darkest", 999) - d["muted"]) <= 12, d or out.stderr[-400:])
    # (2026-10-27, UI-RULES: Open first, as Windows' tray menus; the app's stylesheet drew it as plain as the rest)
    check("tray: Open AutoEQ Studio first, the menu's default (the icon's own click), its words heavier than a plain "
          "item's", d.get("first") == d.get("default") == "Open AutoEQ Studio"
          and d.get("ink", 0) > 1.15 * d.get("plain_ink", 10 ** 6), d and (d.get("first"), d.get("default"),
                                                                            d.get("ink"), d.get("plain_ink")))
