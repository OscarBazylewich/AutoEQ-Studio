"""The app's look (ui\\theme.py, theme_tokens.py, theme_sheet.py, icons.py: Windows 11's, 2026-10-23): Windows'
contrast themes followed (and left again), checked buttons drawn as checked, text that keeps 4.5:1 on what it sits on
whatever Windows' accent colour, the accent followed (also when it changes while the app runs), the graph's colours
told apart (the dataviz skill's checks, tests\\helpers\\palette.py), Windows 11's symbols beside buttons' words, and
the shared parts the checkers' findings of 2026-10-23 were about: a menu's notes readable, Windows 11's chevrons on
menu buttons and submenus, a card's title in a fold title's size, and a card's title and content at one inset.
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
           ("muted", "subtle_sel"), ("muted", "menu"), ("sel_ink", "sel"), ("on_accent", "accent"),
           ("accent_text", "card"), ("accent_text", "accent_soft"), ("warn", "warn_bg"), ("warn", "card"),
           ("err", "card"), ("good", "card"), ("good", "pill"))

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
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication, QPushButton
qapp = QApplication([])
if sys.argv[2] == "windows10":  # (Windows 10's icon font, Segoe MDL2 Assets: as if Segoe Fluent Icons weren't there)
    real = QFontDatabase.families
    QFontDatabase.families = staticmethod(lambda *a: [f for f in real(*a) if f != "Segoe Fluent Icons"])
from ui import icons, theme


def colour(b):  # (the symbol's fullest pixel: its colour, give or take the rounding of a blended pixel)
    img = b.icon().pixmap(b.iconSize()).toImage()  # (its own size: 22 x 16, the symbol and the room after it)
    seen = [img.pixelColor(x, y) for x in range(img.width()) for y in range(img.height())]
    best = max(seen, key=lambda c: c.alpha()) if seen else None
    return best.name() if best is not None and best.alpha() > 200 else None
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
print(json.dumps({"fluent icons": "Segoe Fluent Icons" in QFontDatabase.families(),
                  "light": light, "dark": dark, "text": text, "gone": gone,
                  "ink": [theme.LIGHT["ink"], theme.DARK["ink"]]}))
'''


def _near(a, b, most=2):
    """Two colours (#rrggbb) the same to within `most` in each of red, green and blue."""
    return bool(a and b) and all(abs(int(a[i:i + 2], 16) - int(b[i:i + 2], 16)) <= most for i in (1, 3, 5))


def test_icons_beside_the_words(check):
    # (with Windows 11's icon font and with Windows 10's, as GitHub's machine may have: there the symbol's fullest
    # pixel read #1a1a1a for the text's #1b1b1b, its blend's rounding, and the old exact match failed: 2026-10-23)
    got = {}
    for font in ("windows11", "windows10"):
        out = subproc.run_python(ICONS, session.SESSION.app, font)
        got[font] = out.data or {"error": out.stderr[-300:]}
    check("icons: Windows 11's symbol beside a button's words (the words unchanged), in the theme's text colour and "
          "drawn again when the theme changes; it never keeps its button",
          all(_near(d.get("light"), (d.get("ink") or [None])[0]) and _near(d.get("dark"), (d.get("ink") or [0, None])[1])
              and d.get("text") == "Find…" and d.get("gone") is True for d in got.values()), got)


# A menu as the app's (a note that can't be chosen, an item, a submenu) and two buttons with a menu (one with a symbol,
# as Add a profile, one without, as Retry from these filters), dark and light, read back from their pictures
MENUS = r'''
import json, sys
sys.path.insert(0, sys.argv[1])
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMenu, QPushButton, QVBoxLayout, QWidget
qapp = QApplication([])
from ui import icons, theme, theme_tokens
theme.accent_palette = lambda: theme_tokens.DEFAULT_ACCENT
''' + "{shapes}" + r'''
out = {}
for dark in (True, False):
    theme.apply(qapp, dark=dark, contrast=False)
    holder = QWidget()
    lay = QVBoxLayout(holder)
    menu = QMenu(holder)
    note = menu.addAction("No presets yet: a preset keeps all your settings (not your files)")
    note.setEnabled(False)
    menu.addAction("Save current settings as…")
    sub = menu.addMenu("Try for 5 minutes on")
    sub.addAction("Headphones")
    menu.resize(menu.sizeHint())
    img = menu.grab().toImage()
    g = menu.actionGeometry(note)
    bg = img.pixelColor(g.left() + 3, g.center().y())
    text = max((img.pixelColor(x, y) for x in range(g.left(), g.right()) for y in range(g.top(), g.bottom())),
               key=lambda c: theme_tokens.contrast(c.name(), bg.name()))
    g = menu.actionGeometry(sub.menuAction())
    arrow = ink_box(img, g.right() - 30, g.top() + 2, g.right(), g.bottom() - 1, bg)
    res = out["dark" if dark else "light"] = {"note": round(theme_tokens.contrast(text.name(), bg.name()), 2),
                                              "submenu": open_side(img, arrow, bg, "right")}
    buttons = []
    for words, symbol in (("Add a profile", "add"), ("Retry from these filters", None)):
        b = QPushButton(words)
        if symbol:
            icons.put(b, symbol)
        m = QMenu(b)
        m.addAction("Import an EQ file…")
        b.setMenu(m)
        lay.addWidget(b, 0, Qt.AlignLeft)  # (as wide as it asks to be: its words and its chevron, nothing more)
        buttons.append(b)
    holder.show()
    for _ in range(5):
        qapp.processEvents()
    for b in buttons:
        img = b.grab().toImage()
        bg = img.pixelColor(img.width() // 2, 2)
        found = runs(img, 3, img.width() - 3, 4, img.height() - 4, bg)
        if len(found) < 2:
            res[b.text()] = found
            continue
        box = ink_box(img, found[-1][0], 3, found[-1][1] + 1, img.height() - 3, bg)
        res[b.text()] = {"chevron": open_side(img, box, bg, "down"), "gap": found[-1][0] - found[-2][1] - 1,
                         "after": img.width() - 1 - found[-1][1]}
    holder.close()
    holder.deleteLater()
    for _ in range(3):
        qapp.processEvents()
print(json.dumps(out))
'''


def test_menus_notes_and_chevrons(check, shapes):
    out = subproc.run_python(MENUS.replace("{shapes}", shapes), session.SESSION.app)
    d = out.data or {}
    seen = [d.get(m) or {} for m in ("dark", "light")]
    # (2026-10-23: a menu's notes, Presets' “No presets yet”, Use on device's “Run first”, were in the grey of an item
    # that can't be chosen: 2.5:1 on the menu in light, 3.2:1 in dark)
    check("menus: a note in a menu (an item that can't be chosen: Presets' “No presets yet”, Use on device's “Run "
          "first”, the tray's device playing) is readable, 4.5:1 on the menu, light and dark",
          len(seen) == 2 and all((m.get("note") or 0) >= 4.5 for m in seen),
          [m.get("note") for m in seen] if d else out.stderr[-300:])
    # (Qt's small filled triangles were on Use on device, Retry from these filters and the submenu; Add a profile had
    # a rule of its own)
    check("menus: a button with a menu (Add a profile, Use on device, Retry from these filters) shows Windows 11's "
          "chevron, clear of its words and its edge, and a menu's submenu Windows 11's chevron pointing right; light "
          "and dark",
          len(seen) == 2 and all(m.get("submenu") is True and all(
              isinstance(m.get(k), dict) and m[k]["chevron"] is True and m[k]["gap"] >= 5 and m[k]["after"] >= 10
              for k in ("Add a profile", "Retry from these filters")) for m in seen), d or out.stderr[-300:])


# A card (a QGroupBox, as Make the EQ: a label and a button on it) beside a fold's title size, dark and light: its
# title's size as drawn and where its title and content start
CARDS = r'''
import json, sys
sys.path.insert(0, sys.argv[1])
from PySide6.QtCore import QPoint
from PySide6.QtGui import QFont, QFontMetrics
from PySide6.QtWidgets import QApplication, QGroupBox, QLabel, QPushButton, QVBoxLayout, QWidget
qapp = QApplication([])
from ui import theme, theme_sheet, theme_tokens
theme.accent_palette = lambda: theme_tokens.DEFAULT_ACCENT
''' + "{shapes}" + r'''
out = {"card": theme_sheet.CARD}
for dark in (True, False):
    theme.apply(qapp, dark=dark, contrast=False)
    holder = QWidget()
    lay = QVBoxLayout(holder)
    box = QGroupBox("Make the EQ")
    v = QVBoxLayout(box)
    words = QLabel("Your EQ app")
    run = QPushButton("Run")
    v.addWidget(words)
    v.addWidget(run)
    lay.addWidget(box)
    holder.resize(600, 300)
    holder.show()
    for _ in range(5):
        qapp.processEvents()
    img = box.grab().toImage()
    bg = img.pixelColor(box.width() // 2, 4)
    title = ink_box(img, 10, 3, box.width() - 10, 38, bg)  # (inside the card's round corners)
    at = words.mapTo(box, QPoint(0, 0))
    ink = ink_box(img, at.x(), at.y(), at.x() + words.width(), at.y() + words.height(), bg)
    f = QFont(box.font())
    sizes = {}
    for pt in (10.5, 11):
        f.setPointSizeF(pt)
        sizes[str(pt)] = QFontMetrics(f).horizontalAdvance("Make the EQ")
    out["dark" if dark else "light"] = {
        "box_pt": box.font().pointSizeF(), "words_pt": words.font().pointSizeF(), "run_pt": run.font().pointSizeF(),
        "title_width": title and title[2] - title[0] + 1, "widths": sizes, "title_x": title and title[0],
        "words_x": ink and ink[0], "run_x": run.mapTo(box, QPoint(0, 0)).x()}
    holder.close()
    holder.deleteLater()
    for _ in range(3):
        qapp.processEvents()
print(json.dumps(out))
'''


def test_cards_titles_and_insets(check, shapes):
    out = subproc.run_python(CARDS.replace("{shapes}", shapes), session.SESSION.app)
    d = out.data or {}
    seen = [d.get(m) or {} for m in ("dark", "light")]
    # (2026-10-23: Qt ignores a size on QGroupBox::title, which takes the box's own font: Make the EQ's title was
    # drawn at 10.5 pt beside Settings' 11 pt)
    check("cards: a card's title in a fold's title size (11 pt: Qt draws it in the card's own size), what's on the "
          "card still in 10.5 pt; light and dark",
          len(seen) == 2 and all(m.get("box_pt") == 11 and m.get("words_pt") == m.get("run_pt") == 10.5
                                 and abs((m.get("title_width") or 0) - m["widths"]["11"]) <= 2
                                 < abs((m.get("title_width") or 0) - m["widths"]["10.5"]) for m in seen),
          d or out.stderr[-300:])
    inset = d.get("card", 0) + 1  # (inside its 1 px border)
    # (the card's padding and Qt's own layout margin put its content 9 px right of its title)
    check("cards: a card's title and its content start at one inset (theme_sheet's CARD), the content's words and "
          "controls under the title's; light and dark",
          len(seen) == 2 and all(abs((m.get("title_x") or 0) - inset) <= 2 and abs((m.get("words_x") or 0) - inset) <= 2
                                 and m.get("run_x") == inset for m in seen), d or out.stderr[-300:])


ICONS_ONE_EACH = r'''
import json, sys
sys.path.insert(0, sys.argv[1])
import shiboken6
from PySide6.QtCore import QSize
from PySide6.QtWidgets import QApplication, QPushButton, QWidget
qapp = QApplication([])
from ui import icons, theme
theme.apply(qapp, dark=False, contrast=False)
holder = QWidget()
play = QPushButton("Play", holder)
for name in ("play", "stop", "play", "stop"):  # (Listen's Play / Stop: each press gives the button the other one)
    icons.put(play, name)
entries = [n for ref, n in icons._shown if ref() is play]
for _ in range(3):  # (the device panel, made again on each change: its buttons deleted, new ones given symbols)
    rows = [QPushButton("Rename…", holder) for _ in range(4)]
    for b in rows:
        icons.put(b, "rename")
    for b in rows:
        shiboken6.delete(b)
icons.put(QPushButton("Check again", holder), "refresh")
listed = len(icons._shown)
for ref, _ in list(icons._shown):  # (every button gone: the next theme change lets go of them all)
    if ref() is not None and shiboken6.isValid(ref()):
        shiboken6.delete(ref())
theme.apply(qapp, dark=True, contrast=False)
emptied = len(icons._shown)
again = QPushButton("Play", holder)
icons.put(again, "stop")
theme.apply(qapp, dark=False, contrast=False)
asked = sum(1 for fn in theme._state["listeners"] if fn is icons._redraw)
size = QSize(22, 16)
shown = again.icon().pixmap(size).toImage() == icons.glyph("stop", theme.tokens()["ink"]).pixmap(size).toImage()
print(json.dumps({"entries": entries, "listed": listed, "emptied": emptied, "asked": asked, "shown": shown}))
'''


def test_icons_one_entry_per_button(check):
    # (2026-10-23, the restyle's stage 2: each put() added an entry, so Listen's Play / Stop added one per press and
    # the device panel 4 or 5 on each change until the theme changed; once the list had emptied, the theme was asked
    # again and drew every symbol twice on each change)
    out = subproc.run_python(ICONS_ONE_EACH, session.SESSION.app)
    d = out.data or {}
    check("icons: a button given another symbol keeps only the new one (Listen's Play and Stop), buttons that are gone "
          "are let go of when the next symbol is put (the device panel makes its buttons again on each change), and "
          "the theme is asked once to tell of a change",
          d.get("entries") == ["stop"] and d.get("listed") == 2 and d.get("emptied") == 0 and d.get("asked") == 1
          and d.get("shown") is True, d or out.stderr[-300:])
