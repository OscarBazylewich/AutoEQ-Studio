"""3 Save of the tracer (ui\\trace_window.py): "The graph shows" is one question with 4 types of graph (the user,
2026-11-16; before, the list had "Frequency response (not compensated)" and "Difference from <target>", and the type
"a target line" was one of two add buttons; the fourth type, "A target line as the difference from a target", is
that list's "Difference from <target>" with Add as target). The 4 choices in their order; "Target of the graph", in
sight only for the 2 types with a difference from a target; the one add button, whose name follows the list; the
gray line under it; the files that each type sends to the app and that Save .txt… writes; a difference with no
target; the selection that the app makes (an entry from Find a target, a target line alone, a measurement from a
website) and that the user can change; the Guide's demo of the list; Save .txt… for a target line alone; and the
targets of the app that change while the tracer is open. With the app's sample graph and a drawn look-alike of a
website's target (helpers.website_graph)."""
import math
import os

import numpy as np
import shiboken6
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QImage
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QFileDialog

from helpers import paths, qt
from helpers.tracer_reads import ok_read, save_row
from ui.trace_window import sample_image

# (what the window reaches through Make an EQ: for app\tools\relevant_tests.py)
COVERS = ("ui.trace_core", "ui.trace_auto", "ui.ocr", "ui.eq_page", "ui.guide_trace", "ui.tour", "eq.service",
          "eq.inputs", "a11y")
TARGET = paths.SAMPLE_TARGET
ENTRY = {"name": "Truthear Gate", "tag": "Hangout 5128", "site": "Hangout.Audio", "link": "https://example.invalid/x"}
CHOICES = [("measurement", "A measurement"), ("difference", "A measurement as the difference from a target"),
           ("target", "A target line"), ("target_difference", "A target line as the difference from a target")]
DIFFERENCES = ("difference", "target_difference")  # (the types with "Target of the graph")
AS_TARGET = ("target", "target_difference")  # (the types whose add button is Add as target)
NB = "\N{NO-BREAK SPACE}"  # (between a tab's number and its name in the tracer's words)
WHAT = {"measurement": "Saves the curve as a measurement without altering it",
        "difference": "Adds the selected target to the curve and saves it as a measurement",
        "target": "Saves the curve as a target without altering it",
        "target_difference": "Adds the graph's target to the curve and saves the result as a new target"}
WHAT_2 = {"measurement": "Saves all curves as one measurement without altering them",
          "difference": "Adds the selected target to each curve and saves them as one measurement",
          "target": f"Saves only the curve selected in 2{NB}Trace as a target, without altering it",
          "target_difference": f"Adds the graph's target to the curve selected in 2{NB}Trace and saves it as a new "
                               "target"}
SELECT = "Choose a target under “Target of the graph” to add it to the curve"
NO_TARGETS = "No targets available. Add one on Make an EQ via Find… or Add… next to Target."
FIRST_ROW = "Select target…"  # ("Target of the graph": its gray placeholder with targets in the app, not a row)
NO_TARGET_ROW = "No targets available"  # (its gray placeholder with no target in the app)


def _comp_shows(tw):
    """What "Target of the graph" shows: its gray placeholder while nothing is selected, else the selected row."""
    c = tw.comp
    return c.placeholderText() if c.currentIndex() < 0 else c.currentText()


def _select(box, value):
    """A row of a list selected as the user selects it (the list's signal of a selection)."""
    i = box.findData(value)
    box.setCurrentIndex(i)
    box.activated.emit(i)


def _sample(eq_screen, curves):
    """The tracer of the page on the app's sample graph, its dB values typed, `curves` curves traced, 3 Save in
    sight; "The graph shows" as in a new tracer."""
    page = eq_screen.page
    page.open_trace()
    tw = page.tracer
    img, _s = sample_image()
    tw.load_image(img, "Sample IEM")
    eq_screen.wait_for(lambda: not tw.reading and not tw.loading, 60)
    tw.t.v.update(d1="90", d2="40")
    for _ in range(curves):
        tw.t.auto_trace()
    tw.t.cur = 0
    tw.set_shows("measurement")
    tw.comp.setCurrentIndex(-1)
    tw.changed()
    tw.show_tab(2)
    qt.pump(50)
    return page, tw


def _tab_order(tw):
    """The names, for a screen reader, of the controls of 3 Save that Tab reaches, in the order of Tab. Measured with
    real Tab keys from the picture, until the focus comes to a control again (as test_trace_tab_keys.py's
    _tab_stops). Not with a Python call of nextInFocusChain: PySide6 6.11.2 then records the returned control as a
    child of the control asked (AGENTS.md; such records were a cause of an access violation in the tests,
    2026-11-15). Tab also goes to the side's scroll area one time, and to Open image…, Remove image and Guide: they
    are not in the card of 3 Save. At the end the picture has the focus again, so the pictures of the card show no
    control with the focus."""
    card = tw.pages.currentWidget()
    tw.activateWindow()  # (a key goes to an active window only)
    qt.pump(120)
    tw.stage.setFocus(Qt.OtherFocusReason)  # (as focus_picture does after a new picture)
    qt.pump(30)
    out, seen = [], set()
    for _ in range(60):
        QTest.keyClick(QApplication.focusWidget() or tw, Qt.Key_Tab)
        qt.pump(20)
        w = QApplication.focusWidget()
        key = shiboken6.getCppPointer(w)[0] if w is not None else None
        if w is None or w.window() is not tw or key in seen:
            break
        seen.add(key)
        if card.isAncestorOf(w):
            out.append(w.accessibleName())
    tw.stage.setFocus(Qt.OtherFocusReason)
    qt.pump(30)
    return out


def _sent(page, monkeypatch):
    """Each add to the app recorded (the app says no, "Test.": its files stay as they are)."""
    sent = []
    real_call = page.svc.call
    monkeypatch.setattr(page.svc, "call", lambda route, body=None: (sent.append(body), {"error": "Test."})[1]
                        if route == "/api/files/add" else real_call(route, body))
    return sent


def _boxes(tw, monkeypatch):
    """Each message box of the tracer recorded as (kind, text) and not shown; a question gets Yes and is not
    recorded (Remove image at the end of a test). Each bubble of tell() is recorded too, as ("bubble at <the
    button's words>", text), and not shown."""
    from PySide6.QtWidgets import QMessageBox
    said = []

    def box(kind, title, text, *buttons):
        if kind == "question":
            return QMessageBox.Yes
        said.append((kind, text))
        return QMessageBox.Ok
    monkeypatch.setattr(tw, "box", box)
    monkeypatch.setattr(tw, "tell", lambda button, text: said.append((f"bubble at {button.text()}", text)))
    return said


def _values(text):
    """The (Hz, dB) rows of a curve file's text."""
    rows = [line.split("\t") for line in text.splitlines() if line and not line.startswith("*")]
    return np.array([float(a) for a, _b in rows]), np.array([float(b) for _a, b in rows])


def test_four_types_one_add_button(eq_screen, tmp_path, check):
    a11y = paths.import_tool("a11y")
    page, tw = _sample(eq_screen, 1)
    card = tw.pages.currentWidget()
    choices = [(tw.shows.itemData(i), tw.shows.itemText(i)) for i in range(tw.shows.count())]
    seen, pictures = {}, {}
    for curves in (1, 2):
        if curves == 2:
            tw.t.auto_trace()
            tw.t.cur = 0
            tw.changed()
        for kind, _words in CHOICES:
            _select(tw.shows, kind)
            if kind in DIFFERENCES:
                _select(tw.comp, TARGET)
            qt.pump(50)
            seen[(curves, kind)] = {
                "row": save_row(tw), "target list": (tw.comp_lab.isVisible(), tw.comp.isVisible()),
                "line": tw.save_what.text(), "line in sight": tw.save_what.isVisible(),
                "described": qt.description(tw.save_btn), "add": tw.add_kind(),
                "tab": _tab_order(tw), "unnamed": a11y.unnamed(card),
                # (top to bottom: the list, the list of the target, the buttons, the gray line)
                "below": [w.mapTo(card, QPoint(0, 0)).y() for w in (tw.shows, tw.comp, tw.save_btn, tw.save_what)
                          if w.isVisible()]}
            if curves == 1:
                for name, theme_on in (("light", qt.light), ("dark", qt.dark)):
                    theme_on(eq_screen.qapp)
                    qt.pump(100)
                    path = str(tmp_path / f"3-save-{kind}-{name}.png")
                    card.grab().save(path)  # (read back by the author)
                    pic = QImage(path)
                    pictures[(kind, name)] = tuple(
                        pic.pixelColor(b.mapTo(card, QPoint(5, b.height() // 2))).saturation()
                        for b in (tw.save_btn, tw.download_btn))
                qt.light(eq_screen.qapp)
    names = (tw.shows.accessibleName(), tw.comp.accessibleName(), tw.shows.property("help_key"),
             tw.comp.property("help_key"))
    tw.set_shows("measurement")
    tw.comp.setCurrentIndex(-1)
    tw.remove_image()
    tw.close()
    check("tracer: “The graph shows” has 4 choices, in this order: “A measurement”, “A measurement as the difference "
          "from a target”, “A target line”, “A target line as the difference from a target”", choices == CHOICES,
          choices)
    check("tracer: 3 Save has one add button, in the accent, and Save .txt…; the add button is Add as measurement for "
          "the 2 types of a measurement, and Add as target for the 2 types of a target line",
          len(seen) == 8 and all(
              v["row"] == [("Add as target" if kind in AS_TARGET else "Add as measurement", True), ("Save .txt…", False)]
              and v["add"] == ("target" if kind in AS_TARGET else "measurement") for (_n, kind), v in seen.items()),
          {k: (v["row"], v["add"]) for k, v in seen.items()})
    check("tracer: “Target of the graph” (its label and its list) shows only for the 2 types with a difference from "
          "a target, between “The graph shows” and the buttons",
          all(v["target list"] == ((kind in DIFFERENCES),) * 2 and v["below"] == sorted(v["below"])
              and len(v["below"]) == (4 if kind in DIFFERENCES else 3) for (_n, kind), v in seen.items()),
          {k: (v["target list"], v["below"]) for k, v in seen.items()})
    check("tracer: a gray line under the buttons tells how the app saves the curve for the selected type (one curve, "
          "and more than one curve); it is also the description of the add button for a screen reader",
          all(v["line in sight"] and v["line"] == (WHAT if n == 1 else WHAT_2)[kind] and v["described"] == v["line"]
              for (n, kind), v in seen.items()), {k: (v["line"], v["described"]) for k, v in seen.items()})
    order = ["Name", "Points per octave", "The graph shows", "Target of the graph", "Save from … to (Hz)",
             "Save from … to (Hz)"]
    check("tracer: Tab goes through 3 Save from its top to its end (Name, Points per octave, The graph shows, "
          "Target of the graph when it shows, the two boxes of Save from), each control has a name for a screen "
          "reader, and F1 has an entry for each of the two lists",
          all(v["tab"] == [n for n in order if kind in DIFFERENCES or n != "Target of the graph"]
              and not v["unnamed"] for (_n, kind), v in seen.items())
          and names == ("The graph shows", "Target of the graph", "#tr-shows", "#tr-comp"),
          ({k: (v["tab"], v["unnamed"]) for k, v in seen.items()}, names))
    check("tracer: the pictures of 3 Save for each type (light and dark): the add button has the accent color, "
          "Save .txt… has none", len(pictures) == 8 and all(a > 80 and s < 40 for a, s in pictures.values()), pictures)


def test_each_type_sends_its_files(eq_screen, monkeypatch, tmp_path, check):
    """The files of each type are those of trace_core's outputs (not changed, 2026-11-16): the measurement curves as
    they are, the measurement curves with the target added, the selected curve as a target, or the selected curve
    with the target added as a target. Save .txt… writes the files of the measurement curves."""
    page, tw = _sample(eq_screen, 2)
    sent = _sent(page, monkeypatch)
    boxes, txt_boxes = _boxes(tw, monkeypatch), []
    folder = {}
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", staticmethod(lambda *a, **k: folder["now"]))
    got, txt = {}, {}
    for kind, _words in CHOICES:
        _select(tw.shows, kind)
        if kind in DIFFERENCES:
            _select(tw.comp, TARGET)
        del sent[:]
        tw.save_btn.click()  # (the stand-in app says "Test.": a box)
        got[kind] = sent[-1] if sent else None
        folder["now"] = str(tmp_path / kind)
        os.makedirs(folder["now"])
        del boxes[:]
        tw.save_txt()
        txt_boxes += boxes
        txt[kind] = {}
        for name in sorted(os.listdir(folder["now"])):
            with open(os.path.join(folder["now"], name), encoding="utf-8") as fh:  # (the text: Windows' line ends)
                txt[kind][name] = fh.read()
    t = tw.t
    plain = t.outputs(False, None, "")
    one = t.outputs(True, None, "")
    # (the target as the app has it, with no smoothing, on the 48 points in each octave of the app's curves)
    S = page.S
    r = page.svc.call("/api/preview", {"src": "app", "kind": "target", "names": [TARGET],
                                       "settings": dict(S, site=dict(S["site"], smooth_level=0))})
    lf = np.log(20.0) + np.arange(len(r["vals"])) * math.log(2) / 48
    added = {}
    for f_plain, f_diff in zip(got["measurement"]["files"], got["difference"]["files"]):
        hz, db = _values(f_plain["content"])
        hz2, db2 = _values(f_diff["content"])
        want = np.interp(np.log(hz), lf, np.asarray(r["vals"], float))
        added[f_plain["name"]] = (bool(np.array_equal(hz, hz2)), float(np.abs(db2 - db - want).max()),
                                  float(np.ptp(want)), f_diff["content"].splitlines()[0])
    # (the fourth type: the selected curve, the first one, with the target added, as one file of a target)
    line = got["target_difference"]
    line_file = line["files"][0]
    hz, db = _values(got["target"]["files"][0]["content"])
    hz2, db2 = _values(line_file["content"])
    same = bool(np.array_equal(hz, hz2))
    line_added = (len(line["files"]), line_file["name"], same,
                  float(np.abs(db2 - db - np.interp(np.log(hz), lf, np.asarray(r["vals"], float))).max()) if same
                  else None, line_file["content"].splitlines()[0])
    tw.set_shows("measurement")
    tw.comp.setCurrentIndex(-1)
    tw.remove_image()
    tw.close()
    as_sent = lambda outs: [{"name": o["file"], "content": o["text"]} for o in outs]  # noqa: E731
    check("tracer: “A measurement”: Add as measurement sends the measurement curves as the picture shows them (the "
          "2 files of trace_core's outputs, no target added)",
          got["measurement"]["kind"] == "measurement" and got["measurement"]["files"] == as_sent(plain)
          and [f["name"] for f in got["measurement"]["files"]] == ["Sample IEM L.txt", "Sample IEM R.txt"],
          [f["name"] for f in got["measurement"]["files"]])
    note = (f"* Traced from Sample IEM with AutoEQ Studio (the graph showed the difference from "
            f"{os.path.splitext(TARGET)[0]}: the app added this target)")
    # (0.002 dB: each file has 3 decimals of a dB, and its frequencies have 2 or 3 decimals of a Hz)
    check("tracer: “A measurement as the difference from a target”: Add as measurement sends the same curves with "
          "the selected target added (each value within 0.002 dB of the curve plus the target; the first line names "
          "the target)", got["difference"]["kind"] == "measurement" and len(added) == 2
          and all(same and err <= 0.002 and spread > 3 and first == note for same, err, spread, first in
                  added.values()), added)
    check("tracer: “A target line”: Add as target sends the selected curve as a target, as the picture shows it (one "
          "file, trace_core's output of that curve, no target added)",
          got["target"]["kind"] == "target" and got["target"]["files"] == as_sent(one)
          and [f["name"] for f in got["target"]["files"]] == ["Sample IEM.txt"]
          and got["target"]["files"][0]["content"].split("\n", 1)[1] == plain[0]["text"].split("\n", 1)[1],
          [f["name"] for f in got["target"]["files"]])
    check("tracer: “A target line as the difference from a target”: Add as target sends only the selected curve with "
          "the selected target added, as a target (one file; each value within 0.002 dB of the curve plus the "
          "target; the first line names the target; the same text as the file of that curve for “A measurement as "
          "the difference from a target”)",
          line["kind"] == "target" and line_added[:3] == (1, "Sample IEM.txt", True) and line_added[3] <= 0.002
          and line_added[4] == note and line_file["content"] == got["difference"]["files"][0]["content"],
          (line["kind"], line_added))
    check("tracer: Save .txt… writes the files of the measurement curves for each type, with the target added only "
          "for the 2 types with a difference from a target",
          txt["measurement"] == {o["file"]: o["text"] for o in plain} and txt["target"] == txt["measurement"]
          and txt["difference"] == {f["name"]: f["content"] for f in got["difference"]["files"]}
          and txt.get("target_difference") == txt["difference"]
          # (the only bubble: the sample's curves cross, and a part of one curve has no traced line)
          and all(kind == "bubble at Save .txt…" and text.startswith("Saved a straight line across untraced gap")
                  for kind, text in txt_boxes),
          ({k: sorted(v) for k, v in txt.items()}, txt_boxes))


def test_difference_with_no_target(eq_screen, monkeypatch, check):
    page, tw = _sample(eq_screen, 1)
    sent = _sent(page, monkeypatch)
    boxes = _boxes(tw, monkeypatch)
    asked = []
    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (asked.append(a), ("", ""))[1]))
    _select(tw.shows, "difference")
    qt.pump(30)
    none = {"list": (_comp_shows(tw), tw.comp.currentData() or "", tw.comp.isEnabled(), tw.comp.count() > 0),
            "line": tw.save_what.text(), "button": (tw.save_btn.text(), tw.save_btn.isEnabled())}
    tw.save_btn.click()
    tw.save_txt()
    none["boxes"], none["sent"], none["asked"] = list(boxes), len(sent), len(asked)
    # (the same for a target line as the difference from a target: its add button is Add as target)
    del boxes[:]
    _select(tw.shows, "target_difference")
    qt.pump(30)
    none_line = {"list": (tw.comp.isVisible(), _comp_shows(tw)), "line": tw.save_what.text(),
                 "button": (tw.save_btn.text(), tw.save_btn.isEnabled())}
    tw.save_btn.click()
    tw.save_txt()
    none_line["boxes"], none_line["sent"], none_line["asked"] = list(boxes), len(sent), len(asked)
    _select(tw.shows, "difference")
    rows = [tw.comp.itemText(i) for i in range(tw.comp.count())]
    _select(tw.comp, TARGET)
    with_target = (tw.save_what.text(), tw.users_work())
    # (no target in the app: the list is off, and the line tells the step to do first)
    del boxes[:]
    with monkeypatch.context() as m:
        m.setattr(page, "inputs", dict(page.inputs, targets=[]))
        tw.fill_comp()
        tw.update_ui()
        qt.pump(30)
        empty = {"list": (_comp_shows(tw), tw.comp.currentData() or "", tw.comp.isEnabled(), tw.comp.count()),
                 "in sight": tw.comp.isVisible(), "line": tw.save_what.text()}
        tw.save_btn.click()
        empty["boxes"], empty["sent"] = list(boxes), len(sent)
        del boxes[:]
        _select(tw.shows, "target_difference")
        qt.pump(30)
        empty_line = {"list": (tw.comp.isVisible(), _comp_shows(tw), tw.comp.isEnabled()),
                      "line": tw.save_what.text(), "button": tw.save_btn.text()}
        tw.save_btn.click()
        empty_line["boxes"], empty_line["sent"] = list(boxes), len(sent)
        _select(tw.shows, "difference")
    tw.fill_comp()
    back = tw.comp.count() > 0 and tw.comp.isEnabled()
    tw.set_shows("measurement")
    tw.comp.setCurrentIndex(-1)
    tw.remove_image()
    tw.close()
    check("tracer: a difference from a target with no target selected: “Target of the graph” shows its gray "
          "placeholder “Select target…”, the gray line tells to select the target, and the add and Save .txt… tell the same in a bubble at "
          "the button (the app adds no file)",
          none["list"] == (FIRST_ROW, "", True, True) and none["line"] == SELECT
          and none["button"] == ("Add as measurement", True)
          and none["boxes"] == [("bubble at Add as measurement", SELECT), ("bubble at Save .txt…", SELECT)]
          and none["sent"] == 0 and none["asked"] == 0, none)
    check("tracer: “Target of the graph” has only the targets of the app, from A to Z (“Select target…” is its "
          "placeholder, not a row); with a target selected, the gray line tells that the app adds it (the user's work)",
          FIRST_ROW not in rows and os.path.splitext(TARGET)[0] in rows
          and rows == sorted(rows, key=str.casefold) and with_target == (WHAT["difference"], True),
          (rows, with_target))
    check("tracer: a difference from a target when the app has no target: the list is off with “No targets "
          "available” as its placeholder, the gray line tells to add the target first, and the add tells the same in a "
          "bubble at it; with a target in the app again, the list is on",
          empty["list"] == (NO_TARGET_ROW, "", False, 0) and empty["in sight"]
          and empty["line"] == NO_TARGETS and empty["boxes"] == [("bubble at Add as measurement", NO_TARGETS)] and empty["sent"] == 0
          and back, (empty, back))
    check("tracer: a target line as the difference from a target with no target selected, and when the app has no "
          "target: “Target of the graph” shows, the gray line tells the step to do first, and Add as target and "
          "Save .txt… tell the same in a bubble at the button (the app adds no file)",
          none_line == {"list": (True, FIRST_ROW), "line": SELECT, "button": ("Add as target", True),
                        "boxes": [("bubble at Add as target", SELECT), ("bubble at Save .txt…", SELECT)], "sent": 0,
                        "asked": 0}
          and empty_line == {"list": (True, NO_TARGET_ROW, False), "line": NO_TARGETS,
                             "button": "Add as target", "boxes": [("bubble at Add as target", NO_TARGETS)],
                             "sent": 0},
          (none_line, empty_line))


def test_the_app_selects_the_type(eq_screen, monkeypatch, check):
    from ui import trace_core
    page = eq_screen.page
    page.open_trace()
    tw = page.tracer
    tw.set_shows("measurement")
    img, _s = sample_image()
    state = lambda: (tw.shows.currentData(), tw.save_btn.text(), tw.comp.isVisible(), tw.users_work())  # noqa: E731

    def read(entry, **kw):
        monkeypatch.setattr(trace_core, "auto_read", ok_read(**kw))
        tw.load_image(img, entry=entry)
        at_once = tw.shows.currentData()  # (when the picture comes, before the read ends)
        qt.wait_for(lambda: not tw.loading and not tw.reading_graph and tw.read_ok is not None, 60)
        tw.show_tab(2)
        qt.pump(30)
        return at_once

    def mine(part):
        tw.load_image(img.copy(0, 0, 800 + part, 500), "A picture of yours")  # (a different picture each time)
        qt.wait_for(lambda: not tw.loading and not tw.reading, 60)
        tw.show_tab(2)
        qt.pump(30)

    seen = {}
    at_once = read(dict(ENTRY, **{"as": "target"}))
    seen["Find a target"] = (at_once, state(), tw.save_note.text().endswith("then click Add as target."))
    # (the user selects a different type: it stays, and the note names the button)
    _select(tw.shows, "measurement")
    tw.update_ui()
    seen["the user's selection after it"] = (state(), tw.save_note.text().endswith("click Add as measurement."))
    mine(0)
    seen["a picture of the user after it"] = state()
    read(dict(ENTRY, **{"as": "target"}))
    tw.remove_image()
    seen["Remove image after Find a target"] = state()
    # (from test_trace_save_row.py's test_accent_button_is_the_main_action, merged here by the test audit of
    # 2026-11-25: the row of 3 Save with its accent after the app's "A target line", and an entry with no "as". The
    # app's own entries always have an "as" (eq_page_files.py), so only this test reads the default of select_shows)
    rows = {"Remove image after it": save_row(tw)}
    read(dict(ENTRY, **{"as": "target"}))
    mine(8)
    rows["a picture of yours after it"] = save_row(tw)
    tw.remove_image()
    read(dict(ENTRY))
    rows["Find a measurement"] = (save_row(tw), "Add as measurement." in tw.save_note.text())
    tw.remove_image()
    at_once = read(dict(ENTRY, kind="target"), only=True)
    seen["a target line alone"] = (at_once, state())
    tw.remove_image()
    read(dict(ENTRY, kind="target", **{"as": "measurement"}), only=True)
    seen["a target line alone, Find a measurement"] = state()
    tw.remove_image()
    # (a picture of the user keeps a difference from a target and its target; a picture from a website does not)
    mine(1)
    _select(tw.shows, "difference")
    _select(tw.comp, TARGET)
    mine(2)
    seen["a difference, then a picture of the user"] = (state(), tw.comp.currentData() or "")
    tw.remove_image()
    seen["a difference, then Remove image"] = (state()[0], tw.comp.currentData() or "")
    at_once = read(dict(ENTRY, **{"as": "measurement"}), target_line=True)
    note = tw.save_note.text()
    seen["a measurement from a website after a difference"] = (at_once, state(), tw.comp.currentData() or "",
                                                              tw.save_line.isVisible())
    # (the user selects a target line there: the note names Add as target, and tells that the button of the target
    # line adds that line)
    _select(tw.shows, "target")
    seen["the user's target line on it"] = (state(), tw.save_what.text(), tw.save_note.text())
    # (the user selects a target line on a picture of the user; the next picture is a measurement again)
    tw.remove_image()
    mine(3)
    _select(tw.shows, "target")
    mine(4)
    seen["the user's target line, then a new picture"] = state()
    # (the user selects a target line as the difference from a target: the next picture of the user is a measurement
    # again, and the difference and its target stay; a picture from a website is a measurement with no target)
    tw.remove_image()
    mine(5)
    _select(tw.shows, "target_difference")
    _select(tw.comp, TARGET)
    seen["the user's target line as a difference"] = (state(), tw.comp.currentData() or "", tw.save_what.text())
    mine(6)
    seen["a target line as a difference, then a new picture"] = (state(), tw.comp.currentData() or "")
    _select(tw.shows, "target_difference")
    tw.remove_image()
    seen["a target line as a difference, then Remove image"] = (state()[0], tw.comp.currentData() or "")
    mine(7)
    _select(tw.shows, "target_difference")
    at_once = read(dict(ENTRY, **{"as": "measurement"}))
    seen["a measurement from a website after a target line as a difference"] = (at_once, state(),
                                                                               tw.comp.currentData() or "")
    tw.remove_image()
    tw.close()
    head = "Traced graph for “Truthear Gate” from “Hangout.Audio”. Verify it against the image, then "
    check("tracer: for an entry from Find a target, the app selects “A target line” when the picture comes: the add "
          "button is Add as target, and the note tells to click it (not the user's work)",
          seen["Find a target"] == ("target", ("target", "Add as target", False, False), True), seen["Find a target"])
    check("tracer: the user can change the app's selection: it stays (the user's work), the add button is Add as "
          "measurement, and the note tells to click that button",
          seen["the user's selection after it"] == (("measurement", "Add as measurement", False, True), True),
          seen["the user's selection after it"])
    check("tracer: a picture with only a target line: the app selects “A target line”, but “A measurement” for an "
          "entry from Find… for a measurement",
          seen["a target line alone"] == ("measurement", ("target", "Add as target", False, False))
          and seen["a target line alone, Find a measurement"] == ("measurement", "Add as measurement", False, False),
          (seen["a target line alone"], seen["a target line alone, Find a measurement"]))
    check("tracer: after “A target line” (the app's selection or the user's), a new picture of the user and Remove "
          "image have “A measurement” again",
          seen["a picture of the user after it"] == ("measurement", "Add as measurement", False, False)
          and seen["Remove image after Find a target"] == ("measurement", "Add as measurement", False, False)
          and seen["the user's target line, then a new picture"] == ("measurement", "Add as measurement", False,
                                                                     False), seen)
    measurement = [("Add as measurement", True), ("Save .txt…", False)]
    check("tracer: a new picture or Remove image makes the add button Add as measurement again, in the accent; an "
          "entry from Find a measurement has it too", rows["a picture of yours after it"] == measurement
          and rows["Remove image after it"] == measurement and rows["Find a measurement"] == (measurement, True), rows)
    check("tracer: a difference from a target and its target stay for the next picture of the user and after Remove "
          "image (not the user's work on the new picture)",
          seen["a difference, then a picture of the user"] == (("difference", "Add as measurement", True, False),
                                                               TARGET)
          and seen["a difference, then Remove image"] == ("difference", TARGET), seen)
    check("tracer: a measurement from a website after a difference from a target: the app selects “A measurement”, "
          "and “Target of the graph” has no target (the target of the picture before does not go into the curve)",
          seen["a measurement from a website after a difference"] == (
              "measurement", ("measurement", "Add as measurement", False, False), "", True)
          and note == head + "click Add as measurement. A target line was also detected; use “Add the target line as "
          "target…” to save it.", (seen["a measurement from a website after a difference"],
                                                           note))
    check("tracer: the user selects “A target line” on a picture with a measurement and a target line: the gray line "
          "tells that the app saves only the selected curve, and the note names Add as target and the button of the "
          "target line",
          seen["the user's target line on it"] == (
              ("target", "Add as target", False, True), WHAT_2["target"],
              head + "click Add as target. A target line was also detected: use “Add the target line as target…” to "
              "save it instead of the Average curve."), seen["the user's target line on it"])
    line = {k: v for k, v in seen.items() if "target line as a difference" in k}
    check("tracer: “A target line as the difference from a target” is a selection of the user only (the user's work, "
          "Add as target, with “Target of the graph”); the next picture of the user and Remove image have “A "
          "measurement as the difference from a target” with the same target, and a measurement from a website has "
          "“A measurement” with no target",
          line == {"the user's target line as a difference": (("target_difference", "Add as target", True, True),
                                                               TARGET, WHAT["target_difference"]),
                   "a target line as a difference, then a new picture": (("difference", "Add as measurement", True,
                                                                          False), TARGET),
                   "a target line as a difference, then Remove image": ("difference", TARGET),
                   "a measurement from a website after a target line as a difference": (
                       "measurement", ("measurement", "Add as measurement", False, False), "")}, line)


def test_target_of_the_graph_is_the_users_work(eq_screen, monkeypatch, check):
    """A different target in "Target of the graph" is the user's work (a new Use stops for it), the first target
    again is not; a target in the list while it does not show changes nothing."""
    page, tw = _sample(eq_screen, 0)
    inputs = dict(getattr(page, "inputs", None) or {})
    monkeypatch.setattr(page, "inputs", dict(inputs, targets=list(inputs.get("targets", [])) + ["Stand-in.txt"]))
    tw.fill_comp()
    _select(tw.shows, "difference")
    _select(tw.comp, TARGET)
    # (a new picture of the user: the difference and its target stay, as the values of the new picture)
    img, _s = sample_image()
    tw.load_image(img.copy(0, 0, 900, 600), "Mine")
    eq_screen.wait_for(lambda: not tw.reading and not tw.loading, 60)
    seen = {"new picture": (tw.save_value("shows"), tw.users_work(), tw.changed_picture())}
    _select(tw.comp, "Stand-in.txt")
    seen["an other target"] = (tw.save_value("shows"), tw.users_work(), tw.changed_picture())
    _select(tw.comp, TARGET)
    seen["the first target again"] = (tw.users_work(), tw.changed_picture())
    _select(tw.shows, "measurement")
    seen["a measurement"] = (tw.save_value("shows"), tw.users_work())
    tw.comp.setCurrentIndex(tw.comp.findData("Stand-in.txt"))  # (the list does not show: no selection of a user)
    _select(tw.shows, "measurement")
    seen["a target in the hidden list"] = (tw.save_value("shows"), tw.compensation(), tw.users_work())
    tw.comp.setCurrentIndex(-1)
    tw.remove_image()
    monkeypatch.undo()
    tw.fill_comp()
    tw.close()
    check("tracer: with a difference from a target, a different target in “Target of the graph” is the user's work "
          "(a changed picture), and the first target again is no change",
          seen["new picture"] == (("difference", TARGET), False, False)
          and seen["an other target"] == (("difference", "Stand-in.txt"), True, True)
          and seen["the first target again"] == (False, False), seen)
    check("tracer: “A measurement” in place of the difference is the user's work, and a target in the list that does "
          "not show adds nothing to the curve",
          seen["a measurement"] == (("measurement", ""), True)
          and seen["a target in the hidden list"] == (("measurement", ""), (None, ""), True), seen)


def test_guide_shows_the_list(eq_screen, check):
    """The Guide's step "The graph shows": its demo shows "Target of the graph" (a difference from a target, not
    selected), and all is as before after it; the step "Save" shows the add button."""
    from ui import guide, tour
    page, tw = _sample(eq_screen, 1)
    before = (tw.save_value("shows"), tw.save_btn.text(), tw.comp.isVisible(), tw.save_what.text())
    t = guide.start_trace(tw)
    t.all_chk.setChecked(False)  # (one demo at a time: the test starts it)
    steps = [st["title"] for st in t.steps]
    probs = tour.problems(tw, guide.trace_steps(tw))
    t.go_to_step(steps.index("The graph shows"))
    words = t.steps[t.i]["text"]
    lit = [w is tw.shows for w in t.steps[t.i]["target"]()]
    during, told = [], set()
    t.speed = 4.0
    t.replay()
    done = qt.wait_for(lambda: (during.append((tw.shows.currentData(), tw.comp.isVisible())), told.add(t.say),
                                not t.demo_running)[2], 60)
    t.go_to_step(steps.index("Save"))
    save_words = t.steps[t.i]["text"]
    save_lit = [w.text() for w in t.steps[t.i]["target"]()]
    t.end()
    qt.pump(50)
    after = (tw.save_value("shows"), tw.save_btn.text(), tw.comp.isVisible(), tw.save_what.text())
    work = dict(tw.edited)  # (the values of 3 Save that the user changed: none)
    tw.remove_image()
    tw.close()
    check("tracer's Guide: the steps of 3 · Save are “The graph shows” (it has the 4 types and Target of the graph), "
          "“Save” (the add button and Save .txt…) and “The end”; each control of each step is there",
          steps[-3:] == ["The graph shows", "Save", "The end"] and "Compensated graphs" not in steps and not probs
          and lit == [True] and all(w in words for w in ("“A measurement”", "“A target line”", "The 2 types with a "
                                                         "difference from a target", "Target of the graph"))
          and save_lit == ["Add as measurement", "Save .txt…"]
          and "The add button has the name of the selected type." in save_words, (steps[-3:], probs, lit, save_lit))
    check("tracer's Guide: the demo of “The graph shows” shows a difference from a target with Target of the graph "
          "under the list, and after it the list, the add button and the gray line are as before (no work of the "
          "user)", done and ("difference", True) in during and before == after
          and before[0] == ("measurement", "") and not work, (done, sorted(set(during)), before, after, work))
    check("tracer's Guide: the demo of “The graph shows” tells “The 4 types of graph” at the open list, and then "
          "what Target of the graph is", {"The 4 types of graph", "The target that the app adds to the curve"} <= told,
          sorted(told))


def test_save_txt_of_a_target_line_alone(eq_screen, monkeypatch, tmp_path, check):
    """Save .txt… for a picture with only a target line (the read's one curve is the target line, marked): the box
    said "Trace a curve first.", and no file was made (2026-11-16)."""
    from ui import trace_core
    page = eq_screen.page
    page.open_trace()
    tw = page.tracer
    img, _s = sample_image()
    monkeypatch.setattr(trace_core, "auto_read", ok_read(only=True))
    tw.load_image(img, entry=dict(ENTRY, kind="target"))
    qt.wait_for(lambda: not tw.loading and not tw.reading_graph and tw.read_ok is not None, 60)
    boxes = _boxes(tw, monkeypatch)
    path = str(tmp_path / "Target alone.txt")
    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (path, "")))
    curves = [(c["label"], bool(c.get("target"))) for c in tw.t.curves]
    tw.save_txt()
    text = ""
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    note = tw.save_note.text()
    tw.remove_image()
    tw.close()
    check("tracer: Save .txt… for a picture with only a target line writes the file of that line (no box “Trace a "
          "curve first.”), and the note names the file",
          curves == [("Target", True)] and not boxes and text.startswith("* Traced from Truthear Gate (Hangout 5128) "
                                                                         "with AutoEQ Studio")
          and len(text.splitlines()) > 10 and note == "Saved Target alone.txt", (curves, boxes, note,
                                                                                         text[:80]))


def test_targets_that_change_while_the_tracer_is_open(eq_screen, monkeypatch, check):
    """"Target of the graph" follows the targets of the app while the tracer is open: a target that comes (Add as
    target in the tracer, Add… on Make an EQ) and a target that goes (Find…'s Delete…). The tracer read the targets
    only when it opened or got a picture: with no target in the app, the list stayed off with "No target in the
    app", and the gray line and the box of the add button told to add a target first, after the user did that
    (2026-11-16). The same targets shown again change nothing in an open list."""
    from PySide6.QtWidgets import QPushButton
    page = eq_screen.page
    had, active = list(page.inputs["targets"]), page.S["files"].get("active_target")

    def delete(names):
        """Find…'s Delete… for these targets (ui\\picker.py's remove, after its question)."""
        page.svc.call("/api/files/remove", {"kind": "target", "names": names, "settings": page.S})
        page.reload_state()
        qt.settle()

    def look():
        # (the gray placeholder first, then the rows of the list)
        return (tw.comp.isEnabled(), [tw.comp.placeholderText()] + [tw.comp.itemText(i) for i in range(tw.comp.count())],
                tw.comp.currentData() or "", tw.save_what.text())
    delete(had)
    page, tw = _sample(eq_screen, 1)
    boxes = _boxes(tw, monkeypatch)
    _select(tw.shows, "difference")
    qt.pump(30)
    none = look()
    # (Add as target in the tracer: the traced curve becomes the one target of the app)
    _select(tw.shows, "target")
    tw.save_btn.click()
    qt.settle()  # (the page works out its curves for the new target)
    own = [n for n in page.inputs["targets"] if n not in had]
    del boxes[:]
    _select(tw.shows, "difference")
    qt.pump(30)
    after_own = look()
    tw.save_btn.click()
    own_boxes = list(boxes)
    # (Add… of the Target row of Make an EQ, with the sample targets; the tracer stays open)
    files = [os.path.join(paths.SAMPLES, "targets", n) for n in had]
    monkeypatch.setattr(QFileDialog, "getOpenFileNames", staticmethod(lambda *a, **k: (files, "")))
    next(b for b in page.target_box.findChildren(QPushButton) if b.text() == "Add…").click()
    qt.settle()
    came = look()
    # (the same targets shown again, as when the database lists come: the open list keeps the row that the arrow
    # keys marked)
    tw.activateWindow()
    tw.comp.setFocus()
    tw.comp.showPopup()
    qt.pump(100)
    view = tw.comp.view()
    QTest.keyClick(view, Qt.Key_Down)
    qt.pump(30)
    marked = view.currentIndex().row()
    page.reload_state()
    qt.pump(100)
    kept = (view.window().isVisible(), view.currentIndex().row())
    tw.comp.hidePopup()
    # (the selected target deleted: "Select target…" again)
    if own:
        _select(tw.comp, own[0])
    selected = look()
    delete(own)
    gone = look()
    left = list(page.inputs["targets"])
    if active in left and page.S["files"].get("active_target") != active:  # (the target in use of before)
        page.use_target(active)
        qt.settle()
    tw.set_shows("measurement")
    tw.comp.setCurrentIndex(-1)
    tw.remove_image()
    tw.close()
    names = [os.path.splitext(n)[0] for n in had]
    mine = [os.path.splitext(n)[0] for n in own]
    both = [FIRST_ROW] + sorted(names + mine, key=str.casefold)
    check("tracer: with no target in the app, “Target of the graph” is off with “No targets available”; after Add as "
          "target in the open tracer, the list is on with the new target, and the gray line and the bubble at the add "
          "button tell to select the target",
          none == (False, [NO_TARGET_ROW], "", NO_TARGETS) and len(own) == 1
          and after_own == (True, [FIRST_ROW] + mine, "", SELECT) and own_boxes == [("bubble at Add as measurement", SELECT)],
          (none, own, after_own, own_boxes))
    check("tracer: a target that Add… on Make an EQ adds while the tracer is open is in “Target of the graph” at "
          "once (the targets from A to Z)", came == (True, both, "", SELECT), came)
    check("tracer: Make an EQ shows the same targets again while “Target of the graph” is open: the list stays open "
          "with the row that the arrow keys marked", marked == 1 and kept == (True, 1), (marked, kept))
    check("tracer: a selected target that is deleted goes from “Target of the graph”, and the gray line tells to "
          "select the target (the app has its targets of before again)",
          len(own) == 1 and selected[2:] == (own[0], WHAT["difference"])
          and gone == (True, [FIRST_ROW] + names, "", SELECT) and left == had,
          (own, selected, gone, left))


def test_select_target_is_the_placeholder(eq_screen, monkeypatch, check):
    """The control audit of 2026-11-27 (2-3): "Select target…" was the first row of "Target of the graph", a row with
    no target. It is now the list's gray placeholder while no target is selected; the list has only targets. The way
    back to no target: a picture from a website (select_shows) selects none again; a type with no difference hides
    the list and adds no target."""
    page, tw = _sample(eq_screen, 1)
    _select(tw.shows, "difference")
    qt.pump(30)
    rows = [(tw.comp.itemText(i), tw.comp.itemData(i)) for i in range(tw.comp.count())]
    first = (tw.comp.currentIndex(), tw.comp.placeholderText(), tw.comp.shows_placeholder())
    _select(tw.comp, TARGET)
    chosen = (tw.comp.currentData(), tw.comp.shows_placeholder())
    monkeypatch.setattr(tw, "entry", dict(ENTRY))
    tw.select_shows()
    back = (tw.comp.currentIndex(), tw.comp.shows_placeholder(), tw.shows.currentData())
    monkeypatch.setattr(tw, "entry", None)
    tw.set_shows("measurement")
    tw.remove_image()
    tw.close()
    check("tracer: “Target of the graph” shows the gray placeholder “Select target…” with no target selected, and "
          "its list has only the targets of the app (no row without a target)",
          first == (-1, FIRST_ROW, True) and len(rows) == len(page.inputs["targets"]) > 0
          and all(data for _text, data in rows) and FIRST_ROW not in [text for text, _d in rows], (first, rows))
    check("tracer: a target selected replaces the placeholder; a picture from a website selects no target again (the "
          "placeholder shows)", chosen == (TARGET, False) and back == (-1, True, "measurement"), (chosen, back))

