"""Make an EQ's Guide (ui\\guide_eq.py): what two of its demos point at and the window one opens, in sight and with
room enough (2026-10-23, found by the restyle's checkers). The “Many results?” demo points at a ⇄ rig tag only once
its row is scrolled into sight in Find… (further down the list, the pointer and the tag's words went past the list's
end), and (2026-10-24) the Source list it shows has its search box with a word typed in it; the “Several measurements
of the same model?” demo asks for Which measurement at least as tall as that window's smallest size and what its
wrapped words need. Then (the recheck): the History demo at the window's smallest, its rows readable; the menus the
Presets and Use on device demos draw, the Guide's menus (a submenu's arrow the real menus' chevron), not its drop-down
lists. On Make an EQ opened as the other screen tests open it (the eq_screen fixture); the demos are only looked at,
as the Guide plays them."""
import time

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
        t.go_to_step(next(n for n, st in enumerate(t.steps) if st["title"] == title))
        t.speed = speed
        t.replay()
        ended = s.wait_for(lambda: not t.demo_running, 60)
        return ended, list(t.demo_errors)
    finally:
        t.end()
        qt.pump(200)


def _made_up_online(page, monkeypatch):
    """Find…'s online entries stood in: 24 of the model on a made-up site, the first twenty without a conversion of
    their own, then four with one (so the first ⇄ is far down the list, as with the real lists)."""
    from ui.picker import Picker
    rigs = page.meta.get("rigs") or {}
    on = "5128" if "5128" in rigs else next(iter(rigs))
    other = next(k for k in rigs if k != on)
    rows = [{"src": "db", "key": f"db:Made-up site|Truthear Gate {n:02d}|in-ear", "id": f"made-up-{n}",
             "name": f"Truthear Gate {n:02d}", "other": False, "sub": "in-ear · Made-up site", "link": None,
             "rig": on, "is_target": False, "form": "", "site": "Made-up site", "how": "",
             "convs": [{"from": other, "models": 12, "error": 1.0, "before": 3.0}] if n >= 20 else None}
            for n in range(24)]
    monkeypatch.setattr(Picker, "db_rows", lambda self, ws: [dict(r) for r in rows])


def test_many_results_points_at_tags_in_sight(eq_screen, check, monkeypatch):
    from PySide6.QtCore import QPoint, QRect
    from PySide6.QtWidgets import QLabel, QListWidget
    from ui import tour
    _made_up_online(eq_screen.page, monkeypatch)
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


def test_many_results_source_list_searched(eq_screen, check, monkeypatch):
    # (2026-10-24, left from the restyle: the Source list this demo shows had the word typed as a row of the list,
    # “🔍  crin”, where the real long list has its search box above its rows)
    from PySide6.QtWidgets import QLabel
    from ui import theme, tour
    _made_up_online(eq_screen.page, monkeypatch)
    seen = []
    real_mock = tour.Api.mock

    def mock(api, near, items, *a, **k):  # (each list the demo shows, read as it opens)
        m = real_mock(api, near, items, *a, **k)
        box = m.findChild(QLabel, "tourMockSearch")
        img = qt.picture(box) if box is not None else None
        darkest = min((img.pixelColor(x, y) for x in range(img.width()) for y in range(img.height())),
                      key=lambda c: c.lightness()).name() if img is not None else None
        seen.append({"box": box.text() if box is not None else None, "darkest": darkest,
                     "above its rows": box is not None and bool(m.rows)
                     and box.geometry().bottom() < m.rows[0].geometry().top(),
                     "rows": [r.text() for r in m.rows]})
        return m
    monkeypatch.setattr(tour.Api, "mock", mock)
    ended, errors = _play(eq_screen, "Many results?")
    last = seen[-1] if seen else {}
    word = (last.get("box") or "").lower()
    ink = [int(theme.tokens()["ink"][k:k + 2], 16) for k in (1, 3, 5)]
    drawn = [int((last.get("darkest") or "#ffffff")[k:k + 2], 16) for k in (1, 3, 5)]
    check("guide: the Source list the “Many results?” demo shows has its search box above its rows, a word typed in "
          "it in the text's colour (typed words, not the box's grey hint), the rows those with the word, as the real "
          "long list's; not a row of the list (“🔍  crin”)",
          ended and not errors and bool(word) and last["above its rows"] and bool(last["rows"])
          and all(word in r.lower() and not r.startswith("🔍") for r in last["rows"])
          and all(abs(a - b) <= 40 for a, b in zip(drawn, ink)), (ended, errors, seen))


def test_which_measurement_demo_asks_for_room(eq_screen, check, monkeypatch):
    from ui import tour
    from ui.compare_window import CompareWindow
    page = eq_screen.page
    asked = {}
    real_window, real_say = tour.Api.window, tour.Api.say

    def window(api, w, near=None, size=None):  # (what the demo asks for, and the window's own smallest height, read
        # before the tour shows it: tour.Api.window takes a demo window's smallest size away, so its frame decides)
        if isinstance(w, CompareWindow):
            asked.update({"size": (size.width(), size.height()) if size is not None else None, "window": w,
                          "its smallest": w.minimumHeight()})
        return real_window(api, w, near, size)

    def say(api, text):  # (by the demo's first words the window has its note: what its words need measured then, once)
        w = asked.pop("window", None)
        if w is not None and asked.get("size"):
            asked["its words need"] = w.layout().totalMinimumHeightForWidth(asked["size"][0])
        return real_say(api, text)
    monkeypatch.setattr(tour.Api, "window", window)
    monkeypatch.setattr(tour.Api, "say", say)
    size = page.size()
    try:
        page.resize(1100, 1000)  # (tall enough that the demo's own limit applies, not 70 % of the window)
        qt.pump(200)
        ended, errors = _play(eq_screen, "More than one measurement of the same model?")
    finally:
        page.resize(size)
        qt.pump(200)
    height = asked["size"][1] if asked.get("size") else 0
    need = max(asked.get("its smallest", 10 ** 6), asked.get("its words need", 10 ** 6))
    check("guide: the “Several measurements of the same model?” demo asks for Which measurement at least as tall as "
          "that window's smallest size and what its wrapped words need (it asked for 640, under its smallest, 660)",
          ended and not errors and height >= need, (ended, errors, asked))


def _history_rows(hw):
    """History's first two rows as laid out now: each one's first line's width, and whether its Show button is under
    that line."""
    from PySide6.QtCore import QPoint
    from PySide6.QtWidgets import QFrame, QLabel, QPushButton
    out = []
    for r in [f for f in hw.scroll.widget().findChildren(QFrame) if type(f) is QFrame][:2]:
        head = next(lab for lab in r.findChildren(QLabel) if "→" in lab.text())
        show = next(b for b in r.findChildren(QPushButton) if b.text() == "Show")
        out.append({"words wide": head.width(), "row": (r.width(), r.height()),
                    "Show under the words": show.mapTo(r, QPoint(0, 0)).y() >= head.mapTo(r, QPoint(0, head.height())).y()})
    return out


def test_history_demo_rows_readable_at_the_smallest(eq_screen, check, monkeypatch):
    # (2026-10-23, the restyle's recheck: at the window's smallest the Guide shows History about 523 px wide, and each
    # row's words were squeezed into a column about 100 px wide beside its buttons)
    from ui import tasks, tour
    from ui.history_window import WORDS_ROOM, HistoryWindow
    page = eq_screen.page
    now = time.time()
    monkeypatch.setattr(page, "history", [
        {"key": f"guide{i}", "base": f"guide{i}", "when": now - i * 3600, "mode": "best_fit", "label": "Best fit",
         "device": "Truthear GATe (Wide Bore Tips) (L800 IEM)", "target": "Diffuse field 5128 -1dB per octave (AutoEq)",
         "saved": True, "filters": [{"type": "PK", "freq": 1000, "gain": 1.0, "q": 1.0}], "n_filters": 1, "rms": 0.5,
         "preamp": -1.0} for i in range(3)])
    shown, seen = [], {}
    real_window, real_at = tour.Api.window, tour.Api.at

    def window(api, w, near=None, size=None):  # (the window the demo shows)
        if isinstance(w, HistoryWindow):
            shown.append(w)
        return real_window(api, w, near, size)

    def at(api, w, *a, **k):  # (its rows read once the demo has pointed at them: shown and laid out by then)
        yield from real_at(api, w, *a, **k)
        if shown and "rows" not in seen and tasks.alive(shown[-1]):
            seen.update(width=shown[-1].width(), rows=_history_rows(shown[-1]))
    monkeypatch.setattr(tour.Api, "window", window)
    monkeypatch.setattr(tour.Api, "at", at)
    size = page.size()
    try:
        page.resize(965, 433)  # (the window at its smallest, the top bar's width: the room the Guide has there)
        qt.pump(200)
        ended, errors = _play(eq_screen, "History")
    finally:
        page.resize(size)
        qt.pump(200)
    rows = seen.get("rows") or []
    check("guide: at the window's smallest, the History demo shows History's rows with words that keep room to be read "
          "(squeezed beside the buttons, they were a column about 100 px wide)",
          ended and not errors and seen.get("width", 10 ** 6) < 640 and len(rows) == 2
          and all(r["words wide"] >= WORDS_ROOM for r in rows), (ended, errors, seen))


def test_menus_drawn_with_the_real_submenu_arrow(eq_screen, check, monkeypatch):
    # (2026-10-23, the restyle's recheck: the menus the Presets and Use on device demos draw wrote a submenu's arrow as
    # a typed “▸”, where the real menus show Windows 11's chevron)
    import re
    from PySide6.QtWidgets import QLabel, QPushButton
    from ui import guide_eq, tasks, theme
    page = eq_screen.page
    # (the Presets step lights the top bar's Presets, so it's in the Guide only when Make an EQ is in the app's window:
    # here the page is on its own, so a Presets button is stood in on it, and the page serves as that window)
    bar = QPushButton("Presets", page)
    bar.move(page.width() - 160, 6)
    bar.show()
    for name, value in (("presets_btn", bar), ("help_btn", bar),
                        ("nav", {k: bar for k in ("eq", "devices", "profiles", "settings")})):
        monkeypatch.setattr(page, name, value, raising=False)
    # (a preset with a long name: the menu is as wide as its longest row, so none of its rows is cut, as the real one)
    monkeypatch.setattr(page, "preset_names", lambda: ["For the website, as listener800 and squig.link draw it"])
    seen, looks = [], []
    real_pick = guide_eq.point_at_menu_row

    def pick(api, m, i, *a, **k):  # (each menu as the demo picks from it: shown for a while, laid out)
        if tasks.alive(m):
            # (the Guide's menu draws a submenu's: tour.Mock; Use on device's has two, Update a profile and Use for 5
            # minutes on)
            arrows = m.findChildren(QLabel, "tourMockArrow")
            labels = [r for r in m.rows if isinstance(r, QLabel)]
            seen.append({"rows": [r.text() for r in labels],
                         "cut": [r.text() for r in labels if r.sizeHint().width() > r.width()],
                         "arrow in": [a.parentWidget().text() for a in arrows],
                         "arrow": bool(arrows) and all(_chevron_right(qt.picture(a)) for a in arrows)})
        yield from real_pick(api, m, i, *a, **k)
        if tasks.alive(m):  # (the row picked is pointed at now: how the menu is drawn, its corner and that row)
            img, r = qt.picture(m), m.row(i).geometry()
            looks.append({"kind": m.property("kind"), "corner": img.pixelColor(0, 0).name(),
                          "edge": img.pixelColor(r.left() + 1, r.center().y()).name(),
                          "fill": img.pixelColor(r.right() - 6, r.center().y()).name()})
    monkeypatch.setattr(guide_eq, "point_at_menu_row", pick)
    try:
        played = {title: _play(eq_screen, title) for title in ("Presets", "Save it, or use it on a device")}
    finally:
        qt.close(bar)
    sheet = eq_screen.qapp.styleSheet()
    url = lambda rule: (re.search(rule + r"\s*\{[^}]*(?:image|pixmap):\s*url\(([^)]*)\)", sheet) or [None, None])[1]
    pictures = (url(r"QLabel#tourMockArrow"), url(r"QMenu::right-arrow"))
    check("guide: the menus the Presets and Use on device demos draw show a submenu's arrow as the app's menus do "
          "(Windows 11's chevron, the same picture), not a typed “▸”; none of their rows is cut (Use on device's cut "
          "“not connected”)",
          all(ended and not errors for ended, errors in played.values()) and len(seen) >= 3
          and not any("▸" in row for s in seen for row in s["rows"]) and not any(s["cut"] for s in seen)
          and any("listener800" in row for s in seen for row in s["rows"])
          and all(s["arrow in"] and set(s["arrow in"]) <= {"Delete a preset", "Update a profile", "Use for 5 minutes on"}
                  and s["arrow"] for s in seen)
          and any(s["arrow in"] == ["Update a profile", "Use for 5 minutes on"] for s in seen)
          and pictures[0] is not None and pictures[0] == pictures[1], (played, seen, pictures))
    # (2026-10-23, the restyle's last merge: these two demos drew their menus with the Guide's list, so they had a
    # drop-down's round corners and the accent's bar beside the row pointed at, where the real menus have neither;
    # test_guide.py checks that the Guide's menu looks as a real one)
    stroke = theme.tokens()["stroke"]
    check("guide: the menus the Presets and Use on device demos draw are the Guide's menus, as the real ones (square "
          "corners, the row pointed at filled without the accent's bar beside it), not a drop-down's list",
          len(looks) >= 3 and all(x["kind"] == "menu" and x["corner"] == stroke and x["edge"] == x["fill"]
                                  for x in looks), (looks, stroke))


def test_use_on_device_demo_rows_as_the_real_menu(eq_screen, check, monkeypatch, tmp_path):
    # (2026-11-11: the demo's Update rows came in the sequence of the profiles, or of Windows' device names, where the
    # real menu has the sequence of its device rows (a nickname too); nothing checked the two, or the cut words)
    import copy
    import os
    from PySide6.QtCore import QPoint, QRect
    from PySide6.QtWidgets import QLabel
    from switcher import devices as D
    from ui import guide_eq, tasks
    page, sw = eq_screen.page, eq_screen.sw
    key, speakers = "Headset|EarPods", "Speakers|Realtek(R) High Definition Audio"
    eps = [D.Endpoint("{5}", "Headset", "EarPods", D.ACTIVE, True),
           D.Endpoint("{6}", "Speakers", "Realtek(R) High Definition Audio", D.ACTIVE, True),
           D.Endpoint("{7}", "TV", "NVIDIA", D.ACTIVE, True)]
    long_name = "Daily, a profile with a long name that the menu cuts in the middle, as the Guide does"[:80]
    headset = copy.deepcopy(sw.record(key))
    seen = []
    real_pick = guide_eq.point_at_menu_row

    def pick(api, m, i, *a, **k):  # (the demo's Use on device menu, and the real one filled at the same time)
        rows = [r.text() for r in m.rows if isinstance(r, QLabel)]
        first = any(r.startswith("Update “") for r in rows) and len(seen) < runs[0]
        if first:
            page._fill_use_menu()
            real = [a.text().replace("&&", "&").replace("\t", "  ·  ") for a in page.use_menu.actions()
                    if not a.isSeparator() and a.menu() is None]
            seen.append({"mock": rows, "real": real})
        yield from real_pick(api, m, i, *a, **k)
        if first and tasks.alive(m):  # (the row pointed at: what the tour draws over its card, the lit parts and the
            # words a demo typed, 2026-11-11: the wider menu put the card over File name and its typed “New EQ”)
            t = api.t
            card = t.bubble.geometry()
            typed = [QRect(e[0].mapTo(t.win, QPoint(0, 0)), e[0].size()) for e in t.typed]
            seen[-1]["over the card"] = [r.getRect() for r in list(t.holes) + typed if r.intersects(card)]
            seen[-1]["card, menu"] = (card.getRect(), m.geometry().getRect())
    runs = [0]
    monkeypatch.setattr(guide_eq, "point_at_menu_row", pick)
    monkeypatch.setattr(sw, "_endpoints", lambda: list(eps))
    sw.refresh(quiet=True)
    made = []
    try:
        # (made in the opposite sequence: the profiles' own sequence is not the menu's)
        for name, on in (("Zeta", "TV|NVIDIA"), (long_name, speakers), ("Night", key)):
            path = os.path.join(str(tmp_path), f"{len(made)}.txt")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("Preamp: -3 dB\nFilter 1: ON PK Fc 1000 Hz Gain 3 dB Q 1\n")
            made.append(sw.import_profile(path, name))
            sw.add_to_device(on, made[-1], switch_on=True)
        played = []
        for nickname in ("", "A TV"):  # (with a nickname, TV is first in the real menu: A to Z by the name shown)
            sw.set_nickname("TV|NVIDIA", nickname)
            runs[0] += 1
            played.append(_play(eq_screen, "Save it, or use it on a device"))
    finally:
        sw.set_nickname("TV|NVIDIA", "")
        for pid in made:
            sw.remove_profile(pid)
        monkeypatch.undo()
        sw.refresh(quiet=True)
        for k in [k for k in sw.s["devices"] if k != key]:
            del sw.s["devices"][k]
        sw.s["devices"][key] = headset
        sw.apply()
    ok = len(seen) == 2
    for s in seen:
        ups = lambda rows: [r for r in rows if r.startswith("Update “")]
        devices = lambda rows: rows[:3]
        s["same"] = (ups(s["mock"]) == ups(s["real"])[:2] and len(ups(s["mock"])) == 2
                     and devices(s["mock"]) == devices(s["real"]))
        s["cut"] = any(r.startswith("Update “Daily, a") and "…" in r for r in ups(s["mock"]))
        ok = ok and s["same"]
    ok = ok and seen[0]["cut"]  # (the long name: on the second device, an Update row of the first play)
    check("guide: the Use on device demo's device rows and Update rows are the real menu's, in its sequence (the "
          "profiles made in the opposite sequence; a device with a nickname first), with the same words, a long name "
          "cut as the menu cuts it",
          ok and all(e and not err for e, err in played)
          and seen[0]["mock"][:3] == ["Headset (EarPods)  ·  active",
                                      "Speakers (Realtek(R) High Definition Audio)  ·  connected",
                                      "TV (NVIDIA)  ·  connected"]
          and seen[1]["mock"][0] == "A TV  ·  connected" and seen[1]["mock"][3].startswith("Update “Zeta”"),
          (played, seen))
    check("guide: while the Use on device demo points at its wide menu, nothing that the Guide draws over its card "
          "(a lit part, a typed name) is under the card",
          len(seen) == 2 and all(s.get("over the card") == [] for s in seen)
          and seen[0]["card, menu"][1][2] > 1000 - 400, seen)  # (the menu wider than the room beside a card)


def _chevron_right(img):
    """Whether a small picture is a chevron pointing right (">": ink in it, none at the middle of its left side, which
    a filled triangle has)."""
    bg = img.pixelColor(0, 0)
    ink = [(x, y) for x in range(img.width()) for y in range(img.height())
           if sum(abs(a - b) for a, b in zip(img.pixelColor(x, y).getRgb()[:3], bg.getRgb()[:3])) > 60]
    if not ink:
        return False
    left, top, bottom = min(x for x, _y in ink), min(y for _x, y in ink), max(y for _x, y in ink)
    return (left + 1, (top + bottom) // 2) not in ink and bottom - top >= 4
