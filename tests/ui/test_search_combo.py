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
