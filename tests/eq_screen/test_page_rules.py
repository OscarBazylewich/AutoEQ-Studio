"""Make an EQ's page as the UI rules have it (.claude\\notes\\UI-RULES.md, 2026-10-27, the user's ask: the same kind of
thing done the same way everywhere): while a run goes on its Cancel shows at the Run row's end, where nothing moves for
it (beside Run it pushed Run several… and By hand along); the line under Run takes no room until it says something;
the result is scrolled into sight when the run is done, unless you scrolled meanwhile; Remove takes a run off this
session's runs with Undo; By hand's menu lists an EQ's sources in the order every such list has; the result card's
labelled rows line up in one column, and an EQ by hand's Close sits on its title line. One page for the file."""
import pytest

from helpers import eqpage, qt


def _area(page):
    from PySide6.QtWidgets import QScrollArea
    return next(a for a in page.findChildren(QScrollArea) if a.widget() and a.widget().isAncestorOf(page.run_btn))


def _quick(page):
    page.S["auto"]["enabled"] = False
    page.S["best_fit"].update(filter_counts=[3], random_starts=0, gain_max=[6], q_max=[2], seed_with_site=False)


@pytest.fixture(scope="module")
def ran(eq_screen):
    """A run made with the Run button, the page at its Run row first: what each part did while it went on."""
    page = eq_screen.page
    page.choose_app("apo")
    _quick(page)
    area = _area(page)
    bar = area.verticalScrollBar()
    area.ensureWidgetVisible(page.run_btn, 0, 40)
    qt.pump(50)
    idle = (page.progress_text.isVisibleTo(page), page.progress_text.text())
    page.set_way("auto", remember=False)
    xs = [b.mapTo(page, b.rect().topLeft()).x() for b in (page.run_btn, page.queue_btn)]
    at = bar.value()
    page.run_btn.click()
    qt.pump(30)
    during = {"cancel shown": page.cancel_btn.isVisibleTo(page), "line shown": page.progress_text.isVisibleTo(page),
              "others where they were": [b.mapTo(page, b.rect().topLeft()).x()
                                         for b in (page.run_btn, page.queue_btn)] == xs,
              "cancel after them": page.cancel_btn.mapTo(page, page.cancel_btn.rect().topLeft()).x() > xs[-1]}
    eq_screen.wait_for(lambda: page.run_btn.isEnabled(), 180)
    qt.pump(100)
    return {"idle": idle, "during": during, "at": at, "after": bar.value(), "page": page, "area": area}


def test_cancel_at_the_rows_end(ran, check):
    check("eq page: while a run goes on its Cancel shows at the Run row's end and nothing before it moves; the line "
          "under Run takes no room until it says something",
          ran["idle"] == (False, "") and all(ran["during"].values()), (ran["idle"], ran["during"]))


def test_result_scrolled_to(ran, check):
    page, area = ran["page"], ran["area"]
    box = page.result_box
    top = box.mapTo(area.widget(), box.rect().topLeft()).y()
    seen = area.verticalScrollBar().value() <= top <= area.verticalScrollBar().value() + area.viewport().height()
    check("eq page: a run done, its result is scrolled into sight (it appeared below the folds, the page left at Run)",
          ran["after"] != ran["at"] and seen, (ran["at"], ran["after"], top))


def test_not_scrolled_when_you_moved(eq_screen, check):
    page = eq_screen.page
    _quick(page)
    area = _area(page)
    bar = area.verticalScrollBar()
    area.ensureWidgetVisible(page.run_btn, 0, 40)
    qt.pump(50)
    page.run_btn.click()
    qt.pump(30)
    bar.setValue(0)  # (you scrolled up to the graph while it ran)
    eq_screen.wait_for(lambda: page.run_btn.isEnabled(), 180)
    qt.pump(100)
    check("eq page: a run done while you'd scrolled elsewhere leaves the page where you put it (a run takes 7-20 s)",
          bar.value() == 0, bar.value())


def test_remove_a_run_with_undo(eq_screen, check):
    page = eq_screen.page
    if len(page.session_runs) < 2:
        eqpage.quick_run(eq_screen)
    shown, n = page.run_result, len(page.session_runs)
    page.remove_run()
    gone = (len(page.session_runs) == n - 1, page.run_result is not shown, eq_screen.undo_offered())
    eq_screen.undo()
    back = (len(page.session_runs) == n, page.run_result is shown)
    check("eq page: Remove takes the run shown off this session's runs with Undo in the window's line, which puts it "
          "back and shows it again", gone == (True, True, True) and back == (True, True), (gone, back))


def test_by_hand_sources_in_their_order(eq_screen, check):
    page = eq_screen.page
    page.fill_hand_sources()
    c = page.hand_source
    words = [c.itemText(k) for k in range(c.count())]
    check("eq page: By hand's Start from lists an EQ's sources in the order every such list has (an empty EQ, a copy "
          "of the selected EQ, an EQ file, pasted filters), then the devices' profiles",
          words[:4] == ["An empty EQ", "A copy of the selected EQ", "An EQ file", "Pasted filters"]
          and (bool(words[4:]) and all(w.startswith("Profile: ") for w in words[4:])
               or words[4:] == ["A device's profile (none yet)"]), words)


def test_result_card_lines_up(eq_screen, check):
    page = eq_screen.page
    page.start_by_hand([{"type": "PK", "freq": 1000, "gain": 2, "q": 1}], "pasted", "Lines up")
    qt.pump(50)
    widths = {lab.minimumWidth() for lab in (page.runs_lab, page.count_lab, page.name_lab)}
    title_y = page.res_title.mapTo(page.result_box, page.res_title.rect().center()).y()
    close = page.hand_close.mapTo(page.result_box, page.hand_close.rect().center())
    on_title = abs(close.y() - title_y) <= page.hand_close.height() and close.x() > page.res_title.x()
    page.hand_close.click()
    check("eq page: the result card's labelled rows (Runs this session, Fewer or more filters, File name) start their "
          "boxes in one column; an EQ by hand's Close is on the card's title line, away from Runs this session's "
          "Remove", len(widths) == 1 and min(widths) > 0 and on_title, (widths, title_y, close.y()))


def test_settings_and_advanced_line_up_and_head_their_sections(eq_screen, check):
    # (2026-10-27, the pictures' review: with both folds open, Advanced's boxes started 21 px right of Settings', and
    # the folds' section headings ("Best fit", "Scoring" …) were drawn as plain as the labels under them: a card's
    # plain words rule outranked the headings' semibold)
    from PySide6.QtCore import QPoint
    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import QLabel
    page = eq_screen.page
    s = page.settings
    s.fold.btn.setChecked(True)
    s.adv.btn.setChecked(True)
    qt.pump(100)
    try:
        def first_box(form):
            f = next(f for f in form.fields.values() if f.isVisibleTo(page))
            return f.mapTo(page, QPoint(0, 0)).x()
        xs = (first_box(s.form), first_box(s.adv_form))
        heads = [lab for lab in s.adv_form.findChildren(QLabel) if lab.property("role") == "section"]
        weights = sorted({lab.font().weight() for lab in heads})
    finally:
        s.fold.btn.setChecked(False)
        s.adv.btn.setChecked(False)
        qt.pump(50)
    check("page: Settings' and Advanced's boxes start at one place (one label column for both folds), and their "
          "sections' headings are semibold, as every section's heading",
          xs[0] == xs[1] and heads and weights == [QFont.DemiBold], (xs, len(heads), weights))


def test_eq_app_box_as_wide_as_a_forms(eq_screen, check):
    # (2026-10-27, the rules' review: Your EQ app took the card's whole width; Method, under it, its own)
    from ui.forms import CHOICE_MOST
    page = eq_screen.page
    check("page: Your EQ app's box is as wide as its choices, capped as every form's drop-down (not the card's width)",
          page.app_combo.maximumWidth() == CHOICE_MOST and page.app_combo.width() <= CHOICE_MOST,
          (page.app_combo.width(), page.app_combo.maximumWidth()))
