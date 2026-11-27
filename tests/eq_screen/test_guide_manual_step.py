"""The Guide's step "Or make it manually" (ui\\guide_eq.py, 2026-11-25): it lights Add filter only while Add filter shows
(An empty EQ in Start from), and its demo (Pasted filters, An EQ file, then Add filter on An empty EQ) keeps the Make the
EQ card at one height while it plays and puts back Start from, its rows and the page's runs when it ends. On Make an EQ
opened as the other screen tests open it (the eq_screen fixture)."""
import time

import pytest

from helpers import qt


@pytest.fixture(autouse=True)
def glide(monkeypatch):
    """Windows' animation effects taken as on, whatever this PC's setting: the demo then plays its actions."""
    from ui import tour
    monkeypatch.setattr(tour, "_animations_on", lambda: True)


def _step(t):
    return next(n for n, st in enumerate(t.steps) if st["title"] == "Or make it manually")


def test_manual_step_lights_add_filter_only_when_it_shows(eq_screen, check):
    from ui import guide
    page = eq_screen.page
    c = page.hand_source
    was = (page.way, c.currentIndex())
    lit = {}
    t = guide.start_eq(page)
    t.all_chk.setChecked(False)
    try:
        for key in ("empty", "paste"):
            page.set_way("hand", remember=False)
            c.setCurrentIndex(c.findData(key))
            qt.pump(60)
            lit[key] = page.hand_add in t.steps[_step(t)]["target"]()
    finally:
        t.end()
        qt.pump(200)
        page.set_way(was[0], remember=False)
        c.setCurrentIndex(was[1])
    check("guide: the step “Or make it manually” lights Add filter with An empty EQ in Start from, and not with "
          "Pasted filters (Add filter hidden there)", lit == {"empty": True, "paste": False}, lit)


@pytest.mark.parametrize("key", ["empty", "paste"])
def test_manual_demo_keeps_the_card_height_and_puts_back(eq_screen, check, key):
    from ui import guide
    page = eq_screen.page
    c = page.hand_source
    was = (page.way, c.currentIndex())
    page.set_way("hand", remember=False)
    c.setCurrentIndex(c.findData(key))
    page.hand_paste.setPlainText("Filter 1: ON PK Fc 300 Hz Gain 2 dB Q 1" if key == "paste" else "")
    qt.pump(100)
    before = (c.currentData(), page.hand_paste.isVisible(), page.hand_add.isVisible(), page.hand_start.text(),
              page.hand_paste.toPlainText(), len(page.session_runs), page.run_result is None)
    t = guide.start_eq(page)
    t.all_chk.setChecked(False)
    heights = set()
    try:
        t.go_to_step(_step(t))
        qt.pump(200)
        h = page.eq_box.height()
        t.speed = 8.0
        t.replay()
        end = time.time() + 60
        while t.demo_running and time.time() < end:
            qt.pump(20)
            heights.add(page.eq_box.height())
        ended, errors = not t.demo_running, list(t.demo_errors)
    finally:
        t.end()
        qt.pump(300)
    after = (c.currentData(), page.hand_paste.isVisible(), page.hand_add.isVisible(), page.hand_start.text(),
             page.hand_paste.toPlainText(), len(page.session_runs), page.run_result is None)
    page.hand_paste.clear()
    page.set_way(was[0], remember=False)
    c.setCurrentIndex(was[1])
    check(f"guide: the demo of “Or make it manually” (Start from on {key}) plays to its end, and the Make the EQ card "
          "keeps one height while it plays", ended and not errors and heights == {h}, (ended, errors, h, heights))
    check(f"guide: after the demo of “Or make it manually” (Start from on {key}), Start from, its rows, Add filter, "
          "the button's words, the pasted text and the page's runs are as before", after == before, (before, after))
