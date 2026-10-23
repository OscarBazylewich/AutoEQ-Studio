"""Listen's card on Make an EQ (ui\\listen.py): the versions and Play, keys 1 and 2, the tone marked on the graph, Keep
to compare, Blind test, a version in each ear, History's Listen, the device's own EQ said and switched off, ✕ and
Stop; and the review's fixes: an EQ with no filter on refused, colours not in use, the volume saved a moment later,
a pasted EQ and Undo, the tone's range. Moved from eq_checks.py's listen_checks, review_checks and
review_low_checks. Then the Windows 11 look (2026-10-23): Play / Stop's symbols, each version marked in its curve's
colour by the theme (light and dark), your EQs to compare in columns, the versions in rows that fit the card, Paste
filters' OK as its main action; the device's own EQ said in Windows 11's warning card, Swap's symbol, the EQs to
compare's ✕ quiet and their name boxes named for a screen reader.

As in the old checks, it all happens on one Make an EQ, in order (the tests below are a chain, written in the order
they ran): with a result on its card (a quick Best fit run with the Run button), saved as "UI check" (so History has
it), brought back with History's Show, and made the stand-in device's EQ with Use on device (eq_checks.py lines
1528-1624, the steps before listen_checks). Nothing is played: tests\\listen\\conftest.py stands in for the sound
card for the whole file."""
import json
import types

import pytest
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QPushButton

from helpers import eqpage
from ui.history_window import HistoryWindow

# (what the card reaches through the page: for app\tools\relevant_tests.py)
COVERS = ("ui.listen", "ui.audio", "ui.eq_page", "eq.service", "eq.listening", "switcher.core", "switcher.apo")


@pytest.fixture(scope="module")
def card(eq_screen):
    """Make an EQ as it was when the old Listen checks began: a result on the card, saved (its History entry), shown
    again from History, and the stand-in device's EQ on. Also what the chain below keeps between its tests."""
    s = eq_screen
    eqpage.quick_run(s)
    entry = eqpage.save_result(s)
    eqpage.show_from_history(s, entry)
    eqpage.use_on_device(s)
    return types.SimpleNamespace(s=s, page=s.page, lis=s.page.listen, sw=s.sw, said=s.said, entry=entry, n=None)


def test_versions_and_play(card, check):
    lis = card.lis
    # (Play's sound card stood in for: tests\listen\conftest.py, as eq_checks.py line 2926)
    lis.src.setCurrentIndex(lis.src.findData("tone"))
    lis.source_changed()
    # (both ears hear the same version: chosen by its value. Made firm 2026-10-22: the old check took the Ears list's
    # first choice, meant to be "both"; since the drop-downs are A to Z that's "A different version in each ear", so
    # the keys and Blind test below ran with the ears split: Blind greyed out, and the keys changing a version that
    # wasn't heard)
    lis.ears.setCurrentIndex(lis.ears.findData("both"))
    lis.ears_changed()
    keys = [k for k, *_ in lis.versions()]
    lis.play()
    # was eq_checks.py:2933
    check("listen: the versions are EQ off, the selected EQ, then the EQs to compare; Play plays the selected EQ",
          keys[:2] == ["off", "sel"] and lis.playing and lis.engine.active == "sel" and lis.engine.ears == "both"
          and [s["key"] for s in lis.engine.slots] == keys, (keys, lis.play_btn.text(), lis.engine.ears))


def test_keys_1_and_2(card, check):
    page, lis = card.page, card.lis
    page.setFocus()
    page.keyPressEvent(QKeyEvent(QEvent.KeyPress, Qt.Key_1, Qt.NoModifier))
    k1 = lis.engine.active
    page.keyPressEvent(QKeyEvent(QEvent.KeyPress, Qt.Key_2, Qt.NoModifier))
    # was eq_checks.py:2940
    check("listen: keys 1 and 2 switch to EQ off and the selected EQ",
          (k1, lis.engine.active) == ("off", "sel") and lis.engine.ears == "both",
          (k1, lis.engine.active, lis.engine.ears))


def test_tone_marked(card, check):
    page, lis = card.page, card.lis
    page.draw_marker()
    # was eq_checks.py:2943
    check("listen: the tone's frequency is marked on the graph", page.marker.isVisible()
          and abs(10 ** page.marker.value() - lis.engine.tone_hz) < 0.5, (page.marker.value(), lis.engine.tone_hz))


def test_keep_to_compare(card, check):
    page, lis, said = card.page, card.lis, card.said
    n = card.n = len(lis.pins)
    lis.add_selected()
    lis.add_selected()
    names = [it.name() for it in page.plot.listDataItems()]
    saved = page.svc.call("/api/listen", {"device": page.curves["name"]}).get("eqs") or []
    # was eq_checks.py:2950
    check("listen: Keep to compare adds the result once (kept for this IEM, on the graph, a version to hear)",
          len(lis.pins) == n + 1 and len(saved) == n + 1 and lis.pins[-1]["name"] in names
          and lis.pins[-1]["key"] in [s["key"] for s in lis.engine.slots]
          and any("already" in s for s in said), (len(lis.pins), names))


def test_blind_test(card, check):
    lis = card.lis
    offered = lis.blind.isEnabled()  # (with both ears hearing the same version: test_versions_and_play chose it)
    lis.blind.setChecked(True)
    hidden = [b.text() for b in lis.ab_box.findChildren(QPushButton)]
    lis.reveal()
    shown = [b.text() for b in lis.ab_box.findChildren(QPushButton) if not b.isHidden()]
    # was eq_checks.py:2958
    check("listen: Blind test names the versions A, B, C … until Reveal",
          offered and [t.split()[1] for t in hidden] == ["A", "B", "C"][:len(hidden)] and len(hidden) >= 3
          and all(" = " in t for t in shown), (offered, hidden, shown))


def test_version_in_each_ear_and_swap(card, check):
    lis = card.lis
    lis.blind.setChecked(False)
    lis.ears.setCurrentIndex(lis.ears.findData("split"))
    lis.ears_changed()
    # was eq_checks.py:2964
    check("listen: a different version in each ear (EQ off left, the EQ right; Swap)",
          (lis.engine.ears, lis.engine.left, lis.engine.right) == ("split", "off", "sel") and not lis.blind.isEnabled()
          and (lis.swap() or (lis.engine.left, lis.engine.right) == ("sel", "off")), (lis.engine.left, lis.engine.right))


def test_history_listen_for_another_iem(card, check):
    page, lis, said, entry, n = card.page, card.lis, card.said, card.entry, card.n
    hw = HistoryWindow(page, True)
    hw.listen_to(dict(entry, device="Another IEM", filters=[dict(f, gain=f["gain"] - 1) for f in entry["filters"]]))
    hw.close()
    # was eq_checks.py:2971
    check("listen: History's Listen adds an EQ made for another IEM, and says it won't sound as intended",
          len(lis.pins) == n + 2 and "made for Another IEM" in lis.pins[-1]["note"] and "won't sound" in said[-1], said[-1:])


def test_device_eq_said(card, check):
    lis = card.lis
    # was eq_checks.py:2973
    check("listen: the device's own EQ (Use on device switched it on) is said: it plays on top", lis.apo_box.isVisibleTo(lis)
          and "Headset" in lis.apo_text.text(), lis.apo_text.text())


def test_device_eq_in_a_warning_card(card, check):
    # (Windows 11 look, 2026-10-23: it was a warning-coloured box without the warning symbol the banner and Which
    # measurement's note have. Here in the chain while the device's own EQ is still on)
    from PySide6.QtWidgets import QLabel

    from helpers import qt
    from ui import icons, theme
    lis = card.lis
    qt.pump(100)
    box = lis.apo_box
    signs = [w for w in box.findChildren(QLabel) if w.property("glyph") in (True, "true") and w.isVisible()]
    sign = signs[0] if signs else None
    seen = {"card": box.property("card"), "signs": len(signs),
            "symbol": sign is not None and sign.text() == chr(int(icons.GLYPHS["warning"], 16)),
            "read as": _read_as(sign) if sign is not None else None,
            "in the warning colour": sign is not None and theme.tokens()["warn"] in _ink(sign),
            "words wrap": lis.apo_text.wordWrap(),
            "button at the right": lis.apo_off.parentWidget() is box
            and lis.apo_off.geometry().left() > lis.apo_text.geometry().right()}
    check("listen: the device's own EQ is said in Windows 11's warning card, as the banner: the warning symbol (read "
          "as “Warning”) in the warning colour, the words wrapping, Switch it off at the right",
          seen == {"card": "warn", "signs": 1, "symbol": True, "read as": "Warning", "in the warning colour": True,
                   "words wrap": True, "button at the right": True}, seen)


def test_device_eq_switched_off(card, check):
    lis, sw = card.lis, card.sw
    lis.device_eq_off()
    # was eq_checks.py:2976
    check("listen: Switch it off turns the device's EQ off", sw.record("Headset|EarPods")["active"] is None
          and not lis.apo_box.isVisibleTo(lis))


def test_remove_and_stop(card, check):
    page, lis, n = card.page, card.lis, card.n
    lis._remove(lis.pins[-1])
    lis.stop()
    # was eq_checks.py:2980
    # (since the Windows 11 look, 2026-10-23, the ▶ beside Play is Windows' symbol, not a character of its words)
    check("listen: ✕ removes an EQ to compare; Stop stops and the mark goes",
          len(lis.pins) == n + 1 and not lis.playing and not page.marker.isVisible() and lis.play_btn.text() == "Play")
    card.s.qapp.processEvents()


def test_refuses_eq_with_no_filter_on_and_new_colour(card, dialogs, check):
    s, page, lis = card.s, card.page, card.lis
    # (first, as before it in the old run: History's Show loads the EQ's measurement as a choice does, so Listen has
    # that IEM's EQs to compare: eq_checks.py lines 1692-1693, a check of its own elsewhere)
    eqpage.show_from_history(s, card.entry)
    s.wait_for(lambda: page.curves is not None, 30)
    dialogs.reset()  # (what the message boxes said, from here: eq_checks.py line 1706 emptied its BOXES)
    empty = lis.add("Nothing", [{"type": "PK", "freq": 1000, "gain": 3, "q": 1, "enabled": False}])
    while len(lis.pins) > 1:
        lis._remove(lis.pins[-1])
    lis.add("One", [{"type": "PK", "freq": 500, "gain": 2, "q": 1}])
    lis.add("Two", [{"type": "PK", "freq": 600, "gain": 2, "q": 1}])
    lis._remove(next(p for p in lis.pins if p["name"] == "One"))
    lis.add("Three", [{"type": "PK", "freq": 700, "gain": 2, "q": 1}])
    colours = [p.get("color") for p in lis.pins]
    # was eq_checks.py:1715
    check("review: Listen refuses an EQ with no filter switched on; a new EQ to compare takes a colour not in use",
          empty is False and any("no filters" in text for _kind, text in dialogs.asked)
          and len(set(colours)) == len(colours), colours)


def test_volume_saved_a_moment_later(card, check):
    s, lis, sw = card.s, card.lis, card.sw
    told = []
    listener = lambda what, info: told.append(what)

    def on_disk():
        with open(sw.path, encoding="utf-8") as fh:
            return (json.load(fh).get("listen") or {}).get("vol")
    sw.listeners.append(listener)
    try:
        for v in (-30, -31, -32):
            lis.vol.setValue(v)
        now = (on_disk(), list(told), sw.s["listen"].get("vol"))
        s.wait_for(lambda: on_disk() == -32, 3)
        # was eq_checks.py:1725
        check("review: Listen's volume is saved a moment after it stops moving, and the other screens aren't redrawn "
              "for it", now[0] != -32 and now[1:] == ([], -32) and on_disk() == -32, (now, on_disk()))
    finally:
        sw.listeners.remove(listener)  # (the old check left it there for the rest of its run)


def test_tone_shown_pasted_eq_and_undo(card, check):
    lis = card.lis
    tone_text = lis.tone_lab.text()
    lis._add_text("Filter 1: ON PK Fc 333 Hz Gain 2 dB Q 1", "Pasted check", "pasted")
    pasted_note = lis.pins[-1]["note"] if lis.pins else ""
    lis._remove(lis.pins[-1])
    undo_shown = lis.undo_row.isVisibleTo(lis)
    n = len(lis.pins)
    lis.undo_btn.click()
    # was eq_checks.py:1921
    check("review: Listen: the tone's frequency shown from the start; a pasted EQ says so; ✕ offers Undo, which puts it back",
          tone_text.endswith("Hz") and pasted_note == "pasted" and undo_shown and len(lis.pins) == n + 1,
          (tone_text, pasted_note, undo_shown, len(lis.pins), n))


def test_tone_range_values_used_and_kept(card, check):
    page, lis = card.page, card.lis
    lis.tone_from.setText("nan")
    lis.tone_to.setText("5")
    lis.tone_range_done()
    kept = {k: (page.sw.s.get("listen") or {}).get(k) for k in ("tone_from", "tone_to")}
    # was eq_checks.py:1929
    check("listen: the tone's From and To show the values used (\"nan\", 5 Hz) and are kept for the next start",
          (lis.tone_from.text(), lis.tone_to.text()) == ("20", "20") and kept == {"tone_from": 20, "tone_to": 20}
          and lis.tone_lab.text().endswith("Hz"), (lis.tone_from.text(), lis.tone_to.text(), kept))
    lis.tone_from.setText("20")  # (back to the whole range, as the old check left it: lines 1932-1934)
    lis.tone_to.setText("20000")
    lis.tone_range_done()


# ---------------------------------------------------------------- the Windows 11 look (2026-10-23)
def _edge(widget):
    """The colour in the middle of a control's left edge, as drawn."""
    img = widget.grab().toImage()
    return img.pixelColor(2, img.height() // 2).name()


def _ink(label):
    """Every colour a label is drawn in."""
    img = label.grab().toImage()
    return {img.pixelColor(x, y).name() for x in range(img.width()) for y in range(img.height())}


def _read_as(widget):
    """What a screen reader reads for a widget (its accessible name)."""
    from PySide6.QtGui import QAccessible
    iface = QAccessible.queryAccessibleInterface(widget)
    return (iface.text(QAccessible.Name) if iface is not None else "") or ""


def test_play_and_stop_symbols(card, check):
    lis = card.lis
    b = lis.play_btn
    shown = []
    for text in ("Stop", "Play", "■ Stop", "▶ Play"):  # (a ▶ or ■ written before the word, as before the symbols)
        b.setText(text)
        shown.append((b.text(), b.symbol, not b.icon().isNull()))
    b.setText("Preparing…")
    preparing = (b.text(), b.symbol, b.sizeHint().width() <= b.minimumWidth())
    lis.play()
    playing = (b.text(), b.symbol)
    lis.stop()
    stopped = (b.text(), b.symbol)
    check("listen: Play and Stop show Windows 11's symbol beside their word, whoever sets it (the Guide's demo too); "
          "the button keeps its width while the music is prepared",
          shown == [("Stop", "stop", True), ("Play", "play", True), ("Stop", "stop", True), ("Play", "play", True)]
          and preparing == ("Preparing…", "play", True) and playing == ("Stop", "stop")
          and stopped == ("Play", "play"), (shown, preparing, playing, stopped))


def test_version_marks_follow_the_theme(card, check):
    from PySide6.QtWidgets import QLabel

    from helpers import qt
    from ui import theme
    from ui.listen import COLOURS
    s, lis = card.s, card.lis
    lis.blind.setChecked(False)
    lis.ears.setCurrentIndex(lis.ears.findData("both"))
    lis.ears_changed()
    want = ["meas", "with_eq"] + [COLOURS[p.get("color", i) % len(COLOURS)] for i, p in enumerate(lis.pins)]
    seen = {}
    try:
        for mode, put in (("dark", qt.dark), ("light", qt.light)):
            put(s.qapp)  # (the page draws Listen again in the theme's colours, as when Windows switches)
            qt.pump(150)
            t = theme.tokens()
            btns = [b for b in lis.ab_box.findChildren(QPushButton) if b.isVisible()]
            swatches = [w for w in lis.pins_box.findChildren(QLabel) if w.isVisible() and w.text() == "■"]
            seen[mode] = {"marks": [b.property("listen_mark") for b in btns],
                          "own styles": [w.styleSheet() for w in btns + swatches if w.styleSheet()],
                          "edges": [_edge(b) == t[m] for b, m in zip(btns, want)],
                          "swatches": [t.get(w.property("listen_mark")) in _ink(w) for w in swatches]}
    finally:
        qt.light(s.qapp)  # (as the page was opened)
    check("listen: each version is marked in its curve's colour on the graph (EQ off the measurement's, the selected EQ "
          "the blue of “with the EQ”, not Windows' accent; each EQ to compare its own, as beside it in the list), drawn "
          "by the theme in light and dark",
          all(v["marks"] == want and not v["own styles"] and v["edges"] and all(v["edges"])
              and len(v["swatches"]) == len(lis.pins) and all(v["swatches"]) for v in seen.values())
          and len(seen) == 2, seen)


def test_eqs_to_compare_in_columns(card, check):
    from PySide6.QtCore import QPoint
    from PySide6.QtWidgets import QCheckBox, QLabel, QLineEdit

    from helpers import qt
    lis = card.lis
    qt.pump(100)

    def shown(kind):
        return [w for w in lis.pins_box.findChildren(kind) if w.isVisible()]

    def left(ws):
        return {w.mapTo(lis, QPoint(0, 0)).x() for w in ws}  # (where each one starts)
    notes = [w for w in shown(QLabel) if w.text() != "■"]
    at = {"name boxes' widths": {w.width() for w in shown(QLineEdit)}, "notes": left(notes),
          "Graph": left(shown(QCheckBox)), "✕": left(shown(QPushButton))}
    check("listen: your EQs to compare line up in columns (each name box as wide as the others, its notes, Graph and ✕ "
          "under the one above, however long the notes)",
          len(notes) == len(lis.pins) >= 2 and len({len(n.text()) for n in notes}) > 1
          and all(len(v) == 1 for v in at.values()), (len(lis.pins), at))


def test_eqs_to_compare_x_quiet_and_names(card, check):
    # (each ✕ was a plain button with a border, where every other ✕ of the app is quiet; and a screen reader read each
    # name box as nothing)
    from PySide6.QtWidgets import QLineEdit

    from helpers import qt
    lis = card.lis
    qt.pump(100)
    xs = [b for b in lis.pins_box.findChildren(QPushButton) if b.isVisible() and b.text() == "✕"]

    def plain_at_rest(b):
        """Drawn without a fill or a border of its own while nothing points at it: its edge the colour of its inside."""
        img = b.grab().toImage()
        return img.pixelColor(0, img.height() // 2) == img.pixelColor(3, img.height() // 2)
    quiet = [b.property("quiet") == "true" and plain_at_rest(b) for b in xs]
    names = [_read_as(w) for w in lis.pins_box.findChildren(QLineEdit) if w.isVisible()]
    check("restyle: each EQ to compare's ✕ is quiet as every ✕ (no fill or border until pointed at)",
          len(xs) == len(lis.pins) >= 2 and all(quiet), (len(xs), quiet))
    check("access: each EQ to compare's name box has a name a screen reader reads (“Name of” its EQ)",
          names == [f"Name of {p['name']}" for p in lis.pins] and len(names) >= 2, names)


def test_swap_symbol(card, check):
    from PySide6.QtCore import QSize

    from ui import icons, theme
    lis = card.lis
    swap = next(b for b in lis.split_row.findChildren(QPushButton) if b.text() == "Swap")
    t, size = theme.tokens(), QSize(22, 16)
    want = icons.glyph("swap", t["ink"], on_colour=t["on_accent"], off_colour=t["disabled"]).pixmap(size).toImage()
    check("listen: Swap (a different version in each ear) shows Windows 11's swap symbol beside its word",
          not swap.icon().isNull() and swap.icon().pixmap(size).toImage() == want, swap.icon().isNull())


def test_versions_in_rows_that_fit(card, check):
    from PySide6.QtWidgets import QButtonGroup, QScrollArea

    from helpers import qt
    page, lis = card.page, card.lis
    for n in range(4):
        lis.add(f"An EQ to compare with a long name, number {n + 1}, to see where the row of versions ends",
                [{"type": "PK", "freq": 2000 + 100 * n, "gain": 2, "q": 1}])
    for _ in range(3):
        lis.refresh()
    qt.pump(200)
    area = next(a for a in page.findChildren(QScrollArea) if a.widget() and a.widget().isAncestorOf(lis))
    btns = [b for b in lis.ab_box.findChildren(QPushButton) if b.isVisible()]
    rows = sorted({b.y() for b in btns})
    inside = all(b.geometry().right() < lis.ab_box.width() for b in btns)
    wide = (lis.minimumSizeHint().width(), area.viewport().width())
    check("listen: the versions take as many rows as they need, so many EQs to compare with long names keep the card "
          "within Make an EQ (it never scrolls sideways for them)",
          len(btns) == len(lis.versions()) >= 8 and len(rows) >= 2 and inside and wide[0] <= wide[1],
          (len(btns), rows, inside, wide))
    groups = len(lis.findChildren(QButtonGroup))
    check("listen: drawing the versions again keeps one button group (one more was left behind with each redraw)",
          groups == 1, groups)


def test_paste_ok_is_the_main_action(card, monkeypatch, check):
    from PySide6.QtCore import QCoreApplication, QEvent
    from PySide6.QtWidgets import QDialog, QDialogButtonBox
    lis = card.lis
    seen = {}

    def look(dlg, *a, **k):
        seen.update(ok=dlg.findChild(QDialogButtonBox).button(QDialogButtonBox.Ok).property("primary"),
                    title=dlg.windowTitle())
        return QDialog.Rejected
    monkeypatch.setattr(QDialog, "exec", look)
    n = len(lis.pins)
    lis.add_paste()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    left = len(lis.findChildren(QDialog))
    check("listen: Paste filters… asks in a window whose OK is its main action (the accent); cancelled, nothing is "
          "added and the window goes", seen == {"ok": "true", "title": "Paste filters"} and len(lis.pins) == n
          and left == 0, (seen, len(lis.pins), n, left))
