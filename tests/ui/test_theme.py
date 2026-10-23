"""The app's look (ui\\theme.py, theme_tokens.py, theme_sheet.py, icons.py: Windows 11's, 2026-10-23): Windows'
contrast themes followed (and left again), checked buttons drawn as checked, text that keeps 4.5:1 on what it sits on
whatever Windows' accent colour, the accent followed (also when it changes while the app runs), the graph's colours
told apart (the dataviz skill's checks, tests\\helpers\\palette.py), and Windows 11's symbols beside buttons' words.
The first two moved from selftest.py's contrast_checks and eq_checks.py's review_checks.

Those that apply the theme do it in a Python of their own: applying it restyles the whole application and, once per
process, installs the theme's screen-reader names for good, which would make the accessibility test of this folder
laxer. The rest only read the colours.
"""
from helpers import session, subproc

COVERS = ("ui.theme", "ui.theme_tokens", "ui.theme_sheet", "ui.icons")
# a few of Windows' accent colours as its palettes (Light 3 … Dark 3; the yellow and red as Windows has them, near
# enough), to try the text's contrast on
ACCENTS = {"blue (Windows' default)": ("#99ebff", "#4cc2ff", "#0091f8", "#0078d4", "#005fb8", "#003e92", "#001a68"),
           "yellow": ("#ffe8a3", "#ffd25c", "#ffc41f", "#ffb900", "#d69b00", "#9e7200", "#694c00"),
           "red": ("#ffb3b8", "#ff7a82", "#f5424e", "#e81123", "#b80d1c", "#8a0a15", "#5c070e"),
           "green": ("#9ff0a4", "#6ccb5f", "#3aa53b", "#107c10", "#0e6b0e", "#0b5a08", "#073f05"),
           "purple": ("#d9c2ff", "#c19ff2", "#a383db", "#8764b8", "#6b4c99", "#513a77", "#3b2a57"),
           "grey": ("#d9d9d9", "#b3b3b3", "#8c8c8c", "#767676", "#5e5e5e", "#454545", "#2e2e2e")}
TEXT_ON = (("ink", "bg"), ("ink", "card"), ("ink", "field"), ("ink", "menu"), ("ink", "subtle_hover"),
           ("ink2", "bg"), ("ink2", "card"), ("muted", "bg"), ("muted", "card"), ("muted", "field"),
           ("muted", "subtle_sel"), ("sel_ink", "sel"), ("on_accent", "accent"), ("accent_text", "card"),
           ("accent_text", "accent_soft"), ("warn", "warn_bg"), ("warn", "card"), ("err", "card"), ("good", "card"),
           ("good", "pill"))

CONTRAST = r'''
import json, sys
sys.path.insert(0, sys.argv[1])
from PySide6.QtWidgets import QApplication
qapp = QApplication([])
from ui import theme
hc = dict(theme.LIGHT, bg="#000000", card="#000000", ink="#ffffff", muted="#ffffff", field="#000000",
          accent="#1aebff", on_accent="#000000", btn="#1aebff", on_btn="#000000", on_sel="#000000", c1="#1aebff",
          sel="#1aebff", sel_ink="#000000")
theme.apply(qapp, dark=False, contrast=hc)
css, pal = qapp.styleSheet(), qapp.palette()
on = (theme.tokens()["bg"], "color: #000000" in css and "#1aebff" in css,
      pal.color(pal.ColorRole.HighlightedText).name(), pal.color(pal.ColorRole.Window).name())
theme.apply(qapp, dark=False, contrast=False)
back = theme.tokens()["bg"] == theme.LIGHT["bg"] and "#1aebff" not in qapp.styleSheet()
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


def test_text_keeps_contrast(check):
    from ui import theme_tokens
    low = []
    for name, accent in ACCENTS.items():
        for dark in (False, True):
            t = theme_tokens.build(dark, accent)
            low += [(name, "dark" if dark else "light", a, b, round(theme_tokens.contrast(t[a], t[b]), 2))
                    for a, b in TEXT_ON if theme_tokens.contrast(t[a], t[b]) < 4.5]
    check("theme: text keeps 4.5:1 on what it sits on (the window, cards, boxes, menus, chosen rows, the accent, "
          "warnings), light and dark, whatever Windows' accent colour (blue, yellow, red, green, purple, grey)",
          not low, low[:6])


ACCENT_FOLLOWED = r'''
import json, sys
sys.path.insert(0, sys.argv[1])
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication, QWidget
qapp = QApplication([])
from ui import theme, theme_tokens
green = ("#9ff0a4", "#6ccb5f", "#3aa53b", "#107c10", "#0e6b0e", "#0b5a08", "#073f05")
now = [theme_tokens.DEFAULT_ACCENT]
theme.accent_palette = lambda: now[0]  # (stands in for Windows' setting)
theme.apply(qapp)  # (following Windows)
before = theme.tokens()["accent"]
w = QWidget()
w.show()
now[0] = green  # (the accent changed in Windows' Settings: Windows tells the app's windows)
QCoreApplication.sendEvent(w, QEvent(QEvent.ThemeChange))
for _ in range(20):
    qapp.processEvents()
want = theme_tokens.build(theme.dark(), green)["accent"]
print(json.dumps({"before": before, "after": theme.tokens()["accent"], "want": want,
                  "was": theme_tokens.build(theme.dark())["accent"], "sheet": want in qapp.styleSheet()}))
'''


def test_accent_follows_windows(monkeypatch, check):
    import winreg

    from ui import theme, theme_tokens

    class Key:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False
    green = bytes.fromhex("9ff0a400" "6ccb5f00" "3aa53b00" "107c1000" "0e6b0e00" "0b5a0800" "073f0500" "f7630c00")
    monkeypatch.setattr(winreg, "OpenKey", lambda *a, **k: Key())
    monkeypatch.setattr(winreg, "QueryValueEx", lambda k, name: (green, winreg.REG_BINARY))
    pal = theme.accent_palette()
    light, dark = theme_tokens.build(False, pal), theme_tokens.build(True, pal)
    monkeypatch.setattr(winreg, "QueryValueEx", lambda k, name: (b"\x00" * 8, winreg.REG_BINARY))
    short = theme.accent_palette()

    def missing(*a, **k):
        raise OSError(2, "The system cannot find the file specified")
    monkeypatch.setattr(winreg, "OpenKey", missing)
    unread = theme.accent_palette()
    out = subproc.run_python(ACCENT_FOLLOWED, session.SESSION.app)
    d = out.data or {}
    check("theme: the accent is Windows' own (its palette's Dark 1 in light, Light 2 in dark, as Windows 11's apps; "
          "Windows' default blue when it can't be read), followed when it changes while the app runs; the graph never "
          "takes it",
          pal[4] == "#0e6b0e" and light["accent"] == light["c1"] == "#0e6b0e" and dark["accent"] == "#6ccb5f"
          and short == unread == theme_tokens.DEFAULT_ACCENT and light["with_eq"] == theme_tokens.GRAPH_LIGHT["with_eq"]
          and d.get("before") == d.get("was") and d.get("after") == d.get("want") != d.get("was") and d.get("sheet"),
          (pal, light["accent"], dark["accent"], d or out.stderr[-300:]))


def test_graph_colours_told_apart(check):
    from helpers import palette
    from ui import theme_tokens as T
    found = {}
    for mode, g, base in (("light", T.GRAPH_LIGHT, T.BASE_LIGHT), ("dark", T.GRAPH_DARK, T.BASE_DARK)):
        main_ok, main = palette.check([g["meas"], g["with_eq"], g["c2"]], mode, base["card"], "all")
        extra_ok, extra = palette.check([g["c3"], g["c5"], g["c4"], g["c2"]], mode, base["card"], "adjacent")
        found[mode] = (main_ok and all(state == "PASS" for _, state, _ in main), extra_ok,
                       round(palette.contrast(g["tgt"], base["card"]), 2), [r for r in main + extra if r[1] != "PASS"])
    check("graph: its colours told apart as the dataviz checks say: measurement, with the EQ and the EQ by any two "
          "(colour-blind eyes too, and 3:1 on the card), the extra curves next to each other, the dashed target 3:1; "
          "light and dark",
          all(m and e and tgt >= 3 for m, e, tgt, _ in found.values()), found)


ICONS = r'''
import gc, json, sys, weakref
sys.path.insert(0, sys.argv[1])
from PySide6.QtWidgets import QApplication, QPushButton
qapp = QApplication([])
from ui import icons, theme


def colour(b):
    img = b.icon().pixmap(b.iconSize()).toImage()  # (its own size: 22 x 16, the symbol and the room after it)
    seen = [img.pixelColor(x, y) for x in range(img.width()) for y in range(img.height())]
    strong = [c for c in seen if c.alpha() > 200]
    return strong[0].name() if strong else None
theme.apply(qapp, dark=False, contrast=False)
b = QPushButton("Find…")
icons.put(b, "find")
light, text = colour(b), b.text()
theme.apply(qapp, dark=True, contrast=False)
dark = colour(b)
ref = weakref.ref(b)
del b
gc.collect()
gone = ref() is None
theme.apply(qapp, dark=False, contrast=False)  # (redrawn without the button that's gone)
print(json.dumps({"light": light, "dark": dark, "text": text, "gone": gone,
                  "ink": [theme.LIGHT["ink"], theme.DARK["ink"]]}))
'''


def test_icons_beside_the_words(check):
    out = subproc.run_python(ICONS, session.SESSION.app)
    d = out.data or {}
    check("icons: Windows 11's symbol beside a button's words (the words unchanged), in the theme's text colour and "
          "drawn again when the theme changes; it never keeps its button",
          d.get("light") == d.get("ink", [0])[0] and d.get("dark") == d.get("ink", [0, 0])[1]
          and d.get("text") == "Find…" and d.get("gone") is True, d or out.stderr[-300:])
