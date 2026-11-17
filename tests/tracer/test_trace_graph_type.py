"""3 Save of the tracer (ui\\trace_window.py): "The graph shows" is one question with 3 types of graph (the user,
2026-11-16; before, the list had "Frequency response (not compensated)" and "Difference from <target>", and the type
"a target line" was one of two add buttons). The 3 choices in their order; "Target of the graph", in sight only for
"A measurement as the difference from a target"; the one add button, whose name follows the list; the gray line under
it; the files that each type sends to the app and that Save .txt… writes; a difference with no target; the selection
that the app makes (an entry from Find a target, a target line alone, a measurement from a website) and that the user
can change; the Guide's demo of the list; and Save .txt… for a target line alone. With the app's sample graph and a
drawn look-alike of a website's target (helpers.website_graph)."""
import math
import os

import numpy as np
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QFileDialog

from helpers import paths, qt
from ui.trace_window import sample_image

# (what the window reaches through Make an EQ: for app\tools\relevant_tests.py)
COVERS = ("ui.trace_core", "ui.trace_auto", "ui.ocr", "ui.eq_page", "ui.guide_trace", "ui.tour", "eq.service",
          "eq.inputs", "a11y")
TARGET = paths.SAMPLE_TARGET
ENTRY = {"name": "Truthear Gate", "tag": "Hangout 5128", "site": "Hangout.Audio", "link": "https://example.invalid/x"}
CHOICES = [("measurement", "A measurement"), ("difference", "A measurement as the difference from a target"),
           ("target", "A target line")]
WHAT = {"measurement": "The app saves the curve as a measurement, as the picture shows it.",
        "difference": "The app adds the selected target to the curve. Then it saves the result as a measurement.",
        "target": "The app saves the curve as a target, as the picture shows it."}
WHAT_2 = {"measurement": "The app saves the curves as one measurement, as the picture shows them.",
          "difference": "The app adds the selected target to each curve. Then it saves the result as one measurement.",
          "target": "The app saves only the selected curve as a target, as the picture shows it."}
SELECT = "Select the target in “Target of the graph”. The app adds this target to the curve."
NO_TARGETS = "The app has no target. First, add the target of the graph on Make an EQ."


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
    tw.comp.setCurrentIndex(0)
    tw.changed()
    tw.show_tab(2)
    qt.pump(50)
    return page, tw


def _row(tw):
    """3 Save's buttons in their order, each with whether it is the accent button."""
    return [(w.text(), w.property("primary") in (True, "true")) for w in qt.layout_parts(tw.save_btns)
            if w is not None and w.isWidgetType()]


def _tab_order(tw):
    """The names, for a screen reader, of the controls of 3 Save that Tab reaches, in the order of Tab."""
    card = tw.pages.currentWidget()
    out, w = [], tw.name
    for _ in range(2000):
        if card.isAncestorOf(w) and w.isVisibleTo(card) and w.isEnabled() and w.focusPolicy() & Qt.TabFocus \
                and w.focusProxy() is None:
            out.append(w.accessibleName())
        w = w.nextInFocusChain()
        if w is tw.name:
            break
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
    recorded (Remove image at the end of a test)."""
    from PySide6.QtWidgets import QMessageBox
    said = []

    def box(kind, title, text, *buttons):
        if kind == "question":
            return QMessageBox.Yes
        said.append((kind, text))
        return QMessageBox.Ok
    monkeypatch.setattr(tw, "box", box)
    return said


def _values(text):
    """The (Hz, dB) rows of a curve file's text."""
    rows = [line.split("\t") for line in text.splitlines() if line and not line.startswith("*")]
    return np.array([float(a) for a, _b in rows]), np.array([float(b) for _a, b in rows])


def test_three_types_one_add_button(eq_screen, tmp_path, check):
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
            if kind == "difference":
                _select(tw.comp, TARGET)
            qt.pump(50)
            seen[(curves, kind)] = {
                "row": _row(tw), "target list": (tw.comp_lab.isVisible(), tw.comp.isVisible()),
                "line": tw.save_what.text(), "line in sight": tw.save_what.isVisible(),
                "described": tw.save_btn.accessibleDescription(), "add": tw.add_kind(),
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
    tw.remove_image()
    tw.close()
    check("tracer: “The graph shows” has 3 choices, in this order: “A measurement”, “A measurement as the difference "
          "from a target”, “A target line”", choices == CHOICES, choices)
    check("tracer: 3 Save has one add button, in the accent, and Save .txt…; the add button is Add as measurement for "
          "a measurement and for a difference from a target, and Add as target for a target line",
          all(v["row"] == [("Add as target" if kind == "target" else "Add as measurement", True), ("Save .txt…", False)]
              and v["add"] == ("target" if kind == "target" else "measurement") for (_n, kind), v in seen.items()),
          {k: (v["row"], v["add"]) for k, v in seen.items()})
    check("tracer: “Target of the graph” (its label and its list) shows only for “A measurement as the difference "
          "from a target”, between “The graph shows” and the buttons",
          all(v["target list"] == ((kind == "difference"),) * 2 and v["below"] == sorted(v["below"])
              and len(v["below"]) == (4 if kind == "difference" else 3) for (_n, kind), v in seen.items()),
          {k: (v["target list"], v["below"]) for k, v in seen.items()})
    check("tracer: a gray line under the buttons tells how the app saves the curve for the selected type (one curve, "
          "and more than one curve); it is also the description of the add button for a screen reader",
          all(v["line in sight"] and v["line"] == (WHAT if n == 1 else WHAT_2)[kind] and v["described"] == v["line"]
              for (n, kind), v in seen.items()), {k: (v["line"], v["described"]) for k, v in seen.items()})
    order = ["Name", "Points in each octave", "The graph shows", "Target of the graph", "Save from … to (Hz)",
             "Save from … to (Hz)"]
    check("tracer: Tab goes through 3 Save from its top to its end (Name, Points in each octave, The graph shows, "
          "Target of the graph when it shows, the two boxes of Save from), each control has a name for a screen "
          "reader, and F1 has an entry for each of the two lists",
          all(v["tab"] == [n for n in order if kind == "difference" or n != "Target of the graph"]
              and not v["unnamed"] for (_n, kind), v in seen.items())
          and names == ("The graph shows", "Target of the graph", "#tr-shows", "#tr-comp"),
          ({k: (v["tab"], v["unnamed"]) for k, v in seen.items()}, names))
    check("tracer: the pictures of 3 Save for each type (light and dark): the add button has the accent color, "
          "Save .txt… has none", len(pictures) == 6 and all(a > 80 and s < 40 for a, s in pictures.values()), pictures)


def test_each_type_sends_its_files(eq_screen, monkeypatch, tmp_path, check):
    """The files of each type are those of trace_core's outputs (not changed, 2026-11-16): the measurement curves as
    they are, the measurement curves with the target added, or the selected curve as a target. Save .txt… writes the
    files of the measurement curves."""
    page, tw = _sample(eq_screen, 2)
    sent = _sent(page, monkeypatch)
    boxes, txt_boxes = _boxes(tw, monkeypatch), []
    folder = {}
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", staticmethod(lambda *a, **k: folder["now"]))
    got, txt = {}, {}
    for kind, _words in CHOICES:
        _select(tw.shows, kind)
        if kind == "difference":
            _select(tw.comp, TARGET)
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
    tw.set_shows("measurement")
    tw.comp.setCurrentIndex(0)
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
    check("tracer: Save .txt… writes the files of the measurement curves for each type, with the target added only "
          "for a difference from a target",
          txt["measurement"] == {o["file"]: o["text"] for o in plain} and txt["target"] == txt["measurement"]
          and txt["difference"] == {f["name"]: f["content"] for f in got["difference"]["files"]}
          # (the only box: the sample's curves cross, and a part of one curve has no traced line)
          and all(kind == "information" and text.startswith("The app saved a straight line across the part")
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
    none = {"list": (tw.comp.currentText(), tw.comp.currentData(), tw.comp.isEnabled(), tw.comp.count() > 1),
            "line": tw.save_what.text(), "button": (tw.save_btn.text(), tw.save_btn.isEnabled())}
    tw.save_btn.click()
    tw.save_txt()
    none["boxes"], none["sent"], none["asked"] = list(boxes), len(sent), len(asked)
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
        empty = {"list": (tw.comp.currentText(), tw.comp.currentData(), tw.comp.isEnabled(), tw.comp.count()),
                 "in sight": tw.comp.isVisible(), "line": tw.save_what.text()}
        tw.save_btn.click()
        empty["boxes"], empty["sent"] = list(boxes), len(sent)
    tw.fill_comp()
    back = tw.comp.count() > 1 and tw.comp.isEnabled()
    tw.set_shows("measurement")
    tw.comp.setCurrentIndex(0)
    tw.remove_image()
    tw.close()
    check("tracer: a difference from a target with no target selected: “Target of the graph” has “Select the target” "
          "first, the gray line tells to select the target, and the add and Save .txt… tell the same in a box (the "
          "app adds no file)",
          none["list"] == ("Select the target", "", True, True) and none["line"] == SELECT
          and none["button"] == ("Add as measurement", True) and none["boxes"] == [("warning", SELECT)] * 2
          and none["sent"] == 0 and none["asked"] == 0, none)
    check("tracer: “Target of the graph” has the targets of the app from A to Z after “Select the target”; with a "
          "target selected, the gray line tells that the app adds it (the user's work)",
          rows[0] == "Select the target" and os.path.splitext(TARGET)[0] in rows
          and rows[1:] == sorted(rows[1:], key=str.casefold) and with_target == (WHAT["difference"], True),
          (rows, with_target))
    check("tracer: a difference from a target when the app has no target: the list is off with “No target in the "
          "app”, the gray line tells to add the target first, and the add tells the same in a box; with a target "
          "in the app again, the list is on",
          empty["list"] == ("No target in the app", "", False, 1) and empty["in sight"]
          and empty["line"] == NO_TARGETS and empty["boxes"] == [("warning", NO_TARGETS)] and empty["sent"] == 0
          and back, (empty, back))


def _stand_in_read(target_line=False, only=False):
    """A stand-in for trace_core.auto_read: the picture as it is, the sample's dB values, a part of a curve, all
    checks OK; target_line: also a target line, marked; only: the one curve is the target line (target_only)."""
    def read(rgb, ocr_words=None, jpeg=False, name="Traced graph", want=None):
        from ui import trace_core
        from ui.trace_auto import AutoRead, Check
        t = trace_core.Tracer()
        t.load(np.array(rgb, np.uint8, copy=True), name, jpeg)
        t.v.update(d1="90", d2="40")
        t.curves[0]["ys"][100:200] = 300.0  # (a traced curve)
        line = None
        if only:
            t.curves[0].update(label="Target", target=True)
        elif target_line:
            ys = np.full_like(t.curves[0]["ys"], np.nan)
            ys[100:200] = 350.0
            line = {"label": "Target", "colour": (136, 136, 136), "ys": ys, "target": True}
            t.curves.append(line)
        return AutoRead(True, t, [Check("axes_plot", True, "The app found the graph in the picture.")], t.curves[0],
                        line, None, None, None, 0.01, "", only)
    return read


def test_the_app_selects_the_type(eq_screen, monkeypatch, check):
    from ui import trace_core
    page = eq_screen.page
    page.open_trace()
    tw = page.tracer
    tw.set_shows("measurement")
    img, _s = sample_image()
    state = lambda: (tw.shows.currentData(), tw.save_btn.text(), tw.comp.isVisible(), tw.users_work())  # noqa: E731

    def read(entry, **kw):
        monkeypatch.setattr(trace_core, "auto_read", _stand_in_read(**kw))
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
    seen["Find a target"] = (at_once, state(), tw.save_note.text().endswith("If they agree, click Add as target."))
    # (the user selects a different type: it stays, and the note names the button)
    _select(tw.shows, "measurement")
    tw.update_ui()
    seen["the user's selection after it"] = (state(), tw.save_note.text().endswith("click Add as measurement."))
    mine(0)
    seen["a picture of the user after it"] = state()
    read(dict(ENTRY, **{"as": "target"}))
    tw.remove_image()
    seen["Remove image after Find a target"] = state()
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
    seen["a difference, then a picture of the user"] = (state(), tw.comp.currentData())
    tw.remove_image()
    seen["a difference, then Remove image"] = (state()[0], tw.comp.currentData())
    at_once = read(dict(ENTRY, **{"as": "measurement"}), target_line=True)
    note = tw.save_note.text()
    seen["a measurement from a website after a difference"] = (at_once, state(), tw.comp.currentData(),
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
    tw.remove_image()
    tw.close()
    head = "The app traced the graph of “Truthear Gate” from “Hangout.Audio”. Compare the curve with the picture. "
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
    check("tracer: a difference from a target and its target stay for the next picture of the user and after Remove "
          "image (not the user's work on the new picture)",
          seen["a difference, then a picture of the user"] == (("difference", "Add as measurement", True, False),
                                                               TARGET)
          and seen["a difference, then Remove image"] == ("difference", TARGET), seen)
    check("tracer: a measurement from a website after a difference from a target: the app selects “A measurement”, "
          "and “Target of the graph” has no target (the target of the picture before does not go into the curve)",
          seen["a measurement from a website after a difference"] == (
              "measurement", ("measurement", "Add as measurement", False, False), "", True)
          and note == head + "If they agree, click Add as measurement. The picture also has a target line. Add the "
          "target line as target… adds it as a target.", (seen["a measurement from a website after a difference"],
                                                           note))
    check("tracer: the user selects “A target line” on a picture with a measurement and a target line: the gray line "
          "tells that the app saves only the selected curve, and the note names Add as target and the button of the "
          "target line",
          seen["the user's target line on it"] == (
              ("target", "Add as target", False, True), WHAT_2["target"],
              head + "If they agree, click Add as target. The picture also has a target line. Add the target line as "
              "target… adds that line as a target, not the Average curve."), seen["the user's target line on it"])


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
    tw.comp.setCurrentIndex(0)
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
    during = []
    t.speed = 4.0
    t.replay()
    done = qt.wait_for(lambda: (during.append((tw.shows.currentData(), tw.comp.isVisible())), not t.demo_running)[1],
                       60)
    t.go_to_step(steps.index("Save"))
    save_words = t.steps[t.i]["text"]
    save_lit = [w.text() for w in t.steps[t.i]["target"]()]
    t.end()
    qt.pump(50)
    after = (tw.save_value("shows"), tw.save_btn.text(), tw.comp.isVisible(), tw.save_what.text())
    work = dict(tw.edited)  # (the values of 3 Save that the user changed: none)
    tw.remove_image()
    tw.close()
    check("tracer's Guide: the steps of 3 · Save are “The graph shows” (it has the 3 types and Target of the graph), "
          "“Save” (the add button and Save .txt…) and “The end”; each control of each step is there",
          steps[-3:] == ["The graph shows", "Save", "The end"] and "Compensated graphs" not in steps and not probs
          and lit == [True] and all(w in words for w in ("“A measurement”", "“A measurement as the difference from "
                                                         "a target”", "“A target line”", "Target of the graph"))
          and save_lit == ["Add as measurement", "Save .txt…"]
          and "The add button has the name of the selected type." in save_words, (steps[-3:], probs, lit, save_lit))
    check("tracer's Guide: the demo of “The graph shows” shows a difference from a target with Target of the graph "
          "under the list, and after it the list, the add button and the gray line are as before (no work of the "
          "user)", done and ("difference", True) in during and before == after
          and before[0] == ("measurement", "") and not work, (done, sorted(set(during)), before, after, work))


def test_save_txt_of_a_target_line_alone(eq_screen, monkeypatch, tmp_path, check):
    """Save .txt… for a picture with only a target line (the read's one curve is the target line, marked): the box
    said "Trace a curve first.", and no file was made (2026-11-16)."""
    from ui import trace_core
    page = eq_screen.page
    page.open_trace()
    tw = page.tracer
    img, _s = sample_image()
    monkeypatch.setattr(trace_core, "auto_read", _stand_in_read(only=True))
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
          and len(text.splitlines()) > 10 and note == "The app saved Target alone.txt.", (curves, boxes, note,
                                                                                         text[:80]))
