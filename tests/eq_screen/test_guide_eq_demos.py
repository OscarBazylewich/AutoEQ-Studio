"""Make an EQ's Guide (ui\\guide_eq.py): what two of its demos point at and the window one opens, in sight and with
room enough (2026-10-23, found by the restyle's checkers). The “Many results?” demo points at a ⇄ rig tag only once
its row is scrolled into sight in Find… (further down the list, the pointer and the tag's words went past the list's
end); the “Several measurements of the same model?” demo asks for Which measurement at least as tall as that window's
smallest size and what its wrapped words need. On Make an EQ opened as the other screen tests open it (the eq_screen
fixture); the demos are only looked at, as the Guide plays them."""
import pytest

from helpers import qt


@pytest.fixture(autouse=True)
def glide(monkeypatch):
    """Windows' animation effects taken as on, whatever this PC's setting (as test_guide.py has them): the demos then
    move the pointer, which these checks follow."""
    from ui import tour
    monkeypatch.setattr(tour, "_animations_on", lambda: True)


def _play(s, title, speed=8.0):
    """Make an EQ's Guide on the step `title`, its demo played to its end (waited for up to 60 s), then the tour
    ended: (whether it ended, the demos' errors)."""
    from ui import guide
    t = guide.start_eq(s.page)
    t.all_chk.setChecked(False)
    try:
        t.go(next(n for n, st in enumerate(t.steps) if st["title"] == title))
        t.speed = speed
        t.replay()
        ended = s.wait_for(lambda: not t.demo_running, 60)
        return ended, list(t.demo_errors)
    finally:
        t.end()
        qt.pump(200)


def test_many_results_points_at_tags_in_sight(eq_screen, check, monkeypatch):
    from PySide6.QtCore import QPoint, QRect
    from PySide6.QtWidgets import QLabel, QListWidget
    from ui import tour
    from ui.picker import Picker
    page = eq_screen.page
    rigs = page.meta.get("rigs") or {}
    on = "5128" if "5128" in rigs else next(iter(rigs))
    other = next(k for k in rigs if k != on)

    def made_up(n):
        """An online entry of the model: the first twenty without a conversion of their own, then four with one (so
        the first ⇄ is far down the list, as with the real lists)."""
        return {"src": "db", "key": f"db:Made-up site|Truthear Gate {n:02d}|in-ear", "id": f"made-up-{n}",
                "name": f"Truthear Gate {n:02d}", "other": False, "sub": "in-ear · Made-up site", "link": None,
                "rig": on, "is_target": False, "form": "", "site": "Made-up site", "how": "",
                "convs": [{"from": other, "models": 12, "error": 1.0, "before": 3.0}] if n >= 20 else None}
    rows = [made_up(n) for n in range(24)]
    monkeypatch.setattr(Picker, "db_rows", lambda self, ws: [dict(r) for r in rows])
    seen = []
    real_move = tour.Api.move_to

    def move_to(api, w, *a, **k):  # (where a ⇄ tag is, in its list, as the pointer sets off for it)
        if isinstance(w, QLabel) and "⇄" in w.text():
            lst = w.parentWidget()
            while lst is not None and not isinstance(lst, QListWidget):
                lst = lst.parentWidget()
            vp = lst.viewport()
            r = QRect(w.mapTo(vp, QPoint(0, 0)), w.size())
            seen.append({"in sight": vp.rect().contains(r), "tag": r.getRect(), "list shows": vp.rect().getRect()})
        return real_move(api, w, *a, **k)
    monkeypatch.setattr(tour.Api, "move_to", move_to)
    ended, errors = _play(eq_screen, "Many results?")
    check("guide: the “Many results?” demo points at a ⇄ rig tag only once its row is in sight in Find… (further down "
          "the list, the pointer and the tag's words went past the list's end)",
          ended and not errors and bool(seen) and all(s["in sight"] for s in seen), (ended, errors, seen))


def test_which_measurement_demo_asks_for_room(eq_screen, check, monkeypatch):
    from ui import tour
    from ui.compare_window import CompareWindow
    page = eq_screen.page
    asked = {}
    real_window, real_say = tour.Api.window, tour.Api.say

    def window(api, w, near=None, size=None):  # (what the demo asks for)
        if isinstance(w, CompareWindow):
            asked.update(size=(size.width(), size.height()) if size is not None else None, window=w)
        return real_window(api, w, near, size)

    def say(api, text):  # (by the demo's first words the window has its note: what it needs measured then, once)
        w = asked.pop("window", None)
        if w is not None and asked.get("size"):
            asked["its smallest"] = w.minimumHeight()
            asked["its words need"] = w.layout().totalMinimumHeightForWidth(asked["size"][0])
        return real_say(api, text)
    monkeypatch.setattr(tour.Api, "window", window)
    monkeypatch.setattr(tour.Api, "say", say)
    size = page.size()
    try:
        page.resize(1100, 1000)  # (tall enough that the demo's own limit applies, not 70 % of the window)
        qt.pump(200)
        ended, errors = _play(eq_screen, "Several measurements of the same model?")
    finally:
        page.resize(size)
        qt.pump(200)
    height = asked["size"][1] if asked.get("size") else 0
    need = max(asked.get("its smallest", 10 ** 6), asked.get("its words need", 10 ** 6))
    check("guide: the “Several measurements of the same model?” demo asks for Which measurement at least as tall as "
          "that window's smallest size and what its wrapped words need (it asked for 640, under its smallest, 660)",
          ended and not errors and height >= need, (ended, errors, asked))
