"""Layout items (app\\ui\\__init__.py says why) in Find… and in Make an EQ's page: Find… for a measurement with its
list drawn, and the page built, make no Python object of a layout item, and leave none when they close. (The items of
the app's own layouts, forms.FlowLayout, picker.Lines and listen's rows, are Python's by design: Qt gives each one to
their addItem; helpers.qt.made_item_objects leaves them out.) Until 2026-11-15 each sub-layout went into a layout in a
window with its items, PySide6 kept an object for each item, and the tests crashed now and then with an access
violation: a menu's action in Find… and in the graph of Make an EQ got the object of an item that Qt had deleted. The
tracer's 3 Save row: tests\\tracer\\test_trace_layout_items.py."""
import gc
import os

from helpers import eqpage, qt, session

# (what these windows reach through Make an EQ: for app\tools\relevant_tests.py)
COVERS = ("ui.picker", "ui.forms", "ui.listen", "ui.eq_page", "ui.eq_page_cards", "ui.eq_settings", "eq.service",
          "eq.inputs")


def _types(objs):
    return sorted({type(o).__name__ for o in objs})


def test_find_for_a_measurement_opened_and_closed(tmp_path, check):
    import net
    from ui.picker import Picker
    s = eqpage.open_screen(str(tmp_path))
    seen = {}
    try:
        page = s.page
        net.set_offline(True)
        page.S["library"]["folders"] = [os.path.join(session.SESSION.studio, "samples")]
        before = {id(o) for o in qt.layout_item_objects()}
        pk = Picker(page, "measurement")
        pk.show()
        s.wait_for(lambda: not pk.db.get("loading") and not pk.lib.get("scanning"), 120)
        pk.q.setText("gate")
        pk._later.stop()
        pk.render()
        pk.finish_list()
        made = qt.made_item_objects()
        seen = {"rows": pk.list.count(), "made": len(made), "types": _types(made)}
        del made
        pk.reject()
        qt.close(pk)
        pk = None  # (its Python object let go: what is left after it is the window's own)
        gc.collect()
        left = [o for o in qt.layout_item_objects() if id(o) not in before]
        seen.update(left=len(left), left_types=_types(left))
        del left
    finally:
        eqpage.close_screen(s)
    check("find: Find… for a measurement, its list drawn, has no Python object of a layout item, and leaves none "
          "when it closes", seen.get("rows", 0) > 0 and seen.get("made") == 0 and seen.get("left") == 0, seen)


def test_make_an_eq_built_and_closed(tmp_path, check):
    gc.collect()
    before = {id(o) for o in qt.layout_item_objects()}
    s = eqpage.open_screen(str(tmp_path))
    try:
        made = qt.made_item_objects()
        own = [o for o in qt.layout_item_objects() if id(o) not in before]
        seen = {"made": len(made), "types": _types(made), "own layouts' items": len(own) - len(made)}
        del made, own
    finally:
        eqpage.close_screen(s)
    del s
    gc.collect()
    left = [o for o in qt.layout_item_objects() if id(o) not in before]
    seen.update(left=len(left), left_types=_types(left))
    del left
    check("eq page: Make an EQ's page, built, has no Python object of a layout item (only the items of its own "
          "layouts), and leaves none when it closes",
          seen["made"] == 0 and seen["own layouts' items"] > 0 and seen["left"] == 0, seen)
