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
        w.q.setText("rig conversion")
        found = w.toc.count()
        w.q.setText("zzzz qqqq")
        none = "Nothing matches" in w.view.toPlainText()
        w.q.setText("rig")
        w.go("set-best-fit-filter-counts")
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
from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import QApplication
qapp = QApplication([])
from ui import theme, help_window as hw
out = {}
def settle():
    for _ in range(20):
        qapp.processEvents()
        time.sleep(0.01)
for dark in (False, True):
    theme.apply(qapp, dark=dark, contrast=False)
    w = hw.open_at()
    w.resize(1000, 760)
    w.view.verticalScrollBar().setValue(0)
    settle()
    img = w.view.grab().toImage()  # (the page's top: the room above its first words)
    k = img.devicePixelRatio()
    w.go("rig-tags")
    settle()
    t = theme.tokens()
    page = w.view.document().toHtml()
    links = {c for s in re.findall(r'<a href="#[^"]*"><span style="([^"]*)"', page) for c in re.findall(r"color:(#\w{6})", s)}
    toc, vw = w.toc, w.toc.viewport().width()
    wide, short = [], []
    for n in range(toc.count()):
        it = toc.item(n)
        r = toc.visualItemRect(it)
        fm = QFontMetrics(it.font() if it.data(Qt.FontRole) is not None else toc.font())
        need = fm.boundingRect(QRect(0, 0, r.width() - 22, 100000), Qt.TextWordWrap, it.text()).height() + 12
        if r.right() >= vw:
            wide.append(it.text()[:40])
        elif need > r.height():
            short.append(it.text()[:40])
    chosen = [it.data(Qt.UserRole) for it in toc.selectedItems()]
    out["dark" if dark else "light"] = {
        "links": sorted(links), "accent_text": t["accent_text"],
        "lit": f'bgcolor="{t["accent"]}"' in page and chosen == ["rig-tags"],
        "page": img.pixelColor(int(w.view.width() * k / 2), int(5 * k)).name(), "card": t["card"],
        "wide": wide, "short": short, "rows": toc.count()}
    w.go("set-best-fit-filter-counts")  # (an entry asked for, then a search typed that finds it half-way down)
    settle()
    for text in ("f", "fi", "filter"):
        w.q.setText(text)
    settle()
    out["dark" if dark else "light"]["typed"] = (toc.verticalScrollBar().value(),
                                                 [it.data(Qt.UserRole) for it in toc.selectedItems()])
    w.q.setText("")
    settle()
    bar = toc.verticalScrollBar()  # (the contents scrolled half-way, then an entry there clicked)
    bar.setValue(bar.maximum() // 2)
    settle()
    k = toc.row(toc.itemAt(toc.viewport().rect().center()))
    while k < toc.count() and toc.item(k).data(Qt.UserRole) not in hw._by_id():
        k += 1
    anchor, before = toc.item(k).data(Qt.UserRole), bar.value()
    w.go(anchor)  # (what a click on it does)
    settle()
    out["dark" if dark else "light"]["clicked"] = (before > 0 and bar.value() == before,
                                                   [it.data(Qt.UserRole) for it in toc.selectedItems()] == [anchor])
    w.q.setText("")  # (the page scrolled half-way, the theme changed and back, then a search typed)
    settle()
    pb = w.view.verticalScrollBar()
    pb.setValue(pb.maximum() // 2)
    settle()
    mid = pb.value()
    theme.apply(qapp, dark=not dark, contrast=False)
    settle()
    kept = pb.value()
    theme.apply(qapp, dark=dark, contrast=False)
    settle()
    for text in ("r", "ri", "rig"):
        w.q.setText(text)
    settle()
    out["dark" if dark else "light"]["place"] = (mid > 0, kept == mid, pb.value(), w.view.accessibleName())
    w.q.setText("")
    settle()
print(json.dumps(out))
'''


def test_the_look_follows_the_theme(check):
    # (2026-10-23, the Windows 11 look: the page was the colour of a text box and its links the accent's fill colour;
    # the entry asked for was lit paragraph by paragraph; long questions in the contents came out wider than the list,
    # their ends cut off, and its headings a size smaller than the rest)
    out = subproc.run_python(LOOK, session.SESSION.app)
    d = out.data or {}
    check("help: its page and contents are cards as the rest of the app, its links in the accent's text colour, the "
          "entry asked for on one quiet block with the accent's bar beside it (and chosen in the contents), light and "
          "dark",
          len(d) == 2 and all(v["links"] == [v["accent_text"]] and v["lit"] and v["page"] == v["card"]
                              for v in d.values()), d or out.stderr[-300:])
    check("help: every entry of the contents is as tall as its words and no wider than the list (none cut off)",
          len(d) == 2 and all(not v["wide"] and not v["short"] and v["rows"] > 50 for v in d.values()),
          {m: (v["wide"][:3], v["short"][:3], v["rows"]) for m, v in d.items()} if d else out.stderr[-300:])
    check("help: while a search is typed the contents stay at their top, the entry asked for still chosen in them; "
          "an entry opened from the contents leaves them where they were, chosen there",
          len(d) == 2 and all(v["typed"] == [0, ["set-best-fit-filter-counts"]] and v["clicked"] == [True, True]
                              for v in d.values()),
          {m: (v["typed"], v["clicked"]) for m, v in d.items()} if d else out.stderr[-300:])
    # (2026-10-23: a search typed kept the page's place, so its results showed part-way down with a line cut at the
    # top; and a screen reader said nothing for the page)
    check("help: a search typed shows the page from its top (a theme change leaves it where it was), and the page is "
          "named for a screen reader (“Help page”)",
          len(d) == 2 and all(v.get("place") == [True, True, 0, "Help page"] for v in d.values()),
          {m: v.get("place") for m, v in d.items()} if d else out.stderr[-300:])


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
