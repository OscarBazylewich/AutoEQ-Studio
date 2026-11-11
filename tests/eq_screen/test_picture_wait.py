"""A picture from a website (ui\\picture_wait.py, ui\\eq_page_files.py's trace_from_website, and the tracer with an
entry, ui\\trace_window.py): Find…'s Use on an entry of a database that does not let other programs download its
files opens it in the browser (recorded: helpers.qt's OPENED_URLS, nothing opens) and waits for a new picture on the
clipboard (the off-screen clipboard is this process's own); the picture goes to the tracer, which reads it
automatically and adds it with the entry's name, the website in the file's first line and the source record.

The entries are the fixture's Hangout.Audio 5128 list (tests\\fixtures\\db): "Truthear Gate". Most tests stand in
for trace_core.auto_read (a made AutoRead on the app's sample graph: OK, or one check not OK), so that they test the
window's logic, not the accuracy of the automatic read; the last one uses the real automatic read on a drawn
look-alike of the website's graph (helpers.website_graph, its words given by truth_reader). Online is stood in for
net.offline() only: net.check() stays offline, so nothing can connect."""
import math
import os
import time

import numpy as np
import pytest

from helpers import qt
from ui import trace_core

REAL_AUTO_READ = trace_core.auto_read  # (the real one: the fixture stands in for it)
ENTRY = "Truthear Gate"
TAG = "Hangout 5128"
NAME = f"{ENTRY} ({TAG})"
LINK = "https://graph.hangout.audio/iem/5128/?share=Gate"
SITE = "Hangout.Audio IEMs (Crinacle, 5128)"
# (the sample graph's grid: trace_window.sample_image's L, R, T, B, width, height, lo and hi dB)
SL, SR, ST, SB, SW, SH, LO, HI = 96, 40, 76, 84, 1200, 720, 40, 90


def _rows(pk):
    from PySide6.QtCore import Qt
    return [pk.list.item(i).data(Qt.UserRole) for i in range(pk.list.count()) if pk.list.item(i).data(Qt.UserRole)]


def _said(pk):
    return pk.footer.line.text.text()


def _sample():
    from ui.trace_window import sample_image
    return sample_image()


def stand_in(ok=True, fail="trace_curve", target=False, error=None, delay=0.0, crop=(10, 20), calls=None):
    """A stand-in for trace_core.auto_read: the sample graph cropped (as the real one crops), its axes set, the first
    channel as the measurement curve ("Average") and, with target, the dashed target as the target line."""
    from ui import trace_core
    from ui.trace_auto import AutoRead, Check
    _img, s = _sample()
    chan, tgt = s["curves"][0], s["target"]

    def column_values(pts, cx, cy, w):
        xs = np.array([p[0] for p in pts]) - cx - 0.5
        ys = np.array([p[1] for p in pts]) - cy - 0.5
        return np.interp(np.arange(w), xs, ys, left=np.nan, right=np.nan)

    def fake(rgb, ocr_words=None, jpeg=False, name="Traced graph"):
        if calls is not None:
            calls.append({"shape": np.asarray(rgb).shape, "jpeg": jpeg, "name": name, "ocr": ocr_words})
        if delay:
            time.sleep(delay)
        if error:
            raise RuntimeError(error)
        cx, cy = crop
        t = trace_core.Tracer()
        t.load(np.array(rgb[cy:, cx:], np.uint8, copy=True), name, jpeg)
        if fail == "axes_plot" and not ok:
            return AutoRead(False, t, [Check("axes_plot", False, "The app did not find the grid of a graph in this "
                                             "picture.")], None, None, None, None, None, 0.01)
        X = lambda f: SL + (math.log10(f) - math.log10(20)) / 3 * (SW - SL - SR) - cx  # noqa: E731
        Y = lambda v: ST + (HI - v) / (HI - LO) * (SH - ST - SB) - cy  # noqa: E731
        t.cal.update(x1=X(20), x2=X(20000), y1=Y(HI), y2=Y(LO))
        t.v.update(f1="20", f2="20000", d1=str(HI), d2=str(LO), every=False)
        curve = {"label": "Average", "colour": (232, 116, 59), "ys": column_values(chan, cx, cy, t.W)}
        t.curves, t.cur = [curve], 0
        line = None
        if target:
            line = {"label": "Target", "colour": (136, 136, 136), "ys": column_values(tgt, cx, cy, t.W), "target": True}
            t.curves.append(line)
        checks = [Check("axes_plot", True, "The app found the graph in the picture."),
                  Check(fail, ok, "The reason of this check.")]
        return AutoRead(ok, t, checks, curve, line, None, None, None, 0.01)
    return fake


@pytest.fixture
def flow(eq_screen, monkeypatch):
    """Find… for a measurement with the rows of "truthear gate" (its lists loaded: offline, the saved ones), online
    for the flow's own check (net.offline), auto_read stood in (OK) until a test sets its own; after the test, the
    tracer empty and closed, Find… closed, the clipboard empty."""
    import net
    from PySide6.QtWidgets import QApplication
    from ui import picture_wait, trace_core
    from ui.picker import Picker
    page = eq_screen.page
    QApplication.clipboard().clear()
    monkeypatch.setattr(picture_wait, "SETTLE_MS", 30)
    monkeypatch.setattr(trace_core, "auto_read", stand_in())
    pk = Picker(page, "measurement")
    pk.show()
    eq_screen.wait_for(lambda: not pk.db.get("loading") and pk.db.get("items"), 120)
    pk.q.setText("truthear gate")
    pk.render()
    pk.finish_list()
    monkeypatch.setattr(net, "offline", lambda: False)
    yield {"page": page, "pk": pk, "row": next((r for r in _rows(pk) if r.get("link") and r["name"] == ENTRY), None)}
    wait = getattr(page, "picture_wait", None)
    if wait is not None and not _closed(wait):
        wait.reject()
    tw = getattr(page, "tracer", None)
    if tw is not None:
        qt.wait_for(lambda: not tw.reading_graph, 30)
        tw.remove_image()
        tw.close()
    pk.reject()
    pk.deleteLater()
    QApplication.clipboard().clear()
    qt.pump(50)


def _use(f):
    """Find…'s Use on the website entry's row: the wait window (or None) and the links opened."""
    n = len(qt.OPENED_URLS)
    f["pk"].use_row(f["row"])
    qt.pump(50)
    return getattr(f["page"], "picture_wait", None), qt.OPENED_URLS[n:]


def _copy(img):
    from PySide6.QtWidgets import QApplication
    QApplication.clipboard().setImage(img)


def _graph():
    img, _s = _sample()
    return img


def _closed(wait):
    """The wait window closed (and deleted: the page lets it go when it closes)."""
    from ui import tasks
    return not tasks.alive(wait) or not wait.isVisible()


def _picture_came(page, sec=20):
    """The tracer has the picture and its automatic read has ended."""
    return qt.wait_for(lambda: getattr(page, "tracer", None) is not None and page.tracer.t.has_image
                       and not page.tracer.reading_graph, sec)


# ---------------------------------------------------------------- Find… and the wait window
def test_use_opens_link_and_waits(eq_screen, flow, check):
    from PySide6.QtWidgets import QLabel
    wait, opened = _use(flow)
    shown = wait is not None and wait.isVisible()
    words = " ".join(lab.text() for lab in wait.findChildren(QLabel)) if wait is not None else ""
    check("website flow: Use on a website entry opens its link in the browser and shows the wait window with the "
          "entry's name", flow["row"] is not None and opened == [LINK] and shown and f"“{ENTRY}”" in words
          and wait.windowTitle() == "Picture from the website" and wait.parent() is flow["pk"],
          (opened, shown, words[:200]))
    check("website flow: the wait window is window modal on Find… and does not block (Find… stays open)",
          shown and wait.isModal() and flow["pk"].isVisible(), shown)


def test_old_picture_does_not_end_wait(eq_screen, flow, check):
    _copy(_graph())
    wait, _o = _use(flow)
    qt.pump(400)
    check("website flow: a picture that was on the clipboard before does not end the wait",
          wait is not None and wait.isVisible() and wait.got is None and flow["pk"].isVisible(), wait)


def test_text_does_not_end_wait(eq_screen, flow, check):
    from PySide6.QtWidgets import QApplication
    wait, _o = _use(flow)
    QApplication.clipboard().setText("Some words")
    qt.pump(400)
    check("website flow: new text on the clipboard does not end the wait", wait.isVisible() and wait.got is None)


def test_small_picture_does_not_end_wait(eq_screen, flow, check):
    from PySide6.QtGui import QColor, QImage
    wait, _o = _use(flow)
    small = QImage(299, 400, QImage.Format_RGB888)
    small.fill(QColor("white"))
    _copy(small)
    qt.pump(400)
    check("website flow: a picture smaller than 300 x 200 does not end the wait", wait.isVisible() and wait.got is None)


def test_new_picture_ends_wait(eq_screen, flow, check):
    page, pk = flow["page"], flow["pk"]
    wait, _o = _use(flow)
    _copy(_graph())
    came = _picture_came(page)
    tw = page.tracer
    check("website flow: a new picture on the clipboard closes the wait window and Find…, and the tracer opens with it",
          came and _closed(wait) and not pk.isVisible() and tw.isVisible() and page.picture_wait is None
          and tw.entry and tw.entry["name"] == ENTRY, (came, _closed(wait), pk.isVisible()))
    check("website flow: the tracer gets the name “Truthear Gate (Hangout 5128)”",
          tw.file_lab.whole == NAME and tw.name.text() == NAME and tw.t.src_name == NAME,
          (tw.file_lab.whole, tw.name.text(), tw.t.src_name))


def test_paste_takes_old_picture(eq_screen, flow, check):
    page = flow["page"]
    _copy(_graph())
    wait, _o = _use(flow)
    btn = wait.paste_btn
    main = (btn.isDefault(), btn.property("help_key"), btn.text())
    btn.click()
    came = _picture_came(page)
    check("website flow: Paste the picture takes the picture that was there before", came and _closed(wait)
          and page.tracer.entry["name"] == ENTRY, came)
    check("website flow: Paste the picture is the main button (the accent, Enter's) and has its help",
          main == (True, "#pw-paste", "Paste the picture"), main)


def test_paste_with_nothing(eq_screen, flow, check):
    wait, _o = _use(flow)
    wait.paste()
    qt.pump(100)
    check("website flow: Paste the picture with no picture says so, and the wait continues",
          wait.isVisible() and "no picture on the clipboard" in wait.note.text() and wait.note.isVisible(),
          wait.note.text())


def test_cancel(eq_screen, flow, check):
    from PySide6.QtWidgets import QPushButton
    page, pk = flow["page"], flow["pk"]
    before = getattr(page, "tracer", None)
    had = before is not None and before.t.has_image
    wait, _o = _use(flow)
    cancel = next(b for b in wait.findChildren(QPushButton) if b.text() == "Cancel")
    cancel.click()
    qt.pump(100)
    tw = getattr(page, "tracer", None)
    check("website flow: Cancel closes the wait window, Find… stays, no file and no tracer picture",
          _closed(wait) and pk.isVisible() and page.picture_wait is None
          and (tw is None or tw.t.has_image == had) and not _said(pk), (pk.isVisible(), _said(pk)))
    _copy(_graph())
    qt.pump(400)
    tw = getattr(page, "tracer", None)
    check("website flow: after Cancel, a new picture on the clipboard does nothing", pk.isVisible()
          and (tw is None or tw.t.has_image == had), had)


def test_stop_disconnects(eq_screen, flow, check):
    from ui.picture_wait import PictureWait
    wait = PictureWait(flow["pk"], {"name": ENTRY, "site": SITE})
    wait.open()
    qt.pump(50)
    started = wait._limit.isActive()
    wait.reject()
    _copy(_graph())
    qt.pump(300)
    check("website flow: a closed wait window stops all (the clipboard's signal disconnected, the timers stopped): a "
          "new picture does nothing", started and wait.got is None and not wait._settle.isActive()
          and not wait._limit.isActive(), (started, wait.got))
    wait.deleteLater()


def test_time_limit(eq_screen, flow, monkeypatch, check):
    from ui import picture_wait
    pk = flow["pk"]
    monkeypatch.setattr(picture_wait, "TIMEOUT_MS", 300)
    wait, _o = _use(flow)
    gone = qt.wait_for(lambda: _closed(wait), 10)
    check("website flow: after the time limit the wait window closes and Find…'s line says so",
          gone and pk.isVisible() and "no new picture in 10 minutes" in _said(pk), _said(pk))


def test_offline(eq_screen, flow, monkeypatch, check):
    import net
    pk = flow["pk"]
    monkeypatch.setattr(net, "offline", lambda: True)
    wait, opened = _use(flow)
    check("website flow: offline, nothing opens, no wait window, and the line says how to go online",
          not opened and wait is None and _said(pk).startswith("Offline:") and "Online (top right)" in _said(pk)
          and pk.isVisible(), (opened, _said(pk)))


def test_tracer_with_curves_not_added(eq_screen, flow, check):
    page, pk = flow["page"], flow["pk"]
    page.open_trace()
    tw = page.tracer
    tw.load_image(_graph(), "Mine")
    qt.wait_for(lambda: not tw.reading, 60)
    tw.t.curves[0]["ys"][100:200] = 300.0  # (a traced part)
    tw.close()
    wait, opened = _use(flow)
    check("website flow: the tracer with curves that were not added stops the flow with a message",
          not opened and wait is None and "curves that you did not add" in _said(pk)
          and "select the entry again" in _said(pk) and tw.t.src_name == "Mine", (opened, _said(pk)))
    tw.added = True
    wait, opened = _use(flow)
    check("website flow: after the add of the tracer's curves, the flow starts", opened == [LINK] and wait is not None
          and wait.isVisible(), opened)


def test_entry_route_error_said(eq_screen, flow, check):
    page, pk = flow["page"], flow["pk"]
    n = len(qt.OPENED_URLS)
    started = page.trace_from_website("no-such-entry", over=pk, say=lambda t, ms=10000: pk.footer.say(t, ms))
    check("website flow: an entry that is not in the lists says so in the caller's line, nothing opens",
          not started and len(qt.OPENED_URLS) == n and "not there" in _said(pk), _said(pk))


def test_one_wait_at_a_time(eq_screen, flow, check):
    page, pk = flow["page"], flow["pk"]
    wait, _o = _use(flow)
    n = len(qt.OPENED_URLS)
    again = page.trace_from_website(flow["row"]["id"], over=pk, say=pk.footer.say)
    check("website flow: a second call while the wait window is open shows that window and starts nothing",
          not again and page.picture_wait is wait and len(qt.OPENED_URLS) == n)


# ---------------------------------------------------------------- the tracer with an entry
def _traced(f, monkeypatch, fake):
    from ui import trace_core
    monkeypatch.setattr(trace_core, "auto_read", fake)
    _use(f)
    _copy(_graph())
    came = _picture_came(f["page"])
    return came, f["page"].tracer


def test_all_checks_ok(eq_screen, flow, monkeypatch, check):
    calls = []
    came, tw = _traced(flow, monkeypatch, stand_in(calls=calls))
    note = tw.save_note.text()
    check("website flow: all checks OK, the tracer shows 3 Save and its note names the entry and the website",
          came and tw.pages.currentIndex() == 2 and tw.read_ok is True and f"“{ENTRY}”" in note and SITE in note
          and "Add as measurement" in note and not tw.save_line.isVisible(), (tw.pages.currentIndex(), note))
    check("website flow: the automatic read gets the picture's pixels, the entry's name with its tag and Windows' "
          "text reader", calls and calls[0]["name"] == NAME and calls[0]["shape"][:2] == (SH, SW)
          and calls[0]["ocr"] is not None, calls)
    check("website flow: the stage has the size of the tracer's picture (the crop of the automatic read)",
          tw.stage.qimg is not None and (tw.stage.qimg.width(), tw.stage.qimg.height()) == (tw.t.W, tw.t.H)
          == (SW - 10, SH - 20) and tw.size_lab.text() == f"{SW - 10}×{SH - 20}",
          (tw.stage.qimg.size() if tw.stage.qimg else None, tw.t.W, tw.t.H, tw.size_lab.text()))
    check("website flow: the axis values show in the boxes after the read",
          tw.boxes["d1"].text() == str(HI) and tw.boxes["f2"].text() == "20000",
          (tw.boxes["d1"].text(), tw.boxes["f2"].text()))


def test_reading_takes_no_input(eq_screen, flow, monkeypatch, check):
    from ui import trace_core
    monkeypatch.setattr(trace_core, "auto_read", stand_in(delay=1.0))
    _use(flow)
    _copy(_graph())
    page = flow["page"]
    qt.wait_for(lambda: getattr(page, "tracer", None) is not None and page.tracer.reading_graph, 10)
    tw = page.tracer
    during = (tw.reading_graph, tw.status.text(), tw.stage.isEnabled(), tw.side_scroll.isEnabled())
    came = _picture_came(page)
    check("website flow: while the automatic read runs, the status line says so, and the stage and the side panel "
          "do not accept input", during[0] and during[1] == "The app reads the graph…" and not during[2]
          and not during[3], during)
    check("website flow: after the automatic read, the stage and the side panel accept input again",
          came and tw.stage.isEnabled() and tw.side_scroll.isEnabled())


def test_axes_check_failed(eq_screen, flow, monkeypatch, check):
    came, tw = _traced(flow, monkeypatch, stand_in(ok=False, fail="axes_hz_labels"))
    check("website flow: a check of the axes not OK, the tracer shows 1 Axes with the reason",
          came and tw.pages.currentIndex() == 0 and "cannot trace this picture automatically" in tw.status.text()
          and "The reason of this check." in tw.status.text() and "The reason of this check." in tw.axis_note.text(),
          (tw.pages.currentIndex(), tw.status.text(), tw.axis_note.text()))


def test_trace_check_failed(eq_screen, flow, monkeypatch, check):
    came, tw = _traced(flow, monkeypatch, stand_in(ok=False, fail="trace_band"))
    check("website flow: a check of the curve not OK, the tracer shows 2 Trace with the reason",
          came and tw.pages.currentIndex() == 1 and "The reason of this check." in tw.status.text()
          and "Then go to 3 Save." in tw.status.text(), (tw.pages.currentIndex(), tw.status.text()))


def test_not_a_graph(eq_screen, flow, monkeypatch, check):
    calls = []
    from ui import trace_window
    real = trace_window.TraceWindow.read_labels
    monkeypatch.setattr(trace_window.TraceWindow, "read_labels", lambda self: (calls.append(1), real(self)))
    came, tw = _traced(flow, monkeypatch, stand_in(ok=False, fail="axes_plot"))
    check("website flow: a picture that is not a graph (axes_plot), the tracer shows 1 Axes with the reason and reads "
          "the labels as for any picture", came and tw.pages.currentIndex() == 0 and calls
          and "did not find the grid" in tw.status.text(), (tw.pages.currentIndex(), calls, tw.status.text()))


def test_error_of_the_read(eq_screen, flow, monkeypatch, check):
    calls = []
    from ui import trace_window
    real = trace_window.TraceWindow.read_labels
    monkeypatch.setattr(trace_window.TraceWindow, "read_labels", lambda self: (calls.append(1), real(self)))
    came, tw = _traced(flow, monkeypatch, stand_in(error="made-up failure"))
    check("website flow: an error of the automatic read gives 1 Axes and today's label read",
          came and tw.pages.currentIndex() == 0 and calls and "made-up failure" in tw.status.text()
          and tw.read_ok is False and tw.entry["name"] == ENTRY, (tw.pages.currentIndex(), calls, tw.status.text()))


def test_paste_after_poor_picture_keeps_entry(eq_screen, flow, monkeypatch, check):
    from ui import trace_core
    came, tw = _traced(flow, monkeypatch, stand_in(ok=False, fail="axes_hz_labels"))
    monkeypatch.setattr(trace_core, "auto_read", stand_in())
    _copy(_graph())
    tw.paste()
    again = _picture_came(flow["page"])
    check("website flow: a picture pasted in the tracer after a poor one keeps the entry",
          came and again and tw.entry and tw.entry["name"] == ENTRY and tw.t.src_name == NAME and tw.read_ok is True
          and tw.pages.currentIndex() == 2, (tw.entry, tw.t.src_name, tw.read_ok))
    _copy(_graph())
    tw.paste()
    qt.wait_for(lambda: not tw.reading_graph, 20)
    check("website flow: after a read that was OK, a new picture pasted in the tracer is a picture of yours (no entry)",
          tw.entry is None and tw.t.src_name != NAME, (tw.entry, tw.t.src_name))


def test_entry_cleared(eq_screen, flow, monkeypatch, check):
    from ui import guide
    came, tw = _traced(flow, monkeypatch, stand_in())
    tw.remove_image()
    removed = tw.entry is None and not tw.added and tw.read_ok is None
    flow["pk"].show()
    came2, tw = _traced(flow, monkeypatch, stand_in())
    tw.close()
    closed = tw.entry is None
    flow["page"].open_trace()  # (the Guide runs on a window in sight)
    tw.remove_image()
    tw.entry = {"name": "Left over", "tag": "X"}  # (as if one were left: the Guide's sample must not keep it)
    tour = guide.start_trace(tw)
    sample = (tw.entry, tw.t.src_name)
    tour.end()
    check("website flow: Remove image, the window's close and the Guide's sample clear the entry",
          came and came2 and removed and closed and sample == (None, "Sample graph"), (removed, closed, sample))


def test_add_as_measurement(eq_screen, fresh_studio, flow, monkeypatch, check):
    from eq import rigs
    page = flow["page"]
    came, tw = _traced(flow, monkeypatch, stand_in())
    tw.save("measurement")
    loaded = qt.wait_for(lambda: page.curves is not None and page.curves.get("name") == NAME, 60)
    used = [m["name"] for m in page.inputs["measurements"] if m["included"]]
    others = [m["name"] for m in page.inputs["measurements"] if not m["included"]]
    check("website flow: Add as measurement makes one file “Truthear Gate (Hangout 5128).txt”, in use, the others not",
          came and loaded and used == [NAME + ".txt"] and others and tw.added and tw.isVisible(), (used, others))
    from eq import paths as eq_paths
    with open(os.path.join(eq_paths.MEAS_DIR, NAME + ".txt"), encoding="utf-8") as fh:
        first = fh.readline().strip()
    check("website flow: the file's first line names the website and the link",
          first == f"* Traced from {NAME} with AutoEQ Studio (a picture from {SITE}: {LINK})", first)
    rec = rigs.sources().get(NAME + ".txt") or {}
    check("website flow: the add records the entry's source (its database's website and the entry's name)",
          rec.get("site_url") == "https://graph.hangout.audio/iem/5128/" and rec.get("name") == ENTRY, rec)
    tw.t.v["ppo"] = 24  # (another file under the same name: "… (2).txt"; the same file again keeps its name)
    tw.save("measurement")
    second = sorted(n for n in rigs.sources() if n.startswith(NAME) and n != NAME + ".txt")
    tw.name.setText("My own name")
    tw.t.v["name"] = "My own name"
    tw.save("measurement")
    rig2 = rigs.file_rig(second[0]) if second else None
    check("website flow: the file's rig is 5128 from its source record, also for the name “… (2).txt” and for a name "
          "that the user changed", rig2 == ("5128", True) and rigs.file_rig("My own name.txt") == ("5128", True),
          (second, rig2, rigs.file_rig("My own name.txt")))


def test_target_line(eq_screen, fresh_studio, flow, monkeypatch, check):
    from eq import rigs
    from ui import window_parts
    page = flow["page"]
    came, tw = _traced(flow, monkeypatch, stand_in(target=True))
    note = tw.save_note.text()
    shown = tw.save_line.isVisible()
    check("website flow: a target line shows Add the target line as target…, and the note says so",
          came and shown and "also has a target line" in note and tw.save_line.property("help_key") == "#tr-target-line",
          (shown, note))
    outs = tw.outputs()
    check("website flow: Add as measurement leaves the target line out (one file)",
          [o["file"] for o in outs] == [NAME + ".txt"], [o["file"] for o in outs])
    asked = []
    monkeypatch.setattr(window_parts, "ask_text", lambda *a: (asked.append(a), ("My target", True))[1])
    tw.add_target_line()
    qt.wait_for(lambda: page.inputs.get("active_target") == "My target.txt", 30)
    rec = rigs.sources().get("My target.txt") or {}
    check("website flow: Add the target line as target… asks for the name (the entry's in the default) and adds the "
          "line as the target in use, with the source record under the target's name",
          asked and asked[0][3] == f"Target from {NAME}" and page.inputs.get("active_target") == "My target.txt"
          and rec.get("name") == "My target" and rec.get("site_url") == "https://graph.hangout.audio/iem/5128/",
          (asked, page.inputs.get("active_target"), rec))
    i = next(i for i, c in enumerate(tw.t.curves) if c.get("target"))
    tw.t.cur = i
    tw.t.smooth()  # (the user changes the target line: it is a measurement curve)
    tw.changed()
    tw.show_tab(2)
    check("website flow: a target line that the user changed loses its button, and 3 Save says that it is a "
          "measurement curve", not tw.save_line.isVisible() and "You changed the curve “Target”" in tw.save_note.text()
          and len(tw.outputs()) == 2, tw.save_note.text())


def test_rename_of_target_line(eq_screen, flow, monkeypatch, check):
    from PySide6.QtWidgets import QLineEdit
    came, tw = _traced(flow, monkeypatch, stand_in(target=True))
    tw.show_tab(1)
    box = next(b for b in tw.curves_box.findChildren(QLineEdit) if b.text() == "Target")
    box.setText("R")
    box.textEdited.emit("R")
    check("website flow: a rename of the target line removes its target mark (a measurement curve)",
          came and not any(c.get("target") for c in tw.t.curves) and not tw.save_line.isVisible(),
          [c.get("target") for c in tw.t.curves])


def test_no_target_line(eq_screen, flow, monkeypatch, check):
    came, tw = _traced(flow, monkeypatch, stand_in())
    check("website flow: no target line, the button is not shown", came and not tw.save_line.isVisible()
          and "target line" not in tw.save_note.text())


def test_wait_window_light_and_dark(eq_screen, flow, tmp_path, check):
    from PySide6.QtGui import QImage
    from PySide6.QtWidgets import QLabel
    wait, _o = _use(flow)
    wait.paste()  # (its note shown too)
    qt.pump(100)
    saved = {}
    for name, theme_on in (("light", qt.light), ("dark", qt.dark)):
        theme_on(eq_screen.qapp)
        qt.pump(100)
        path = str(tmp_path / f"wait-{name}.png")
        wait.grab().save(path)
        img = QImage(path)
        saved[name] = (img.width(), img.height(), img.pixelColor(5, 5).lightness())
    qt.light(eq_screen.qapp)
    words = [lab for lab in wait.findChildren(QLabel) if lab.isVisible()]
    whole = all(lab.height() >= lab.heightForWidth(lab.width()) - 1 for lab in words if lab.wordWrap())
    check("website flow: the wait window in light and dark (its picture read back: light behind the words in light, "
          "dark in dark, every line whole)", saved["light"][2] > 128 > saved["dark"][2] and saved["light"][0] >= 480
          and whole, (saved, whole))


def test_tracer_front_when_not_active(eq_screen, flow, monkeypatch, check):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication
    page = flow["page"]
    alerts, trays = [], []
    monkeypatch.setattr(QApplication, "applicationState", staticmethod(lambda: Qt.ApplicationInactive))
    monkeypatch.setattr(QApplication, "alert", staticmethod(lambda w, ms=0: alerts.append(w)))

    class _Win:
        class app:
            @staticmethod
            def tray_message(title, text):
                trays.append((title, text))
    monkeypatch.setattr(page, "window", lambda: _Win)
    came, tw = _traced(flow, monkeypatch, stand_in())
    check("website flow: when the app is not the active program, the taskbar button of the tracer flashes and a tray "
          "message says where the picture is", came and alerts == [tw] and trays
          and trays[0][0] == "AutoEQ Studio has the picture" and f"“{ENTRY}”" in trays[0][1], (alerts, trays))


@pytest.mark.timeout(300)
def test_real_read_from_the_clipboard(eq_screen, flow, monkeypatch, check):
    from helpers.website_graph import truth_reader, website_graph
    from ui import trace_auto
    monkeypatch.setattr(trace_core, "auto_read", REAL_AUTO_READ)
    img, truth = website_graph(plot_w=1000, target="solid")
    monkeypatch.setattr(trace_auto, "read_strip", truth_reader(truth))
    _use(flow)
    _copy(img)
    came = _picture_came(flow["page"], 120)
    tw = flow["page"].tracer
    check("website flow: a drawn graph of the website from the clipboard goes to 3 Save (the real automatic read)",
          came and tw.read_ok is True and tw.pages.currentIndex() == 2 and tw.save_line.isVisible()
          and [o["file"] for o in tw.outputs()] == [NAME + ".txt"], (came, tw.read_ok, tw.status.text()))
