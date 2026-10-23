"""Listen's card on Make an EQ (ui\\listen.py): the versions and Play, keys 1 and 2, the tone marked on the graph, Keep
to compare, Blind test, a version in each ear, History's Listen, the device's own EQ said and switched off, ✕ and
Stop; and the review's fixes: an EQ with no filter on refused, colours not in use, the volume saved a moment later,
a pasted EQ and Undo, the tone's range. Moved from eq_checks.py's listen_checks, review_checks and
review_low_checks.

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
    check("listen: ✕ removes an EQ to compare; Stop stops and the mark goes",
          len(lis.pins) == n + 1 and not lis.playing and not page.marker.isVisible() and lis.play_btn.text() == "▶ Play")
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
