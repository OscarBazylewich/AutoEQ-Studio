"""The Tab key in the tracer (ui\\trace_window.py). README.txt tells this to the user, in the paragraph about Tab
of THE WINDOW: in the tracer, Tab goes only to the text boxes, the lists, the slider, and the buttons Open image…,
Remove image and Guide. So a change of the focus policy of a control of the tracer must change README.txt too.
The buttons, the tabs and the tick boxes of the side take no focus on purpose (_no_focus: Space stays the
picture's; with the focus on it, Add as measurement took Space and added the curve), nor do the zoom buttons on the
picture.
Measured 2026-11-22 with real Tab keys on the app's sample graph with 2 traced curves, from the picture (where the
app puts the focus after a new picture):
  1 Axes   the 4 boxes of the red and blue lines
  2 Trace  the slider Color tolerance and the name box of each curve
  3 Save   Name, Points in each octave, The graph shows, Target of the graph, the 2 boxes of Save from (Hz)
then, on each tab, Open image…, Remove image and Guide. The side had 9, 19 and 7 buttons and tick boxes in sight
on these tabs, and Tab went to none. (The side's scroll area takes one Tab key too: it is not a control, and it is
not checked.) Only real keys measure this: no Python call of nextInFocusChain (AGENTS.md)."""
import shiboken6
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QAbstractButton, QApplication, QComboBox, QLineEdit, QSlider

from helpers import qt
from ui.trace_window import sample_image

COVERS = ("ui.eq_page",)  # (the window is opened for Make an EQ's page)
KINDS = (QLineEdit, QComboBox, QSlider)  # (a text box, a list, a slider)


def _key(w):
    return shiboken6.getCppPointer(w)[0]


def _name(w):
    """A control as a check's detail names it: its class and its words."""
    words = w.text() if isinstance(w, QAbstractButton) else ""
    return f"{type(w).__name__} {(words or w.accessibleName() or w.toolTip())[:40]!r}"


def _tab_stops(tw):
    """The controls that real Tab keys give the focus to, from the picture, until the focus comes to one again."""
    tw.activateWindow()
    qt.pump(120)
    tw.stage.setFocus(Qt.OtherFocusReason)  # (as focus_picture does after a new picture)
    qt.pump(30)
    stops, seen = [], set()
    for _ in range(60):
        QTest.keyClick(QApplication.focusWidget() or tw, Qt.Key_Tab)
        qt.pump(20)
        w = QApplication.focusWidget()
        if w is None or w.window() is not tw or _key(w) in seen:
            break
        seen.add(_key(w))
        stops.append(w)
    return stops


def test_tab_in_the_tracer_goes_to_boxes_lists_and_sliders_but_to_no_button_of_the_side(eq_screen, check):
    page = eq_screen.page
    page.open_trace()
    tw = page.tracer
    img, _truth = sample_image()
    tw.load_image(img, "Sample IEM")
    eq_screen.wait_for(lambda: not tw.reading and not tw.loading, 60)
    tw.t.v.update(d1="90", d2="40")
    for _ in range(2):
        tw.t.auto_trace()
    tw.t.cur = 0
    tw.set_shows("difference")  # (3 Save then shows its third list, Target of the graph)
    tw.changed()
    side = tw.side_scroll.widget()
    top = [tw.open_btn, tw.remove_btn, tw.guide_btn]
    zoom = list(tw.stage.zoom_btns.values())
    # (a control of each tab that must be among those in sight: the checks below are not empty)
    known = ((tw.boxes["d1"], tw.detect_btn, tw.snap), (tw.tol, tw.auto_btn, tw.dashed),
             (tw.shows, tw.save_btn, tw.auto_on))
    seen, to_each, to_no_button = {}, True, True
    for i, tab in enumerate(("1 Axes", "2 Trace", "3 Save")):
        tw.show_tab(i)
        qt.pump(80)
        stops = _tab_stops(tw)
        got = {_key(w) for w in stops}
        in_sight = [w for w in side.findChildren(QAbstractButton) + [x for k in KINDS for x in side.findChildren(k)]
                    if w.isVisible() and w.isEnabled()]
        wanted = [w for w in in_sight if isinstance(w, KINDS)]
        buttons = [w for w in in_sight if isinstance(w, QAbstractButton)]  # (also the tabs and the tick boxes)
        in_side = [w for w in stops if side.isAncestorOf(w)]
        others = [w for w in stops if not side.isAncestorOf(w) and w is not tw.side_scroll]
        box, button, tick = known[i]
        to_each = (to_each and {_key(w) for w in in_side} == {_key(w) for w in wanted} and _key(box) in got
                   and {_key(w) for w in others} == {_key(w) for w in top})
        to_no_button = (to_no_button and not [w for w in buttons + zoom if _key(w) in got]
                        and all(any(b is w for w in buttons) for b in (button, tick, *tw.tab_btns))
                        and all(z.isVisible() and z.isEnabled() for z in zoom))
        seen[tab] = {"Tab went to": [_name(w) for w in stops],
                     "boxes, lists and sliders in sight": [_name(w) for w in wanted],
                     "buttons and tick boxes of the side in sight": len(buttons),
                     "of them, Tab went to": [_name(w) for w in buttons + zoom if _key(w) in got]}
    tw.set_shows("measurement")
    tw.comp.setCurrentIndex(0)
    tw.remove_image()
    tw.close()
    check("tracer: on 1 Axes, 2 Trace and 3 Save, real Tab keys go to each text box, list and slider of the side, "
          "then to Open image…, Remove image and Guide, and to no other control (README.txt tells this)",
          to_each, seen)
    check("tracer: real Tab keys go to no button, tab or tick box of the side, and to no zoom button on the picture",
          to_no_button, seen)
