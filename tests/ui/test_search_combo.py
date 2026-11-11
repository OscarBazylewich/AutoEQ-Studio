"""Drop-down lists (ui\\search_combo.py, every drop-down in the app) in Windows 11's look: a short list and one with its
search box (over SEARCH_FROM choices) look alike (the checkers' finding of 2026-10-23: the short one opened square on
the menus' colour with its chosen row only outlined, the long one on the cards' colour with a box of its own inside).
Drawn themed in a Python of their own (applying the theme restyles the whole application), dark and light. Their
order and search are checked with Find… (tests\\eq_screen\\test_picker.py)."""
from helpers import session, subproc

COVERS = ("ui.search_combo", "ui.theme_sheet")  # (reached through another Python: its code names them as text)

# A short drop-down (three choices, the second chosen) and a long one (twenty), each opened and read back from its
# picture: its surface, its edge, the chosen row's fill and the colour at its left (the accent's bar), and for the long
# one its list's edge and a style of its own (none: the theme's)
LISTS = r'''
import json, sys
sys.path.insert(0, sys.argv[1])
from PySide6.QtCore import QPoint
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget
qapp = QApplication([])
from ui import theme, theme_tokens
from ui.search_combo import SEARCH_FROM, SearchCombo
theme.accent_palette = lambda: theme_tokens.DEFAULT_ACCENT
LONG = "Truthear GATe (Wide Bore Tips) (L800 IEM)  (10 files)"


def pump():
    for _ in range(5):
        qapp.processEvents()


def row(img, top_left, rect):  # (the row's fill in its middle, and the colour at its very left)
    return [img.pixelColor(top_left.x() + rect.width() // 2, top_left.y() + 2).name(),
            img.pixelColor(top_left.x() + 1, top_left.y() + rect.height() // 2).name()]


out = {}
for dark in (True, False):
    theme.apply(qapp, dark=dark, contrast=False)
    t = theme.tokens()
    holder = QWidget()
    lay = QVBoxLayout(holder)
    short, long_, narrow = SearchCombo(holder), SearchCombo(holder), SearchCombo(holder)
    short.addItems(["Best fit", "Website AutoEQ (find best settings)", "Website AutoEQ (one run)"])
    short.setCurrentIndex(1)
    long_.addItems([f"Choice {i}" for i in range(1, 21)])
    narrow.addItems(["Short", LONG] + [f"Choice {i}" for i in range(1, SEARCH_FROM - 1)])  # (as many as a short has)
    narrow.setFixedWidth(160)  # (narrower than its longest choice, as a name's drop-down in a small window)
    for c in (short, long_, narrow):
        lay.addWidget(c)
    holder.show()
    pump()
    res = out["dark" if dark else "light"] = {"want": [t["menu"], t["stroke"], t["sel"], t["accent"]]}
    short.showPopup()
    pump()
    pop, view = short.view().window(), short.view()
    img = pop.grab().toImage()
    r = view.visualRect(short.model().index(1, 0))
    res["short"] = {"surface": img.pixelColor(pop.width() // 2, pop.height() - 3).name(),
                    "edge": img.pixelColor(pop.width() // 2, 0).name(),
                    "row": row(img, view.viewport().mapTo(pop, r.topLeft()), r)}
    short.hidePopup()
    long_.showPopup()
    pump()
    pop = long_._popup
    img = pop.grab().toImage()
    lst = pop.list
    r = lst.visualItemRect(lst.currentItem())
    at = lst.mapTo(pop, QPoint(0, 0))
    res["long"] = {"surface": img.pixelColor(pop.width() // 2, 3).name(), "edge": img.pixelColor(pop.width() // 2, 0).name(),
                   "row": row(img, lst.viewport().mapTo(pop, r.topLeft()), r),
                   "list_edge": img.pixelColor(at.x(), at.y() + lst.height() // 2).name(), "own_style": pop.styleSheet()}
    long_.hidePopup()
    narrow.showPopup()
    pump()
    view = narrow.view()
    rows = [view.visualRect(narrow.model().index(i, 0)) for i in range(narrow.count())]
    res["narrow"] = {"in_sight_width": view.viewport().width(),
                     "needs": QFontMetrics(view.font()).horizontalAdvance(LONG) + 16,  # (its words and its row's padding)
                     "in_sight": sum(1 for r in rows if r.top() >= 0 and r.bottom() < view.viewport().height()),
                     "count": narrow.count()}
    narrow.hidePopup()
    holder.close()
    holder.deleteLater()
    pump()
print(json.dumps(out))
'''


def test_short_and_long_lists_alike(check):
    out = subproc.run_python(LISTS, session.SESSION.app)
    d = out.data or {}
    seen = [d.get(m) or {} for m in ("dark", "light")]

    def alike(m):
        menu, stroke, sel, accent = m.get("want") or [None] * 4
        short, long_ = m.get("short") or {}, m.get("long") or {}
        return (all(x.get("surface") == menu and x.get("edge") == stroke and x.get("row") == [sel, accent]
                    for x in (short, long_)) and long_.get("list_edge") == menu and long_.get("own_style") == "")
    check("drop-down lists: one look, short or long (with its search box): on the menus' colour in a thin border, the "
          "chosen row filled with the accent's bar beside it, the long one's list without a box of its own and its "
          "look the theme's; light and dark",
          len(seen) == 2 and all(alike(m) for m in seen), d or out.stderr[-300:])
    # (2026-10-23, the one look's own first try: Qt's list was only as wide as its drop-down, a long name cut, and
    # showed 10 choices; Fusion's menu-like list before it widened itself and showed them all)
    check("drop-down lists: a short list shows every choice whole, as wide as its longest name (a drop-down narrower "
          "than it, as a name's in a small window) and all of them in sight",
          len(seen) == 2 and all((m.get("narrow") or {}).get("in_sight_width", 0) >= m["narrow"]["needs"]
                                 and m["narrow"]["in_sight"] == m["narrow"]["count"] for m in seen),
          [m.get("narrow") for m in seen] if d else out.stderr[-300:])


def test_long_list_stays_on_the_screen(check):
    # (2026-11-10, the user: Your EQ app's list, opened low in a maximized window scrolled just so, went up past the
    # screen's top: no search box in sight. It had no room below, and above only less than its height)
    from PySide6.QtCore import QRect
    from ui.search_combo import place_list
    screen = QRect(0, 0, 1920, 1040)
    seen = {"fits below": place_list(100, 32, 200, 500, 400, screen),
            "more room above, not enough": place_list(560, 32, 200, 500, 600, screen),
            "more room below, not enough": place_list(300, 32, 200, 500, 800, screen),
            "fits above": place_list(900, 32, 200, 500, 400, screen),
            "past the right": place_list(100, 32, 1700, 500, 400, screen)}
    check("drop-down lists: the long list opens below its drop-down when it fits there, else on the side with more "
          "room and only as high as that room (its search box, at its top, stays on the screen), and not past the "
          "screen's right",
          seen == {"fits below": (200, 134, 400), "more room above, not enough": (200, 0, 558),
                   "more room below, not enough": (200, 334, 706), "fits above": (200, 498, 400),
                   "past the right": (1420, 134, 400)}, seen)


# Drop-downs at their own size (the size the layouts give most of them), each choice chosen in turn and read back as
# it is drawn; then one made narrow
OWN_SIZE = r'''
import json, sys
sys.path.insert(0, sys.argv[1])
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget
qapp = QApplication([])
from ui import theme, theme_tokens
from ui.search_combo import SearchCombo
theme.accent_palette = lambda: theme_tokens.DEFAULT_ACCENT
LISTS = (["6", "12", "24", "48", "96"], ["A", "B"], ["100000", "1"], ["All rigs", "711", "5128"],
         ["Frequency response (not compensated)", "Difference from a target"])
out = {}
for mode, dark in (("dark", True), ("light", False)):
    theme.apply(qapp, dark=dark)
    host = QWidget()
    lay = QVBoxLayout(host)
    combos = []
    for items in LISTS:
        c = SearchCombo(host)
        c.addItems(items)
        lay.addWidget(c)
        combos.append(c)
    host.show()
    for _ in range(5):
        qapp.processEvents()
    cut = []
    for c in combos:
        c.setFixedWidth(c.sizeHint().width())
        for i in range(c.count()):
            c.setCurrentIndex(i)
            if c.shown_text() != c.itemText(i):
                cut.append([c.itemText(i), c.shown_text()])
    narrow = combos[-1]
    narrow.setCurrentIndex(0)
    narrow.setFixedWidth(120)
    out[mode] = {"cut": cut, "narrow": narrow.shown_text()}
    host.close()
print(json.dumps(out))
'''


def test_choice_whole_at_the_drop_downs_own_size(check):
    # (2026-11-11, seen in a picture of the tracer: Points in each octave showed "…", not "48". At its own size a
    # drop-down's room is just its widest choice's width, and the "…" rule kept 4 pixels free)
    out = subproc.run_python(OWN_SIZE, session.SESSION.app)
    d = out.data or {}
    whole = "Frequency response (not compensated)"
    check("drop-down lists: at its own size a drop-down shows each of its choices whole (\"48\", not \"…\"); made "
          "narrower than its choice, the choice ends in “…”; light and dark",
          set(d) == {"dark", "light"} and all(
              m["cut"] == [] and m["narrow"].endswith("…") and whole.startswith(m["narrow"][:-1].rstrip())
              and 1 < len(m["narrow"]) < len(whole) for m in d.values()), d or out.stderr[-300:])
