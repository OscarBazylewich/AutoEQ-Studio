"""Make an EQ with a result in the window's smallest width (ui\\eq_page_parts.py's WrapRow, used for the filters' tools
of the result card in ui\\eq_page_cards.py; 2026-11-16). The tools (Table, Sliders, Add filter, Sort, Undo all, Show
the graph while you edit, Calculate from these filters) were a plain row that needed 869 px, and the card has 779 px
of room in a window 841 px wide: the page scrolled sideways by 90 px, and Calculate from these filters was out of view
(measured). Now the row takes a second line when it does not fit: the tick box and Calculate from these filters go
there together (the tick box at the left end, the button at the card's right end), not the button alone (the user,
2026-11-16: one button on a line did not look good). In the smallest window the page has no sideways scroll and each
tool is in view, in light and in dark, with the table, the sliders and a manual EQ; in a wider window the row is on
one line, each tool where a plain row puts it. One page for the file (the eq_screen fixture)."""
from PySide6.QtCore import QPoint, QRect
from PySide6.QtWidgets import QPushButton, QWidget

from helpers import eqpage, qt

# (what the page reaches that the imports here do not show: for app\tools\relevant_tests.py)
COVERS = ("ui.eq_page_parts", "ui.eq_page_cards")

# (px: the main window's smallest width with Make an EQ shown, at 100 % scale, where the page's view is 829 px wide:
# measured 2026-11-16; and a width where the tools fit on one line: they do from 931 px)
NARROW, WIDE = 841, 1000
SIZE = (1000, 900)  # (the page's size in the eq_screen fixture)
TWO_LINES = [0, 0, 0, 0, 0, 1, 1]  # (each tool's line when the row does not fit on one: _tools' sequence)


def _tools(page):
    """The filters' tools, in the sequence the page makes them."""
    named = {b.text(): b for b in page.result_box.findChildren(QPushButton)}
    return [page.view_btns["table"], page.view_btns["sliders"], named["Add filter"], named["Sort"], page.revert_btn,
            page.live_check, page.retry_btn]


def _lines(rects):
    """The line of each rect (0: the first): two are on one line when their middles are 3 px or less apart (a tick
    box is lower than a button, in the middle of its line's height)."""
    middles = []
    for r in rects:
        if not any(abs(r.center().y() - m) <= 3 for m in middles):
            middles.append(r.center().y())
    middles.sort()
    return [next(i for i, m in enumerate(middles) if abs(r.center().y() - m) <= 3) for r in rects]


def _seen(page, width):
    """The page at this width with the tools scrolled into view (up and down only): its sideways scroll, and where
    each tool is."""
    page.resize(width, 760)
    qt.pump(250)
    area = page.page_area
    area.ensureWidgetVisible(page.view_btns["table"], 0, 100)
    bar = area.horizontalScrollBar()
    bar.setValue(0)
    qt.pump(50)
    vp, tools = area.viewport(), _tools(page)
    rects = [QRect(w.mapTo(vp, QPoint(0, 0)), w.size()) for w in tools]
    gaps = [b.left() - a.left() - a.width() for a, b in zip(rects, rects[1:])]
    return {"sideways scroll": bar.maximum(), "view": vp.width(), "page needs": area.widget().minimumSizeHint().width(),
            "in view": [vp.rect().contains(r) for r in rects], "lines": _lines(rects), "gaps": gaps,
            "x": [r.left() for r in rects],
            "Show the graph while you edit at the left end": rects[5].left() == rects[0].left(),
            "Calculate from these filters at the right end": page.retry_btn.geometry().right()
            == page.name_edit.geometry().right()}


def _fits_on_two_lines(d):
    return (d["sideways scroll"] == 0 and d["page needs"] <= d["view"] and all(d["in view"])
            and d["lines"] == TWO_LINES and d["Show the graph while you edit at the left end"]
            and d["Calculate from these filters at the right end"])


def _run(eq_screen):
    page = eq_screen.page
    if page.run_result is None or page.run_result.get("mode") != "best_fit":
        page.choose_app("apo")
        page.set_way("auto", remember=False)
        eqpage.quick_run(eq_screen)
    return page


def test_no_sideways_scroll_at_the_smallest_width(eq_screen, check):
    page = _run(eq_screen)
    seen = {}
    try:
        for theme in ("light", "dark"):
            (qt.dark if theme == "dark" else qt.light)(eq_screen.qapp)
            for view in ("table", "sliders"):
                page.set_view(view, remember=False)
                seen[f"{theme}, {view}"] = _seen(page, NARROW)
    finally:
        qt.light(eq_screen.qapp)
        page.set_view("table", remember=False)
        page.resize(*SIZE)
        qt.pump(200)
    check("eq page: with a result in the window's smallest width (841 px), Make an EQ has no sideways scroll, and each "
          "of the filters' tools is in view, Show the graph while you edit and Calculate from these filters together on "
          "a second line (the tick box at its left end, the button at the card's right end): in light and in dark, with "
          "the table and with the sliders (the tools were one row of 869 px in 779 px of room: the page scrolled "
          "sideways by 90 px)",
          len(seen) == 4 and all(_fits_on_two_lines(d) for d in seen.values()), seen)


def test_a_manual_eq_at_the_smallest_width(eq_screen, check):
    page = _run(eq_screen)
    try:
        page.start_manual([], "from scratch")
        qt.pump(100)
        seen = _seen(page, NARROW)
    finally:
        page.close_manual()
        page.set_way("auto", remember=False)
        page.resize(*SIZE)
        qt.pump(200)
    check("eq page: a manual EQ in the window's smallest width has no sideways scroll, and each of the filters' tools "
          "is in view, on two lines (the tick box and Calculate from these filters on the second)",
          _fits_on_two_lines(seen), seen)


def test_the_tools_on_one_line_in_a_wider_window(eq_screen, check):
    page = _run(eq_screen)
    try:
        seen = _seen(page, WIDE)
    finally:
        page.resize(*SIZE)
        qt.pump(200)
    s = page.result_box.layout().spacing()
    # (a plain row's: its spacing between two tools, 8 px more after each tab, and 12 px more between the groups)
    plain = [s + 8, s + 20, s, s, s + 12]
    check("eq page: in a window 1000 px wide the filters' tools are on one line, each where a plain row puts it (8 px "
          "more after each tab, 12 px more between the groups), Calculate from these filters at the card's right end, "
          "and the page has no sideways scroll",
          seen["sideways scroll"] == 0 and all(seen["in view"]) and seen["lines"] == [0] * 7
          and seen["gaps"][:5] == plain and seen["Calculate from these filters at the right end"],
          {**seen, "a plain row's gaps": plain})


def test_the_tools_keep_their_sequence_on_two_lines(eq_screen, check):
    page = _run(eq_screen)
    tools = _tools(page)
    try:
        seen = _seen(page, NARROW)
    finally:
        page.resize(*SIZE)
        qt.pump(200)
    read = sorted(range(len(tools)), key=lambda i: (seen["lines"][i], seen["x"][i]))
    chain, w = [], tools[0]
    for _ in range(len(page.findChildren(QWidget)) + 1):  # (once round the page's Tab sequence at most)
        chain += [i for i, t in enumerate(tools) if w is t]
        w = w.nextInFocusChain()
        if w is tools[0]:
            break
    check("eq page: on two lines the filters' tools keep their sequence (from left to right, then the second line), "
          "and the Tab sequence follows it: Table, Sliders, Add filter, Sort, Undo all, then on the second line Show "
          "the graph while you edit, Calculate from these filters",
          seen["lines"] == TWO_LINES and read == list(range(7)) and chain == list(range(7)),
          {"as read": read, "Tab sequence": chain, "lines": seen["lines"], "x": seen["x"]})
