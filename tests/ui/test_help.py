"""Help (ui\\help_window.py, ui\\help_texts.py): its words told in AutoEQ Studio's own controls, every "See also" and
F1 key found, the search, and F1 on a control. Moved from selftest.py's help_checks."""
import json
import os
import re

from helpers import paths

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
