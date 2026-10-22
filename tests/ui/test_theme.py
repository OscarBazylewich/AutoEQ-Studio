"""The app's look (ui\\theme.py): Windows' contrast themes followed (and left again), and checked buttons drawn as
checked. Moved from selftest.py's contrast_checks and eq_checks.py's review_checks.

Each applies the theme in a Python of its own: applying it restyles the whole application and, once per process,
installs the theme's screen-reader names for good, which would make the accessibility test of this folder laxer.
"""
from helpers import session, subproc

COVERS = ("ui.theme",)

CONTRAST = r'''
import json, sys
sys.path.insert(0, sys.argv[1])
from PySide6.QtWidgets import QApplication
qapp = QApplication([])
from ui import theme
hc = dict(theme.LIGHT, bg="#000000", card="#000000", ink="#ffffff", muted="#ffffff", field="#000000",
          btn="#1aebff", on_btn="#000000", on_sel="#000000", c1="#1aebff", sel="#1aebff")
theme.apply(qapp, dark=False, contrast=hc)
css, pal = qapp.styleSheet(), qapp.palette()
on = (theme.tokens()["bg"], "color: #000000" in css and "#1aebff" in css,
      pal.color(pal.ColorRole.HighlightedText).name(), pal.color(pal.ColorRole.Window).name())
theme.apply(qapp, dark=False, contrast=False)
back = theme.tokens() is theme.LIGHT and "#1aebff" not in qapp.styleSheet()
real = theme.system_tokens()
print(json.dumps({"on": on, "back": back, "real": real}))
'''

CHECKED = r'''
import json, sys
sys.path.insert(0, sys.argv[1])
from PySide6.QtWidgets import QApplication
qapp = QApplication([])
from ui import theme
theme.apply(qapp, dark=True)
theme.apply(qapp, dark=False)
print(json.dumps({"checked": "QPushButton:checked" in qapp.styleSheet()}))
'''


def test_contrast_theme_followed_and_left(check):
    # (Windows' contrast themes: the app's colours become Windows' own for it, here a stand-in set; white text on a
    # button only where the theme says so; and back)
    out = subproc.run_python(CONTRAST, session.SESSION.app)
    d = out.data or {}
    on, back, real = tuple(d.get("on") or ()), d.get("back"), d.get("real") or {}
    # was selftest.py:864
    check("contrast: with a Windows contrast theme on, the app takes its colours (window, text, highlight, the text "
          "on a highlighted button), and goes back after; this PC's theme colours are read",
          on == ("#000000", True, "#000000", "#000000") and back and all(v.startswith("#") and len(v) == 7
                                                                        for v in real.values()),
          (on, back) if d else out.stderr[-300:])


def test_checked_buttons_drawn_checked(check):
    # (the light theme, as the old check found it after the EQ screen went dark and back: eq_checks.py lines 1805-1808)
    out = subproc.run_python(CHECKED, session.SESSION.app)
    d = out.data or {}
    # was eq_checks.py:1815
    check("review: checked buttons are drawn as checked (the tracer's tools, Listen's versions)",
          d.get("checked") is True, d or out.stderr[-300:])
