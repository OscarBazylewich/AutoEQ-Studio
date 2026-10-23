"""Find… › Sources (ui\\sources_window.py): a group with databases you added switched off asks first (No keeps them);
a database switched off and on, one added by its address (a wrong or repeated address said), removed again; This
PC's folders one per line; offline, squig.link's list isn't fetched. Moved from eq_checks.py's rest_checks (lines
2022-2076), on a page opened as the old checks opened it (the eq_screen fixture), offline. The two checks share one
Sources window and one list of what it said, as there, so they're one test: the second's two messages come from the
adds made before the first check. Its Windows 11 look (the restyle, 2026-10-23): at its smallest, every part has its
room; closed straight after a tick, it never reaches for its deleted tree; the folders' box shows four whole lines;
and on a short screen (a laptop at 150 % or 175 %, stood in) it fits above the taskbar, its parts scroll and its
bottom row stays in sight."""
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
    """The widgets shown directly on `holder` (a window, or the page that scrolls inside it); none for no holder."""
    from PySide6.QtWidgets import QWidget
    if holder is None:
        return []
    return [w for w in holder.findChildren(QWidget) if w.parentWidget() is holder and w.isVisible()]


def _page(src):
    """The page Sources' parts are on, inside the window's scroll area (since 2026-10-23); None without one."""
    from PySide6.QtWidgets import QScrollArea
    area = src.findChild(QScrollArea)
    return area.widget() if area is not None else None


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
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: said.append(a[2])))
    try:
        src = Sources(page)
        rows, _ = src.rows()
        builtin = next(r for r in rows if r["builtin"])
        src.set_on(builtin, False)
        off = builtin["name"] in S["databases"]["disabled"]
        src.set_on(builtin, True)
        on = builtin["name"] not in S["databases"]["disabled"]
        src.add("example.squig.link")
        src.add("https://example.squig.link/")
        src.add("https://example.squig.link")
        added = S["databases"]["extra"] == kept_db.get("extra", []) + ["https://example.squig.link/"]
        # (review 2) the added one's group switched off, answered No: nothing changes (it asked after removing them)
        src.render()
        grp = next(src.tree.topLevelItem(i) for i in range(src.tree.topLevelItemCount())
                   if any("example.squig.link" in src.tree.topLevelItem(i).child(j).text(0).lower()
                          or "example" in src.tree.topLevelItem(i).child(j).text(0).lower()
                          for j in range(src.tree.topLevelItem(i).childCount())))
        with monkeypatch.context() as m:
            m.setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.No))
            grp.setCheckState(0, Qt.Unchecked)
        qapp.processEvents()
        asked_first = "https://example.squig.link/" in S["databases"]["extra"]
        # was eq_checks.py:2057
        check("sources: switching off a group with ones you added asks first; No keeps them", asked_first,
              S["databases"]["extra"])
        extra = next(r for r in src.rows()[0] if r["extra"] and "example.squig.link" in r["url"])
        src.set_on(extra, False)
        removed = S["databases"]["extra"] == kept_db.get("extra", [])
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
          "removed again, the folders one per line; offline, squig.link's list isn't fetched",
          off and on and added and removed and folders == ["C:\\Music", "D:\\Curves"] and offline_note
          and len(said) == 2 and "https://" in said[0] and "already" in said[1], (off, on, added, removed, folders, said))


def test_smallest_size_fits(eq_screen, check):
    # (Qt's own smallest size counts each wrapped line of text once: at it, the databases' tree was pushed over the
    # heading under it. Since 2026-10-23 its parts are on a page that can scroll: the window's parts and the page's
    # are both looked at)
    import net
    from ui.sources_window import Sources
    was_off = net.offline()
    net.set_offline(True)  # (its longest note, squig.link's list needing the internet, on two lines)
    src = Sources(eq_screen.page)
    try:
        src._refresh_soon.stop()
        src.show()
        src.resize(1, 1)  # (to its smallest)
        qt.pump(300)
        size = (src.width(), src.height())
        parts, inside = _parts(src), _parts(_page(src))
        over = _overlapping(parts) + _overlapping(inside)
        tree = (src.tree.height(), src.tree.minimumHeight())
    finally:
        src._refresh_soon.stop()
        qt.close(src)
        net.set_offline(was_off)
    check("restyle: Sources at its smallest gives every part its room (the databases' tree never over the heading "
          "under it)", parts and not over and tree[0] >= tree[1], (size, tree, over[:3]))


def test_folders_box_shows_four_lines(eq_screen, check):
    # (80 px high, it held three and a half lines at Windows 11's 10.5 pt: the fourth of the usual folders was cut in
    # half, and the box scrolled by a line)
    from PySide6.QtGui import QTextCursor
    from ui.sources_window import Sources
    src = Sources(eq_screen.page)
    try:
        src._refresh_soon.stop()
        src.show()
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
    # (at 560 x 680 at its smallest, and opening 820 high, its bottom row (Refresh the lists now, Open the downloads
    # folder, Close) was under the taskbar of a 1920 x 1080 laptop at 150 %, out of reach. The screen is stood in:
    # the room Qt says it has above the taskbar)
    import net
    from PySide6.QtCore import QRect
    from PySide6.QtGui import QScreen
    from PySide6.QtWidgets import QPushButton, QScrollArea
    from ui.sources_window import Sources
    bottom_row = ("Refresh the lists now", "Open the downloads folder", "Close")
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
                area = src.findChild(QScrollArea)  # (the page of its parts, scrolling when they need more room)
                seen[height] = {
                    "opens": opens, "smallest": (src.width(), src.height()),
                    "fits": opens[1] + TITLE_BAR <= height and src.height() + TITLE_BAR <= height
                    and max(opens[0], src.width()) <= width,
                    "bottom row in sight": len(row) == 3 and all(b.isVisible() and src.rect().contains(b.geometry())
                                                                 for b in row),
                    "over": _overlapping(_parts(src)) + _overlapping(_parts(_page(src))),
                    "tree": (src.tree.height(), src.tree.minimumHeight()),
                    "scrolls": area is not None and area.verticalScrollBar().maximum() > 0}
            finally:
                src._refresh_soon.stop()
                qt.close(src)
    finally:
        net.set_offline(was_off)
    small, big = [seen[h] for _w, h in SMALL_SCREENS], seen[1032]
    check("restyle: Sources fits a laptop's screen at 150 % and 175 % (its size and its smallest above the taskbar): "
          "its parts scroll there, nothing over another, and its bottom row (Refresh the lists now, Open the downloads "
          "folder, Close) stays in sight; on a big screen it opens and shrinks as before, without scrolling",
          all(s["fits"] and s["bottom row in sight"] and not s["over"] and s["tree"][0] >= s["tree"][1]
              and s["scrolls"] for s in small)
          and big["opens"] == (760, 820) and big["smallest"] == (560, 700) and not big["scrolls"]
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
        seen = (first is src.folders, type(first).__name__)
    finally:
        src._refresh_soon.stop()
        qt.close(src)
    check("access: Tab goes round Sources' controls only (its page that scrolls is no stop of its own): from Close to "
          "the folders' box", seen[0], seen[1])


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
