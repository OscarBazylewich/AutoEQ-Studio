"""Find… › Sources (ui\\sources_window.py): a group with databases you added switched off asks first (No keeps them);
a database switched off and on, one added by its address (a wrong or repeated address said), removed again; This
PC's folders one per line; offline, squig.link's list isn't fetched. Moved from eq_checks.py's rest_checks (lines
2022-2076), on a page opened as the old checks opened it (the eq_screen fixture), offline. The two checks share one
Sources window and one list of what it said, as there, so they're one test: the second's two messages come from the
adds made before the first check. Its Windows 11 look (the restyle, 2026-10-23): closed straight after a tick, it
never reaches for its deleted tree; the folders' box shows four whole lines; and on a short screen (a laptop at 150 %
or 175 %, stood in) it fits above the taskbar with every part its room and its bottom row in sight, and on a big one
it opens and shrinks as before, with no page that scrolls (a tab for each part since the UI audit, 2026-11-08)."""
import json

from helpers import qt

# (a 1920 x 1080 laptop's room above the taskbar at 150 % and 175 %, as Qt gives it; and Windows 11's title bar there)
SMALL_SCREENS = ((1280, 672), (1097, 569))
TITLE_BAR = 32


def _overlapping(widgets):
    """The pairs of widgets drawn over each other, by their names."""
    name = lambda w: f"{type(w).__name__} “{(w.text() if hasattr(w, 'text') else w.accessibleName())[:20]}”"
    return [(name(a), name(b)) for i, a in enumerate(widgets) for b in widgets[i + 1:]
            if a.geometry().intersects(b.geometry())]


def _parts(holder):
    """The widgets shown directly on `holder` (a window, or the page of its tab that shows)."""
    from PySide6.QtWidgets import QWidget
    return [w for w in holder.findChildren(QWidget) if w.parentWidget() is holder and w.isVisible()]


def test_sources(eq_screen, monkeypatch, check):
    import net
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QMessageBox
    from ui.sources_window import Sources
    page, qapp = eq_screen.page, eq_screen.qapp
    S = page.S
    kept_db, kept_folders = json.loads(json.dumps(S["databases"])), list(S["library"].get("folders") or [])
    was_off = net.offline()
    net.set_offline(True)
    said = []
    from ui import bubble
    told = bubble.tell
    monkeypatch.setattr(bubble, "tell", lambda anchor, text, *a, **k: (said.append(text), told(anchor, text, *a, **k))[1])
    try:
        src = Sources(page)
        rows, _ = src.rows()
        builtin = next(r for r in rows if r["builtin"])
        src.set_on(builtin, False)
        off = builtin["name"] in S["databases"]["disabled"]
        src.set_on(builtin, True)
        on = builtin["name"] not in S["databases"]["disabled"]
        src.add_database("example.squig.link")
        src.add_database("https://example.squig.link/")
        src.add_database("https://example.squig.link")
        added = S["databases"]["extra"] == kept_db.get("extra", []) + ["https://example.squig.link/"]
        # (the control audit, 2026-11-27, 4-1: the added one's group switched off asked "Disabling removes your added
        # databases. Continue?" and then removed them; now it asks nothing and they stay in the list, off)
        src.render()
        grp = next(src.tree.topLevelItem(i) for i in range(src.tree.topLevelItemCount())
                   if any("example.squig.link" in src.tree.topLevelItem(i).child(j).text(0).lower()
                          for j in range(src.tree.topLevelItem(i).childCount())))
        asked = []
        with monkeypatch.context() as m:
            m.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: asked.append(a) or QMessageBox.No))
            grp.setCheckState(0, Qt.Unchecked)
        qapp.processEvents()
        extra = next(r for r in src.rows()[0] if r["extra"] and "example.squig.link" in r["url"])
        check("sources: switching off a group with ones you added asks nothing, and they stay in the list, off",
              not asked and "https://example.squig.link/" in S["databases"]["extra"] and not extra["on"]
              and "https://example.squig.link/" in S["databases"]["extra_off"], (asked, S["databases"]))
        src.set_on(extra, True)
        src.set_on(extra, False)
        removed = S["databases"]["extra"] == kept_db.get("extra", []) + ["https://example.squig.link/"] \
            and S["databases"]["extra_off"] == ["https://example.squig.link/"]
        src.set_on(extra, True)
        removed = removed and S["databases"]["extra_off"] == []
        S["databases"]["extra"] = kept_db.get("extra", [])
        src.folders.setPlainText("C:\\Music\n\n  D:\\Curves  ")
        folders = S["library"]["folders"]
        offline_note = "Offline" in src.dir_note.text()
        src._refresh_soon.stop()
        S["databases"].clear()
        S["databases"].update(kept_db)
        S["library"]["folders"] = kept_folders
        src.reject()
    finally:
        net.set_offline(was_off)
    # was eq_checks.py:2073
    check("sources: a database switched off and on, one added by its address (a wrong or repeated address said), "
          "switched off and on (kept in the list), the folders one per line; offline, squig.link's list isn't fetched",
          off and on and added and removed and folders == ["C:\\Music", "D:\\Curves"] and offline_note
          and len(said) == 2 and "https://" in said[0] and said[1] == "Database already added",
          (off, on, added, removed, folders, said))


def test_added_database_off_then_removed(eq_screen, check):
    # (the control audit, 2026-11-27, 4-1: unticking a database that you added deleted it at once, with no question and
    # no Undo, so the Off list could never show one. Now its tick box only switches it off; its ✕ removes it, and Undo
    # puts it back in its place, off as it was. Settings from before, with no "extra_off", still open)
    from PySide6.QtCore import Qt
    import net
    from ui.sources_window import Sources
    page = eq_screen.page
    S = page.S
    kept = json.loads(json.dumps(S["databases"]))
    was_off = net.offline()
    net.set_offline(True)
    mine = ["https://first.example.org/", "https://second.example.org/", "https://third.example.org/"]
    S["databases"]["extra"] = list(mine)
    S["databases"].pop("extra_off", None)  # (settings saved before this change)
    seen = {}
    try:
        src = Sources(page)
        src._refresh_soon.stop()
        rows = lambda: [src.tree.topLevelItem(i).child(j) for i in range(src.tree.topLevelItemCount())
                        for j in range(src.tree.topLevelItem(i).childCount())]
        row = lambda name: next((it for it in rows() if it.text(0) == name), None)
        seen["opens with old settings"] = S["databases"].get("extra_off") == [] and row("second.example.org") is not None
        row("second.example.org").setCheckState(0, Qt.Unchecked)  # (as a click on its tick box)
        qt.pump(50)
        src._refresh_soon.stop()
        it = row("second.example.org")
        seen["unticked"] = (list(S["databases"]["extra"]), list(S["databases"]["extra_off"]),
                            it and (it.checkState(0) == Qt.Unchecked, it.text(1)))
        src.show_box.setCurrentIndex(src.show_box.findData("off"))
        src.render()
        seen["Off shows it"] = [r.text(0) for r in rows() if r.text(0).endswith("example.org")]
        src.show_box.setCurrentIndex(src.show_box.findData("all"))
        src.render()
        x = src.tree.itemWidget(row("second.example.org"), 2)
        x.click()
        qt.pump(50)
        src._refresh_soon.stop()
        seen["removed"] = (list(S["databases"]["extra"]), list(S["databases"]["extra_off"]),
                           row("second.example.org") is None,
                           src.footer.line.text.text())
        src.footer.line.undo_btn.click()
        qt.pump(50)
        src._refresh_soon.stop()
        it = row("second.example.org")
        seen["undone"] = (S["databases"]["extra"], S["databases"]["extra_off"],
                          it is not None and it.checkState(0) == Qt.Unchecked)
        qt.close(src)
    finally:
        net.set_offline(was_off)
        S["databases"].clear()
        S["databases"].update(kept)
        page.svc.call("/api/settings", {"settings": S})
    check("sources: settings from before the Off mark of added databases open the window",
          seen["opens with old settings"], seen)
    check("sources: unticking a database that you added only switches it off: it stays in the list, unticked, “off”",
          seen["unticked"] == (mine, [mine[1]], (True, "off")), seen["unticked"])
    check("sources: the Off list shows a database that you added and switched off",
          seen["Off shows it"] == ["second.example.org"], seen["Off shows it"])
    check("sources: a database's ✕ removes it, with “Removed …” and Undo; Undo puts it back in its place, still off",
          seen["removed"][:3] == ([mine[0], mine[2]], [], True) and seen["removed"][3] == "Removed “second.example.org”"
          and seen["undone"] == (mine, [mine[1]], True), (seen["removed"], seen["undone"]))


def test_squiglink_note_hidden_while_loading(eq_screen, monkeypatch, check):
    # (the text survey, 2026-11-24: the gray line above squig.link's list said "From squig.link's list (in progress…),
    # or with the URL of a page." while the list loaded; that text went, and the line is hidden then: the list's own
    # line says that it loads. Online is stood in for net.offline() only; the answer of the background call is given
    # by the test, so nothing connects)
    import net
    from ui import sources_window
    from ui.sources_window import Sources
    answers = []
    monkeypatch.setattr(net, "offline", lambda: False)
    # (only the calls of the Sources window are stood in: tasks is the app's one module, so a call of the page that
    # an earlier test left waiting came here too, and the list's answer given to it failed in the page, KeyError
    # 'name'. The other calls go to the real function)
    real = sources_window.tasks.background
    monkeypatch.setattr(sources_window.tasks, "background",
                        lambda work, done, owner=None: answers.append(done) if isinstance(owner, Sources)
                        else real(work, done, owner=owner))
    src = Sources(eq_screen.page)
    try:
        src._refresh_soon.stop()
        src.show()
        src.show_tab(2)  # (its tab: Add a database)
        qt.pump(100)
        loading = (src.dir_note.isVisible(), src.dir_note.text(), src.dir_empty.label.text())
        answers[-1](None, "no connection")
        qt.pump(50)
        failed = (src.dir_note.isVisible(), src.dir_note.text())
        answers[-1]({"items": [{"name": n, "type": "IEMs", "url": f"https://{n.lower()}.squig.link/"}
                               for n in ("Example", "Sample")]}, None)
        qt.pump(50)
        loaded = (src.dir_note.isVisible(), src.dir_note.text())
    finally:
        src._refresh_soon.stop()
        qt.close(src)
    seen = {"loading": loading, "failed": failed, "loaded": loaded}
    check("sources: the gray line above squig.link's list is hidden while the list loads, and shows when the list did "
          "not load and with the number of databases",
          loading[:2] == (False, "") and loading[2] == "Loading squig.link's list…"
          and failed == (True, "You can still add a database by URL below")
          and loaded == (True, "2 squig.link databases"), seen)


def test_folders_box_shows_four_lines(eq_screen, check):
    # (80 px high, it held three and a half lines at Windows 11's 10.5 pt: the fourth of the usual folders was cut in
    # half, and the box scrolled by a line)
    from PySide6.QtGui import QTextCursor
    from ui.sources_window import Sources
    src = Sources(eq_screen.page)
    try:
        src._refresh_soon.stop()
        src.show()
        src.show_tab(0)  # (its tab: This PC)
        qt.pump(200)
        box = src.folders
        usual = box.placeholderText().splitlines()  # (shown in grey while the list is empty: Downloads … Music)
        box.blockSignals(True)  # (typed in as the folders to search for a moment: not saved)
        box.setPlainText("\n".join(usual))
        qt.pump(100)
        end = QTextCursor(box.document().lastBlock())
        end.movePosition(QTextCursor.EndOfBlock)
        seen = {"lines": len(usual), "scrolls by": box.verticalScrollBar().maximum(),
                "last line's bottom": box.cursorRect(end).bottom(), "room": box.viewport().height()}
        box.setPlainText("")
        box.blockSignals(False)
    finally:
        src._refresh_soon.stop()
        qt.close(src)
    check("restyle: Sources' folders box shows four whole lines at Windows 11's text size (the usual four folders: "
          "Downloads, Documents, Desktop, Music), without scrolling",
          seen["lines"] == 4 and seen["scrolls by"] == 0 and seen["last line's bottom"] < seen["room"], seen)


def test_fits_a_small_screen(eq_screen, monkeypatch, check):
    # (at 560 x 680 at its smallest, and opening 820 high, its bottom row (Update the lists, Open the downloads
    # folder, Close) was under the taskbar of a 1920 x 1080 laptop at 150 %, out of reach. The screen is stood in:
    # the room Qt says it has above the taskbar)
    import net
    from PySide6.QtCore import QRect
    from PySide6.QtGui import QScreen
    from PySide6.QtWidgets import QPushButton, QScrollArea
    from ui.sources_window import Sources
    bottom_row = ("Update the lists", "Open the downloads folder", "Close")
    was_off = net.offline()
    net.set_offline(True)  # (its longest note on two lines)
    seen = {}
    try:
        for width, height in SMALL_SCREENS + ((1920, 1032),):  # (and a big screen: nothing changes there)
            monkeypatch.setattr(QScreen, "availableGeometry", lambda self, w=width, h=height: QRect(0, 0, w, h))
            src = Sources(eq_screen.page)
            try:
                src._refresh_soon.stop()
                opens = (src.width(), src.height())
                src.show()
                src.resize(1, 1)  # (to its smallest)
                qt.pump(300)
                row = [b for b in src.findChildren(QPushButton) if b.text() in bottom_row]
                seen[height] = {
                    "opens": opens, "smallest": (src.width(), src.height()),
                    "fits": opens[1] + TITLE_BAR <= height and src.height() + TITLE_BAR <= height
                    and max(opens[0], src.width()) <= width,
                    "bottom row in sight": len(row) == 3 and all(b.isVisible() and src.rect().contains(b.geometry())
                                                                 for b in row),
                    "over": _overlapping(_parts(src)) + _overlapping(_parts(src.pages.currentWidget())),
                    "tree": (src.tree.height(), src.tree.minimumHeight()),
                    # (a scroll area of the window's own: the page of its parts, before the UI audit's tabs. The check
                    # before read whether that area scrolled, and there has been none since: it could not fail;
                    # the test audit, 2026-11-25)
                    "no page that scrolls": src.findChild(QScrollArea) is None}
            finally:
                src._refresh_soon.stop()
                qt.close(src)
    finally:
        net.set_offline(was_off)
    small, big = [seen[h] for _w, h in SMALL_SCREENS], seen[1032]
    # (the UI audit, 2026-11-08: a tab for each part, so nothing scrolls as a page)
    check("restyle: Sources fits a laptop's screen at 150 % and 175 % (its size and its smallest above the taskbar): "
          "nothing over another, and its bottom row (Update the lists, Open the downloads folder, Close) stays in "
          "sight; on a big screen it opens and shrinks as before, without scrolling",
          all(s["fits"] and s["bottom row in sight"] and not s["over"] and s["tree"][0] >= s["tree"][1]
              for s in small)
          and big["opens"] == (760, 820) and big["smallest"] == (560, 700) and big["no page that scrolls"]
          and big["bottom row in sight"] and not big["over"], seen)


def test_page_is_no_tab_stop(eq_screen, check):
    # (Qt's scroll areas take Tab by default: the page its parts are on (since 2026-10-23) would have been a stop of its
    # own, showing nothing, between Close and the folders' box)
    from PySide6.QtWidgets import QPushButton
    from ui.sources_window import Sources
    src = Sources(eq_screen.page)
    try:
        src._refresh_soon.stop()
        src.show()
        qt.pump(100)
        close = next(b for b in src.findChildren(QPushButton) if b.text() == "Close")
        close.setFocus()
        src.focusNextChild()  # (Tab from the last button: round to the first control)
        first = src.focusWidget()
        seen = (first is src.tab_btns[0], type(first).__name__)
    finally:
        src._refresh_soon.stop()
        qt.close(src)
    check("access: Tab goes round Sources' controls only: from Close to its first tab, This PC", seen[0], seen[1])


def test_closed_straight_after_a_tick(eq_screen, check):
    # (after a tick its tree is drawn again a moment later, not inside the item's own signal; a window closed and
    # deleted in that moment had it reach for its deleted tree: found 2026-10-23, as Find…'s scroll place was)
    from PySide6.QtCore import Qt
    from ui.sources_window import Sources
    page = eq_screen.page
    S = page.S
    kept = json.loads(json.dumps(S["databases"]))
    src = Sources(page)
    try:
        src._refresh_soon.stop()
        site = next(src.tree.topLevelItem(i).child(0) for i in range(src.tree.topLevelItemCount())
                    if src.tree.topLevelItem(i).childCount())
        name = site.text(0)
        site.setCheckState(0, Qt.Unchecked if site.checkState(0) == Qt.Checked else Qt.Checked)  # (as a click)
        src._refresh_soon.stop()
        before = len(qt.QT_ERRORS)
        qt.close(src)
        qt.pump(100)  # (the moment after, while this test is still the one running)
        new = [text for _test, text in qt.QT_ERRORS[before:]]
    finally:
        S["databases"].clear()
        S["databases"].update(kept)
        page.svc.call("/api/settings", {"settings": S})
    check("sources: closed straight after a database was switched off or on, it never reaches for its deleted tree",
          not new, (name, new))


def test_browse_database_from_a_picture(eq_screen, check):
    # (2026-11-11, the picture from a website: a database that does not let other programs download its files (the
    # fixture's Hangout.Audio 5128 list) says that its entries come from a picture, not "only in the list")
    from eq import databases
    from ui.sources_window import Sources
    page = eq_screen.page
    page.svc.call("/api/db/refresh", {"settings": page.S})  # (offline: the saved lists)
    qt.wait_for(lambda: not databases.status()["loading"] and databases.status()["count"], 120)
    src = Sources(page)
    try:
        src._refresh_soon.stop()
        src.poll()  # (the lists' status, drawn)
        counts ={src.tree.topLevelItem(i).child(j).text(0): src.tree.topLevelItem(i).child(j).text(1)
                  for i in range(src.tree.topLevelItemCount()) for j in range(src.tree.topLevelItem(i).childCount())}
    finally:
        qt.close(src)
    hangout = counts.get("Hangout.Audio IEMs (Crinacle, 5128)", "")
    check("sources: a database that the app traces from a picture says “· from image” after its count",
          hangout.endswith(" · from image") and not any("only in the list" in c for c in counts.values()), hangout)


def test_curve_file_counts_say_one_file(eq_screen, monkeypatch, check):
    # (a review of the text survey, 2026-11-24: This PC's gray line said "1 curve files", and "1 cloud-only OneDrive
    # files skipped". A stand-in for the EQ part's answer about the search)
    from ui.sources_window import Sources
    src = Sources(eq_screen.page)
    said = []
    try:
        src._refresh_soon.stop()
        src._lib_poll.stop()
        for st in ({"scanning": True, "found": 1}, {"scanning": True, "found": 2},
                   {"found": 1, "cloud": 1, "folders": ["C:\\Music"]}, {"found": 3, "cloud": 2, "folders": ["C:\\Music"]}):
            monkeypatch.setattr(src.svc, "call", lambda path, body=None, st=st: st)
            src.poll_lib()
            said.append(src.lib_status.text())
            src._lib_poll.stop()
    finally:
        monkeypatch.undo()
        qt.close(src)
    check("sources: This PC's gray line says “1 curve file” and “1 cloud-only OneDrive file” for one, the plural for more",
          said == ["Searching… 1 curve file", "Searching… 2 curve files",
                   "1 curve file in Music (1 cloud-only OneDrive file skipped; download to include)",
                   "3 curve files in Music (2 cloud-only OneDrive files skipped; download to include)"], said)


def test_database_added_offline_says_no_loading(eq_screen, monkeypatch, check):
    # (a review of the text survey, 2026-11-24: offline, a database added said "Database added. Loading list…", but
    # the app loads no list offline. Online is stood in for net.offline() only, and the background calls of the
    # Sources window get no answer, so nothing connects: as test_squiglink_note_hidden_while_loading)
    import net
    from ui import sources_window
    from ui.sources_window import Sources
    page = eq_screen.page
    S = page.S
    kept = json.loads(json.dumps(S["databases"]))
    real = sources_window.tasks.background
    monkeypatch.setattr(sources_window.tasks, "background",
                        lambda work, done, owner=None: None if isinstance(owner, Sources)
                        else real(work, done, owner=owner))
    said = {}
    try:
        for off in (True, False):
            monkeypatch.setattr(net, "offline", lambda off=off: off)
            src = Sources(page)
            try:
                src.add_database(f"https://stand-in-{'off' if off else 'on'}.squig.link")
                said["offline" if off else "online"] = src.footer.line.text.text()
            finally:
                src._refresh_soon.stop()
                qt.close(src)
            S["databases"].clear()
            S["databases"].update(json.loads(json.dumps(kept)))
    finally:
        monkeypatch.undo()
        page.svc.call("/api/settings", {"settings": S})
    check("sources: a database added says “Database added” offline, and “Database added. Loading list…” online",
          said == {"offline": "Database added", "online": "Database added. Loading list…"}, said)
