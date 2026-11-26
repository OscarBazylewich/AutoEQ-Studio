"""Make an EQ's page when a run is done, in a window of a usual laptop's height (ui\\eq_page_result.py's _follow_result;
2026-11-15, found by the verifier of the Calculate fault). The result card is scrolled into sight (UI-RULES 30), and
the focus goes back to Calculate. A card taller than the view was centered: Calculate, with the focus, and the card's
top were out of sight (a view of 768 px: Calculate at -71 px; 650 px: -130 px, the card's top at -36 px, measured).
Now the page goes down as far as the card needs, but never past the card's top or past the control with the focus,
when that control is in sight. Round 3 (2026-11-15): the page's last layout before the scroll, the room above a card
higher than the view, a card all in sight that keeps the page where it is, and By hand's Start, which follows the same
rule, as Manually's Add filter does (2026-11-25), at each click. One page for the file (the eq_screen fixture)."""
from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from helpers import qt


def _rect(page, w):
    vp = page.page_area.viewport()
    return QRect(w.mapTo(vp, QPoint(0, 0)), w.size())


def _quick(page):
    page.choose_app("apo")
    page.S["auto"]["enabled"] = False
    page.S["best_fit"].update(filter_counts=[3, 5], random_starts=0, gain_max=[6], q_max=[2], seed_with_site=False)
    page.set_way("auto", remember=False)


def _run_at(eq_screen, size, during=None):
    """A run from a click on Calculate, in sight, with the page at this size; during(page) while the run goes on (the
    job's end read only after it). What shows when the run is done, and where Calculate and the card were when the
    page had scrolled to the result (_follow_result)."""
    page = eq_screen.page
    page.resize(*size)
    qt.pump(200)
    page.activateWindow()
    area = page.page_area
    area.ensureWidgetVisible(page.run_btn, 0, 200)
    qt.pump(60)
    real, scrolled = page._follow_result, []

    def follow():
        real()
        scrolled.append((_rect(page, page.run_btn).top(), _rect(page, page.result_box).top()))
    page._follow_result = follow
    try:
        QTest.mouseClick(page.run_btn, Qt.LeftButton, Qt.NoModifier, QPoint(10, 10))
        if during is not None:
            page._poll.stop()
            qt.pump(50)
            during(page)
            page._poll.start()
        done = eq_screen.wait_for(lambda: page.run_btn.isEnabled(), 180)
        qt.pump(200)
    finally:
        del page._follow_result
    vp = area.viewport().rect()
    f = QApplication.focusWidget()
    card = _rect(page, page.result_box)
    return {"done": done, "focus": f, "focus in sight": f is not None and vp.contains(_rect(page, f)),
            "card top in sight": 0 <= card.top() < vp.height(), "all the card in sight": vp.contains(card),
            "card height": card.height(), "view height": vp.height(), "card top": card.top(),
            "scrolled to": scrolled, "at the end": (_rect(page, page.run_btn).top(), card.top())}


def test_a_run_done_keeps_the_focus_and_the_cards_top_in_sight(eq_screen, check):
    page = eq_screen.page
    _quick(page)
    seen, moved = {}, {}
    try:
        for size in ((1000, 900), (1000, 768), (1000, 650)):
            d = _run_at(eq_screen, size)
            seen[size] = {"done": d["done"], "focus is Calculate": d["focus"] is page.run_btn,
                          "focus in sight": d["focus in sight"], "card top in sight": d["card top in sight"],
                          "all the card in sight in the view of 900 px": size[1] != 900 or d["all the card in sight"]}
            moved[size] = (d["scrolled to"], d["at the end"])
    finally:
        page.resize(1000, 900)
        qt.pump(200)
    check("eq page: a run done, the result card is scrolled into sight with its top, and Calculate, with the focus, "
          "stays in sight, in views of 900, 768 and 650 px (the card was centered, Calculate out of sight)",
          all(all(v.values()) for v in seen.values()), seen)
    # (2026-11-15, round 3: the page scrolled before Qt's last layout for the new result. After the scroll, the graph
    # above Calculate grew 19 px at the first run of a page, and the card moved 10 px up at each run)
    check("eq page: Calculate and the result card stay where the page scrolled them to for the result (the page's "
          "last layout moved them after the scroll: Calculate 10 px to 29 px, the card 10 px up)",
          all(len(s) == 1 and s[0] == end for s, end in moved.values()), moved)


def test_a_focus_out_of_sight_does_not_keep_the_card_away(eq_screen, check):
    # (a control out of sight with the focus at the end, put there by the app and not by a scroll of the page: the
    # card comes into sight from its top all the same, and the page does not go to that control)
    from PySide6.QtWidgets import QPushButton
    page = eq_screen.page
    _quick(page)
    find = next(b for b in page.target_box.findChildren(QPushButton) if b.text() == "Find…")
    try:
        d = _run_at(eq_screen, (1000, 768), during=lambda p: find.setFocus(Qt.OtherFocusReason))
        low = _run_at(eq_screen, (1000, 650), during=lambda p: find.setFocus(Qt.OtherFocusReason))
    finally:
        page.resize(1000, 900)
        qt.pump(200)
    check("eq page: a run done with the focus on a control out of sight (the Target row's Find…, at the page's top), "
          "the result card comes into sight from its top all the same, and the page does not go to that control",
          d["done"] and d["focus"] is find and not d["focus in sight"] and d["card top in sight"],
          {k: v for k, v in d.items() if k != "focus"})
    # (2026-11-15, round 3: the verifier's mutation D3, the card's top at the view's top edge, no test found it.
    # 2026-11-24: this check read the card's top in the view of 768 px, where the card was 704 px high: not higher
    # than the view, but too high for 40 px of room above and below it (704 + 80 > 768), so its top was at 40 px. The
    # line under the card's numbers then went from two lines of text to one: the card 685 px, 685 + 80 < 768, all of
    # it in sight with 40 px under its end and 43 px above its top, as _follow_result intends. So the view of 650 px
    # here, with a check that the card is higher than it: the text of the card can change its height, and the check
    # keeps its meaning)
    check("eq page: in a view of 650 px the result card is higher than the view (what the next check needs)",
          low["done"] and low["card height"] > low["view height"], (low["card height"], low["view height"]))
    check("eq page: a card higher than the view comes into sight with 40 px of room above its top (its title not at "
          "the edge of the view)", low["card top"] == 40, low["card top"])
    # (the view of 768 px: the card with the room of 40 px on each side fits or does not, by the text on the card)
    fits = d["card height"] + 80 <= d["view height"]
    check("eq page: a card that fits in the view with 40 px of room above and below comes into sight with 40 px "
          "under its end, and a card too high for that with 40 px above its top (a view of 768 px)",
          d["view height"] - d["card top"] - d["card height"] == 40 if fits else d["card top"] == 40,
          (fits, d["card top"], d["card height"], d["view height"]))


def test_a_card_in_sight_keeps_the_page_where_it_is(eq_screen, check):
    # (2026-11-15, round 3: the verifier's mutation D4 took the page up to the card's end also when all the card was
    # in sight: 192 px in a window of 1100 px. No test found it. A result first, so that the card is there)
    page = eq_screen.page
    _quick(page)
    area = page.page_area
    bar = area.verticalScrollBar()
    try:
        if page.current()[1] is None:
            _run_at(eq_screen, (1000, 900))
        page.resize(1000, 1100)
        qt.pump(200)
        page.activateWindow()
        bar.setValue(page.run_btn.mapTo(area.widget(), QPoint(0, 0)).y() - 60)  # (Calculate at 60 px, the card under)
        qt.pump(60)
        at, before = bar.value(), area.viewport().rect().contains(_rect(page, page.result_box))
        QTest.mouseClick(page.run_btn, Qt.LeftButton, Qt.NoModifier, QPoint(10, 10))
        done = eq_screen.wait_for(lambda: page.run_btn.isEnabled(), 180)
        qt.pump(200)
        seen = (done, before, at, bar.value(), area.viewport().rect().contains(_rect(page, page.result_box)))
    finally:
        page.resize(1000, 900)
        qt.pump(200)
    check("eq page: a run done with all the result card in sight before and after leaves the page where it is (the "
          "page went up to the card's end)", seen[:2] == (True, True) and seen[2] == seen[3] and seen[4], seen)


def _pasted(n):
    return "\n".join(f"Filter {i + 1}: ON PK Fc {100 + 400 * i} Hz Gain -2 dB Q 1" for i in range(n))


def test_by_hand_keeps_start_and_the_cards_top_in_sight(eq_screen, check):
    # (2026-11-15, round 3: By hand's Start centered a card higher than the view, as Calculate did, measured with 5
    # to 16 filters: Start, with the focus, at -57 px in a view of 768 px and at -116 px in 650 px, the card's top at
    # -22 px in 650 px. Now the rule of a run done: the card from its top, Start kept in sight)
    page = eq_screen.page
    area = page.page_area
    bar = area.verticalScrollBar()
    seen = {}
    try:
        for size in ((1000, 768), (1000, 650)):
            page.resize(*size)
            qt.pump(200)
            page.set_way("hand", remember=False)
            page.hand_source.setCurrentIndex(page.hand_source.findData("paste"))
            page.hand_paste_name.setText("Ten filters")
            page.hand_paste.setPlainText(_pasted(10))
            page.activateWindow()
            y = page.hand_start.mapTo(area.widget(), QPoint(0, 0)).y()
            bar.setValue(max(0, y - area.viewport().height() // 2))  # (Start in the middle of the view)
            qt.pump(60)
            QTest.mouseClick(page.hand_start, Qt.LeftButton, Qt.NoModifier, QPoint(10, 10))
            qt.pump(400)
            vp = area.viewport().rect()
            f = QApplication.focusWidget()
            card = _rect(page, page.result_box)
            seen[size] = {"10 filters": len(page.EDIT) == 10, "card higher than the view": card.height() > vp.height(),
                          "focus is Start": f is page.hand_start, "Start in sight": vp.contains(_rect(page, f)),
                          "card top in sight": 0 <= card.top() < vp.height()}
            page.close_manual()
            qt.pump(100)
    finally:
        page.set_way("auto", remember=False)
        page.resize(1000, 900)
        qt.pump(200)
    check("eq page: By hand's Start (10 pasted filters) shows the card from its top and keeps Start, with the focus, "
          "in sight, in views of 768 and 650 px (the card was centered: Start and the card's top out of sight)",
          all(all(v.values()) for v in seen.values()), seen)


def test_add_filter_keeps_itself_and_the_cards_top_in_sight(eq_screen, check):
    # (2026-11-25: Manually's Add filter, clicked again and again, as its first click starts a manual EQ the way Start
    # does; each later click scrolls the same way, so the new rows come into sight as far as the button allows)
    page = eq_screen.page
    area = page.page_area
    bar = area.verticalScrollBar()
    seen = {}
    try:
        for size in ((1000, 768), (1000, 650)):
            page.session_runs = []
            page.show_run(None)
            page.resize(*size)
            qt.pump(200)
            page.set_way("hand", remember=False)
            page.hand_source.setCurrentIndex(page.hand_source.findData("empty"))
            page.activateWindow()
            y = page.hand_add.mapTo(area.widget(), QPoint(0, 0)).y()
            bar.setValue(max(0, y - area.viewport().height() // 2))
            qt.pump(60)
            for n in range(1, 9):
                QTest.mouseClick(page.hand_add, Qt.LeftButton, Qt.NoModifier, QPoint(10, 10))
                qt.pump(200)
                vp = area.viewport().rect()
                f = QApplication.focusWidget()
                card = _rect(page, page.result_box)
                seen[(size, n)] = {"filters": len(page.EDIT) == n, "one manual EQ": len(page.session_runs) == 1,
                                   "focus is Add filter": f is page.hand_add,
                                   "Add filter in sight": f is not None and vp.contains(_rect(page, f)),
                                   "card top in sight": 0 <= card.top() < vp.height()}
            page.close_manual()
            qt.pump(100)
    finally:
        page.set_way("auto", remember=False)
        page.resize(1000, 900)
        qt.pump(200)
    bad = {k: v for k, v in seen.items() if not all(v.values())}
    check("eq page: Manually's Add filter, clicked 8 times, adds a filter to one manual EQ each time, and keeps itself, "
          "with the focus, and the result card's top in sight, in views of 768 and 650 px", not bad and len(seen) == 16,
          bad or len(seen))
