"""Find… (ui\\picker.py) at its smallest width (680 px), at 1000 px and at the width it opens at (900 px): each source
tab's label whole with 0, 12 and 3,456 results (also while This PC is searched: "…" after its number), and each
message of its message line (the footer's) whole, in light and in dark (2026-11-11: "This PC  0…" was cut at 1000
px, and the messages were cut at 680 px)."""
import os

import pytest

from helpers import qt, session

WIDTHS = (680, 900, 1000)
COUNTS = ("0", "12", "3,456")


def _picker(page, width):
    """Find… for a measurement, shown at `width` px (its lists waited for), its timers stopped: the labels set by a
    test stay as they are."""
    from ui.picker import Picker
    pk = Picker(page, "measurement")
    pk.show()
    qt.wait_for(lambda: not pk.db.get("loading") and not pk.lib.get("scanning"), 120)
    pk._poll.stop()
    pk._later.stop()
    pk.resize(width, 720)
    qt.pump(200)
    return pk


def _keep(widget, name):
    """A picture of the widget in the test folder's pictures (kept with AUTOEQSTUDIO_KEEP_TEST_FOLDER=1)."""
    folder = os.path.join(session.SESSION.root, "pictures")
    os.makedirs(folder, exist_ok=True)
    qt.picture(widget).save(os.path.join(folder, name + ".png"))


def _cut_tabs(pk):
    """The source tabs whose label is cut: narrower than their words need (Qt clips a button's words)."""
    return [(b.text(), b.width(), b.sizeHint().width()) for b in pk.src_by_key.values()
            if b.width() < b.sizeHint().width()]


def test_tab_labels_whole(eq_screen, check):
    from ui.picker import SOURCES
    seen = {}
    for width in WIDTHS:
        pk = _picker(eq_screen.page, width)
        try:
            for n in COUNTS:
                for scanning in ("", "…"):
                    for key, name in SOURCES:
                        pk.src_by_key[key].setText(f"{name}  {n}{scanning if key == 'pc' else ''}")
                    qt.pump(50)
                    cut = _cut_tabs(pk)
                    if cut:
                        seen[(width, n + scanning)] = cut
            _keep(pk, f"find-tabs-{width}")
        finally:
            qt.close(pk)
    check("Find…: each source tab's label is whole at 680, 900 and 1000 px with 0, 12 and 3,456 results (also with "
          "“…” while This PC is searched)", not seen, seen)


def _messages(name):
    """Each message that Find… can show in its message line (UI-RULES 7): its own and the page's that it gives `say`
    (ui\\eq_page_files.py), with a long file name and a long cause where a message has one."""
    return [("Offline: to open this entry, change to Online (top right).", None),
            ("Windows cannot open the website of this entry.", None),
            ("No new picture came in 10 minutes. Select the entry again.", None),
            (f"The app moved “{name}” to Measurement.", lambda: None),
            (f"The app moved “{name}” to Target.", lambda: None),
            ("The app cannot use that file: The file is not in the app. Select the file again in Find….", None)]


@pytest.mark.parametrize("look", ["light", "dark"])
def test_messages_whole(eq_screen, look, check):
    qapp, seen, bad = eq_screen.qapp, {}, {}
    getattr(qt, look)(qapp)
    qapp.processEvents()
    try:
        for width in WIDTHS:
            pk = _picker(eq_screen.page, width)
            try:
                line = pk.footer.line
                for k, (text, undo) in enumerate(_messages("Truthear Gate (Wide Bore Tips) L1 5128.txt")):
                    pk.footer.say(text, 0, undo)
                    qt.pump(50)
                    lab = line.text
                    # (the height its words need at its width, as the label lays them out; one line: their length)
                    need = lab.heightForWidth(lab.width()) if lab.wordWrap() else lab.sizeHint().height()
                    whole = lab.height() >= need and (lab.wordWrap() or lab.fontMetrics().horizontalAdvance(text)
                                                      <= lab.width())
                    inside = pk.rect().contains(lab.geometry().translated(line.mapTo(pk, line.rect().topLeft())))
                    seen[(width, k)] = (lab.width(), lab.height(), need, whole, inside)
                    if not (whole and inside):
                        bad[(width, text[:40])] = seen[(width, k)]
                    if k == 3:
                        _keep(pk.footer, f"find-message-{width}-{look}")
                        _keep(pk, f"find-window-message-{width}-{look}")
                pk.footer.say("", 0)
            finally:
                qt.close(pk)
    finally:
        qt.light(qapp)
        qapp.processEvents()
    check(f"Find… ({look}): each message of its message line is whole at 680, 900 and 1000 px (it wraps to more "
          "lines when it is longer than the line), and in the window", not bad, bad)


def test_tabs_say_what_the_mark_means(eq_screen, check):
    # (2026-11-12: "This PC  0…" looked like a cut label. The "…" says that This PC is still searched, or, as the
    # number of All and Online databases, that the online lists still load: each tab's tooltip and its Help entry
    # say so, and F1 on a tab opens that entry)
    from ui import help_window
    from ui.picker import SOURCES, Picker
    pk = Picker(eq_screen.page, "measurement")
    try:
        tips = {name: pk.src_by_key[key].toolTip() for key, name in SOURCES}
        entries = {name: help_window.entry_of_widget(pk.src_by_key[key]) for key, name in SOURCES}
    finally:
        qt.close(pk)
    body = " ".join(b for b in help_window._by_id().get("set-pk-src", {}).get("body", []) if isinstance(b, str))
    # (the first sentence is for each tab: All shows all sources, so "one source" alone was not true for it)
    seen = {"tooltips say it": sorted(n for n, t in tips.items() if "“…”: the app continues to search this PC or to "
                                      "load the online lists." in t and t.endswith("F1 opens Help.")
                                      and t.startswith("Shows the items of all sources or of one source, and their "
                                                       "number.")),
            "F1 entries": sorted(set(entries.values())),
            "Help says it": "“…” after the number of This PC: the app continues to search this PC" in body
            and "“…” as the number of All or Online databases: the app continues to load the online lists." in body}
    check("Find…: the tooltip of each source tab and its Help entry say what “…” after a number means (This PC is "
          "still searched, the online lists still load); F1 on a tab opens that entry",
          seen == {"tooltips say it": sorted(n for _k, n in SOURCES), "F1 entries": ["set-pk-src"],
                   "Help says it": True}, (seen, tips))
