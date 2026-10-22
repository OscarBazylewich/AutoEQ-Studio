"""The tray stays light: the switching part and the window load neither the EQ part nor its maths (numpy, scipy, the
website's maths in V8). In a Python of its own, since this process may have loaded them already. Moved from
selftest.py's light_checks."""
from helpers import session, subproc

COVERS = ("switcher.core", "switcher.apo", "switcher.devices", "ui.window", "ui.icons", "ui.winsys")


def test_tray_and_window_stay_light(check):
    code = ("import sys; sys.path.insert(0, sys.argv[1]); from switcher import core, apo, devices; from ui import window, "
            "icons, winsys; print(sorted(m for m in ('eq', 'numpy', 'scipy', 'py_mini_racer') if m in sys.modules))")
    out = subproc.run_python(code, session.SESSION.app)
    # was selftest.py:1035
    check("light: the tray and window load neither the EQ part nor its maths", out.stdout.strip() == "[]",
          out.stdout.strip() or out.stderr[-300:])
