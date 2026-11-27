"""Make the EQ's two ways (ui\\eq_page_cards.py's _eq_card, eq_page_result.py's set_way; the user's ask, 2026-10-27:
choosing an automatic EQ or one made by hand should be the first thing in the card, not a small By hand menu at the
end of the Run row): the tabs come first; Your EQ app under them in both; only the chosen way's steps shown (Method,
Search, Run; or Start from, Start); the three parts' labels in one column; the tab you click kept for the next start
(not a switch the app makes: a run shows Automatically, an EQ by hand begun elsewhere By hand); the main button's
words for each Start from item ("Import an EQ file…" for an EQ file, else "Start"; 2026-11-25), Add filter only with An
empty EQ, the Name and Filters boxes only on Manually with Pasted filters, and the card's height that only they change;
what's needed first said in a bubble. One page for the file (the eq_screen fixture)."""
from PySide6.QtCore import QPoint

from helpers import eqpage, qt


def _y(page, w):
    return w.mapTo(page, QPoint(0, 0)).y()


def _x(page, w):
    return w.mapTo(page, QPoint(0, 0)).x()


def test_the_way_first_and_only_its_steps(eq_screen, check):
    page = eq_screen.page
    was = page.way
    shown, folds = {}, set()
    try:
        for way in ("auto", "hand"):
            page.set_way(way, remember=False)
            qt.pump(30)
            shown[way] = {"tab": [k for k, b in page.way_btns.items() if b.isChecked()],
                          "app": page.app_combo.isVisibleTo(page),
                          "run": page.run_btn.isVisibleTo(page) and page.mode_combo.isVisibleTo(page),
                          "start": page.hand_start.isVisibleTo(page) and page.hand_source.isVisibleTo(page)}
            folds.add((_y(page, page.settings.fold), _y(page, page.settings.adv)))
        under_app = all(_y(page, page.app_combo) < _y(page, b) for b in page.way_btns.values())
        lined_up = _x(page, page.way_btns["auto"]) == _x(page, page.app_combo) - page.app_combo.x() +             page._way_labels[0].x()
        page.set_way("auto", remember=False)
        qt.pump(30)
        column = {_x(page, page.app_combo), _x(page, page.mode_combo)}
        page.set_way("hand", remember=False)
        qt.pump(30)
        column.add(_x(page, page.hand_source))
    finally:
        page.set_way(was, remember=False)
    # (the UI audit, 2026-11-08: Your EQ app above the tabs, as it is for the two; the tabs' words start at the labels'
    # left edge; the card as high with either tab, so Settings, More settings and the cards under them do not move)
    check("make the EQ: Your EQ app first, then the two ways as tabs (their words lined up with the labels), then only "
          "the chosen way's steps (Method and Calculate, or Start from and Start), their boxes in one column; Settings "
          "and More settings in one place with either tab",
          under_app and lined_up and shown == {"auto": {"tab": ["auto"], "app": True, "run": True, "start": False},
                                               "hand": {"tab": ["hand"], "app": True, "run": False, "start": True}}
          and len(column) == 1 and len(folds) == 1, (under_app, lined_up, shown, column, folds))


def test_the_tab_you_click_is_kept(eq_screen, check):
    page, sw = eq_screen.page, eq_screen.sw
    was, kept = page.way, sw.s.get("make_way")
    try:
        page.way_btns["hand"].click()
        clicked = sw.s.get("make_way")
        page.set_way("auto", remember=False)  # (as a run shows it)
        shown = sw.s.get("make_way")
        page.start_manual([], "from scratch")  # (as Profiles' Edit in Make an EQ begins one)
        by_hand = page.way
    finally:
        page.session_runs = []
        page.show_run(None)
        page.set_way(was, remember=False)
        if kept is None:
            sw.s.pop("make_way", None)
        else:
            sw.s["make_way"] = kept
    check("make the EQ: the tab you click is kept for the next start; one the app shows (a run, an EQ by hand begun "
          "elsewhere) isn't, and an EQ by hand shows By hand", (clicked, shown, by_hand) == ("hand", "hand", "hand"),
          (clicked, shown, by_hand))


def test_a_run_shows_automatically(eq_screen, check):
    page = eq_screen.page
    was = page.way
    page.set_way("hand", remember=False)
    try:
        eqpage.quick_run(eq_screen)
        way = page.way
    finally:
        page.set_way(was, remember=False)
    check("make the EQ: a run (Run, or Retry from the result card) shows Automatically, where its progress and Cancel "
          "are", way == "auto", way)


def test_start_says_what_it_asks_and_what_it_needs(eq_screen, dialogs, check):
    page = eq_screen.page
    was = (page.way, page.hand_source.currentIndex())
    try:
        page.set_way("hand", remember=False)
        words, parts = {}, {}
        for key in ("empty", "copy", "file", "paste"):
            page.hand_source.setCurrentIndex(page.hand_source.findData(key))
            words[key] = page.hand_start.text()
            parts[key] = (page.hand_add.isVisibleTo(page), page.hand_paste.isVisibleTo(page),
                          page.hand_paste_name.isVisibleTo(page))
        page.set_way("auto", remember=False)
        parts["paste, on Automatically"] = (page.hand_add.isVisibleTo(page), page.hand_paste.isVisibleTo(page),
                                            page.hand_paste_name.isVisibleTo(page))
        page.set_way("hand", remember=False)
        page.session_runs = []
        page.show_run(None)
        page.hand_source.setCurrentIndex(page.hand_source.findData("copy"))
        n = len(dialogs.asked)
        page.hand_start.click()
        told = dialogs.asked[n:]
        nothing = page.current()[1] is None
    finally:
        page.set_way(was[0], remember=False)
        page.hand_source.setCurrentIndex(was[1])
    check("make the EQ: Manually's main button reads “Import an EQ file…” for an EQ file (it asks for the file), "
          "else “Start”; a copy of the selected EQ with none on the result card says so in a bubble at Start, and "
          "starts nothing",
          words == {"empty": "Start", "copy": "Start", "file": "Import an EQ file…", "paste": "Start"}
          and [k for k, _t in told] == ["bubble"] and told[0][1] == "No EQ in results yet. Calculate one first or start from a different item." and nothing,
          (words, told, nothing))
    check("make the EQ: Add filter shows only with An empty EQ, and the Name and Filters boxes only on Manually with "
          "Pasted filters",
          parts == {"empty": (True, False, False), "copy": (False, False, False), "file": (False, False, False),
                    "paste": (False, True, True), "paste, on Automatically": (False, False, False)}, parts)


def test_card_height_with_each_item(eq_screen, check):
    from ui.eq_page_result import HAND_SOURCES
    page = eq_screen.page
    was = (page.way, page.hand_source.currentIndex())
    height = {}

    def measure(state):
        qt.pump(60)
        height[state] = page.eq_box.height()
    try:
        page.set_way("auto", remember=False)
        measure("Automatically")
        page.set_way("hand", remember=False)
        c = page.hand_source
        for key in ("empty", "copy", "file", "profile"):
            c.setCurrentIndex(c.findData(key) if key != "profile" else len(HAND_SOURCES))  # (the first profile)
            measure(key)
        c.setCurrentIndex(c.findData("paste"))
        measure("paste")
        page.set_way("auto", remember=False)
        measure("Automatically, paste still selected")
        page.resize(841, 900)
        page.set_way("hand", remember=False)
        qt.pump(250)
        bar = page.page_area.horizontalScrollBar()
        sideways = (bar.maximum(), page.hand_paste.mapTo(page.eq_box, QPoint(0, 0)).x() + page.hand_paste.width()
                    <= page.eq_box.width())
    finally:
        page.resize(1000, 900)
        page.set_way(was[0], remember=False)
        page.hand_source.setCurrentIndex(was[1])
        qt.pump(100)
    one = {k: v for k, v in height.items() if k != "paste"}
    check("make the EQ: the card has one height on Automatically and on Manually with An empty EQ, a copy, an EQ file "
          "and a profile, also on Automatically with Pasted filters still selected; only Manually with Pasted filters "
          "is higher (its Name and Filters boxes)", len(set(one.values())) == 1 and height["paste"] > height["empty"],
          height)
    check("make the EQ: with Pasted filters in the smallest window (841 px) the page has no sideways scroll, and the "
          "Filters box ends inside the card", sideways == (0, True), sideways)
