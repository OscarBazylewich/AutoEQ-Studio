"""Help (ui\\help_window.py, ui\\help_texts.py): its words told in AutoEQ Studio's own controls, every "See also" and
F1 key found, the search, and F1 on a control (moved from selftest.py's help_checks); its look in Windows 11's, light
and dark (2026-10-23), in a Python of its own: applying the theme restyles the whole application, as test_theme.py
says; its page from the top for a search and named for a screen reader, and Rig tags' words as Find… shows the tags."""
import json
import os
import re

from helpers import paths, session, subproc

COVERS_FILES = ("app/ui/*.py",)  # (st-083 reads every ui file's help_window.tag(...) calls)


def test_words_name_the_apps_controls(check):
    from ui.help_texts import WIKI
    words = json.dumps(WIKI, ensure_ascii=False)
    gone = [w for w in ("ⓘ", "(top bar)", "Match loudness", "AutoEQ Local", "Settings › Sources", "Settings › App",
                        "Adjust next to", '"id": "presets"') if w in words]
    # was selftest.py:880
    check("help: its words name AutoEQ Studio's controls (no ⓘ, top bar, presets or browser of AutoEQ Local's page)",
          not gone, gone)


def test_links_and_f1_keys(check):
    from ui import help_window as hw
    by = hw._by_id()
    missing = [(e["id"], s) for e in by.values() for s in e.get("see") or [] if s not in by]
    keys = set()
    ui = os.path.join(paths.PROJECT_APP, "ui")  # (the project's own sources, as the old check read them)
    for name in os.listdir(ui):
        if name.endswith(".py"):
            with open(os.path.join(ui, name), encoding="utf-8") as fh:
                keys |= set(re.findall(r'help_window\.tag\([^,]+, "([^"]+)"\)', fh.read()))
    unknown = sorted(k for k in keys if not hw.help_key(k))
    # was selftest.py:890
    check("help: every “See also” opens an entry, and every control tagged for F1 has a help text",
          not missing and not unknown and len(keys) >= 10, (missing, unknown, len(keys)))


def test_search_and_going_to_an_entry(qapp, check):
    from ui import help_window as hw
    w = hw.open_at()
    try:
        w.q.setText("rig change database")  # ("rig change" alone is in 16 entries)
        found = w.found
        w.q.setText("zzzz qqqq")
        none = "No results with all of these words" in w.view.toPlainText()
        w.q.setText("rig")
        w.show_entry("set-best-fit-filter-counts")
        # was selftest.py:899
        check("help: the search keeps the entries with every word; going to an entry clears a search that hid it and "
              "lights it", 0 < found < 15 and none and w.q.text() == "" and w.lit == "set-best-fit-filter-counts",
              (found, none))
    finally:
        w.close()


def test_f1_on_a_control(qapp, check):
    from PySide6.QtWidgets import QCheckBox
    from ui import help_window as hw
    box = QCheckBox("x")
    hw.tag(box, "best_fit.filter_counts.1")
    # was selftest.py:903
    check("help: F1 on a control opens its setting's entry (a “to” box: its “from” box's)",
          hw.entry_of_widget(box) == "set-best-fit-filter-counts" and "F1" in box.toolTip(), box.toolTip())


LOOK = r'''
import json, re, sys, time
sys.path.insert(0, sys.argv[1])
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QTreeWidgetItemIterator
qapp = QApplication([])
from ui import theme, help_window as hw
out = {}
def settle():
    for _ in range(20):
        qapp.processEvents()
        time.sleep(0.01)
def shown_items(toc):
    out, it = [], QTreeWidgetItemIterator(toc)
    while it.value():
        item = it.value()
        p, seen = item.parent(), not item.isHidden()
        while seen and p is not None:
            seen = not p.isHidden() and p.isExpanded()
            p = p.parent()
        if seen:
            out.append(item)
        it += 1
    return out
for dark in (False, True):
    theme.apply(qapp, dark=dark, contrast=False)
    w = hw.open_at()
    w.resize(1000, 760)
    w.q.setText("")
    for i in range(w.toc.topLevelItemCount()):
        w.toc.topLevelItem(i).setExpanded(False)
    w.show_page("start")
    settle()
    toc, vw = w.toc, w.toc.viewport().width()
    top = [toc.topLevelItem(i) for i in range(toc.topLevelItemCount())]
    start = [len(shown_items(toc)), any(it.isExpanded() for it in top)]
    img = w.view.grab().toImage()  # (the page's top: the room above its first words)
    k = img.devicePixelRatio()
    w.show_entry("rig-tags")
    settle()
    t = theme.tokens()
    page = w.view.document().toHtml()
    links = {c for s in re.findall(r'<a href="#[^"]*"><span style="([^"]*)"', page) for c in re.findall(r"color:(#\w{6})", s)}
    cur = toc.currentItem()
    wide = [it.text(0)[:40] for it in shown_items(toc) if toc.visualItemRect(it).right() >= vw]
    v = out["dark" if dark else "light"] = {
        "start": start, "links": sorted(links), "accent_text": t["accent_text"],
        "chosen": cur is not None and cur.data(0, Qt.UserRole) == "rig-tags" and cur.parent().isExpanded(),
        "one entry": page.count("<h3") == 1, "page": img.pixelColor(int(w.view.width() * k / 2), int(5 * k)).name(),
        "card": t["card"], "wide": wide, "name": w.view.accessibleName()}
    w.q.setText("filter")
    settle()
    groups = [it for it in shown_items(toc) if it.childCount()]
    found = [it for it in shown_items(toc) if not it.childCount()]
    v["search"] = [bool(found), all(g.isExpanded() for g in groups),
                   all(w._matches(hw._by_id()[it.data(0, Qt.UserRole)], ["filter"]) for it in found
                       if it.data(0, Qt.UserRole) in hw._by_id())]
    w.q.setText("")
    w.show_entry("set-best-fit-filter-counts")
    settle()
    cur = toc.currentItem()
    v["setting"] = [cur.data(0, Qt.UserRole), cur.parent().isExpanded(), w.view.document().toHtml().count("<h3")]
print(json.dumps(out))
'''


def test_the_look_follows_the_theme(check):
    # (2026-10-23, the Windows 11 look: the page was the colour of a text box and its links the accent's fill colour;
    # long questions in the contents came out wider than the list. The UI audit, 2026-11-08: the contents are groups
    # that open and close, and the page shows one entry at a time)
    out = subproc.run_python(LOOK, session.SESSION.app)
    d = out.data or {}
    check("help: its page and contents are cards as the rest of the app, its links in the accent's text colour, the "
          "entry asked for alone on the page and chosen in the contents (its group open), light and dark",
          len(d) == 2 and all(v["links"] == [v["accent_text"]] and v["chosen"] and v["one entry"] and v["page"] == v["card"]
                              for v in d.values()), d or out.stderr[-300:])
    check("help: the contents start with their groups closed (a few rows), and no entry is wider than the list",
          len(d) == 2 and all(v["start"][0] <= 12 and not v["start"][1] and not v["wide"] for v in d.values()),
          {m: (v["start"], v["wide"][:3]) for m, v in d.items()} if d else out.stderr[-300:])
    check("help: a search keeps the entries with its words, each group with one open; F1's entry (a setting) opens "
          "its group and is alone on the page; the page is named for a screen reader (“Help page”)",
          len(d) == 2 and all(v["search"] == [True, True, True] and v["setting"] == ["set-best-fit-filter-counts", True, 1]
                              and v["name"] == "Help page" for v in d.values()),
          {m: (v["search"], v["setting"], v["name"]) for m, v in d.items()} if d else out.stderr[-300:])


def test_rig_tags_say_what_find_shows(check):
    # (2026-10-23: Help said a guessed tag (“711?”) had a dashed outline and that ⇄ was blue when its conversion is for
    # your target's rig; Find… draws every tag as the same plain chip, the “?” and “ ⇄” in its words)
    from ui import help_window as hw
    e = hw._by_id()["rig-tags"]
    words = " ".join(x for b in e["body"] for x in (b if isinstance(b, list) else [b]))
    check("help: Rig tags says what Find… shows: every tag the same plain chip, its words saying how sure (“5128”, "
          "“711?”, “rig ?”, “mixed”, “5128 ⇄”), no dashed outline or blue",
          not any(w in words.lower() for w in ("dashed", "outline", "blue"))
          and all(f"“{tag}”" in words for tag in ("5128", "711?", "rig ?", "mixed", "5128 ⇄")), words)


def test_help_fits_a_small_screen(qapp, monkeypatch, check):
    # (2026-10-24, left from the restyle: it opened 760 high, under the taskbar of a 1920 x 1080 laptop at 150 % (672
    # px above it) and 175 %)
    from helpers import qt
    from ui.help_window import HelpWindow
    seen = qt.on_screens(monkeypatch, HelpWindow)
    big = seen[qt.BIG_SCREEN]
    check("help: its window opens within a laptop's screen at 150 % and 175 % (above the taskbar, its smallest size "
          "too), its parts not squeezed; on a big screen as before (1000 x 760)",
          all(seen[s]["fits"] for s in qt.SMALL_SCREENS) and big["fits"] and big["opens"] == (1000, 760), seen)


def test_help_starts_a_cards_room_from_its_edges(qapp, check):
    # (2026-10-27, the pictures' review: Help kept Qt's own 11 px, every other window CARD, UI-RULES 5)
    from ui import help_window as hw
    from ui.theme_sheet import CARD
    w = hw.open_at()
    try:
        m = w.layout().contentsMargins()
        edges = (m.left(), m.top(), m.right(), m.bottom())
    finally:
        w.close()
    check("help: its words and lists start CARD (16 px) from the window's edges, as every window's", edges == (CARD,) * 4,
          edges)
