"""The window (ui\\window.py): its screens, the EQ screen made only when it's opened (and not at all while the app
starts hidden in the tray: the tray stays light), Online / Offline at the top, and closing it leaving the app in the
tray. Moved from selftest.py's qt_checks.

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
