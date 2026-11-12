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
NB = "\N{NO-BREAK SPACE}"  # (between a tab's number and its name in the tracer's words)
WHERE = ("The app uses the first new picture on the clipboard or in the Downloads folder. It only reads the files of "
         "this folder:")
# (the format characters that an entry's words must not keep: zero-width spaces and joiners, direction marks and
# overrides, the word joiner and the isolates, the byte order mark)
FORMAT = [chr(c) for c in (*range(0x200B, 0x2010), *range(0x202A, 0x202F), *range(0x2060, 0x206A), 0xFEFF)]
NOT_GRAPH_WORDS = "Copy a new picture of the graph. Then paste it in the tracer (Ctrl+V)."


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
    monkeypatch.setattr(picture_wait, "POLL_MS", 30)
    monkeypatch.setattr(trace_core, "auto_read", stand_in())
    folder = picture_wait.downloads_folder()
    had = set(os.listdir(folder)) if os.path.isdir(folder) else set()
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
    for name in (set(os.listdir(folder)) if os.path.isdir(folder) else set()) - had:  # (the test's own files)
        os.remove(os.path.join(folder, name))


def _use(f):
    """Find…'s Use on the website entry's row: the wait window (or None) and the links opened."""
    n = len(qt.OPENED_URLS)
    _LAST_USE["since"] = _token(f["page"])
    f["pk"].use_row(f["row"])
    qt.pump(50)
    return getattr(f["page"], "picture_wait", None), qt.OPENED_URLS[n:]


def _copy(img):
    from PySide6.QtWidgets import QApplication
    QApplication.clipboard().setImage(img)


def _graph():
    img, _s = _sample()
    return img


def _one_pixel_changed():
    """The sample graph with one pixel in a different color: the same size, but a different picture (a better picture
    of the same graph, as far as the tracer can know)."""
    from PySide6.QtGui import QColor
    img = _graph().copy()
    c = img.pixelColor(5, 5)
    img.setPixelColor(5, 5, QColor(255 - c.red(), 255 - c.green(), 255 - c.blue()))
    return img


def _closed(wait):
    """The wait window closed (and deleted: the page lets it go when it closes)."""
    from ui import tasks
    return not tasks.alive(wait) or not wait.isVisible()


def _token(page):
    """The tracer's count of pictures and reads (graph_token: each new picture adds to it), -1 with no tracer."""
    tw = getattr(page, "tracer", None)
    return tw.graph_token if tw is not None else -1


_LAST_USE = {"since": None}  # (_token() at the last _use: a picture there from before does not count)


def _picture_came(page, sec=20, since=None):
    """The tracer has the picture and its automatic read has ended (since: _token() before the picture was given, so
    that a picture there from before does not count; by default, the one of the last _use)."""
    since = _LAST_USE["since"] if since is None else since
    return qt.wait_for(lambda: getattr(page, "tracer", None) is not None and page.tracer.t.has_image
                       and not page.tracer.reading_graph and (since is None or page.tracer.graph_token > since), sec)


# ---------------------------------------------------------------- Find… and the wait window
def test_use_opens_link_and_waits(eq_screen, flow, check):
    from PySide6.QtWidgets import QLabel
    from helpers.dialogs import DIALOGS
    asked = len(DIALOGS.asked)
    wait, opened = _use(flow)
    qt.pump(300)  # (a download, if one started, has its answer by now)
    errors = [a for a in DIALOGS.asked[asked:] if a[0] in ("warning", "critical")]
    shown = wait is not None and wait.isVisible()
    words = " ".join(lab.text() for lab in wait.findChildren(QLabel)) if wait is not None else ""
    check("website flow: Use on a website entry opens its link in the browser and shows the wait window with the "
          "entry's name", flow["row"] is not None and opened == [LINK] and shown and f"“{ENTRY}”" in words
          and wait.windowTitle() == "Picture from the website" and wait.parent() is flow["pk"],
          (opened, shown, words[:200]))
    check("website flow: the wait window is window modal on Find… and does not block (Find… stays open)",
          shown and wait.isModal() and flow["pk"].isVisible(), shown)
    check("website flow: after Use on a website entry, Find… started no download behind the wait window (no error "
          "message, its message line empty)", shown and not errors and not flow["pk"].busy and _said(flow["pk"]) == "",
          (errors, flow["pk"].busy, _said(flow["pk"])))


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
    main = (btn.isDefault(), btn.property("help_key"), btn.text(), "F1" not in btn.toolTip())
    btn.click()
    came = _picture_came(page)
    check("website flow: Paste the picture takes the picture that was there before", came and _closed(wait)
          and page.tracer.entry["name"] == ENTRY, came)
    check("website flow: Paste the picture is the main button (the accent, Enter's) and has its help (its tooltip "
          "does not name F1: F1 does nothing in this window)", main == (True, "#pw-paste", "Paste the picture", True),
          main)


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
          gone and pk.isVisible() and _said(pk) == "No new picture came in 10 minutes. Select the entry again.",
          _said(pk))


def test_offline(eq_screen, flow, monkeypatch, check):
    import net
    pk = flow["pk"]
    monkeypatch.setattr(net, "offline", lambda: True)
    wait, opened = _use(flow)
    check("website flow: offline, nothing opens, no wait window, and the line says how to go online",
          not opened and wait is None and _said(pk).startswith("Offline:") and "Online (top right)" in _said(pk)
          and pk.isVisible(), (opened, _said(pk)))


ONE_CURVE = ("The tracer has a curve that you did not add. To keep it, add it in the tracer. "
             "To remove it, click Remove image in the tracer. Then select the entry again.")
CURVES = ("The tracer has curves that you did not add. To keep them, add them in the tracer. To remove them, click "
          "Remove image in the tracer. Then select the entry again.")


def _told():
    """The words of the "do this first" bubble in sight (ui.bubble.tell), or ""."""
    from ui import bubble
    b = bubble.last("tell")
    return b.text.text() if b is not None and b.isVisible() else ""


def _close_bubble():
    from ui import bubble
    b = bubble.last("tell")
    if b is not None:
        b.hide()


def test_no_browser_says_so(eq_screen, flow, monkeypatch, check):
    from PySide6.QtGui import QDesktopServices
    pk = flow["pk"]
    monkeypatch.setattr(QDesktopServices, "openUrl", staticmethod(lambda url: False))
    wait, _o = _use(flow)
    check("website flow: when Windows cannot open the link, Find…'s line says so and no wait starts",
          wait is None and _said(pk) == "Windows cannot open the website of this entry.", _said(pk))


def test_messages_fit_finds_line(eq_screen, flow, monkeypatch, check):
    """Each message of the flow in Find…'s line is whole at Find…'s opening width (900 px): the line cuts a longer
    one at its edge."""
    import net
    from PySide6.QtGui import QDesktopServices, QFontMetrics
    from ui import picture_wait
    pk = flow["pk"]
    pk.resize(900, pk.height())
    qt.pump(100)
    said = {}
    monkeypatch.setattr(net, "offline", lambda: True)
    _use(flow)
    said["offline"] = _said(pk)
    monkeypatch.setattr(net, "offline", lambda: False)
    monkeypatch.setattr(picture_wait, "TIMEOUT_MS", 200)
    wait, _o = _use(flow)
    qt.wait_for(lambda: wait is not None and _closed(wait), 10)
    said["time limit"] = _said(pk)
    with monkeypatch.context() as m:
        m.setattr(QDesktopServices, "openUrl", staticmethod(lambda url: False))
        _use(flow)
        said["no browser"] = _said(pk)
    line = pk.footer.line.text
    fm = QFontMetrics(line.font())
    wide = {k: (fm.horizontalAdvance(t), line.width()) for k, t in said.items()}
    check("website flow: each message in Find…'s line fits it at Find…'s opening width (900 px)",
          pk.width() == 900 and all(t for t in said.values()) and all(w <= room for w, room in wide.values()),
          (said, wide))


def test_tracer_with_curves_not_added(eq_screen, flow, check):
    page, pk = flow["page"], flow["pk"]
    page.open_trace()
    tw = page.tracer
    tw.load_image(_graph(), "Mine")
    qt.wait_for(lambda: not tw.reading, 60)
    tw.t.curves[0]["ys"][100:200] = 300.0  # (a traced part)
    tw.close()
    _close_bubble()
    wait, opened = _use(flow)
    told = _told()
    check("website flow: the tracer with a curve that was not added stops the flow with a bubble (UI-RULES 25) that "
          "names Remove image, in the words for one curve", not opened and wait is None and told == ONE_CURVE
          and _said(pk) == "" and tw.t.src_name == "Mine", (opened, told, _said(pk)))
    tw.t.add_curve()
    tw.t.curves[1]["ys"][300:400] = 250.0
    _close_bubble()
    wait, opened = _use(flow)
    check("website flow: with more than one curve, the bubble has the words for more than one curve",
          not opened and wait is None and _told() == CURVES, _told())
    _close_bubble()
    tw.added = True
    wait, opened = _use(flow)
    check("website flow: after the add of the tracer's curves, the flow starts", opened == [LINK] and wait is not None
          and wait.isVisible(), opened)


def test_entry_route_error_said(eq_screen, flow, check):
    page, pk = flow["page"], flow["pk"]
    n = len(qt.OPENED_URLS)
    _close_bubble()
    started = page.trace_from_website("no-such-entry", over=pk, say=lambda t, ms=10000: pk.footer.say(t, ms))
    check("website flow: an entry that is not in the lists says so in a bubble (its words whole), nothing opens",
          not started and len(qt.OPENED_URLS) == n and "not there" in _told() and _said(pk) == "", (_told(), _said(pk)))


def test_one_wait_at_a_time(eq_screen, flow, check):
    page, pk = flow["page"], flow["pk"]
    wait, _o = _use(flow)
    n = len(qt.OPENED_URLS)
    again = page.trace_from_website(flow["row"]["id"], over=pk, say=pk.footer.say)
    check("website flow: a second call while the wait window is open shows that window and starts nothing",
          not again and page.picture_wait is wait and len(qt.OPENED_URLS) == n)


# ---------------------------------------------------------------- the Downloads folder (the session's stand-in)
def _downloads():
    from ui import picture_wait
    return picture_wait.downloads_folder()


def _stamps(folder):
    return {e.name: (e.stat().st_mtime_ns, e.stat().st_size) for e in os.scandir(folder)}


def test_downloads_folder_is_the_test_folder(eq_screen, flow, monkeypatch, check):
    from PySide6.QtWidgets import QLabel
    from helpers import session
    from ui import picture_wait
    folder = _downloads()
    wait, _o = _use(flow)
    shown = wait.path is not None and wait.path.text() == os.path.normpath(folder) and "Screenshot" in " ".join(
        lab.text() for lab in wait.findChildren(QLabel)) and wait.where.text() == WHERE
    check("website flow: the wait window shows the Downloads folder that it looks at (the session's stand-in)",
          folder and session.inside(folder) and shown, (folder, wait.path and wait.path.text()))
    root, data = os.environ.get("AUTOEQSTUDIO_ROOT"), os.environ.get("AUTOEQSTUDIO_DATA")
    monkeypatch.delenv("AUTOEQSTUDIO_DOWNLOADS")
    copy = picture_wait.downloads_folder()
    check("website flow: a test copy of the app (AUTOEQSTUDIO_ROOT) with no Downloads stand-in looks at no folder",
          root and copy == "", copy)
    monkeypatch.delenv("AUTOEQSTUDIO_ROOT")
    monkeypatch.setenv("AUTOEQSTUDIO_DATA", data or "x")
    only_data = picture_wait.downloads_folder()
    monkeypatch.setenv("AUTOEQSTUDIO_DOWNLOADS", folder)
    check("website flow: a process with only AUTOEQSTUDIO_DATA set (a test copy, as userfiles.py's rule) looks at no "
          "folder unless AUTOEQSTUDIO_DOWNLOADS is set", only_data == "" and picture_wait.downloads_folder() == folder,
          only_data)


def test_old_file_does_not_end_wait(eq_screen, flow, check):
    folder = _downloads()
    _graph().save(os.path.join(folder, "old graph.png"))
    wait, _o = _use(flow)
    qt.pump(600)
    check("website flow: a picture file that was in Downloads before does not end the wait",
          not _closed(wait) and wait.got is None and flow["pk"].isVisible())


def test_new_file_ends_wait(eq_screen, flow, check):
    from ui import picture_wait
    folder = _downloads()
    old, pending, tries = picture_wait.folder_pictures(folder), {}, {}
    path = os.path.join(folder, "Screenshot of the graph.png")
    _graph().save(path)
    first = picture_wait.new_picture(folder, old, pending, tries)
    second = picture_wait.new_picture(folder, old, pending, tries)
    check("website flow: a new picture file in Downloads is read after two equal looks (the first look only notes it)",
          first[0] is None and second[0] is not None and not second[0].isNull() and second[1] is False,
          (first, second))
    os.remove(path)
    page = flow["page"]
    wait, _o = _use(flow)
    qt.wait_for(lambda: wait._old is not None, 10)
    _graph().save(path)
    came = _picture_came(page)
    check("website flow: a new picture file in Downloads ends the wait, and the tracer opens with it",
          came and _closed(wait) and not flow["pk"].isVisible() and page.tracer.entry["name"] == ENTRY, came)


def test_file_not_complete(eq_screen, flow, check):
    from PySide6.QtCore import QBuffer, QByteArray, QIODevice
    from ui import picture_wait
    folder = _downloads()
    data = QByteArray()
    buf = QBuffer(data)
    buf.open(QIODevice.WriteOnly)
    _graph().save(buf, "PNG")
    whole = bytes(data)
    path = os.path.join(folder, "half.png")
    old, pending, tries = picture_wait.folder_pictures(folder), {}, {}
    with open(path, "wb") as fh:
        fh.write(whole[:len(whole) // 2])
    half = [picture_wait.new_picture(folder, old, pending, tries)[0] for _ in range(3)]
    with open(path, "wb") as fh:
        fh.write(whole)
    full = [picture_wait.new_picture(folder, old, pending, tries)[0] for _ in range(2)]
    check("website flow: a file that is not complete (half of a PNG) does not end the wait, the complete file does",
          all(h is None for h in half) and full[0] is None and full[1] is not None and tries.get("half.png", 0) == 0,
          (half, full, tries))
    os.remove(path)
    old, pending, tries = picture_wait.folder_pictures(folder), {}, {}
    with open(path, "wb") as fh:
        fh.write(whole[:100])
    looks = [picture_wait.new_picture(folder, old, pending, tries)[0] for _ in range(picture_wait.READ_TRIES + 2)]
    check("website flow: a file that does not read as a picture is tried some looks, then it is old",
          all(x is None for x in looks) and old.get("half.png") is not None and "half.png" not in pending,
          (old, pending))


def test_not_picture_files(eq_screen, flow, check):
    folder = _downloads()
    wait, _o = _use(flow)
    qt.wait_for(lambda: wait._old is not None, 10)
    for name in ("graph.pdf", "graph.png.crdownload", "graph.png.part"):
        with open(os.path.join(folder, name), "wb") as fh:
            fh.write(b"0" * 5000)
    qt.pump(500)
    check("website flow: a new file that is not a picture (.pdf, .crdownload, .part) does not end the wait",
          not _closed(wait) and wait.got is None)


def test_look_changes_nothing(eq_screen, flow, check):
    from ui import picture_wait
    folder = _downloads()
    _graph().save(os.path.join(folder, "a.png"))
    with open(os.path.join(folder, "b.png"), "wb") as fh:
        fh.write(b"not a picture")
    before = _stamps(folder)
    old, pending, tries = {}, {}, {}
    for _ in range(picture_wait.READ_TRIES + 3):
        picture_wait.new_picture(folder, old, pending, tries)
    wait, _o = _use(flow)
    qt.pump(400)
    check("website flow: the look changes nothing in the folder (names, sizes and times are the same after)",
          _stamps(folder) == before, (before, _stamps(folder)))


def _png(img=None):
    """The bytes of a PNG file (the sample graph, or img)."""
    from PySide6.QtCore import QBuffer, QByteArray, QIODevice
    data = QByteArray()
    buf = QBuffer(data)
    buf.open(QIODevice.WriteOnly)
    (img if img is not None else _graph()).save(buf, "PNG")
    return bytes(data)


def _plain(w, h):
    from PySide6.QtGui import QColor, QImage
    img = QImage(w, h, QImage.Format_RGB888)
    img.fill(QColor("white"))
    return img


def test_error_at_the_first_look(eq_screen, flow, monkeypatch, check):
    """An error of the first look (a drive that does not answer at that moment) must not make each old picture new."""
    folder = _downloads()
    _graph().save(os.path.join(folder, "holiday 2019.png"))
    real, failed = os.scandir, []

    def scandir(path="."):
        if os.path.normcase(os.path.normpath(str(path))) == os.path.normcase(os.path.normpath(folder)) and not failed:
            failed.append(path)
            raise PermissionError(13, "The device does not answer", str(path))
        return real(path)
    monkeypatch.setattr(os, "scandir", scandir)
    wait, _o = _use(flow)
    known = qt.wait_for(lambda: wait._old is not None, 10)
    qt.pump(500)
    check("website flow: an error at the first look keeps the old files not known until a look is successful: an old "
          "picture does not end the wait", failed and known and "holiday 2019.png" in wait._old and not _closed(wait)
          and wait.got is None, (failed, wait._old))


def test_folder_look_with_no_answer(eq_screen, flow, check):
    from ui import picture_wait
    folder = _downloads()
    missing = os.path.join(folder, "not there")
    pending, tries = {}, {}
    check("website flow: a folder that is not there gives no list (not known), and a look with no list of old files "
          "changes nothing", picture_wait.folder_pictures(missing) is None and picture_wait.folder_pictures("") is None
          and picture_wait.new_picture(folder, None, pending, tries) == (None, False) and not pending,
          (picture_wait.folder_pictures(missing), pending))


def test_file_that_another_program_holds(eq_screen, flow, monkeypatch, check):
    """A stand-in for a file that a different program holds with no sharing: it does not open (and Qt reads nothing)
    for 7 looks, then it reads. Each look while it is held is not a try."""
    import builtins
    from PySide6.QtGui import QImage
    from ui import picture_wait
    folder = _downloads()
    old, pending, tries = picture_wait.folder_pictures(folder), {}, {}
    path = os.path.join(folder, "held.png")
    with open(path, "wb") as fh:
        fh.write(_png())
    held = [True]
    same = lambda p: os.path.normcase(os.path.abspath(str(p))) == os.path.normcase(os.path.abspath(path))  # noqa: E731

    def held_open(p, *a, **k):
        if held[0] and same(p):
            raise PermissionError(13, "The file is in use by a different program", str(p))
        return builtins.open(p, *a, **k)
    monkeypatch.setattr(picture_wait, "open", held_open, raising=False)
    monkeypatch.setattr(picture_wait, "QImage", lambda *a: QImage() if held[0] and a and same(a[0]) else QImage(*a))
    during = [picture_wait.new_picture(folder, old, pending, tries)[0] for _ in range(8)]
    counted = dict(tries)
    held[0] = False
    after = [picture_wait.new_picture(folder, old, pending, tries)[0] for _ in range(2)]
    check("website flow: a file that a different program holds for 7 looks is not a try, and it is read after",
          all(x is None for x in during) and not counted and "held.png" not in old and after[0] is not None
          and not after[0].isNull(), (during, counted, after, old.get("held.png")))


def test_folder_rules(eq_screen, flow, check):
    """Short checks of the look's rules with new_picture directly."""
    from ui import picture_wait
    folder = _downloads()
    check("website flow: a picture less than 200 px high is not a graph (400 x 199), 400 x 200 is",
          not picture_wait.big_enough(_plain(400, 199)) and picture_wait.big_enough(_plain(400, 200)))
    old, pending, tries = picture_wait.folder_pictures(folder), {}, {}
    for name in ("graph.png.crdownload", "graph.png.part"):  # (a real PNG, under the browser's names for a download)
        with open(os.path.join(folder, name), "wb") as fh:
            fh.write(_png())
    looks = [picture_wait.new_picture(folder, old, pending, tries)[0] for _ in range(3)]
    check("website flow: a real PNG under the name .crdownload or .part (a download that is not complete) is not used",
          all(x is None for x in looks) and not pending, (looks, pending))
    small = os.path.join(folder, "icon.png")
    _plain(299, 400).save(small)
    looks = [picture_wait.new_picture(folder, old, pending, tries)[0] for _ in range(2)]
    check("website flow: a small picture file in Downloads does not end the wait, and it is old after its first read",
          all(x is None for x in looks) and "icon.png" in old and "icon.png" not in pending and not tries,
          (looks, old.get("icon.png"), tries))
    a, b = os.path.join(folder, "first.png"), os.path.join(folder, "second.png")
    _plain(500, 300).save(a)
    _plain(700, 300).save(b)
    t = time.time()
    os.utime(a, (t - 60, t - 60))  # (the older of the two)
    os.utime(b, (t, t))
    looks = [picture_wait.new_picture(folder, old, pending, tries)[0] for _ in range(2)]
    check("website flow: two new pictures in one look: the newest is used", looks[0] is None and looks[1] is not None
          and looks[1].width() == 700, [x and x.width() for x in looks])
    old, pending, tries = picture_wait.folder_pictures(folder), {}, {}
    _plain(640, 360).save(a)  # (the old file "first.png" changes: a new picture under an old name)
    looks = [picture_wait.new_picture(folder, old, pending, tries)[0] for _ in range(2)]
    check("website flow: an old file that changed (the same name) is a new picture", looks[0] is None
          and looks[1] is not None and looks[1].width() == 640, [x and x.width() for x in looks])


def test_jpeg_file_flag(eq_screen, flow, monkeypatch, check):
    from ui import trace_core
    calls = []
    monkeypatch.setattr(trace_core, "auto_read", stand_in(calls=calls))
    folder = _downloads()
    wait, _o = _use(flow)
    qt.wait_for(lambda: wait._old is not None, 10)
    _graph().save(os.path.join(folder, "graph.jpg"), "JPG", 95)
    came = _picture_came(flow["page"])
    check("website flow: a .jpg file in Downloads goes to the automatic read as a JPEG (its settings depend on it)",
          came and calls and calls[0]["jpeg"] is True and flow["page"].tracer.t.ta["jpeg"] is True, calls)


def test_copied_picture_file(eq_screen, flow, tmp_path, check):
    from PySide6.QtCore import QMimeData, QUrl
    from PySide6.QtWidgets import QApplication
    path = str(tmp_path / "copied graph.png")
    _graph().save(path)
    wait, _o = _use(flow)
    md = QMimeData()
    md.setUrls([QUrl.fromLocalFile(path)])
    QApplication.clipboard().setMimeData(md)
    came = _picture_came(flow["page"])
    check("website flow: a picture file copied in File Explorer (its name on the clipboard) ends the wait",
          came and _closed(wait) and flow["page"].tracer.entry["name"] == ENTRY, came)


def test_ctrl_v_in_the_wait_window(eq_screen, flow, check):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    _copy(_graph())
    wait, _o = _use(flow)
    wait.activateWindow()
    qt.pump(50)
    QTest.keyClick(wait, Qt.Key_V, Qt.ControlModifier)
    came = _picture_came(flow["page"])
    check("website flow: Ctrl+V in the wait window takes the picture on the clipboard", came and _closed(wait), came)


LONG_PATHS = (r"C:\Users\maximilian.mustermann\OneDrive\Dokumente\Eigene_Dateien\Internet\Browser\Downloads",
              r"C:\Users\maximilian.mustermann\OneDrive\Dokumente\Eigene_Dateien\Internet\Browser\Heruntergeladene"
              r"_Bilder\Downloads")


def _cut(wait):
    """The labels of the wait window whose words do not all show: wrapped words with less height than they need or
    a word wider than the label, a label past the window's right edge, the path line drawn wider than its room."""
    from PySide6.QtCore import QPoint, QRect, Qt
    from PySide6.QtGui import QFontMetrics
    from PySide6.QtWidgets import QLabel
    from ui.picture_wait import PathLine
    bad = []
    for lab in wait.findChildren(QLabel):
        if not lab.isVisible() or not lab.text():
            continue
        fm = QFontMetrics(lab.font())
        right = lab.mapTo(wait, QPoint(lab.width(), 0)).x()
        if right > wait.width():
            bad.append(("past the edge", lab.text()[:30], right, wait.width()))
        if isinstance(lab, PathLine):
            if fm.horizontalAdvance(lab.shown_text()) > lab.contentsRect().width():
                bad.append(("path", lab.shown_text()))
        elif lab.wordWrap():
            need = fm.boundingRect(QRect(0, 0, lab.width(), 10000), Qt.TextWordWrap, lab.text())
            if need.width() > lab.width() or lab.height() < lab.heightForWidth(lab.width()) - 1:
                bad.append(("cut", lab.text()[:30], need.width(), lab.width(), lab.height()))
    return bad


def test_long_downloads_path(eq_screen, flow, monkeypatch, check):
    from ui import picture_wait
    from ui.picture_wait import PictureWait
    seen = {}
    # (the paths are not of the test folders: this test's wait windows look at no folder)
    monkeypatch.setattr(picture_wait, "folder_pictures", lambda folder: None)
    for path in LONG_PATHS:
        monkeypatch.setenv("AUTOEQSTUDIO_DOWNLOADS", path)
        wait = PictureWait(flow["pk"], {"name": ENTRY, "site": SITE})
        wait.open()
        qt.pump(200)
        wait.paste()  # (with its note too)
        qt.pump(100)
        seen[len(path)] = (_cut(wait), wait.path.shown_text(), wait.path.toolTip() == path, wait.width())
        wait.reject()
        wait.deleteLater()
    qt.pump(50)
    check("website flow: a long Downloads path with no space (91 and 115 characters): no word of the window is cut, "
          "nothing goes past its right edge, and the path is cut in its middle with “…” (its tooltip whole)",
          sorted(seen) == [91, 115] and all(not v[0] and "…" in v[1] and v[2] and v[3] <= 640 for v in seen.values())
          and all(v[1].startswith("C:\\") and v[1].endswith("Downloads") for v in seen.values()), seen)


def test_screen_reader(eq_screen, flow, monkeypatch, check):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QDialog, QPushButton
    from helpers import paths
    a11y = paths.import_tool("a11y")

    def tab_order(win, first):
        """The controls that Tab goes to, from `first`, one round."""
        out, w = [], first
        for _ in range(50):
            if w is None or (out and w is first):
                break
            if w.isVisible() and w.isEnabled() and w.focusPolicy() & Qt.TabFocus and win.isAncestorOf(w):
                out.append(w.accessibleName() or getattr(w, "text", lambda: "")())
            w = w.nextInFocusChain()
        return out
    wait, _o = _use(flow)
    qt.pump(100)
    desc = wait.accessibleDescription()
    first = wait.focusWidget() or wait.paste_btn
    order = tab_order(wait, first)
    check("website flow: a screen reader reads the wait window's heading and steps (its description), each control "
          "has a name, and Tab goes from Paste the picture to Cancel",
          f"“{ENTRY}”" in desc and "Windows + Shift + S" in desc and "Maximize the window" in desc
          and not a11y.unnamed(wait) and not a11y.unreachable(wait)
          and order[:2] == ["Paste the picture (a picture from the website)", "Cancel"], (desc, order))
    check("website flow: the wait window's description has the folder words and the folder's path, and the window "
          "has its name for a screen reader", f"{WHERE} {os.path.normpath(_downloads())}" in desc
          and wait.accessibleName() == "Picture from the website", (desc, wait.accessibleName()))
    wait.reject()
    came, tw = _traced(flow, monkeypatch, stand_in(target=True))
    seen = {}

    def look(dlg):
        from PySide6.QtWidgets import QLineEdit
        dlg.show()
        qt.pump(100)
        box = dlg.findChild(QLineEdit)
        seen.update(unnamed=a11y.unnamed(dlg), unreachable=a11y.unreachable(dlg), order=tab_order(dlg, box),
                    buttons=[b.text() for b in dlg.findChildren(QPushButton)])
        dlg.hide()
        return QDialog.Rejected
    monkeypatch.setattr(QDialog, "exec", look)
    tw.add_target_line()
    check("website flow: the name box of Add the target line as target… has a name for each control, and Tab goes "
          "from the box to Add to Cancel", came and not seen.get("unnamed") and not seen.get("unreachable")
          and seen.get("order", [])[:3] == ["Name of the target", "Add", "Cancel"]
          and tw.save_line.accessibleName(), seen)


# ---------------------------------------------------------------- the tracer with an entry
def _traced(f, monkeypatch, fake):
    from ui import trace_core
    monkeypatch.setattr(trace_core, "auto_read", fake)
    since = _token(f["page"])
    _use(f)
    _copy(_graph())
    came = _picture_came(f["page"], since=since)
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
          and f"Then go to 3{NB}Save." in tw.status.text(), (tw.pages.currentIndex(), tw.status.text()))


def test_not_a_graph(eq_screen, flow, monkeypatch, check):
    calls = []
    from ui import trace_window
    real = trace_window.TraceWindow.read_labels
    monkeypatch.setattr(trace_window.TraceWindow, "read_labels", lambda self: (calls.append(1), real(self)))
    came, tw = _traced(flow, monkeypatch, stand_in(ok=False, fail="axes_plot"))
    check("website flow: a picture that is not a graph (axes_plot), the tracer shows 1 Axes with the reason and reads "
          "the labels as for any picture", came and tw.pages.currentIndex() == 0 and calls
          and "did not find the grid" in tw.status.text(), (tw.pages.currentIndex(), calls, tw.status.text()))
    qt.wait_for(lambda: not tw.reading, 60)
    check("website flow: for a picture that is not a graph, the words tell the user to copy a new picture and paste "
          "it (not to correct a step), and 1 Axes has one message (the label read's)",
          tw.status.text() == "The app cannot trace this picture automatically. The app did not find the grid of a "
          "graph in this picture. Copy a new picture of the graph. Then paste it in the tracer (Ctrl+V)."
          and "automatically" not in tw.axis_note.text() and "3 Save" not in tw.axis_note.text(),
          (tw.status.text(), tw.axis_note.text()))


def test_error_of_the_read(eq_screen, flow, monkeypatch, check):
    calls = []
    from ui import trace_window
    real = trace_window.TraceWindow.read_labels
    monkeypatch.setattr(trace_window.TraceWindow, "read_labels", lambda self: (calls.append(1), real(self)))
    came, tw = _traced(flow, monkeypatch, stand_in(error="made-up failure"))
    check("website flow: an error of the automatic read gives 1 Axes and today's label read, the entry's name stays",
          came and tw.pages.currentIndex() == 0 and calls and tw.read_ok is False and tw.entry["name"] == ENTRY
          and tw.t.src_name == NAME, (tw.pages.currentIndex(), calls, tw.t.src_name))
    check("website flow: after an error of the read, no Python words on the screen, and the words name 1 Axes and "
          "2 Trace", tw.status.text() == f"The app cannot trace this picture automatically. Do the steps 1{NB}Axes and "
          f"2{NB}Trace manually. Then go to 3{NB}Save."
          and "made-up failure" not in tw.status.text() + tw.axis_note.text(), tw.status.text())


def test_paste_after_poor_picture_keeps_entry(eq_screen, flow, monkeypatch, check):
    from ui import trace_core
    came, tw = _traced(flow, monkeypatch, stand_in(ok=False, fail="axes_hz_labels"))
    monkeypatch.setattr(trace_core, "auto_read", stand_in())
    _copy(_one_pixel_changed())  # (a better picture: the same pixels again are not read again)
    tw.paste()
    again = _picture_came(flow["page"])
    check("website flow: a picture pasted in the tracer after a poor one keeps the entry",
          came and again and tw.entry and tw.entry["name"] == ENTRY and tw.t.src_name == NAME and tw.read_ok is True
          and tw.pages.currentIndex() == 2, (tw.entry, tw.t.src_name, tw.read_ok))
    _copy(_graph().copy(0, 0, 800, 500))
    tw.paste()
    qt.wait_for(lambda: not tw.reading_graph, 20)
    check("website flow: after a read that was OK, a new picture pasted in the tracer is a picture of yours (no entry)",
          tw.entry is None and tw.t.src_name != NAME, (tw.entry, tw.t.src_name))


class _Drop:
    """A stand-in for Qt's drop event: its data only."""

    def __init__(self, md):
        self.md = md

    def mimeData(self):
        return self.md


def test_other_ways_keep_the_entry(eq_screen, flow, monkeypatch, check):
    """After a poor read, a better picture dropped on the tracer or pasted on the Make an EQ page keeps the entry, as
    the same paste in the tracer."""
    from PySide6.QtCore import QMimeData
    from ui import trace_core
    page = flow["page"]
    came, tw = _traced(flow, monkeypatch, stand_in(ok=False, fail="axes_hz_labels"))
    md = QMimeData()
    md.setImageData(_one_pixel_changed())  # (a better picture: not the same pixels)
    tw.dropEvent(_Drop(md))
    again = qt.wait_for(lambda: not tw.reading_graph and tw.read_ok is not None, 20)
    check("website flow: a picture dropped on the tracer after a poor one keeps the entry",
          came and again and tw.entry and tw.entry["name"] == ENTRY and tw.t.src_name == NAME,
          (tw.entry, tw.t.src_name))
    monkeypatch.setattr(trace_core, "auto_read", stand_in())
    _copy(_graph())
    page.paste_picture()  # (Ctrl+V on the Make an EQ page: the main window was the active window)
    came2 = qt.wait_for(lambda: not tw.reading_graph and tw.read_ok is True, 20)
    check("website flow: a picture pasted on the Make an EQ page after a poor read keeps the entry (as in the tracer)",
          came2 and tw.entry and tw.entry["name"] == ENTRY and tw.t.src_name == NAME, (tw.entry, tw.t.src_name))


def test_entry_cleared(eq_screen, flow, monkeypatch, check):
    from ui import guide
    came, tw = _traced(flow, monkeypatch, stand_in())
    tw.remove_image()
    removed = tw.entry is None and not tw.added and tw.read_ok is None
    flow["pk"].show()
    came2, tw = _traced(flow, monkeypatch, stand_in())
    flow["page"].open_trace()  # (the Guide runs on a window in sight)
    tw.remove_image()
    tw.entry = {"name": "Left over", "tag": "X"}  # (as if one were left: the Guide's sample must not keep it)
    tour = guide.start_trace(tw)
    sample = (tw.entry, tw.t.src_name)
    tour.end()
    check("website flow: Remove image and the Guide's sample clear the entry",
          came and came2 and removed and sample == (None, "Sample graph"), (removed, sample))


def test_close_keeps_the_entry(eq_screen, fresh_studio, flow, monkeypatch, check):
    """The entry belongs to the picture: the tracer closed and opened again still adds it with the website and the
    source record (also with a name that the user typed). A close during the read is the same."""
    from eq import paths as eq_paths
    from eq import rigs
    page = flow["page"]
    came, tw = _traced(flow, monkeypatch, stand_in())
    tw.close()
    page.open_trace()
    tw.name.setText("My IEM")
    tw.t.v["name"] = "My IEM"
    tw.save("measurement")
    with open(os.path.join(eq_paths.MEAS_DIR, "My IEM.txt"), encoding="utf-8") as fh:
        first = fh.readline().strip()
    rec = rigs.sources().get("My IEM.txt") or {}
    check("website flow: the tracer closed and opened again: Add as measurement still names the website and the link, "
          "and records the source (the rig, also with a name that the user typed)",
          came and first == f"* Traced from {NAME} with AutoEQ Studio (a picture from {SITE}: {LINK})"
          and rec.get("name") == ENTRY and rigs.file_rig("My IEM.txt") == ("5128", True), (first, rec))
    monkeypatch.setattr(trace_core, "auto_read", stand_in(delay=1.0))
    flow["pk"].show()
    _use(flow)
    _copy(_graph())
    qt.wait_for(lambda: tw.reading_graph, 10)
    tw.close()  # (while the read runs: its answer comes into the closed window)
    done = qt.wait_for(lambda: not tw.reading_graph and tw.read_ok is not None, 20)
    check("website flow: the tracer closed while the read runs: the read's own curves do not stop a new Use",
          done and any(map(tw.t.has_data, tw.t.curves)) and tw.unadded_curves() == 0, tw.unadded_curves())
    page.open_trace()
    tw.name.setText("My IEM 2")
    tw.t.v["name"] = "My IEM 2"
    tw.save("measurement")
    rec = rigs.sources().get("My IEM 2.txt") or {}
    check("website flow: the tracer closed while the read runs, then opened: the add records the source",
          done and tw.read_ok is True and rec.get("name") == ENTRY and rigs.file_rig("My IEM 2.txt") == ("5128", True),
          (done, rec))


def test_close_then_a_picture_of_yours(eq_screen, flow, monkeypatch, check):
    page = flow["page"]
    came, tw = _traced(flow, monkeypatch, stand_in(ok=False, fail="axes_hz_labels"))
    kept = tw.kept_entry() is not None
    tw.close()
    page.open_trace()
    _copy(_graph().copy(0, 0, 800, 500))  # (an unrelated picture: the same one again keeps the result)
    tw.paste()
    qt.wait_for(lambda: not tw.reading_graph, 20)
    check("website flow: after the close of the tracer, an unrelated picture pasted in it gets no entry (also after a "
          "poor read)", came and kept and tw.entry is None and tw.t.src_name != NAME, (kept, tw.entry, tw.t.src_name))


def test_read_curves_do_not_stop_use(eq_screen, flow, monkeypatch, check):
    """A picture from a website whose curves only the automatic read made: a new Use replaces it with no message (the
    tracer closed with its ✕, a different entry). A curve that the user changed stops it with the bubble."""
    page, pk = flow["page"], flow["pk"]
    came, tw = _traced(flow, monkeypatch, stand_in())
    tw.close()
    pk.q.setText("gate")
    pk.render()
    pk.finish_list()
    other = next((r for r in _rows(pk) if r.get("link") and r["name"] == "Tangzu XuanWu Gate"), None)
    pk.show()
    _close_bubble()
    n = len(qt.OPENED_URLS)
    since = _token(page)
    pk.use_row(other)
    qt.pump(50)
    wait = page.picture_wait
    check("website flow: Use, the read OK, the tracer closed with ✕, Use on a different entry: the wait window opens",
          came and other is not None and wait is not None and wait.isVisible() and len(qt.OPENED_URLS) == n + 1
          and not _told(), (other, wait, _told()))
    _copy(_graph())
    came2 = _picture_came(page, since=since) and tw.entry["name"] == "Tangzu XuanWu Gate"
    tw.t.cur = 0
    tw.smooth()  # (the user changes the curve)
    pk.show()
    _close_bubble()
    n = len(qt.OPENED_URLS)
    pk.use_row(other)
    qt.pump(50)
    check("website flow: Use while the tracer has a curve that the user changed: the bubble shows, no browser opens",
          came2 and _told() == ONE_CURVE and len(qt.OPENED_URLS) == n and page.picture_wait is None,
          (came2, _told(), qt.OPENED_URLS[n:], tw.entry, tw.t.undo_stack and len(tw.t.undo_stack)))


def test_added_flags_go_with_a_new_picture(eq_screen, fresh_studio, flow, monkeypatch, check):
    """After an add, a new picture is not "added": its curves stop a new Use; and a pasted picture after an add gets
    no entry."""
    came, tw = _traced(flow, monkeypatch, stand_in(ok=False, fail="trace_band"))
    tw.t.cur = 0
    tw.t.push_undo()
    tw.t.curves[0]["ys"][100:200] = 300.0  # (a curve by hand)
    tw.save("measurement")
    added = tw.added
    _copy(_graph())
    tw.paste()
    qt.wait_for(lambda: not tw.reading_graph, 20)
    no_entry = tw.entry is None and tw.t.src_name != NAME and not tw.added
    tw.t.curves[0]["ys"][100:200] = 300.0  # (the user traces on the new picture)
    flow["pk"].show()
    _close_bubble()
    wait, opened = _use(flow)
    check("website flow: after an add, a pasted picture gets no entry, and its new curves stop a new Use",
          came and added and no_entry and not opened and wait is None and _told() == ONE_CURVE,
          (added, no_entry, opened, _told()))


DELAY = 1.0  # (the stand-in read of test_new_picture_during_the_read)


def test_new_picture_during_the_read(eq_screen, flow, monkeypatch, check):
    """A new picture, or Remove image, while the automatic read runs: the old read's answer is dropped."""
    page = flow["page"]
    fake, ended = stand_in(delay=DELAY), []

    def slow(*a, **k):  # (the stand-in read, and a mark when its thread has the answer)
        try:
            return fake(*a, **k)
        finally:
            ended.append(1)
    monkeypatch.setattr(trace_core, "auto_read", slow)
    _use(flow)
    _copy(_graph())
    qt.wait_for(lambda: getattr(page, "tracer", None) is not None and page.tracer.reading_graph, 10)
    tw = page.tracer
    tw.load_image(_graph().copy(0, 0, 800, 500), "Mine")
    late = qt.wait_for(lambda: len(ended) == 1, 30)  # (the old read's thread has its answer)
    qt.pump(300)  # (the answer comes to the window)
    check("website flow: a new picture during the automatic read: the old read does not replace it, its name is "
          "correct, and the stage and the side panel accept input", late and tw.t.src_name == "Mine" and tw.t.W == 800
          and tw.entry is None and tw.read_ok is None and tw.stage.isEnabled() and tw.side_scroll.isEnabled(),
          (tw.t.src_name, tw.t.W, tw.stage.isEnabled(), tw.side_scroll.isEnabled()))
    flow["pk"].show()
    _use(flow)
    _copy(_graph())
    qt.wait_for(lambda: tw.reading_graph, 10)
    tw.remove_image()
    late = qt.wait_for(lambda: len(ended) == 2, 30)
    qt.pump(300)
    check("website flow: Remove image during the automatic read: the picture does not come back, and the stage and "
          "the side panel accept input", late and not tw.t.has_image and tw.entry is None and tw.stage.isEnabled()
          and tw.side_scroll.isEnabled(), (tw.t.has_image, tw.t.src_name))


def test_keys_during_the_read(eq_screen, flow, monkeypatch, check):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    page = flow["page"]
    monkeypatch.setattr(trace_core, "auto_read", stand_in(delay=1.5))
    _use(flow)
    _copy(_graph())
    qt.wait_for(lambda: getattr(page, "tracer", None) is not None and page.tracer.reading_graph, 10)
    tw = page.tracer
    for key in (Qt.Key_A, Qt.Key_Delete, Qt.Key_S):
        QTest.keyClick(tw, key)
    qt.pump(50)
    unchanged = tw.reading_graph and not any(map(tw.t.has_data, tw.t.curves)) and not tw.t.undo_stack
    _copy(_graph().copy(0, 0, 800, 500))
    QTest.keyClick(tw, Qt.Key_V, Qt.ControlModifier)
    qt.pump(100)
    check("website flow: while the automatic read runs, the keys A, Delete and S change nothing, and Ctrl+V loads a "
          "new picture", unchanged and tw.t.W == 800 and not tw.reading_graph, (unchanged, tw.t.W))


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


CHANGED_LINE = ("You changed the curve “Target”. Thus, it is a measurement curve: Add as measurement also adds it. To "
                "add it as a target, select it. Then click Add as target. To remove it from the measurement, click its "
                f"✕ (Remove curve) on 2{NB}Trace.")


def _values(path):
    """The (Hz, dB) rows of a curve file (the lines that are numbers)."""
    import re
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            parts = re.split(r"[\s,;]+", line.strip())
            try:
                out.append((float(parts[0]), float(parts[1])))
            except (ValueError, IndexError):
                continue
    return out


def _sample_db(which):
    """f(Hz) -> dB of a curve of the sample graph (its pixel points through the graph's axes): "target", or a
    channel's index."""
    _img, s = _sample()
    pts = s["target"] if which == "target" else s["curves"][which]
    lf = np.array([math.log10(20) + (x - SL) / (SW - SL - SR) * 3 for x, _y in pts])
    db = np.array([HI - (y - ST) / (SH - ST - SB) * (HI - LO) for _x, y in pts])
    return lambda f: float(np.interp(math.log10(f), lf, db))


def _error(rows, fn, lo=30, hi=15000):
    """(mean, largest) difference in dB of rows against fn, from lo to hi Hz."""
    d = [abs(db - fn(f)) for f, db in rows if lo <= f <= hi]
    return (float(np.mean(d)), float(np.max(d))) if d else (99.0, 99.0)


def test_target_line(eq_screen, fresh_studio, flow, monkeypatch, check):
    from eq import rigs
    from ui import window_parts
    page = flow["page"]
    came, tw = _traced(flow, monkeypatch, stand_in(target=True))
    note = tw.save_note.text()
    shown = tw.save_line.isVisible()
    check("website flow: a target line shows Add the target line as target…, and the note says so",
          came and shown and "also has a target line" in note
          and tw.save_line.property("help_key") == "#tr-target-line", (shown, note))
    outs = tw.outputs()
    check("website flow: Add as measurement leaves the target line out (one file)",
          [o["file"] for o in outs] == [NAME + ".txt"], [o["file"] for o in outs])
    asked = []
    monkeypatch.setattr(window_parts, "ask_text", lambda *a: (asked.append(a), ("My target", True))[1])
    cur = tw.t.cur
    tw.add_target_line()
    qt.wait_for(lambda: page.inputs.get("active_target") == "My target.txt", 30)
    rec = rigs.sources().get("My target.txt") or {}
    check("website flow: Add the target line as target… asks for the name (the entry's in the default) and adds the "
          "line as the target in use, with the source record under the target's name",
          asked and asked[0][3] == f"Target from {NAME}" and page.inputs.get("active_target") == "My target.txt"
          and rec.get("name") == "My target" and rec.get("site_url") == "https://graph.hangout.audio/iem/5128/",
          (asked, page.inputs.get("active_target"), rec))
    from eq import paths as eq_paths
    saved = _values(os.path.join(eq_paths.TARGET_DIR, "My target.txt"))
    err_tgt, err_meas = _error(saved, _sample_db("target")), _error(saved, _sample_db(0))
    check("website flow: the saved target file has the values of the picture's target line (not of the measurement "
          "curve), and the selected curve is the same after the add",
          len(saved) > 50 and err_tgt[0] <= 0.3 and err_meas[0] > 1.0 and tw.t.cur == cur,
          (len(saved), err_tgt, err_meas, tw.t.cur, cur))
    i = next(i for i, c in enumerate(tw.t.curves) if c.get("target"))
    tw.t.cur = i
    tw.t.smooth()  # (the user changes the target line: it is a measurement curve)
    tw.changed()
    tw.show_tab(2)
    check("website flow: a target line that the user changed loses its button, and 3 Save says that it is a "
          "measurement curve and how to keep it out of the measurement",
          not tw.save_line.isVisible() and tw.save_note.text() == CHANGED_LINE and len(tw.outputs()) == 2,
          tw.save_note.text())


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


def test_website_graph_is_not_compensated(eq_screen, flow, monkeypatch, check):
    """"The graph shows" selected for a picture before (a difference from a target) does not stay for a picture from a
    website: the app would add that target to the website's curve."""
    page = flow["page"]
    page.open_trace()
    tw = page.tracer
    tw.load_image(_graph(), "Mine")
    targets = [tw.comp.itemData(i) for i in range(tw.comp.count()) if tw.comp.itemData(i)]
    if targets:
        tw.comp.setCurrentIndex(tw.comp.findData(targets[0]))
    before = tw.comp.currentData()
    qt.wait_for(lambda: not tw.reading, 60)
    tw.close()
    came, tw = _traced(flow, monkeypatch, stand_in())
    outs = tw.outputs()
    plain = tw.t.outputs(False, None, tw.source_note())
    first = outs[0]["text"].splitlines()[0]
    check("website flow: a compensation selected for a picture before, then a picture from a website: “The graph "
          "shows” is the response, and the file has no target added (its first line, its values)",
          came and before and tw.comp.currentData() == "" and "the app added this target" not in first
          and outs[0]["text"] == plain[0]["text"], (before, tw.comp.currentData(), first))


def test_line_end_in_entry_name(eq_screen, flow, monkeypatch, check):
    """An entry's words come from a website's list: a line end in its name must not make data lines in the file."""
    page = flow["page"]
    entry = page.svc.call("/api/db/entry", {"id": flow["row"]["id"]})["entry"]
    page.open_trace()
    tw = page.tracer
    tw.load_image(_graph(), entry=dict(entry, name="Evil\n20 99\n30 99", site="Site\r\nX"))
    qt.wait_for(lambda: not tw.reading_graph and tw.read_ok is not None, 20)
    text = tw.outputs()[0]["text"]
    lines = text.splitlines()
    data_from_name = [ln for ln in lines if ln.strip() in ("20 99", "30 99 (Hangout 5128) with AutoEQ Studio")
                      or ln.startswith(("20 99", "30 99"))]
    check("website flow: a line end in the entry's name: the file has one comment line and no data line from the name, "
          "and the name box has one line", sum(ln.startswith("*") for ln in lines) == 1 and not data_from_name
          and lines[0].startswith("* Traced from Evil 20 99 30 99 (Hangout 5128)") and "Site X" in lines[0]
          and "\n" not in tw.name.text() and "\n" not in tw.save_note.text(), (lines[:3], tw.name.text()))
    # (a right-to-left override showed the name in reverse; the other format characters are not visible)
    from ui.picture_wait import PictureWait
    rlo = "Gate\N{RIGHT-TO-LEFT OVERRIDE}gnp.exe"
    tw.load_image(_graph(), entry=dict(entry, name=rlo, site="Site\N{ZERO WIDTH SPACE}\N{LEFT-TO-RIGHT MARK}"))
    qt.wait_for(lambda: not tw.reading_graph and tw.read_ok is not None, 20)
    out = tw.outputs()[0]
    wait = PictureWait(flow["pk"], dict(entry, name=rlo))
    shown = {"heading": wait.head.text(), "top row": tw.file_lab.whole, "name box": tw.name.text(),
             "file name": out["file"], "first line": out["text"].splitlines()[0]}
    wait.deleteLater()
    marked = {k: v for k, v in shown.items() if any(c in v for c in FORMAT)}
    check("website flow: a right-to-left override (U+202E) and the other format characters in the entry's words: no "
          "such character in the heading of the wait window, the top row, the name box, the file name and its first "
          "line", not marked and "Gategnp.exe" in shown["heading"] and shown["file name"].startswith("Gategnp.exe"),
          {k: ascii(v) for k, v in shown.items()})


def test_entry_words_on_one_line(eq_screen, flow, monkeypatch, check):
    """A tab, U+0085, a C1 and a C0 control character and spaces at the ends of an entry's words: one line, through
    one_line, the wait window itself, and the flow from the route to the tray message."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication
    from ui.picture_wait import PictureWait, one_line
    words = [one_line(t) for t in (" Gate\tX\N{NEXT LINE}Y\x9bZ\x07 ", "\x00Gate\x7f")]
    fmt = [one_line(f"A{c}B") for c in FORMAT]
    # (2026-11-11: a format character has no width, so it goes with no space: this check had "A B")
    check("website flow: one_line makes a tab, U+0085, a C1 and a C0 control character one space, removes each format "
          "character with no space, and removes the spaces at the ends", words == ["Gate X Y Z", "Gate"]
          and fmt == ["AB"] * len(FORMAT), (words, [ascii(f) for f in fmt if f != "AB"]))
    wait = PictureWait(flow["pk"], {"name": "Gate\tX\N{NEXT LINE}Y", "site": SITE})
    head = wait.head.text()
    wait.deleteLater()
    check("website flow: the wait window puts the entry's words on one line (also when its caller did not)",
          head == "The app waits for a picture of “Gate X Y”…", ascii(head))
    page = flow["page"]
    real = page.svc.call

    def call(route, body=None):
        r = real(route, body)
        if route == "/api/db/entry" and r.get("entry"):
            r = dict(r, entry=dict(r["entry"], name="Gate\tX\N{NEXT LINE}Y\x9b"))
        return r
    monkeypatch.setattr(page.svc, "call", call)
    trays = []
    monkeypatch.setattr(QApplication, "applicationState", staticmethod(lambda: Qt.ApplicationInactive))
    monkeypatch.setattr(QApplication, "alert", staticmethod(lambda w, ms=0: None))

    class _Win:
        class app:
            @staticmethod
            def tray_message(title, text):
                trays.append(text)
    monkeypatch.setattr(page, "window", lambda: _Win)
    wait, _o = _use(flow)
    heading = wait.head.text() if wait is not None else ""
    _copy(_graph())
    came = _picture_came(page)
    check("website flow: a name with a tab, U+0085 and a C1 control character through Find…'s Use: the heading of the "
          "wait window, the tracer's name and the tray message have it on one line",
          came and heading == "The app waits for a picture of “Gate X Y”…" and trays
          and trays[0] == "The tracer shows the graph of “Gate X Y”. Go to the window of the tracer."
          and page.tracer.t.src_name == f"Gate X Y ({TAG})", (ascii(heading), [ascii(t) for t in trays]))


def test_zero_width_character_in_a_word(eq_screen, flow, check):
    """A character with no width in a word of an entry's name (a zero-width space, a joiner, a direction mark, the
    byte order mark, a soft hyphen) goes with no space: the name showed as "Ga te" (2026-11-11). A line end, a tab
    and a control character still become one space."""
    from ui.picture_wait import PictureWait, clean_entry, one_line
    no_width = [*FORMAT, chr(0xAD), chr(0x061C), chr(0x180E)]  # (also the soft hyphen, two marks of other scripts)
    words = {ascii(c): one_line(f"Ga{c}te") for c in no_width}
    spaces = {ascii(c): one_line(f"Ga{c}te") for c in ("\n", "\r\n", "\t", chr(0x85), chr(0x2028), chr(0x9B),
                                                        chr(0x07), "\N{ZERO WIDTH SPACE} \N{ZERO WIDTH SPACE}")}
    name = "Truthear Ga\N{ZERO WIDTH SPACE}te\N{ZERO WIDTH JOINER}"
    wait = PictureWait(flow["pk"], {"name": name, "site": "Site\N{LEFT-TO-RIGHT MARK}s"})
    head = wait.head.text()
    intro = wait.accessibleDescription()
    wait.deleteLater()
    page = flow["page"]
    entry = page.svc.call("/api/db/entry", {"id": flow["row"]["id"]})["entry"]
    page.open_trace()
    tw = page.tracer
    tw.load_image(_graph(), entry=dict(entry, name=name))
    qt.wait_for(lambda: not tw.reading_graph and tw.read_ok is not None, 20)
    shown = (tw.file_lab.whole, tw.name.text(), tw.outputs()[0]["file"], clean_entry({"name": name})["name"])
    check("website flow: a character with no width in a word goes with no space (each format character, the soft "
          "hyphen)", all(v == "Gate" for v in words.values()), {k: ascii(v) for k, v in words.items() if v != "Gate"})
    check("website flow: a line end, a tab, U+0085, U+2028 and a control character in a word become one space",
          all(v == "Ga te" for v in spaces.values()), {k: ascii(v) for k, v in spaces.items()})
    check("website flow: a name with a zero-width space and a joiner: the wait window, the tracer's top row, the Name "
          "box and the file name show “Truthear Gate”", "“Truthear Gate”" in head and "Sites" in intro
          and shown[0] == shown[1] == f"Truthear Gate ({TAG})" and shown[2].startswith("Truthear Gate (")
          and shown[3] == "Truthear Gate", (ascii(head), [ascii(v) for v in shown]))


def test_entry_words_are_plain_text(eq_screen, flow, check):
    """An entry's words from a list with "<b>" or "<img>": shown as these characters (plain text), not as bold words
    or a picture, in the wait window and in the tracer."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QLabel
    from ui.picture_wait import PictureWait
    html, site = "<b>Gate</b> & <img src=x>", "<i>Site</i>"
    wait = PictureWait(flow["pk"], {"name": html, "site": site})
    labels = {lab.text(): lab.textFormat() for lab in wait.findChildren(QLabel)
              if html in lab.text() or site in lab.text()}
    wait.deleteLater()
    check("website flow: the heading and the intro of the wait window show the entry's words as plain text",
          len(labels) == 2 and all(f == Qt.PlainText for f in labels.values()), labels)
    page = flow["page"]
    entry = page.svc.call("/api/db/entry", {"id": flow["row"]["id"]})["entry"]
    page.open_trace()
    tw = page.tracer
    tw.load_image(_graph(), entry=dict(entry, name=html))
    qt.wait_for(lambda: not tw.reading_graph and tw.read_ok is not None, 20)
    tw.show_tab(2)
    qt.pump(50)
    top, note = tw.file_lab, tw.save_note
    check("website flow: the tracer's top row and the note of 3 Save show the entry's words as plain text",
          top.textFormat() == Qt.PlainText and html in top.whole and note.textFormat() == Qt.PlainText
          and f"“{html}”" in note.text(), (top.textFormat(), top.whole, note.textFormat(), note.text()))


def test_entry_words_in_tooltips(eq_screen, flow, check):
    """An entry's name with "<b>" or "<img>" in a tooltip (the wait window's heading, the tracer's top row): Qt shows
    a tooltip that looks like rich text as rich text, so the tooltip is the name escaped in <qt> and shows its
    characters. A usual name's tooltip is the name itself."""
    import html as html_words
    from PySide6.QtGui import QTextDocument
    from ui.picture_wait import PictureWait

    def shows(tip):  # (the characters that Qt shows for the tooltip)
        doc = QTextDocument()
        doc.setHtml(tip)
        return doc.toPlainText()
    hostile = "<b>Gate</b> & <img src=x>"
    tips = {}
    for name in (hostile + " Word" * 20, ENTRY + " Word" * 20):
        wait = PictureWait(flow["pk"], {"name": name, "site": SITE})
        tips[name[:4]] = (name, wait.head.toolTip())
        wait.deleteLater()
    page = flow["page"]
    entry = page.svc.call("/api/db/entry", {"id": flow["row"]["id"]})["entry"]
    page.open_trace()
    tw = page.tracer
    for name in (hostile, ENTRY):
        tw.load_image(_graph(), entry=dict(entry, name=name))
        qt.wait_for(lambda: not tw.reading_graph and tw.read_ok is not None, 20)
        tips["top " + name[:4]] = (f"{name} ({TAG})", tw.file_lab.toolTip(), tw.file_lab.accessibleName())
    long_name, tip = tips["<b>G"]
    top_name, top_tip, top_read = tips["top <b>G"]
    check("website flow: a name with “<b>” and “<img>”: the tooltip of the wait window's heading and of the tracer's "
          "top row is the name escaped in <qt>, and it shows the name's characters",
          tip == f"<qt>{html_words.escape(long_name)}</qt>" and shows(tip) == long_name
          and top_tip == f"<qt>{html_words.escape(top_name)}</qt>" and shows(top_tip) == top_name, tips)
    check("website flow: a usual name's tooltip is the name itself (the heading's and the top row's)",
          tips[ENTRY[:4]][1] == tips[ENTRY[:4]][0] and tips["top " + ENTRY[:4]][1] == NAME, tips)
    check("website flow: a name with “<b>” and “<img>”: the top row's name for a screen reader is the name itself "
          "(not the escaped form)", top_read == top_name, top_read)


def test_long_entry_name(eq_screen, flow, check):
    """A name of 500 characters (a damaged list): the heading shows NAME_MAX characters at most, then "…", the whole
    name in its tooltip, and no word of the window is cut."""
    from ui.picture_wait import NAME_MAX, PictureWait
    seen = {}
    for name in ("A" * 500, "Word " * 100, ENTRY):
        wait = PictureWait(flow["pk"], {"name": name, "site": SITE})
        wait.open()
        qt.pump(200)
        wait.paste()  # (with its note too)
        qt.pump(100)
        head = wait.head.text()
        shown = head[len("The app waits for a picture of “"):-len("”…")]
        seen[name[:5]] = (wait.width(), _cut(wait), len(shown), shown.endswith("…"), wait.head.toolTip())
        wait.reject()
        wait.deleteLater()
    qt.pump(50)
    long_ok = all(v[0] == 520 and not v[1] and v[2] <= NAME_MAX + 1 and v[3] for k, v in seen.items() if k != ENTRY[:5])
    check("website flow: a name of 500 characters, with no space and with spaces: the window is 520 px wide, no label "
          "is cut, the heading has 80 characters of the name at most and “…”, its tooltip has the whole name",
          long_ok and seen["AAAAA"][4] == "A" * 500 and seen["Word "][4] == ("Word " * 100).strip(),
          {k: v[:4] for k, v in seen.items()})
    check("website flow: a usual name is whole in the heading, with no tooltip",
          seen[ENTRY[:5]][2] == len(ENTRY) and seen[ENTRY[:5]][4] == "", seen[ENTRY[:5]])
    check("website flow: the heading has 80 characters of a long name at most and “…” (81 characters together); a "
          "name of words has 79 characters (the 80th is a space) and “…”",
          all(v[2] <= 81 and v[3] for k, v in seen.items() if k != ENTRY[:5]) and seen["Word "][2] == 80,
          {k: v[2] for k, v in seen.items()})


def _side_on_save(tw):
    """3 Save's side as it shows: the side's width, and the visible controls whose right edge is past the side's."""
    from PySide6.QtCore import QPoint
    from PySide6.QtWidgets import QWidget
    vp = tw.side_scroll.viewport()
    past = [(type(w).__name__, w.mapTo(vp, QPoint(w.width(), 0)).x())
            for w in tw.pages.currentWidget().findChildren(QWidget)
            if w.isVisibleTo(tw) and w.mapTo(vp, QPoint(w.width(), 0)).x() > vp.width()]
    return tw.side_scroll.widget().width(), past


def test_long_name_on_3_save(eq_screen, fresh_studio, flow, monkeypatch, tmp_path, check):
    """A name of 500 characters (a damaged list) on 3 Save: the side is as wide as with a usual name, each control is
    in it (the Name box, "The graph shows" and the note went past its right edge), the note has 80 characters of the
    name at most and "…", and the Name box has the whole name (it scrolls). The same after Add as measurement and
    after Save .txt… (their notes have the file's name)."""
    from PySide6.QtWidgets import QFileDialog
    page = flow["page"]
    entry = page.svc.call("/api/db/entry", {"id": flow["row"]["id"]})["entry"]
    page.open_trace()
    tw = page.tracer
    usual = tw.size()
    seen, saved, room = {}, {}, {}
    for name in (ENTRY, "A" * 500, ("Word " * 100).strip(), "W" * 80):
        tw.load_image(_graph(), entry=dict(entry, name=name))
        qt.wait_for(lambda: not tw.reading_graph and tw.read_ok is not None, 20)
        tw.show_tab(2)
        note = tw.save_note
        for which, size in (("usual", usual), ("smallest", tw.minimumSize().expandedTo(tw.minimumSizeHint()))):
            tw.resize(size)
            qt.pump(150)
            words = note.text()
            shown = words[words.find("“") + 1:words.find("”")]
            seen[(name[:5], which)] = (*_side_on_save(tw), shown, note.minimumSizeHint().width() <= note.width(),
                                       tw.name.text() == f"{name} ({TAG})")
            room[(name[:5], which)] = (tw.note_room(), note.width())
        tw.resize(usual)
        qt.pump(150)
        # (Save .txt…: a file's name of 100 characters with no space, or the usual name)
        path = str(tmp_path / ((name[:100] if " " not in name else ENTRY) + " file.txt"))
        monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a, path=path, **k: (path, ""))
        tw.save_txt()
        qt.pump(150)
        saved[(name[:5], "txt")] = (*_side_on_save(tw), note.text(), os.path.exists(path))
        tw.save("measurement")  # (Add as measurement: the note names the file that the app made)
        qt.pump(150)
        saved[(name[:5], "add")] = (*_side_on_save(tw), note.text(), tw.added)
    usual_side = {w: v[0] for (k, w), v in seen.items() if k == ENTRY[:5]}
    check("website flow: a name of 500 characters (with no space, with spaces) on 3 Save: the side is as wide as with "
          "a usual name, no control goes past its right edge, at the usual and the smallest size of the window",
          len(seen) == 8 and all(v[0] == usual_side[w] and not v[1] for (_k, w), v in seen.items()),
          {k: v[:2] for k, v in seen.items()})
    check("website flow: the same after Save .txt… and after Add as measurement (the note has the file's name): the "
          "file is made, the side is as wide as with a usual name, no control goes past its right edge",
          len(saved) == 8 and all(v[3] and v[0] == usual_side["usual"] and not v[1] for v in saved.values())
          and all(v[2].startswith("The app saved ") for v in saved.values())
          and f"“{NAME}”" in saved[(ENTRY[:5], "add")][2] and f"{ENTRY} file.txt" in saved[(ENTRY[:5], "txt")][2],
          {k: (v[0], v[1], v[3], v[2][:60]) for k, v in saved.items()})
    check("website flow: the room for a name in 3 Save's note is the note's width at the smallest size of the window",
          all(r[0] == r[1] for (_k, w), r in room.items() if w == "smallest")
          and all(r[0] <= r[1] for r in room.values()), room)
    check("website flow: 3 Save's note has 80 characters of a long name at most and “…”, the whole note in its room; "
          "the Name box has the whole name; a usual name is whole in the note",
          all(len(v[2]) <= 81 and v[2].endswith("…") and v[3] and v[4] for (k, _w), v in seen.items() if k != ENTRY[:5])
          and all(v[2] == ENTRY and v[3] and v[4] for (k, _w), v in seen.items() if k == ENTRY[:5]),
          {k: (len(v[2]), v[3], v[4]) for k, v in seen.items()})


def test_window_as_high_as_its_words(eq_screen, flow, check):
    """The wait window is as high as its words need at its width, also when that is more than two thirds of the
    screen (Qt's limit for adjustSize: on a small screen at 150 %, it cut the last line of step 2)."""
    from ui.picture_wait import PictureWait
    seen = {}
    for site in (SITE, " ".join(["Site"] * 600)):
        wait = PictureWait(flow["pk"], {"name": ENTRY, "site": site})
        wait.open()
        qt.pump(200)
        first = (wait.height(), wait.heightForWidth(wait.width()))
        wait.paste()  # (M2: the note makes the window higher)
        qt.pump(100)
        after = (wait.height(), wait.heightForWidth(wait.width()), wait.note.isVisible())
        seen[len(site)] = (first, after, wait.screen().availableGeometry().height() * 2 // 3, _cut(wait))
        wait.reject()
        wait.deleteLater()
    qt.pump(50)
    check("website flow: the wait window is as high as its words need at its width when it opens and after the note "
          "(M2), also past two thirds of the screen, and no line is cut",
          all(f[0] == f[1] and a[0] == a[1] > f[0] and a[2] and not cut for f, a, _lim, cut in seen.values())
          and max(v[1][0] for v in seen.values()) > max(v[2] for v in seen.values()), seen)


def test_page_paste_of_a_picture_file(eq_screen, flow, monkeypatch, tmp_path, check):
    """The Make an EQ page's paste: a picture file copied in File Explorer after a poor read keeps the entry; a picture
    after a read that was OK gets none."""
    from PySide6.QtCore import QMimeData, QUrl
    from PySide6.QtWidgets import QApplication
    from ui import trace_core
    page = flow["page"]
    came, tw = _traced(flow, monkeypatch, stand_in(ok=False, fail="axes_hz_labels"))
    path = str(tmp_path / "better graph.png")
    _one_pixel_changed().save(path)  # (a better picture: not the same pixels)
    monkeypatch.setattr(trace_core, "auto_read", stand_in())
    md = QMimeData()
    md.setUrls([QUrl.fromLocalFile(path)])
    QApplication.clipboard().setMimeData(md)
    since = _token(page)
    page.paste_picture()
    again = _picture_came(page, since=since) and tw.read_ok is True
    check("website flow: a picture file copied in File Explorer and pasted on the Make an EQ page after a poor read "
          "keeps the entry", came and again and tw.entry and tw.entry["name"] == ENTRY and tw.t.src_name == NAME,
          (again, tw.entry, tw.t.src_name))
    _copy(_graph().copy(0, 0, 800, 500))
    since = _token(page)
    page.paste_picture()
    qt.wait_for(lambda: tw.graph_token > since and not tw.reading_graph and not tw.reading, 60)
    check("website flow: after a read that was OK, a picture pasted on the Make an EQ page gets no entry",
          tw.graph_token > since and tw.entry is None and tw.t.src_name != NAME, (tw.entry, tw.t.src_name))


def test_white_picture_one_message(eq_screen, flow, monkeypatch, check):
    """A picture that is not a graph and has no labels (white): 1 Axes has one message (the label read's), not also
    the status line's words."""
    from ui import trace_core
    monkeypatch.setattr(trace_core, "auto_read", stand_in(ok=False, fail="axes_plot"))
    page = flow["page"]
    _use(flow)
    _copy(_plain(900, 500))
    came = _picture_came(page)
    tw = page.tracer
    qt.wait_for(lambda: not tw.reading, 60)
    note, status = tw.axis_note.text(), tw.status.text()
    check("website flow: a white picture that is not a graph: the status line tells the user to copy a new picture, "
          "and the note of 1 Axes does not repeat it", came and NOT_GRAPH_WORDS in status
          and "automatically" not in note and "Copy a new picture" not in note and "3" not in note, (status, note))


ONE_CHANGE = ("The tracer has a picture with your changes. To remove it, click Remove image in the tracer. Then select "
              "the entry again.")


def test_users_work_stops_use(eq_screen, flow, monkeypatch, check):
    """The user's work on a picture from a website after its read: a rename, a redo step, a typed axis value, a moved
    line. A read that was OK and no change: none. Remove image clears the rename and the close."""
    from PySide6.QtWidgets import QLineEdit
    pk = flow["pk"]
    came, tw = _traced(flow, monkeypatch, stand_in())
    none = (tw.unadded_curves(), tw.changed_picture(), tw.users_work())
    tw.show_tab(1)
    box = next(b for b in tw.curves_box.findChildren(QLineEdit) if b.text() == "Average")
    box.setText("Avg")
    box.textEdited.emit("Avg")
    renamed = (tw.renamed, tw.unadded_curves())
    tw.close()
    flags = (tw.renamed, tw.was_closed)
    tw.remove_image()
    cleared = (tw.renamed, tw.was_closed)
    check("website flow: a read that was OK and no change is not the user's work; a rename is; Remove image clears the "
          "rename and the close", came and none == (0, False, False) and renamed == (True, 1)
          and flags == (True, True) and cleared == (False, False), (none, renamed, flags, cleared))
    pk.show()
    came, tw = _traced(flow, monkeypatch, stand_in())
    tw.t.cur = 0
    tw.smooth()
    tw.undo()
    redo = (bool(tw.t.undo_stack), bool(tw.t.redo_stack), tw.unadded_curves())
    check("website flow: smooth, then undo: the redo step is the user's work (the curve stops a new Use)",
          came and redo == (False, True, 1), redo)
    tw.remove_image()
    pk.show()
    came, tw = _traced(flow, monkeypatch, stand_in(ok=False, fail="axes_db_labels"))
    tw.show_tab(0)
    tw.boxes["d1"].setText("95")
    tw.boxes["d1"].textEdited.emit("95")
    typed = (tw.t.typed["d"], tw.unadded_curves())
    pk.show()
    _close_bubble()
    wait, opened = _use(flow)
    check("website flow: a failed read (axes_db_labels), a typed Top value, then Use: no wait window, the bubble for "
          "the curve", came and typed == (True, 1) and wait is None and not opened and _told() == ONE_CURVE,
          (typed, wait, opened, _told()))
    tw.t.curves[0]["ys"][:] = np.nan  # (as a read that traced no curve)
    tw.changed()
    _close_bubble()
    wait, opened = _use(flow)
    typed_only = (tw.unadded_curves(), tw.changed_picture(), _told())
    tw.t.typed = {"d": False, "f": False}
    no_change = tw.changed_picture()
    tw.t.move_line("y1", tw.t.cal["y1"] + 3)  # (the user drags the top red line)
    moved = tw.changed_picture()
    check("website flow: no curve, but a typed value or a moved line: Use stops with words for a changed picture",
          typed_only == (0, True, ONE_CHANGE) and wait is None and not opened and not no_change and moved,
          (typed_only, no_change, moved))


def test_moved_line_and_users_picture(eq_screen, flow, monkeypatch, check):
    """After a read that was OK, a moved line with a curve there is the user's work (the curve stops a new Use). A
    picture of the user (no entry) with a typed axis value and no curve is a changed picture too (2026-11-11: it was
    replaced with no message; this test held that before)."""
    came, tw = _traced(flow, monkeypatch, stand_in())
    before = tw.unadded_curves()
    tw.t.move_line("y1", tw.t.cal["y1"] + 3)  # (the user drags the top red line)
    moved = (tw.t.moved["d"], tw.unadded_curves())
    check("website flow: after a read that was OK, a moved line with a curve there: the curve is the user's work",
          came and before == 0 and moved == (True, 1), (before, moved))
    tw.load_image(_graph(), entry=dict(tw.entry))  # (a second read that was OK)
    qt.wait_for(lambda: not tw.reading_graph and tw.read_ok is not None, 20)
    again = tw.unadded_curves()
    tw.t.move_line("x1", tw.t.cal["x1"] + 3)  # (the user drags the left blue line)
    moved_hz = (tw.t.moved["d"], tw.t.moved["f"], tw.unadded_curves())
    check("website flow: the same for a moved Hz line (a blue line) after a second read that was OK",
          tw.read_ok is True and again == 0 and moved_hz == (False, True, 1), (again, moved_hz))
    _copy(_graph().copy(0, 0, 800, 500))
    tw.paste()  # (a picture of yours: no entry)
    qt.wait_for(lambda: not tw.reading, 60)
    for c in tw.t.curves:  # (no curve)
        c["ys"][:] = np.nan
    tw.t.typed["d"] = True  # (a typed dB value)
    users = (tw.entry, tw.t.has_image, any(map(tw.t.has_data, tw.t.curves)), tw.changed_picture())
    check("website flow: a picture of the user (no entry) with a typed axis value and no curve: a changed picture "
          "(a new Use stops for it)", users == (None, True, False, True), users)


def _change(tw, what):
    """A change of the user on 3 Save, as its signals come from a click or a key: the Name box, "The graph shows",
    "Points in each octave" or the range to save."""
    tw.show_tab(2)
    if what == "name":
        tw.name.setText("My name")
        tw.name.textEdited.emit("My name")
    elif what == "comp":
        tw.comp.activated.emit(0)  # (the user selects a row of the list: also the one that it had)
    elif what == "ppo":
        i = tw.ppo.findData(24)
        tw.ppo.setCurrentIndex(i)
        tw.ppo.activated.emit(i)
    else:
        tw.boxes["fmin"].setText("30")
        tw.boxes["fmin"].textEdited.emit("30")


def _no_curve(tw):
    for c in tw.t.curves:
        c["ys"][:] = np.nan
    tw.changed()


def test_changes_of_3_save_stop_use(eq_screen, flow, monkeypatch, check):
    """A changed Name box, "The graph shows", "Points in each octave" or range to save is the user's work: a new Use
    stops for it, with a curve (the words for the curve) and with no curve (the words for a changed picture), for a
    picture from a website and for a picture of the user. The values that the automatic read and the automatic
    settings set are not the user's work, and a picture with no change is replaced. (2026-11-11: these changes did
    not count, and a new Use replaced them with no message.)"""
    pk = flow["pk"]
    kinds = ("name", "comp", "ppo", "range")
    seen = {}
    for what in kinds:
        came, tw = _traced(flow, monkeypatch, stand_in())
        before = (tw.unadded_curves(), tw.changed_picture(), tw.users_work(), set(tw.edited))
        _change(tw, what)
        with_curve = (tw.unadded_curves(), tw.users_work())
        _no_curve(tw)
        no_curve = tw.changed_picture()
        pk.show()
        _close_bubble()
        wait, opened = _use(flow)
        seen[("entry", what)] = (came, before, with_curve, no_curve, wait is None and not opened, _told())
        _close_bubble()
        if wait is not None:  # (Use did not stop: the wait closed, for the next step)
            wait.reject()
        tw.remove_image()
        pk.show()
    for what in kinds:
        page = flow["page"]
        page.open_trace()
        tw = page.tracer
        tw.load_image(_graph().copy(0, 0, 900, 600), "Mine")  # (a picture of yours: no entry)
        qt.wait_for(lambda tw=tw: not tw.reading and not tw.loading, 60)
        _no_curve(tw)
        before = (tw.entry, tw.changed_picture(), tw.users_work())
        _change(tw, what)
        _close_bubble()
        wait, opened = _use(flow)
        seen[("yours", what)] = (before, tw.changed_picture(), wait is None and not opened, _told())
        _close_bubble()
        if wait is not None:
            wait.reject()
        tw.remove_image()
        pk.show()
    tw.load_image(_graph().copy(0, 0, 900, 600), "Mine")
    qt.wait_for(lambda: not tw.reading and not tw.loading, 60)
    _no_curve(tw)
    tw.make_auto(None)  # (the automatic settings set the values of 3 Save again)
    unchanged = (tw.changed_picture(), tw.users_work(), set(tw.edited))
    wait, opened = _use(flow)
    replaced = wait is not None and bool(opened)
    if wait is not None:
        wait.reject()
    check("website flow: after a read that was OK, a changed Name box, “The graph shows”, “Points in each octave” or "
          "range to save is the user's work: with the curve, Use stops with the words for the curve; with no curve, "
          "with the words for a changed picture", all(
              v[0] and v[1] == (0, False, False, set()) and v[2] == (1, True) and v[3] and v[4] and v[5] == ONE_CHANGE
              for k, v in seen.items() if k[0] == "entry"), {k: v for k, v in seen.items() if k[0] == "entry"})
    check("website flow: a picture of the user (no entry, no curve) with each of these changes: Use stops with the "
          "words for a changed picture", all(v[0] == (None, False, False) and v[1] and v[2] and v[3] == ONE_CHANGE
                                             for k, v in seen.items() if k[0] == "yours"),
          {k: v for k, v in seen.items() if k[0] == "yours"})
    check("website flow: a picture of the user with no change (the automatic settings set its values): not the user's "
          "work, and Use replaces it", unchanged == (False, False, set()) and replaced, (unchanged, replaced))


def test_file_pasted_on_page_after_good_read(eq_screen, flow, monkeypatch, tmp_path, check):
    """A picture file copied in File Explorer and pasted on the Make an EQ page after a read that was OK: a picture of
    the user (no entry)."""
    from PySide6.QtCore import QMimeData, QUrl
    from PySide6.QtWidgets import QApplication
    page = flow["page"]
    came, tw = _traced(flow, monkeypatch, stand_in())
    path = str(tmp_path / "other graph.png")
    _graph().copy(0, 0, 800, 500).save(path)  # (a different picture: the same one again keeps the result)
    md = QMimeData()
    md.setUrls([QUrl.fromLocalFile(path)])
    QApplication.clipboard().setMimeData(md)
    since = _token(page)
    page.paste_picture()
    qt.wait_for(lambda: tw.graph_token > since and not tw.reading_graph and not tw.reading, 60)
    check("website flow: after a read that was OK, a picture file pasted on the Make an EQ page gets no entry",
          came and tw.graph_token > since and tw.entry is None and tw.t.src_name == "other graph",
          (tw.entry, tw.t.src_name))


def test_users_picture_after_read_drops_its_note(eq_screen, flow, monkeypatch, check):
    came, tw = _traced(flow, monkeypatch, stand_in())
    _copy(_graph().copy(0, 0, 800, 500))
    tw.paste()  # (after a read that was OK: a picture of yours)
    qt.wait_for(lambda: not tw.reading, 60)
    tw.t.curves[0]["ys"][100:200] = 300.0  # (the user traces a curve)
    tw.changed()
    tw.show_tab(2)
    check("website flow: a picture of yours after a traced one: 3 Save's note no longer names the website's graph",
          came and tw.auto_note == "" and "The app traced the graph" not in tw.save_note.text(), tw.save_note.text())


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
    alerts.clear()
    trays.clear()
    monkeypatch.setattr(QApplication, "applicationState", staticmethod(lambda: Qt.ApplicationActive))
    flow["pk"].show()
    came2, tw = _traced(flow, monkeypatch, stand_in())
    check("website flow: when the app is the active program, no flash and no tray message", came2 and not alerts
          and not trays, (alerts, trays))


@pytest.mark.timeout(300)
def test_real_read_from_the_clipboard(eq_screen, fresh_studio, flow, monkeypatch, check):
    from eq import paths as eq_paths
    from eq import rigs
    from helpers.website_graph import truth_reader, website_graph
    from ui import trace_auto
    page = flow["page"]
    monkeypatch.setattr(trace_core, "auto_read", REAL_AUTO_READ)
    img, truth = website_graph(plot_w=1000, target="solid")
    monkeypatch.setattr(trace_auto, "read_strip", truth_reader(truth))
    _use(flow)
    _copy(img)
    came = _picture_came(page, 120)
    tw = page.tracer
    check("website flow: a drawn graph of the website from the clipboard goes to 3 Save (the real automatic read)",
          came and tw.read_ok is True and tw.pages.currentIndex() == 2 and tw.save_line.isVisible()
          and [o["file"] for o in tw.outputs()] == [NAME + ".txt"], (came, tw.read_ok, tw.status.text()))
    tw.save_meas.click()  # (Add as measurement)
    loaded = qt.wait_for(lambda: page.curves is not None and page.curves.get("name") == NAME, 60)
    path = os.path.join(eq_paths.MEAS_DIR, NAME + ".txt")
    first = ""
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as fh:
            first = fh.readline().strip()
    rec = rigs.sources().get(NAME + ".txt") or {}
    used = [m["name"] for m in page.inputs["measurements"] if m["included"]]
    err = _error(_values(path), truth["avg"], 20, 20000) if os.path.isfile(path) else (99.0, 99.0)
    check("website flow: the real read, then Add as measurement: the file in the inputs folder with the entry's name, "
          "in use, its first line names the website and the link, the source record and the rig, and its values agree "
          "with the graph (mean error 0.1 dB or less, largest 0.5 dB or less)",
          loaded and used == [NAME + ".txt"]
          and first == f"* Traced from {NAME} with AutoEQ Studio (a picture from {SITE}: {LINK})"
          and rec.get("name") == ENTRY and rigs.file_rig(NAME + ".txt") == ("5128", True)
          and err[0] <= 0.1 and err[1] <= 0.5, (loaded, used, first, rec, err))


# ---------------------------------------------------------------- the final review's tests (2026-11-11)
def _ctrl_v(tw, repeat=False):
    """Ctrl+V on the tracer as Windows sends it (repeat: the key held down)."""
    from PySide6.QtCore import QEvent, Qt
    from PySide6.QtGui import QKeyEvent
    from PySide6.QtWidgets import QApplication
    QApplication.sendEvent(tw, QKeyEvent(QEvent.KeyPress, Qt.Key_V, Qt.ControlModifier, "", repeat))


def test_same_picture_again_keeps_the_result(eq_screen, flow, monkeypatch, check):
    """Ctrl+V in the tracer after the screen copy (the picture that the wait window took is still on the clipboard):
    the automatic result, the entry and the name stay. A different picture is a picture of yours, as before."""
    from helpers.dialogs import DIALOGS
    came, tw = _traced(flow, monkeypatch, stand_in(target=True))
    asked = len(DIALOGS.asked)
    _ctrl_v(tw)
    qt.wait_for(lambda: not tw.reading_graph and not tw.reading, 30)
    after = (tw.entry, tw.t.src_name, tw.pages.currentIndex(), [bool(tw.t.has_data(c)) for c in tw.t.curves],
             DIALOGS.asked[asked:], tw.status.text())
    check("website flow: Ctrl+V with the picture that the tracer has from the website keeps the automatic result, the "
          "entry and the name, and the status line says so", came and tw.entry and tw.entry["name"] == ENTRY
          and tw.t.src_name == NAME and tw.pages.currentIndex() == 2 and len(tw.t.curves) == 2
          and all(map(tw.t.has_data, tw.t.curves)) and not DIALOGS.asked[asked:]
          and tw.status.text() == "The tracer has this picture.", after)
    since = tw.graph_token
    _copy(_one_pixel_changed())
    _ctrl_v(tw)
    qt.wait_for(lambda: not tw.reading_graph and not tw.reading, 30)
    check("website flow: a different picture pasted after a read that was OK (the same size, one pixel different) is "
          "a picture of yours, as before", tw.graph_token > since and tw.entry is None and tw.t.src_name != NAME,
          (tw.graph_token - since, tw.entry, tw.t.src_name))


def test_same_picture_after_a_close_keeps_the_result(eq_screen, flow, monkeypatch, check):
    """The tracer closed and opened again, then Ctrl+V with the picture that it has from the website: the automatic
    result, the entry and the name stay (Help #pw-paste: the same picture again keeps the result)."""
    came, tw = _traced(flow, monkeypatch, stand_in(target=True))
    tw.close()
    flow["page"].open_trace()
    since = tw.graph_token
    _ctrl_v(tw)
    qt.wait_for(lambda: not tw.reading_graph and not tw.reading, 30)
    after = (tw.entry and tw.entry.get("name"), tw.t.src_name, tw.graph_token - since, tw.status.text())
    check("website flow: after a close of the tracer, the same picture again keeps the automatic result, the entry "
          "and the name", came and after == (ENTRY, NAME, 0, "The tracer has this picture.")
          and all(map(tw.t.has_data, tw.t.curves)), after)


def test_same_picture_after_an_add_is_a_picture_of_yours(eq_screen, fresh_studio, flow, monkeypatch, check):
    """After Add as measurement, the same picture again is a picture of yours (Help #pw-paste: the result stays only
    before you add the curve)."""
    came, tw = _traced(flow, monkeypatch, stand_in())
    tw.save("measurement")
    since = tw.graph_token
    _ctrl_v(tw)
    qt.wait_for(lambda: not tw.reading_graph and not tw.reading, 30)
    check("website flow: after Add as measurement, the same picture again is a picture of yours (no entry)",
          came and tw.graph_token > since and tw.entry is None and tw.t.src_name != NAME,
          (tw.graph_token - since, tw.entry, tw.t.src_name))


def test_same_picture_after_a_poor_read_keeps_the_users_change(eq_screen, flow, monkeypatch, check):
    """A read that was not OK on 2 Trace, the user changes the curve, then Ctrl+V with the same picture: the picture
    is not read again, and the change of the user stays."""
    came, tw = _traced(flow, monkeypatch, stand_in(ok=False, fail="trace_band"))
    qt.wait_for(lambda: not tw.reading, 30)
    tw.t.cur = 0
    tw.smooth()
    before = (tw.graph_token, len(tw.t.undo_stack))
    _ctrl_v(tw)
    qt.wait_for(lambda: not tw.reading_graph and not tw.reading, 30)
    after = (tw.graph_token, len(tw.t.undo_stack))
    check("website flow: after a read that was not OK and a change of the user, the same picture again is not read "
          "again and the change stays", came and before[1] == 1 and after == before and tw.entry
          and tw.entry["name"] == ENTRY and tw.status.text() == "The tracer has this picture.",
          (before, after, tw.status.text()))


def test_ctrl_v_two_times_or_held_keeps_the_entry(eq_screen, flow, monkeypatch, check):
    """After a picture that is not a graph, the user pastes a picture of the graph: one Ctrl+V, two Ctrl+V 150 ms apart
    (the second one while the read runs), or Ctrl+V held (the key repeats). Each time the entry stays and the read is
    OK."""
    out = {}
    for how in ("one", "two 150 ms apart", "held, 6 repeats 33 ms apart"):
        flow["pk"].show()
        came, tw = _traced(flow, monkeypatch, stand_in(ok=False, fail="axes_plot"))
        qt.wait_for(lambda tw=tw: not tw.reading, 30)
        monkeypatch.setattr(trace_core, "auto_read", stand_in(delay=0.6))
        _copy(_one_pixel_changed())  # (a better picture: not the same pixels)
        _ctrl_v(tw)
        if how.startswith("two"):
            qt.pump(150)
            _ctrl_v(tw)
        elif how.startswith("held"):
            for _ in range(6):
                qt.pump(33)
                _ctrl_v(tw, True)
        qt.wait_for(lambda tw=tw: not tw.reading_graph, 30)
        qt.pump(100)
        out[how] = (came, tw.entry and tw.entry.get("name"), tw.t.src_name, tw.read_ok, tw.pages.currentIndex())
        tw.remove_image()
    check("website flow: one Ctrl+V after a picture that is not a graph keeps the entry",
          out["one"] == (True, ENTRY, NAME, True, 2), out)
    check("website flow: two Ctrl+V 150 ms apart after a picture that is not a graph keep the entry",
          out["two 150 ms apart"] == (True, ENTRY, NAME, True, 2), out)
    check("website flow: a held Ctrl+V after a picture that is not a graph keeps the entry",
          out["held, 6 repeats 33 ms apart"] == (True, ENTRY, NAME, True, 2), out)


def test_held_ctrl_v_pastes_one_time(eq_screen, flow, monkeypatch, check):
    """Ctrl+V held down: Windows repeats the key, and the tracer pastes only at the first press (each paste reads the
    whole picture on the window's thread: about 0.3 s for a 4K screen copy)."""
    came, tw = _traced(flow, monkeypatch, stand_in())
    pastes = []
    monkeypatch.setattr(tw, "paste", lambda: pastes.append(1))
    _ctrl_v(tw)
    for _ in range(5):
        _ctrl_v(tw, True)
    check("website flow: a held Ctrl+V (one press and 5 repeats) pastes one time", came and len(pastes) == 1, pastes)


def test_find_a_target_says_add_as_target(eq_screen, fresh_studio, flow, monkeypatch, check):
    """Find a target with "Targets and measurements": Use on a website entry (its group is measurement). The note of
    3 Save tells the user to click Add as target (also beside a target line of the picture), and Add as target makes
    the traced curve the target in use. The mark of the wanted add does not go into the source record."""
    from eq import rigs
    from ui.picker import Picker
    page = flow["page"]
    page.reload_state()  # (fresh_studio puts the service's files and settings back: the page reads them again)
    qt.pump(50)
    flow["pk"].hide()
    monkeypatch.setattr(trace_core, "auto_read", stand_in(target=True))
    pk = Picker(page, "target")
    try:
        pk.show()
        eq_screen.wait_for(lambda: not pk.db.get("loading") and pk.db.get("items"), 120)
        pk.q.setText("truthear gate")
        pk.anykind.setChecked(True)
        pk.render()
        pk.finish_list()
        row = next((r for r in _rows(pk) if r.get("link") and r["name"] == ENTRY), None)
        meas = [m["name"] for m in page.inputs["measurements"] if m["included"]]
        since = _token(page)
        pk.use_row(row)
        qt.pump(50)
        _copy(_graph())
        came = _picture_came(page, since=since)
        tw = page.tracer
        note = tw.save_note.text()
        body = tw.source(NAME)  # (what the add sends to the app)
        tw.save_tgt.click()
        qt.pump(500)
        after = (page.inputs.get("active_target"), [m["name"] for m in page.inputs["measurements"] if m["included"]])
        record = rigs.sources().get(NAME + ".txt")
    finally:
        pk.reject()
        pk.deleteLater()
    check("website flow: Find a target, a website entry of the other group: the note of 3 Save tells the user to click "
          "Add as target, and says that the target line is a second target", row is not None and row.get("other")
          and came and "If they agree, click Add as target." in note and "Add as measurement" not in note
          and "Add the target line as target… adds that line as a target, not the Average curve." in note, note)
    check("website flow: Find a target, Add as target makes the traced curve the target in use and does not "
          "change the measurements in use; the source record has no mark of the wanted add",
          after[0] == NAME + ".txt" and meas and after[1] == meas  # (the measurements in use do not change)
          and body is not None and "as" not in body and record is not None and "as" not in record
          and record.get("name") == NAME, (after, meas, body, record))


def test_one_measurement_curve_and_a_target_line_have_no_note(eq_screen, flow, monkeypatch, check):
    """2 Trace's note about one file for each curve: not for one measurement curve and the marked target line (Add as
    measurement saves one file); with two measurement curves it shows."""
    came, tw = _traced(flow, monkeypatch, stand_in(target=True))
    tw.show_tab(1)
    note = tw.curves_note.text()
    files = [o["file"] for o in tw.outputs()]
    check("website flow: 2 Trace has no note about one file for each curve with one measurement curve and a marked "
          "target line", came and note == "" and files == [NAME + ".txt"], (note, files))
    tw.t.cur = next(i for i, c in enumerate(tw.t.curves) if c.get("target"))
    tw.t.smooth()  # (the target line becomes a measurement curve: two files)
    tw.changed()
    check("website flow: with two measurement curves the note of 2 Trace shows",
          tw.curves_note.text().startswith("The app saves the curves as one device") and len(tw.outputs()) == 2,
          tw.curves_note.text())


def test_renamed_target_line_shows_the_note(eq_screen, flow, monkeypatch, check):
    from PySide6.QtWidgets import QLineEdit
    came, tw = _traced(flow, monkeypatch, stand_in(target=True))
    tw.show_tab(1)
    before = tw.curves_note.text()
    box = next(b for b in tw.curves_box.findChildren(QLineEdit) if b.text() == "Target")
    box.setText("R")
    box.textEdited.emit("R")
    check("website flow: a renamed target line is a measurement curve: the note about one file for each curve shows "
          "at once", came and before == "" and tw.curves_note.text().startswith("The app saves the curves")
          and len(tw.outputs()) == 2, (before, tw.curves_note.text()))


def test_time_values_of_the_wait(check):
    from ui import picture_wait
    check("website flow: the time values of the wait: a limit of 10 minutes (the messages say so), a look at the "
          "Downloads folder each second, the clipboard read 150 ms after its signal",
          (picture_wait.TIMEOUT_MS, picture_wait.POLL_MS, picture_wait.SETTLE_MS) == (10 * 60 * 1000, 1000, 150),
          (picture_wait.TIMEOUT_MS, picture_wait.POLL_MS, picture_wait.SETTLE_MS))


def test_clipboard_that_gives_its_picture_late(eq_screen, flow, monkeypatch, check):
    from ui import picture_wait
    real, calls = picture_wait.clipboard_picture, []

    def late():
        calls.append(1)
        return (None, False) if len(calls) <= 2 else real()
    wait, _o = _use(flow)
    monkeypatch.setattr(picture_wait, "clipboard_picture", late)
    _copy(_graph())
    came = _picture_came(flow["page"])
    check("website flow: a clipboard that gives its picture only at the third read ends the wait",
          came and len(calls) == 3 and _closed(wait), (came, calls))


def test_jpeg_marks_of_files_and_copies(eq_screen, flow, tmp_path, check):
    from PySide6.QtCore import QMimeData, QUrl
    from PySide6.QtWidgets import QApplication
    from ui import picture_wait
    folder = _downloads()
    flags = {}
    for name in ("a.jpeg", "b.jfif", "c.JPG", "d.PNG"):
        old, pending, tries = picture_wait.folder_pictures(folder), {}, {}
        _graph().save(os.path.join(folder, name), "PNG" if name.endswith("PNG") else "JPG", 95)
        looks = [picture_wait.new_picture(folder, old, pending, tries) for _ in range(2)]
        flags[name] = (looks[1][0] is not None, looks[1][1])
    check("website flow: new .jpeg, .jfif and .JPG files in the Downloads folder are read as JPEG, a .PNG file as not "
          "JPEG", flags == {"a.jpeg": (True, True), "b.jfif": (True, True), "c.JPG": (True, True),
                           "d.PNG": (True, False)}, flags)
    path = str(tmp_path / "copied.jpg")
    _graph().save(path, "JPG", 95)
    md = QMimeData()
    md.setUrls([QUrl.fromLocalFile(path)])
    QApplication.clipboard().setMimeData(md)
    img, jpeg = picture_wait.clipboard_picture()
    check("website flow: a .jpg file copied in File Explorer is read as JPEG", img is not None and jpeg is True, jpeg)


def test_jpeg_without_its_end_mark_is_not_taken(eq_screen, flow, check):
    """A JPEG file that a program still writes (no end mark FF D9 yet): Qt reads the part as a picture, but the wait
    does not take it. After READ_TRIES looks with no change, the file is taken as it is."""
    from PySide6.QtCore import QBuffer, QIODevice
    from ui import picture_wait
    folder = _downloads()
    buf = QBuffer()
    buf.open(QIODevice.WriteOnly)
    _graph().save(buf, "JPG", 90)
    data = bytes(buf.data())
    out = {}
    looks_n = picture_wait.READ_TRIES + 1  # (the first look only lists a new file)
    for name, part in (("half.jpg", data[:len(data) // 2]), ("whole.jpg", data), ("most.jpeg", data[:-2])):
        old, pending, tries = picture_wait.folder_pictures(folder), {}, {}
        with open(os.path.join(folder, name), "wb") as fh:
            fh.write(part)
        out[name] = [picture_wait.new_picture(folder, old, pending, tries)[0] is not None for _ in range(looks_n)]
    check("website flow: a JPEG file in the Downloads folder without its end mark is not taken at once, a whole one is "
          "taken at the second look", out["half.jpg"][:3] == [False] * 3 and out["most.jpeg"][:3] == [False] * 3
          and out["whole.jpg"][:2] == [False, True], out)
    check("website flow: a JPEG file that stays without its end mark is taken after READ_TRIES looks",
          out["half.jpg"] == [False] * (looks_n - 1) + [True], out)


def test_guide_button_off_during_the_read(eq_screen, flow, monkeypatch, check):
    monkeypatch.setattr(trace_core, "auto_read", stand_in(delay=1.0))
    _use(flow)
    _copy(_graph())
    page = flow["page"]
    qt.wait_for(lambda: getattr(page, "tracer", None) is not None and page.tracer.reading_graph, 10)
    tw = page.tracer
    during = tw.guide_btn.isEnabled()
    came = _picture_came(page)
    check("website flow: while the automatic read runs, the Guide button does not accept input (and accepts it after)",
          came and not during and tw.guide_btn.isEnabled(), during)


def test_empty_name_of_the_target_line_adds_nothing(eq_screen, fresh_studio, flow, monkeypatch, check):
    from eq import paths as eq_paths
    from ui import window_parts
    came, tw = _traced(flow, monkeypatch, stand_in(target=True))
    had = set(os.listdir(eq_paths.TARGET_DIR))
    monkeypatch.setattr(window_parts, "ask_text", lambda *a: ("  ", True))
    tw.add_target_line()
    qt.pump(200)
    new = set(os.listdir(eq_paths.TARGET_DIR)) - had
    check("website flow: an empty name for Add the target line as target… adds no target",
          came and not new and not tw.added, new)


def test_paste_the_picture_takes_a_small_picture(eq_screen, flow, check):
    from PySide6.QtGui import QColor, QImage
    wait, _o = _use(flow)
    small = QImage(299, 400, QImage.Format_RGB888)
    small.fill(QColor("white"))
    _copy(small)
    qt.pump(300)
    stays = wait.isVisible() and wait.got is None
    wait.paste()
    came = _picture_came(flow["page"])
    check("website flow: Paste the picture takes a picture smaller than 300 x 200 (the picture on the clipboard, old "
          "or new)", stays and came and _closed(wait) and flow["page"].tracer.t.W == 299 - 10,
          (stays, came, flow["page"].tracer.t.W))


def test_find_in_its_modal_loop(eq_screen, monkeypatch, check):
    """Find… as the page opens it (page.find: a modal loop), through the website path: Use, the wait window, a picture,
    Find… closes, the tracer has the entry. (The tests' QDialog.exec closes a dialog at once: here Picker.exec runs a
    real event loop, as Qt's.)"""
    import net
    from PySide6.QtCore import QEventLoop, Qt, QTimer
    from PySide6.QtWidgets import QApplication
    from ui import picture_wait
    from ui.picker import Picker
    page = eq_screen.page
    QApplication.clipboard().clear()
    monkeypatch.setattr(picture_wait, "SETTLE_MS", 30)
    monkeypatch.setattr(picture_wait, "POLL_MS", 30)
    monkeypatch.setattr(trace_core, "auto_read", stand_in())
    seen = {}
    since = _token(page)

    def real_exec(self):
        self.setWindowModality(Qt.ApplicationModal)
        self.show()
        loop = QEventLoop()
        self.finished.connect(loop.quit)

        def use():
            if self.db.get("loading") or not self.db.get("items"):
                QTimer.singleShot(100, use)
                return
            self.q.setText("truthear gate")
            self.render()
            self.finish_list()
            row = next((r for r in _rows(self) if r.get("link") and r["name"] == ENTRY), None)
            monkeypatch.setattr(net, "offline", lambda: False)
            self.use_row(row)
            wait = getattr(page, "picture_wait", None)
            seen["wait"] = wait is not None and wait.isVisible() and wait.isModal()
            QTimer.singleShot(100, lambda: _copy(_graph()))
        QTimer.singleShot(100, use)
        QTimer.singleShot(120000, loop.quit)  # (never a test that does not end)
        loop.exec()
        seen["find closed in its loop"] = not self.isVisible()
        return self.result()
    monkeypatch.setattr(Picker, "exec", real_exec)
    page.find("measurement")
    came = _picture_came(page, since=since)
    tw = getattr(page, "tracer", None)
    ok = (came and seen.get("wait") and seen.get("find closed in its loop") and tw.entry and tw.entry["name"] == ENTRY
          and tw.read_ok is True and tw.pages.currentIndex() == 2 and page.picture_wait is None)
    if tw is not None:
        qt.wait_for(lambda: not tw.reading_graph, 30)
        tw.remove_image()
        tw.close()
    QApplication.clipboard().clear()
    check("website flow: Find… in its modal loop: Use on a website entry, a picture: Find… closes and the tracer has "
          "the entry and its read", ok, (came, seen, tw and tw.entry))
