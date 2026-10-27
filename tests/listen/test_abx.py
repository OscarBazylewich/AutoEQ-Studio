"""Listen's ABX test (ui\\abx.py and ui\\listen.py, 2026-10-26): the chance of a score by guessing alone, exactly (the
binomial tail), and what the result says at the 5 % line; each trial's X its own random choice, said only at the end;
then on Make an EQ (an EQ by hand on the card; the sound card stood in for: tests\\listen\\conftest.py): A and B chosen
from the versions, the test level-matched with both ears the same while it runs (Listen's own choices put back
after), the version buttons and keys 1-9 put away, Listen to A, B and X playing what they should, the score at the
end and kept for the session, Stop saying what was answered, and the test ended when a version it uses goes."""
import math
import random

import pytest

from ui import abx


def test_chance_of_a_score(check):
    got = {k: round(abx.chance(k, 16), 6) for k in (0, 9, 12, 13, 16)}
    want = {k: round(sum(math.comb(16, i) for i in range(k, 17)) / 65536, 6) for k in (0, 9, 12, 13, 16)}
    check("abx: the chance of k or more right of 16 by guessing is the binomial tail (16: 1 in 65,536; 13: 1.1 %; "
          "12: 3.8 %; 9: 40 %; 0: certain)",
          got == want and got[16] == round(1 / 65536, 6) and abs(got[13] - 0.010635) < 1e-6 and got[0] == 1.0, got)


def test_trials_and_the_verdict(check):
    t = abx.Abx("off", "sel", 16, rng=random.Random(7))
    xs = list(t.xs)
    heard = []
    for i in range(16):
        heard.append(t.key("X"))
        t.answer(xs[i])  # (every answer right)
    t.answer("A")  # (past the end: not counted)
    sure = t.verdict()
    half = abx.Abx("off", "sel", 16, rng=random.Random(7))
    for i, x in enumerate(half.xs):
        half.answer(x if i < 9 else ("A" if x == "B" else "B"))  # (9 right)
    check("abx: each trial's X is A or B at random (both appear), heard as its version; 16 of 16 can't be guessing "
          "(you can tell them apart); 9 of 16 could be luck (said so)",
          set(xs) == {"A", "B"} and heard == [("off" if x == "A" else "sel") for x in xs] and t.done and t.right() == 16
          and "you can tell them apart" in sure and "less than 0.1 %" in sure and "could be luck" in half.verdict()
          and "40 %" in half.verdict(), (xs, sure, half.verdict()))


@pytest.fixture(scope="module")
def lis(eq_screen):
    page = eq_screen.page
    page.start_by_hand([{"type": "PK", "freq": 1000, "gain": 3, "q": 1}], "pasted", "ABX me")
    page.listen.play()  # (nothing is heard: tests\listen\conftest.py)
    return page.listen


def test_a_whole_test(lis, eq_screen, check):
    sw = eq_screen.page.sw
    lis.lm.setChecked(False)
    lis.ears.setCurrentIndex(lis.ears.findData("split"))
    lis.ears_changed()
    lis.refresh()
    a, b = lis.abx_a.currentData(), lis.abx_b.currentData()
    saved = dict(sw.s.get("listen") or {})
    lis.abx_begin()
    t = lis.abx
    during = (lis.lm.isChecked(), lis.ears.currentData(), lis.ab_box.isVisibleTo(lis), lis.abx_box.isVisibleTo(lis),
              lis.abx_row.isEnabled(), lis.engine.active, lis.engine.level_match, lis.engine.ears)
    saved_during = dict(sw.s.get("listen") or {})
    first_x = t.key("X")
    note = lis.note.text()
    lit = [b.text() for b in (*lis.abx_hear.values(), *lis.abx_says.values())
           if b.isChecked() or b.property("primary") == "true"]
    lis.abx_listen("A")
    heard_a = lis.active
    lis.abx_listen("B")
    heard_b = lis.active
    lis.choose_number(0)  # (key 1: put away while it runs)
    after_key = lis.active
    for i in range(t.n):
        lis.abx_answer(t.xs[i])
    said = lis.abx_said.text()
    check("abx: Start ABX tests A and B (EQ off and the EQ to start with), heard level-matched with both ears the same "
          "while it runs (not kept as your Listen settings), the version buttons put away (and the keys: the card "
          "doesn't offer them then); X heard first, only its button lit; Listen to A and B play theirs; key 1 does "
          "nothing",
          (a, b) == ("off", "sel") and during[:5] == (True, "both", False, True, False) and during[5] == first_x
          and during[6:] == (True, "both") and saved_during == saved and lit == ["Listen to X"]
          and "Keys 1-9" not in note and heard_a == "off" and heard_b == "sel" and after_key == "sel",
          (a, b, during, saved, saved_during, lit, note, heard_a, heard_b, after_key))
    check("abx: answered to the end, the score and what it means are said (and kept for the session); Listen's own "
          "choices are back (not level-matched, a version in each ear, as they were; heard so too)",
          lis.abx is None and "16 of 16 right" in said and "tell them apart" in said and len(lis.abx_results) == 1
          and not lis.lm.isChecked() and lis.ears.currentData() == "split" and not lis.abx_box.isVisibleTo(lis)
          and (lis.engine.level_match, lis.engine.ears) == (False, "split") and sw.s.get("listen") == saved,
          (said, lis.engine.level_match, lis.engine.ears))
    lis.ears.setCurrentIndex(lis.ears.findData("both"))
    lis.ears_changed()
    lis.lm.setChecked(True)


def test_blind_test_kept(lis, check):
    lis.blind.setChecked(True)
    order = lis.blind_order
    kept = list(order)
    lis.abx_begin()
    during = lis.blind.isChecked()
    lis.abx_end(finished=False, quiet=True)
    check("abx: a blind test you had is off while ABX runs, and back after with its letters as they were (not drawn "
          "again)", not during and lis.blind.isChecked() and lis.blind_order is order and order == kept,
          (during, kept, lis.blind_order))
    lis.blind.setChecked(False)


def test_play_first_said_while_stopped(lis, check):
    lis.abx_begin()
    lis.stop()
    stopped = lis.abx_text.text()
    lis.play()  # (nothing is heard: tests\listen\conftest.py)
    playing = lis.abx_text.text()
    lis.abx_end(finished=False, quiet=True)
    check("abx: while nothing plays, the trial says to Play first; pressing Play takes that away at once",
          "(Play first.)" in stopped and "(Play first.)" not in playing, (stopped, playing))


def test_stopped_part_way(lis, check):
    lis.abx_begin()
    t = lis.abx
    for i in range(3):
        lis.abx_answer(t.xs[i])
    lis.abx_end(finished=False)
    said = lis.abx_said.text()
    check("abx: Stop the test says what was answered so far (and that it stopped), with the earlier test this session",
          said.startswith("Stopped after 3 of 16 trials") and "3 of 3 right" in said and "Earlier ABX tests" in said,
          said)


def test_ended_when_its_version_goes(lis, eq_screen, check):
    page = eq_screen.page
    keep = (page.run_result, page.sel)
    said = []
    for answered in (0, 1):
        lis.abx_begin()
        for i in range(answered):
            lis.abx_answer(lis.abx.xs[i])
        try:
            page.run_result, page.sel = None, None  # (the selected EQ gone: B can't be heard)
            lis.refresh()
            said.append((lis.abx is None, lis.abx_said.text()))
        finally:
            page.run_result, page.sel = keep
            lis.refresh()
    check("abx: a version the test uses going away ends it, said by its name as it was when the test began (before "
          "an answer; and with one answered, in the result too)",
          said[0] == (True, "The ABX test stopped before any answer: Selected EQ (by hand) is gone.") and said[1][0]
          and said[1][1].startswith("Stopped after 1 of 16 trials (Selected EQ (by hand) is gone). "
                                    "EQ off vs Selected EQ (by hand): "), said)


def test_ended_when_its_version_changes(lis, eq_screen, check):
    page = eq_screen.page
    lis.abx_begin()
    t = lis.abx
    for i in range(2):
        lis.abx_answer(t.xs[i])
    lis.refresh()  # (nothing changed: it goes on)
    went_on = lis.abx is t
    page.EDIT[0]["gain"] += 2  # (an edit, as the table or a handle on the EQ graph makes one)
    try:
        page.live_update()
        ended, said = lis.abx is None, lis.abx_said.text()
    finally:
        page.EDIT[0]["gain"] -= 2
        page.live_update()
    check("abx: the selected EQ edited while it's tested ends the test (its other trials would test another EQ): "
          "what was answered is said, and why",
          went_on and ended and said.startswith("Stopped after 2 of 16 trials (Selected EQ (by hand) changed)."),
          (went_on, ended, said))


def test_buttons_named_by_their_words(lis, check):
    from ui import help_window
    btns = [lis.abx_start, *lis.abx_hear.values(), *lis.abx_says.values(),
            next(b for b in lis.abx_box.findChildren(type(lis.abx_start)) if b.text() == "Stop the test")]
    names = [b.accessibleName() or b.text() for b in btns]
    entry = help_window.entry_for("#snd-abx")
    check("abx: a screen reader names each ABX button by its words (not all \"ABX test\"), and F1 on any of them "
          "opens ABX test's entry in Help",
          names == [b.text() for b in btns] and entry and all(help_window.entry_of_widget(b) == entry for b in btns),
          (names, entry, [help_window.entry_of_widget(b) for b in btns]))


def test_same_version_twice_refused(lis, dialogs, check):
    lis.abx_b.setCurrentIndex(lis.abx_b.findData(lis.abx_a.currentData()))
    lis.abx_begin()
    asked = [t for kind, t in dialogs.asked if kind == "information"]
    lis.refresh()
    check("abx: the same version as A and B is refused, said", lis.abx is None and asked and "two different" in asked[-1],
          asked)
