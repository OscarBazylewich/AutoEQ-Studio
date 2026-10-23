"""The window (ui\\window.py): its screens, the EQ screen made only when it's opened (and not at all while the app
starts hidden in the tray: the tray stays light), Online / Offline at the top, and closing it leaving the app in the
tray. Moved from selftest.py's qt_checks. Then its look in Windows 11's (the restyle, 2026-10-23): the top bar's
Presets and its chevron, the app's message boxes, the line at the bottom, the banner and the trial bar (drawn themed
in a Python of their own, but the last).

Two of these look at what a Python has loaded (the EQ part, numpy, pyqtgraph), and this test process may have loaded
them already (Make an EQ's tests, a helper): those make their window in a Python of their own (CHILD below), on a
stand-in APO folder in the test's folder, and the test checks what it prints.
"""
import net
from helpers import session, subproc

COVERS = ("ui.window", "switcher.core", "switcher.apo", "switcher.devices", "net")

# The old self-test's window (selftest.py lines 336-363) in a Python of its own. argv: the app's copy, the test's
# folder (holding apo\config: the fake_apo fixture), the screen to start on ("devices": shown; "eq": never shown, as
# when the app starts hidden in the tray). It prints one JSON line.
CHILD = r'''
import json, os, sys
sys.path.insert(0, sys.argv[1])
top, page = sys.argv[2], sys.argv[3]
from PySide6.QtWidgets import QApplication
qapp = QApplication.instance() or QApplication([])
from switcher import core
from switcher import devices as D
from switcher.apo import Apo


class Stub:  # (what the window asks of the app)
    hotkey_problem = ""

    def __init__(self):
        self.said = []

    def tray_message(self, title, text):
        self.said.append(title)

    @staticmethod
    def autostart_on():
        return False

    def set_autostart(self, on):
        pass

    @staticmethod
    def set_offline(on):
        import net
        net.set_offline(on)


conf = os.path.join(top, "apo", "config")
eps = [D.Endpoint("{5}", "Headset", "EarPods", D.ACTIVE, False),
       D.Endpoint("{1}", "Headphones", "Buds", D.NOT_PRESENT, True)]
sw = core.Switcher(os.path.join(top, "s.json"), Apo(conf), endpoints=lambda: eps, playing=lambda: "{5}")
from ui.window import Window
sw.s["page"] = page
win = Window(sw, Stub())
if page == "devices":
    win.show()
qapp.processEvents()
print(json.dumps({"nav": [b.text() for b in win.nav.values()], "page": win.page(), "eq_page_none": win.eq_page is None,
                  "eq_pending": bool(getattr(win, "_eq_pending", False)), "eq": "eq" in sys.modules,
                  "pyqtgraph": "pyqtgraph" in sys.modules, "numpy": "numpy" in sys.modules}))
'''


def test_screens_and_the_eq_part_not_loaded(check, fake_apo, tmp_path):
    out = subproc.run_python(CHILD, session.SESSION.app, str(tmp_path), "devices")
    d = out.data or {}
    # was selftest.py:364
    check("window: the screens; the EQ screen isn't made (nor the EQ part loaded) until it's opened",
          d.get("nav") == ["Make an EQ", "Devices", "Profiles", "Settings"] and d.get("page") == "devices"
          and d.get("eq_page_none") is True and d.get("eq") is False and d.get("pyqtgraph") is False,
          d or out.stderr[-300:])


# Message boxes in the app's theme (dark, Windows' default blue), in a Python of their own: a question (Yes, No) and
# Your files' question (three buttons of its own): the fill of the answer Enter gives, and each button's width
BOXES = r'''
import json, sys
sys.path.insert(0, sys.argv[1])
from PySide6.QtWidgets import QApplication, QMessageBox
qapp = QApplication([])
from ui import theme, theme_tokens
theme.accent_palette = lambda: theme_tokens.DEFAULT_ACCENT
theme.apply(qapp, dark=True, contrast=False)
out = {"accent": theme.tokens()["accent"]}
q = QMessageBox(QMessageBox.Question, "Remove profile", "Remove “X”?", QMessageBox.Yes | QMessageBox.No)
q.setDefaultButton(QMessageBox.Yes)
f = QMessageBox(QMessageBox.Question, "Your AutoEQ Studio files", "Move them there now? A file is never replaced.")
move = f.addButton("Move them", QMessageBox.AcceptRole)
f.addButton("Choose another folder…", QMessageBox.ActionRole)
f.addButton("Not now", QMessageBox.RejectRole)
f.setDefaultButton(move)
for name, box in (("question", q), ("files", f)):
    box.show()
    for _ in range(5):
        qapp.processEvents()
    img = box.grab().toImage()
    b = box.defaultButton()
    at = b.mapTo(box, b.rect().topLeft())
    out[name] = {"fill": img.pixelColor(at.x() + 4, at.y() + b.height() // 2).name(),
                 "narrow": [x.text() for x in box.buttons() if x.width() < x.sizeHint().width()],
                 "widths": sorted(x.width() for x in box.buttons())}
    box.close()
print(json.dumps(out))
'''

# (after tests\ui\conftest.py's THEMED_WINDOW: a message in the line at the bottom, read back from its picture)
STATUS = r'''
win.status("Saved.", 0)
for _ in range(5):
    qapp.processEvents()
bar = win.statusBar()
img = bar.grab().toImage()
first = next((x for x in range(img.width()) if any(max(img.pixelColor(x, y).getRgb()[:3]) > 0x70
                                                    for y in range(img.height()))), None)
print(json.dumps({"first": first, "grip": bar.isSizeGripEnabled(),
                  "screens": win.pages["devices"].layout().contentsMargins().left()}))
'''


# (after tests\ui\conftest.py's THEMED_WINDOW and SHAPES: the top bar's Presets as drawn, dark then light: the stretches
# of inked columns left to right (its symbol, its words, then what ends it: a chevron, open at its top as a "v", or a
# typed "▾", filled), its menu, and what the menu holds as it opens before Make an EQ has opened)
PRESETS = r'''
out = {}
b = win.presets_btn
b.setVisible(True)  # (shown on Make an EQ only: the window is on Devices here)
for dark in (True, False):
    theme.apply(qapp, dark=dark, contrast=False)
    for _ in range(5):
        qapp.processEvents()
    img = b.grab().toImage()
    bg = img.pixelColor(1, img.height() // 2)
    found = runs(img, 2, img.width() - 2, 4, img.height() - 4, bg)
    box = ink_box(img, found[-1][0], 3, found[-1][1] + 1, img.height() - 3, bg) if len(found) >= 2 else None
    out["dark" if dark else "light"] = {"runs": found, "chevron": open_side(img, box, bg, "down"),
                                        "gap": found[-1][0] - found[-2][1] - 1 if len(found) >= 2 else None,
                                        "after": img.width() - 1 - found[-1][1] if found else None}
if b.menu() is not None:
    b.menu().aboutToShow.emit()  # (as it opens)
out.update(text=b.text(), menu=b.menu() is win.presets_menu,
           notes=[[a.text(), a.isEnabled()] for a in win.presets_menu.actions()])
print(json.dumps(out))
'''


def test_presets_chevron_and_its_menu(themed_window, shapes, check, fake_apo, tmp_path):
    # (2026-10-23, the restyle's recheck: “Presets ▾” had its arrow typed in its words, a small filled triangle beside
    # Use on device's Windows 11 chevron)
    from ui import help_text_eq
    out = subproc.run_python(themed_window + shapes + PRESETS, session.SESSION.app, str(tmp_path))
    d = out.data or {}
    seen = [d.get(m) or {} for m in ("dark", "light")]
    title = next(it["title"] for s in help_text_eq.SETTINGS_EQ for it in s["items"] if it["key"] == "#presets")
    check("window: the top bar's Presets shows Windows 11's chevron as every button with a menu does (its own menu: "
          "the theme's picture, clear of its words), not a “▾” typed in its words, light and dark; its menu is filled "
          "as it opens (before Make an EQ has opened, a note saying when presets are ready); Help names it as it reads",
          d.get("text") == "Presets" and d.get("menu") is True
          and all(m.get("chevron") is True and (m.get("gap") or 0) >= 4 and (m.get("after") or 0) >= 6 for m in seen)
          and d.get("notes") == [["Presets are ready as soon as Make an EQ has opened", False]]
          and title.startswith(f"{d.get('text')} ") and "▾" not in title,
          dict(d, help=title) if d else out.stderr[-300:])


def test_message_boxes_as_windows_11(check):
    out = subproc.run_python(BOXES, session.SESSION.app)
    d = out.data or {}
    boxes = [d.get(k) or {} for k in ("question", "files")]
    check("message boxes: the answer Enter gives in the accent (as Windows 11's dialogs), every button wide enough for "
          "its words and none narrower than 64 px",
          all(b.get("fill") == d.get("accent") and b.get("narrow") == [] and min(b.get("widths") or [0]) >= 64
              for b in boxes), d or out.stderr[-300:])


def test_the_status_line_lined_up(themed_window, check, fake_apo, tmp_path):
    out = subproc.run_python(themed_window + STATUS, session.SESSION.app, str(tmp_path))
    d = out.data or {}
    check("window: the line at the bottom starts where the screens do (its words lined up with theirs), with no size "
          "grip (Windows 11's)", d.get("first") is not None and abs(d["first"] - d.get("screens", 0)) <= 3
          and d.get("grip") is False, d or out.stderr[-300:])


def test_the_banner_and_the_trial_bar_as_windows_11(devices_window, check):
    from PySide6.QtWidgets import QLabel, QPushButton
    win = devices_window.win

    def signs(bar):
        return [(lab.accessibleName(), lab.property("role"), lab.objectName()) for lab in bar.findChildren(QLabel)
                if lab.property("glyph") == "true"]
    plain = [b.text() for b in win.trial_bar.findChildren(QPushButton) if b.icon().isNull()]
    check("window: the banner is Windows 11's warning bar (the warning sign in the warning colour, the words, the "
          "action), and the trial bar has a clock and symbols beside Keep it and Stop now",
          signs(win.banner) == [("Warning", "warn", "")] and win.banner_btn.parentWidget() is win.banner
          and signs(win.trial_bar) == [("Trying an EQ", None, "trialGlyph")] and plain == [],
          (signs(win.banner), signs(win.trial_bar), plain))


def test_online_offline(devices_window, online, check):
    # (online first, as the old self-test started: the `online` fixture puts the session's offline back after)
    win = devices_window.win
    win.online_btn.click()
    off = (net.offline(), win.online_btn.text(), win.chk_offline.isChecked())
    win.online_btn.click()
    # was selftest.py:371
    check("window: Online / Offline at the top switches the whole app, and Settings shows it",
          off == (True, "○ Offline", True) and not net.offline() and win.online_btn.text() == "● Online", off)


def test_closing_leaves_the_app_in_the_tray(devices_window, check):
    w = devices_window
    w.win.close()
    # was selftest.py:591
    check("window: closing it leaves the app in the tray (said once)",
          not w.win.isVisible() and w.app.said and w.sw.s["told_tray"], (w.win.isVisible(), w.app.said))


def test_starting_hidden_on_make_an_eq(check, fake_apo, tmp_path):
    out = subproc.run_python(CHILD, session.SESSION.app, str(tmp_path), "eq")
    d = out.data or {}
    # was selftest.py:598
    check("window: starting hidden on Make an EQ makes the screen only when the window is shown (the tray stays light)",
          d.get("eq_page_none") is True and d.get("eq_pending") is True and d.get("eq") is False
          and d.get("numpy") is False, d or out.stderr[-300:])
