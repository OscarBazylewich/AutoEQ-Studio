"""The targets of a list-only database in Find a target, and a download that a website refuses in Find… (2026-11-12,
ui\\picker.py, ui\\eq_page_files.py, ui\\picture_wait.py, ui\\sources_window.py): a target of the fixture's
Hangout.Audio 5128 list shows "trace from the website ↗", and Use opens its share link and waits, with the entry
marked as a target for the tracer and the words about the settings of the website; a Use whose download is refused
(a made HTTP 403: nothing connects) says so in Find…'s line and goes on with the trace in the same Use; Sources
then says "· from a picture" for that database. Pictures in light and dark are read back (each saved in the test's
own folder, its path printed).

Online is stood in for net.offline() only (net.check() stays offline); databases._get is stood in for (db_guard);
the refusals are kept in the test's own folder; the lists are put back after each test."""
import os

import pytest

from helpers import qt

HANGOUT = "https://graph.hangout.audio/iem/5128/"
TARGET = "JM-1"
SUPER = "Super* Review IEMs"


def _rows(pk):
    from PySide6.QtCore import Qt
    return [(pk.list.item(i), pk.list.item(i).data(Qt.UserRole)) for i in range(pk.list.count())
            if pk.list.item(i).data(Qt.UserRole)]


def _picker(page, kind, query):
    from ui.picker import Picker
    pk = Picker(page, kind)
    pk.show()
    qt.wait_for(lambda: not pk.db.get("loading") and pk.db.get("items"), 120)
    pk.q.setText(query)
    pk._later.stop()
    pk.render()
    pk.finish_list()
    qt.pump(300)
    return pk


def _wait_shown(page):
    """The page's wait window when it shows (one deleted with the window that it was on does not count)."""
    from ui import tasks
    wait = getattr(page, "picture_wait", None)
    return wait if wait is not None and tasks.alive(wait) and wait.isVisible() else None


def _pictures(widget, tmp_path, name, eq_screen):
    """The widget in light and dark, saved and read back: (path, lightness at (5, 5), width, height) of each."""
    from PySide6.QtGui import QImage
    out = {}
    for look, theme_on in (("light", qt.light), ("dark", qt.dark)):
        theme_on(eq_screen.qapp)
        qt.pump(150)
        path = str(tmp_path / f"{name}-{look}.png")
        widget.grab().save(path)
        img = QImage(path)
        out[look] = (path, img.pixelColor(5, 5).lightness(), img.width(), img.height())
        print("picture:", path)
    qt.light(eq_screen.qapp)
    qt.pump(50)
    return out


def _dark_and_light(p):
    return p["light"][1] > 128 > p["dark"][1]


@pytest.fixture
def online(eq_screen, db_guard, monkeypatch, tmp_path):
    """The saved lists loaded (offline: the fixture's), online for the app's own checks, the refusals in this test's
    folder; after the test the wait window, the tracer and the clipboard as before."""
    import net
    from PySide6.QtWidgets import QApplication
    from eq import databases
    from ui import picture_wait
    page = eq_screen.page
    page.svc.call("/api/db/refresh", {"settings": page.S})
    qt.wait_for(lambda: not databases.status()["loading"] and databases.status()["count"], 120)
    monkeypatch.setattr(databases, "LIST_ONLY_PATH", str(tmp_path / "list_only.json"))
    monkeypatch.setattr(picture_wait, "SETTLE_MS", 30)
    monkeypatch.setattr(picture_wait, "POLL_MS", 30)
    monkeypatch.setattr(net, "offline", lambda: False)
    QApplication.clipboard().clear()
    yield page
    wait = _wait_shown(page)
    if wait is not None:
        wait.reject()
    qt.pump(50)
    QApplication.clipboard().clear()


def test_target_of_a_website_in_find_a_target(eq_screen, online, tmp_path, check):
    from PySide6.QtWidgets import QLabel
    from ui import picture_wait
    page = online
    pk = _picker(page, "target", TARGET.lower())
    try:
        found = [(item, r) for item, r in _rows(pk) if r["name"] == TARGET and r["site"].startswith("Hangout")]
        item, row = found[0] if found else (None, None)
        w = pk.list.itemWidget(item) if item is not None else None
        marks = [lab.text() for lab in w.findChildren(QLabel)] if w is not None else []
        check("website targets: Find a target shows a target of a database that does not let other programs "
              "download its files, with trace from the website ↗ (not of the other group)",
              row is not None and row["is_target"] and not row.get("other") and row.get("link")
              and "trace from the website ↗" in marks, (row, marks))
        pics = _pictures(w, tmp_path, "find-target-row", eq_screen) if w is not None else {}
        check("website targets: the row of the target in light and dark (read back)",
              pics and _dark_and_light(pics) and pics["light"][2] > 400, pics)
        n = len(qt.OPENED_URLS)
        pk.use_row(row)
        qt.pump(100)
        wait = _wait_shown(page)
        opened = qt.OPENED_URLS[n:]
        check("website targets: Use opens the share link of the target and shows the wait window",
              opened == [HANGOUT + "?share=JM-1_Target"] and wait is not None and wait.isVisible(), opened)
        check("website targets: the wait window gives the tracer the entry as a target",
              wait is not None and wait.entry.get("kind") == "target" and wait.entry.get("as") == "target"
              and wait.entry.get("site_page") is False, wait.entry if wait else None)
        words = [lab.text() for lab in wait.findChildren(QLabel)] if wait else []
        check("website targets: the wait window tells that the website can change a target with its settings, and "
              "what to do when the graph does not show the entry",
              picture_wait.TARGET_SETTINGS in words and any(picture_wait.NOT_SHOWN in t for t in words)
              and wait.target_note.isVisible(), words)
        usual = _pictures(wait, tmp_path, "wait-target", eq_screen)
        wait.resize(wait.minimumSizeHint())
        wait.fit_height()
        qt.pump(100)
        cut = [lab.text()[:40] for lab in wait.findChildren(QLabel)
               if lab.isVisible() and lab.wordWrap() and lab.height() < lab.heightForWidth(lab.width()) - 1]
        small = _pictures(wait, tmp_path, "wait-target-smallest", eq_screen)
        check("website targets: the wait window for a target in light and dark, at its usual and its smallest size "
              "(read back, every line whole)", _dark_and_light(usual) and _dark_and_light(small) and not cut
              and small["light"][2] <= usual["light"][2], (usual, small, cut))
    finally:
        qt.close(pk)
        qt.pump(100)


def test_measurement_wait_has_no_target_words(eq_screen, online, check):
    from ui import picture_wait
    page = online
    pk = _picker(page, "measurement", "truthear gate")
    try:
        row = next((r for _i, r in _rows(pk) if r.get("link") and r["name"] == "Truthear Gate"), None)
        pk.use_row(row)
        qt.pump(100)
        wait = _wait_shown(page)
        check("website targets: the wait window for a measurement has no words about the target settings, and the "
              "entry goes to the tracer as a measurement", wait is not None and wait.target_note is None
              and wait.entry.get("as") == "measurement" and picture_wait.NOT_SHOWN in wait.steps()[0],
              wait.steps() if wait else None)
    finally:
        qt.close(pk)
        qt.pump(100)


def test_page_link_tells_to_select_the_entry(eq_screen, online, check):
    from PySide6.QtWidgets import QLabel
    from ui import picture_wait
    from ui.picture_wait import PictureWait
    entry = {"id": "x", "kind": "measurement", "name": "Truthear Gate", "site": "A website", "link": HANGOUT,
             "site_url": HANGOUT, "site_page": True}
    wait = PictureWait(eq_screen.page, entry)
    try:
        words = [lab.text() for lab in wait.findChildren(QLabel)]
        check("website lists: for a link to the page of the database, the wait window tells the user to select the "
              "entry", "Your browser shows “A website”. Give the app a picture of the graph of this entry:" in words
              and picture_wait.SELECT in wait.steps()[0] and picture_wait.NOT_SHOWN not in wait.steps()[0], words)
    finally:
        wait.deleteLater()


def test_words_of_a_website_entry(check):
    # (2026-11-13: the verifier's MF4 and MF5. For a database whose link is the page of the database
    # (modernGraphTool, a name with a comma), "the app opens the entry on the website" was not true; Help did not
    # tell what to do for a target)
    import re
    from eq import databases
    from ui import help_text_eq
    paras = next(it["body"] for group in help_text_eq.SETTINGS_EQ for it in group["items"]
                 if it["key"] == "#pw-paste")
    # (the final verification's SF6: 3 Save gives the first and the last frequency only when the target line stops
    # before an end of the frequency axis)
    target = ("For an entry of a target, show only the target on the graph of the website. The tracer then traces the "
              "target line. If the line stops before an end of the frequency axis, 3 Save shows its first and last "
              "frequency.",
              "For an entry of a target or from Find a target, Add as target is the first button. The text on 3 Save "
              "tells you to click it. If the app cannot trace only the target line, remove the measurement curve from "
              "the graph of the website. Then copy a new picture.")
    sentences = [s for p in paras for s in re.split(r"(?<=[.!?])\s+(?=[A-Z])", p)]
    check("website words: Help tells to show only the target for an entry of a target, each sentence 20 words or "
          "fewer, each paragraph 6 sentences or fewer",
          all(p in paras for p in target)
          and all(len(s.split()) <= 20 for p in target for s in re.split(r"(?<=[.])\s+", p))
          and " ".join(paras).count("Add as target is the first button") == 1  # (one sentence tells it)
          and all(len(re.split(r"(?<=[.!?])\s+(?=[A-Z])", p)) <= 6 for p in paras)
          and all(len(s.split()) <= 25 for s in sentences), [s for s in sentences if len(s.split()) > 25])
    words = {"BROWSE_NOTE": databases.BROWSE_NOTE, "REFUSED_NOTE": databases.REFUSED_NOTE, "Help": " ".join(paras)}
    check("website words: the messages and Help say that the app opens the website, not the entry (a link can be the "
          "page of the database)",
          databases.BROWSE_NOTE.endswith("The app opens the website and traces a picture of the graph of the entry.")
          and databases.REFUSED_NOTE.endswith("Thus, the app opens the website and traces a picture of the graph of "
                                              "the entry.")
          and not any("opens the entry" in w or "open it on its website" in w for w in words.values()), words)


def test_entry_with_no_link_opens_nothing(eq_screen, online, check):
    # (2026-11-13, the verifier's MF1: an entry with no link in the lists of this moment opened an empty address, and
    # Windows said that it cannot open the website)
    from eq import databases
    page = online
    entry = next(it for it in databases.items() if it["site"] == SUPER and not it.get("link"))
    said, n = [], len(qt.OPENED_URLS)
    started = page.trace_from_website(entry["id"], over=page, say=lambda t, ms=10000: said.append(t))
    check("website lists: an entry with no link opens nothing, starts no wait and says so",
          started is False and qt.OPENED_URLS[n:] == [] and _wait_shown(page) is None
          and said == ["The app has no link to the website of this entry. Select the entry again."],
          (started, qt.OPENED_URLS[n:], said))


def test_find_a_target_can_hide_the_entries_it_cannot_download(eq_screen, online, tmp_path, check):
    # (2026-11-13, the verifier's MF3: Find a target has targets of a website now, and it hid the tick box)
    page = online
    pk = _picker(page, "target", TARGET.lower())
    try:
        before = [r["name"] for _i, r in _rows(pk) if r.get("link")]
        shown = pk.f_dl.isVisible() and pk.f_dl.isEnabled()
        pics = {}
        for width in (pk.minimumWidth() or 680, 900):
            pk.resize(width, 720)
            qt.pump(150)
            from PySide6.QtCore import QPoint, QRect
            box = QRect(pk.f_dl.mapTo(pk, QPoint(0, 0)), pk.f_dl.size())
            inside = pk.rect().contains(box) and pk.f_dl.width() >= pk.f_dl.sizeHint().width()
            pics[width] = (_pictures(pk, tmp_path, f"find-target-filters-{width}", eq_screen), inside, pk.width())
        pk.f_dl.setChecked(True)
        pk.render()
        pk.finish_list()
        qt.pump(200)
        after = [r["name"] for _i, r in _rows(pk) if r.get("link")]
        pk.f_dl.setChecked(False)
    finally:
        qt.close(pk)
        qt.pump(100)
    check("website targets: Find a target shows “Available to download”, and the tick box hides the targets that the "
          "app cannot download", shown and TARGET in before and after == [], (shown, before, after))
    check("website targets: Find a target with the tick box in light and dark, at its smallest width and at 900 px "
          "(read back, the box whole)", all(_dark_and_light(p) and inside for p, inside, _w in pics.values()),
          {w: (p, inside) for w, (p, inside, _fw) in pics.items()})


def test_refused_download_shows_the_links_with_no_new_load_of_the_lists(eq_screen, online, monkeypatch, check):
    # (the verifier's M14 and M24: Find… asks for its rows again when the number of changes of the lists changes. In
    # the older test, a new load of the lists gave the rows; here no load of the lists occurs)
    import urllib.error
    from eq import databases
    monkeypatch.setattr(databases, "start_refresh", lambda cfg, force=False: False)
    monkeypatch.setattr(databases, "_get", lambda url, **k: (_ for _ in ()).throw(
        urllib.error.HTTPError(url, 403, "made in the test", None, None)))
    # (the config of Super* Review with no targets: the refusal then adds no entries, and only the number of changes
    # tells Find… that its rows changed. The saved lists of the tests (1.6.1) have no targets for it)
    conf = databases._confs.get("https://squig.link/")  # noqa: SLF001 - the config that the lists keep in memory
    monkeypatch.setitem(databases._confs, "https://squig.link/", dict(conf or {}, targets=[]))  # noqa: SLF001
    page = online
    pk = _picker(page, "measurement", "truthear gate")
    count = len(pk.db["items"])
    try:
        row = next((r for _i, r in _rows(pk) if r["site"] == SUPER and r["name"] == "Truthear Gate"
                    and not r.get("link")), None)
        pk.use_row(row)
        qt.wait_for(lambda: _wait_shown(page) is not None, 30)
        page.picture_wait.reject()
        qt.pump(100)
        qt.wait_for(lambda: any(r.get("link") for _i, r in _rows(pk) if r["site"] == SUPER), 10)
        rows = [r for _i, r in _rows(pk) if r["site"] == SUPER]
    finally:
        qt.close(pk)
        qt.pump(100)
    check("website lists: after the refusal, with no new load of the lists and no new entries, the rows of that "
          "database have their links", row is not None and rows and all(r.get("link") for r in rows)
          and len(databases.items()) == count, ([(r["name"], r.get("link")) for r in rows], count))


def test_refused_preview_says_so_in_find(eq_screen, online, monkeypatch, check):
    # (the verifier's M25: the message of a Preview whose download the website refuses was not tested in the window)
    import urllib.error
    from eq import databases
    monkeypatch.setattr(databases, "_get", lambda url, **k: (_ for _ in ()).throw(
        urllib.error.HTTPError(url, 403, "made in the test", None, None)))
    page = online
    pk = _picker(page, "measurement", "truthear gate")
    try:
        row = next((r for _i, r in _rows(pk) if r["site"] == SUPER and r["name"] == "Truthear Gate"
                    and not r.get("link")), None)
        curves = bool(page.curves)
        pk.preview(row)
        qt.wait_for(lambda: pk.footer.line.text.text(), 30)
        said = pk.footer.line.text.text()
        qt.wait_for(lambda: any(r.get("link") for _i, r in _rows(pk) if r["site"] == SUPER), 20)
        rows = [r for _i, r in _rows(pk) if r["site"] == SUPER]
        opened = _wait_shown(page)
    finally:
        qt.close(pk)
        qt.pump(100)
    check("website lists: a Preview whose download the website refuses says so in Find…'s line, opens nothing, and "
          "the rows of that database get their links", curves and said == databases.BROWSE_NOTE.format(site=SUPER)
          and opened is None and rows and all(r.get("link") for r in rows), (curves, said, opened))


def test_target_words_of_the_wait_window_come_from_the_kind_of_the_entry(eq_screen, online, check):
    # (the verifier's M28 and M29. The kind of the entry is correct, not "as": the website changes a target with its
    # settings (tilt and bass), not a measurement. A target from Find a measurement is a target on the website, and a
    # measurement from Find a target is a measurement there)
    from ui import picture_wait
    from ui.picture_wait import PictureWait
    seen = {}
    for kind, as_ in (("target", "measurement"), ("measurement", "target"), ("target", "target")):
        entry = {"id": "x", "kind": kind, "as": as_, "name": "JM-1", "site": "A website", "link": HANGOUT,
                 "site_url": HANGOUT, "site_page": False}
        wait = PictureWait(eq_screen.page, entry)
        try:
            seen[(kind, as_)] = (wait.target_note is not None,
                                 picture_wait.TARGET_SETTINGS in wait.accessibleDescription())
        finally:
            wait.deleteLater()
    check("website targets: the words about the settings of the website show for an entry of kind target (also from "
          "Find a measurement), not for a measurement (also from Find a target), and a screen reader reads them",
          seen == {("target", "measurement"): (True, True), ("measurement", "target"): (False, False),
                   ("target", "target"): (True, True)}, seen)


def test_refused_download_goes_on_with_the_trace(eq_screen, online, monkeypatch, tmp_path, check):
    import urllib.error
    from eq import databases
    from ui.sources_window import Sources

    def refused(url, **k):
        raise urllib.error.HTTPError(url, 403, "made in the test", None, None)
    monkeypatch.setattr(databases, "_get", refused)
    page = online
    pk = _picker(page, "measurement", "truthear gate")
    try:
        row = next((r for _i, r in _rows(pk) if r["site"] == SUPER and r["name"] == "Truthear Gate"
                    and not r.get("link")), None)
        n = len(qt.OPENED_URLS)
        pk.use_row(row)
        qt.wait_for(lambda: _wait_shown(page) is not None, 30)
        opened = qt.OPENED_URLS[n:]
        said = pk.footer.line.text.text()
        check("website lists: Use whose download the website refuses (HTTP 403) goes on with the trace in the same "
              "Use: the share link opens and the wait window shows", row is not None
              and opened == ["https://squig.link/?share=Truthear_Gate"] and page.picture_wait.isVisible(), opened)
        check("website lists: Find…'s line tells what occurs",
              said == databases.REFUSED_NOTE.format(site=SUPER), said)
        page.picture_wait.reject()
        qt.pump(100)
        qt.wait_for(lambda: any(r.get("link") for _i, r in _rows(pk) if r["site"] == SUPER), 20)
        rows = [r for _i, r in _rows(pk) if r["site"] == SUPER]
        check("website lists: after the refusal the rows of that database have their links (Use only, no Preview)",
              rows and all(r.get("link") for r in rows), [(r["name"], r.get("link")) for r in rows])
        pics = _pictures(pk, tmp_path, "find-refused-message", eq_screen)
        check("website lists: Find… with the message in light and dark (read back)", _dark_and_light(pics), pics)
    finally:
        qt.close(pk)
        qt.pump(100)
    src = Sources(page)
    try:
        src._refresh_soon.stop()
        src.poll()
        counts = {src.tree.topLevelItem(i).child(j).text(0): src.tree.topLevelItem(i).child(j).text(1)
                  for i in range(src.tree.topLevelItemCount()) for j in range(src.tree.topLevelItem(i).childCount())}
    finally:
        qt.close(src)
    check("website lists: Sources says “· from a picture” for the database that refused the download",
          counts.get(SUPER, "").endswith(" · from a picture"), counts.get(SUPER))
    check("website lists: the refusal is kept in the saved data", os.path.isfile(databases.LIST_ONLY_PATH)
          and databases.norm_url("https://squig.link/") in databases.refusals(), databases.refusals())
