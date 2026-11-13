"""The tracer's window with a picture of a website's target (ui\\trace_window.py's read_graph and take_read for a read
of the target line alone, trace_auto's target_only): 3 Save's note and its main action, the two adds, and the
messages when the kind of the entry and the picture do not agree. The read is the real one on a drawn look-alike
(helpers.website_graph.target_graph), with the true words of the picture in place of Windows' text reader."""
import re

from PySide6.QtCore import QPoint
from PySide6.QtGui import QImage

from helpers import qt
from helpers.website_graph import target_graph, truth_reader, website_graph
from ui import trace_auto

# (what the window reaches through Make an EQ: for app\tools\relevant_tests.py)
COVERS = ("ui.trace_core", "ui.trace_auto", "ui.ocr", "ui.eq_page", "eq.service", "eq.inputs")
ENTRY = {"name": "Sample Target", "tag": "Site 1", "site": "Sample.Site", "link": "https://example.invalid/t",
         "kind": "target"}
HEAD = "The app traced the target “Sample Target” from “Sample.Site”."
END = "Compare the curve with the picture. If they agree, click Add as target."
# (the first and the last traced frequency, in 3 Save's note: the line has no points under a label and where the
# website fades it, 2026-11-13)
NOTE = re.compile(re.escape(HEAD) + r" The app traced the target line from \d+(\.\d)? Hz to \d+(\.\d)? kHz\.\n"
                  + re.escape(END) + "$")


def _row(tw):
    """3 Save's buttons in their order, each with whether it is the accent button."""
    lay = tw.save_btns
    return [(lay.itemAt(i).widget().text(), lay.itemAt(i).widget().property("primary") in (True, "true"))
            for i in range(lay.count()) if lay.itemAt(i).widget() is not None]


def _read(tw, monkeypatch, img, truth, entry):
    monkeypatch.setattr(trace_auto, "read_strip", truth_reader(truth))
    tw.load_image(img, entry=entry)
    qt.wait_for(lambda: not tw.loading and not tw.reading_graph and tw.read_ok is not None, 90)


def _pictures(eq_screen, tw, tmp_path, name):
    """The window in light and dark (read back by the author: the status line in full)."""
    for theme, theme_on in (("light", qt.light), ("dark", qt.dark)):
        theme_on(eq_screen.qapp)
        qt.pump(150)
        tw.grab().save(str(tmp_path / f"{name}-{theme}.png"))
    qt.light(eq_screen.qapp)
    qt.pump(50)


def test_target_alone_in_3_save(eq_screen, monkeypatch, tmp_path, check):
    from ui.trace_window import QMessageBox
    page = eq_screen.page
    page.open_trace()
    tw = page.tracer
    img, truth = target_graph(1200)
    _read(tw, monkeypatch, img, truth, ENTRY)
    target = [("Add as target", True), ("Add as measurement", False), ("Save .txt…", False)]
    seen = {"ok": tw.read_ok, "read_target": tw.read_target, "tab": tw.pages.currentIndex(),
            "note": tw.save_note.text(), "row": _row(tw), "line button": tw.save_line.isVisible(),
            "curves": [(c["label"], c.get("target")) for c in tw.t.curves]}
    pictures = {}
    usual = tw.size()
    for which, size in (("usual", usual), ("smallest", tw.minimumSize().expandedTo(tw.minimumSizeHint()))):
        tw.resize(size)
        for name, theme_on in (("light", qt.light), ("dark", qt.dark)):
            theme_on(eq_screen.qapp)
            qt.pump(150)
            path = str(tmp_path / f"target-alone-3-save-{which}-{name}.png")
            tw.grab().save(path)  # (the whole window: read back by the author)
            side = str(tmp_path / f"target-alone-3-save-{which}-{name}-side.png")
            tw.pages.currentWidget().grab().save(side)
            pic = QImage(side)
            fill = [pic.pixelColor(b.mapTo(tw.pages.currentWidget(), QPoint(5, b.height() // 2))).saturation()
                    for b in (tw.save_tgt, tw.save_meas)]
            note_whole = tw.save_note.height() >= tw.save_note.heightForWidth(tw.save_note.width())
            pictures[(which, name)] = (tuple(fill), note_whole)
    qt.light(eq_screen.qapp)
    tw.resize(usual)
    # the two adds: the files that each one sends (the service stands in: it records and says no)
    sent, said = [], []
    real_call = page.svc.call
    monkeypatch.setattr(page.svc, "call", lambda route, body=None: (sent.append((route, body)), {"error": "Test."})[1]
                        if route == "/api/files/add" else real_call(route, body))
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: said.append(a[2] if len(a) > 2 else ""))
    tw.save("target")
    tw.save("measurement")
    tw.remove_image()
    seen["after remove"] = (tw.read_target, _row(tw)[0])
    # (a new picture of the user after a target read: Add as measurement is the main action again)
    _read(tw, monkeypatch, img, truth, ENTRY)
    first = tw.read_target
    tw.load_image(website_graph(plot_w=1000)[0], "Mine")
    qt.wait_for(lambda: not tw.loading, 30)
    seen["after a new picture"] = (first, tw.read_target, _row(tw)[0])
    tw.close()
    check("tracer: an entry of a target, a picture with only the target line: the read is OK, 3 Save is in sight, "
          "the one curve is the target line (\"Target\", marked)", seen["ok"] is True and seen["read_target"] is True
          and seen["tab"] == 2 and seen["curves"] == [("Target", True)], seen)
    check("tracer: 3 Save's note says that the app traced the target, from which frequency to which, and Add as "
          "target", bool(NOTE.match(seen["note"])), seen["note"])
    check("tracer: after Remove image, and after a new picture of the user, Add as measurement is the main action "
          "again", seen["after remove"] == (False, ("Add as measurement", True))
          and seen["after a new picture"] == (True, False, ("Add as measurement", True)), seen)
    check("tracer: Add as target is the first button of 3 Save, in the accent; Add the target line as target… does "
          "not show", seen["row"] == target and seen["line button"] is False, seen)
    check("tracer: the pictures (light and dark, the usual and the smallest size): Add as target has the accent color, "
          "Add as measurement has none, and the note shows all its lines", len(pictures) == 4
          and all(t > 80 and m < 40 and whole for (t, m), whole in pictures.values()), pictures)
    files = [b["files"] for r, b in sent]
    check("tracer: Add as target and Add as measurement each send the target line as one file of 400 points or more "
          "(no message that there is no curve)", [b["kind"] for _r, b in sent] == ["target", "measurement"]
          and all(len(f) == 1 and f[0]["content"].count("\n") > 400 for f in files) and said == ["Test.", "Test."],
          ([(b["kind"], [x["name"] for x in b["files"]]) for _r, b in sent], said))


def test_kind_of_entry_and_picture_disagree(eq_screen, monkeypatch, tmp_path, check):
    from ui.trace_window import CORRECT_STEP, NOT_GRAPH
    page = eq_screen.page
    page.open_trace()
    tw = page.tracer
    img, truth = website_graph(plot_w=1000, target="solid", curves=False)
    _read(tw, monkeypatch, img, truth, dict(ENTRY, kind="measurement", name="Sample IEM"))
    seen = {"measurement": (tw.read_ok, tw.read_target, tw.pages.currentIndex(), tw.status.text(), _row(tw)[0],
                            any(tw.t.has_data(c) for c in tw.t.curves))}
    _pictures(eq_screen, tw, tmp_path, "measurement-entry")
    tw.remove_image()
    # (the website's graph of a target, -20 dB to 20 dB: axes_db_range fails first, the final verification's SF5)
    img, truth = target_graph(1200)
    _read(tw, monkeypatch, img, truth, dict(ENTRY, kind="measurement", name="Sample IEM"))
    seen["graph of a target"] = (tw.read_ok, tw.pages.currentIndex(), tw.status.text())
    _pictures(eq_screen, tw, tmp_path, "measurement-entry-graph-of-a-target")
    tw.remove_image()
    img, truth = website_graph(plot_w=1000, target="solid")
    _read(tw, monkeypatch, img, truth, ENTRY)
    seen["target"] = (tw.read_ok, tw.read_target, tw.pages.currentIndex(), tw.status.text(), _row(tw)[0])
    tw.remove_image()
    img, truth = website_graph(plot_w=1000, target="solid", curves=False)
    _read(tw, monkeypatch, img, truth, {k: v for k, v in ENTRY.items() if k != "kind"})
    seen["no kind"] = (tw.read_ok, bool(NOTE.match(tw.save_note.text())), _row(tw)[0])
    tw.remove_image()
    _read(tw, monkeypatch, img, truth, dict(ENTRY, **{"as": "measurement"}))
    seen["as a measurement"] = (tw.read_ok, tw.save_note.text().endswith("click Add as measurement."), _row(tw)[0])
    tw.remove_image()
    # (two target lines, 8 dB apart: trace_single of a target line alone, the verifier's M2)
    img, truth = website_graph(plot_w=1396, target="solid", curves=False, db_range=(-20, 20),
                               target_fn=lambda f: 2 + 8 / (1 + (f / 100) ** 2),
                               extra=[(lambda f: 10 + 8 / (1 + (f / 100) ** 2), "#b0b0b0")])
    _read(tw, monkeypatch, img, truth, ENTRY)
    seen["two targets"] = (tw.read_ok, tw.pages.currentIndex(), tw.status.text())
    _pictures(eq_screen, tw, tmp_path, "two-targets")
    tw.remove_image()
    tw.close()
    head = "The app cannot trace this picture automatically. "
    # (2026-11-13, the verifier's M3: the words of a measurement and the step to correct, no curve "Target")
    check("tracer: an entry of a measurement, a picture with only a target line: the read is not OK, 2 Trace is in "
          "sight, the status line has the reason of a measurement, the sentence about the gray line and the step to "
          "correct, and the tracer has no curve",
          seen["measurement"] == (False, False, 1, head + trace_auto.NO_STRONG_CURVE + " " + trace_auto.ONLY_GREY_LINE
                                  + "\n" + CORRECT_STEP, ("Add as measurement", True), False), seen["measurement"])
    check("tracer: an entry of a measurement, the website's graph of a target (-20 dB to 20 dB): 1 Axes is in sight, "
          "and the status line has the reason of the dB axis, the sentence about the gray line and the step to correct",
          seen["graph of a target"] == (False, 0, head + "The dB axis is -20 dB to 20 dB. This range is not usual for "
                                        "a graph of an IEM or headphone. " + trace_auto.ONLY_GREY_LINE + "\n"
                                        + CORRECT_STEP), seen["graph of a target"])
    check("tracer: an entry of a target, a picture with a measurement across the target line: the read is not OK, and "
          "the status line tells to remove the measurement and to copy a new picture",
          seen["target"] == (False, False, 1, head + trace_auto.KIND_NOT_TARGET + "\n" + NOT_GRAPH,
                             ("Add as measurement", True)), seen["target"])
    check("tracer: an entry of a target, a picture with two target lines: the read is not OK, 2 Trace is in sight, "
          "and the status line tells to show only one target and to copy a new picture",
          seen["two targets"] == (False, 1, head + trace_auto.MORE_TARGETS + "\n" + NOT_GRAPH), seen["two targets"])
    check("tracer: an entry with no kind, a picture with only a target line: a target, Add as target first",
          seen["no kind"] == (True, True, ("Add as target", True)), seen["no kind"])
    check("tracer: Find… for a measurement on an entry of a target (\"as\": \"measurement\"): the note says Add as "
          "measurement, and it is first", seen["as a measurement"] == (True, True, ("Add as measurement", True)),
          seen["as a measurement"])
