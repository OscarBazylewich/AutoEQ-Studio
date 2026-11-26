"""Layout items (app\\ui\\__init__.py says why) in the tracer: its 3 Save card, whose type of graph changes again
and again (the add button gets a new name, and the row "Target of the graph" shows and hides; until 2026-11-16,
show_save_row put the main one of two add buttons first: Qt deleted and made again the items of the row), makes no
Python object of a layout item and leaves none that no layout holds. (The items of the app's own layouts, forms.FlowLayout in
the page's settings and eq_page_parts.WrapRow in its result card, are Python's by design:
helpers.qt.made_item_objects leaves them out.) Until 2026-11-15 the row
went into its card with its items, PySide6 kept an object for each, and the tests crashed now and then with an access
violation: a new Qt object got the object of an item that Qt had deleted. Find… and Make an EQ's page:
tests\\eq_screen\\test_layout_items.py."""
from helpers import qt
from helpers.tracer_reads import ok_read

# (what the window reaches through Make an EQ: for app\tools\relevant_tests.py)
COVERS = ("ui.trace_window", "ui.trace_core", "ui.trace_auto", "ui.ocr", "ui.eq_page", "eq.service", "eq.inputs")
ENTRY = {"name": "Truthear Gate", "tag": "Hangout 5128", "site": "Hangout.Audio", "link": "https://example.invalid/x"}


def _types(objs):
    return sorted({type(o).__name__ for o in objs})


def test_tracer_save_row_changed_again_and_again(eq_screen, monkeypatch, check):
    # (the file's page, open until after its last test: what the tracer and the page made is still there when the
    # check after each test (tests\conftest.py) looks)
    from ui import trace_core
    from ui.trace_window import sample_image
    monkeypatch.setattr(trace_core, "auto_read", ok_read())
    page = eq_screen.page
    page.open_trace()
    tw = page.tracer
    img, _s = sample_image()
    firsts, rows = [], []
    for _round in range(4):
        for kind in ("measurement", "target", "measurement"):
            # (an entry from Find a measurement, then from Find a target: the add button of 3 Save has its name)
            tw.load_image(img, entry=dict(ENTRY, **{"as": kind}))
            qt.wait_for(lambda: not tw.loading and not tw.reading_graph and tw.read_ok is not None, 60)
            tw.show_tab(2)
            qt.pump(20)
            firsts.append({"Add as target": "target", "Add as measurement": "measurement"}.get(
                tw.save_btn.text() if tw.save_btns.indexOf(tw.save_btn) == 0 else "", "?"))
            rows.append(tw.comp.isVisible())
            # (the user selects a difference from a target: the row of "Target of the graph" shows)
            i = tw.shows.findData("difference")
            tw.shows.setCurrentIndex(i)
            tw.shows.activated.emit(i)
            qt.pump(20)
            rows.append(tw.comp.isVisible())
            tw.remove_image()
    stale, made = qt.stale_layout_items(), qt.made_item_objects()
    seen = {"main actions": firsts, "stale": len(stale), "made": len(made), "types": _types(made),
            "the row of the target": rows}
    del stale, made
    tw.set_shows("measurement")  # (the page's tracer stays for the tests after this one: the type of a new tracer)
    tw.close()
    check("tracer: 3 Save's row with its main action changed 12 times (as measurement, as target, as measurement) "
          "leaves no layout item object that no layout holds",
          seen.get("stale") == 0 and seen.get("main actions") == ["measurement", "target", "measurement"] * 4
          and seen.get("the row of the target") == [False, True] * 12, seen)
    check("tracer: the tracer with a picture and its 3 Save row has no Python object of a layout item",
          seen.get("made") == 0, seen)
