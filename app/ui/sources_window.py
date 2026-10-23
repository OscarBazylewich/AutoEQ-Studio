"""Sources (AutoEQ Local's Settings › Sources, natively; sources.js): where Find… looks.
- This PC: the folders searched for curve files (one per line; empty: Downloads, Documents, Desktop, Music), and
  "Search again now"
- Online databases: every database by kind of rig, each on or off (a group at once too), how many curves each list
  has, a filter and All / On / Off; ones you added can be removed
- Add a database: from squig.link's list (searched), or any squig.link-style page by its address
- Refresh the lists now (online only); Open the downloads folder
Changes are saved at once and the lists load again a moment later (offline: the saved ones).
The look: Windows 11's; the databases' tree is styled as the lists by theme_sheet's find_windows (sourcesTree); the
folders' box as tall as four lines of its text (the four usual folders whole). Its size kept within the screen's free
room (picker.fit_to_screen): on a short screen (a laptop at 150 %) its parts scroll as a page, as Windows 11's
Settings do, and the bottom row (Refresh, Open the downloads folder, Close) stays in sight.
"""
import math

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QFontMetricsF
from PySide6.QtWidgets import (QDialog, QFrame, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget,
                               QListWidgetItem, QMessageBox, QPlainTextEdit, QPushButton, QScrollArea, QTreeWidget,
                               QTreeWidgetItem, QVBoxLayout, QWidget)

import net
from ui import help_window, icons, tasks, theme
from ui.picker import fit_to_screen
from ui.search_combo import SearchCombo

url_key = lambda u: u.strip().rstrip("/").lower()


def _muted(text=""):
    lab = QLabel(text)
    lab.setWordWrap(True)
    theme.mark(lab, role="muted")
    return lab


def _head(text):
    lab = QLabel(text)
    theme.mark(lab, role="section")
    return lab


def lines_high(box, n):
    """The height of a many-line text box that shows n whole lines of its text: the lines in its text size, the
    document's margin above and below them, and the box's frame and padding (the stylesheet's). A fixed 80 px held
    three and a half lines at 10.5 pt: the fourth of the usual folders was cut in half."""
    box.ensurePolished()  # (the stylesheet's text size and padding)
    frame = box.height() - box.contentsRect().height()
    return frame + math.ceil(2 * box.document().documentMargin() + n * QFontMetricsF(box.font()).lineSpacing()) + 1


class _Page(QWidget):
    """Sources' parts on a page that scrolls (in a QScrollArea): never lower than they need at its width (each wrapped
    note counted line by line), and no taller either, so the lists take the room there is. (Qt's scroll area asks a
    page for its height at a width, which is otherwise its parts' preferred heights: it would scroll on any screen.)"""

    def heightForWidth(self, width):
        return self.layout().totalMinimumHeightForWidth(width)


class Sources(QDialog):
    def __init__(self, page):
        super().__init__(page)
        self.page, self.svc = page, page.svc
        self.setWindowTitle("Sources: where Find… looks")
        # (Qt's own minimum counts each wrapped line of text once, and then pushed the databases' tree over the
        # heading under it: room here for the notes on two lines. Both within the screen's free room: shorter, its
        # parts scroll)
        fit_to_screen(self, (760, 820), (560, 700))
        S = page.S
        S["databases"].setdefault("enabled", [])
        S["databases"].setdefault("extra", [])
        S["databases"].setdefault("disabled", [])
        self.st, self.dir = {"sites": []}, None
        outer = QVBoxLayout(self)
        self.scroll = QScrollArea()  # (the parts as a page that scrolls when the window is shorter than they need)
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setFocusPolicy(Qt.NoFocus)  # (Tab goes to its parts, each scrolled into sight: no stop of its own)
        body = _Page()
        v = QVBoxLayout(body)
        v.setContentsMargins(0, 0, 0, 0)
        v.addWidget(_head("This PC"))
        v.addWidget(QLabel("Folders to search (one per line, with their subfolders):"))
        self.folders = QPlainTextEdit("\n".join(S["library"].get("folders") or []))
        self.folders.setPlaceholderText("\n".join(page.meta.get("library_defaults") or []) or "Downloads, Documents, …")
        self.folders.setFixedHeight(lines_high(self.folders, 4))  # (the four usual folders, whole)
        help_window.tag(self.folders, "library.folders")
        self.folders.textChanged.connect(self.folders_changed)
        v.addWidget(self.folders)
        row = QHBoxLayout()
        rescan = QPushButton("Search again now")
        icons.put(rescan, "find")
        rescan.clicked.connect(self.rescan)
        row.addWidget(rescan)
        self.lib_status = _muted()
        row.addWidget(self.lib_status, 1)
        v.addLayout(row)
        v.addWidget(_head("Online databases"))
        v.addWidget(_muted("Lists refresh every few days; curves download when you use or preview them."))
        bar = QHBoxLayout()
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("Filter the databases…")
        self.filter.textChanged.connect(self.render)
        bar.addWidget(self.filter, 1)
        self.show_box = SearchCombo()
        self.show_box.setAccessibleName("Show the databases")
        for k, name in (("all", "All"), ("on", "On"), ("off", "Off")):
            self.show_box.addItem(name, k)
        self.show_box.sort_items()
        self.show_box.activated.connect(lambda _i: self.render())
        bar.addWidget(self.show_box)
        self.db_status = _muted()
        bar.addWidget(self.db_status)
        v.addLayout(bar)
        self.tree = QTreeWidget()
        self.tree.setObjectName("sourcesTree")  # (as the lists: theme_sheet's find_windows)
        self.tree.setMinimumHeight(110)  # (the window's main list: a few rows, however small the window)
        self.tree.setHeaderLabels(["Database", "Curves", ""])
        self.tree.setAccessibleName("Online databases")
        hd = self.tree.header()  # (the name takes the room; the counts and links their own width)
        hd.setStretchLastSection(False)
        hd.setSectionResizeMode(0, QHeaderView.Stretch)
        hd.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hd.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tree.itemChanged.connect(self.item_changed)
        self.tree.itemClicked.connect(self.item_clicked)
        help_window.tag(self.tree, "databases")
        v.addWidget(self.tree, 1)
        v.addWidget(_head("Add a database"))
        self.dir_note = _muted("From squig.link's list, or by page address.")
        v.addWidget(self.dir_note)
        self.dir_q = QLineEdit()
        self.dir_q.setPlaceholderText("Search by reviewer or type (IEMs, 5128, headphones)…")
        self.dir_q.textChanged.connect(self.render_dir)
        v.addWidget(self.dir_q)
        self.dir_list = QListWidget()
        self.dir_list.setAccessibleName("squig.link's databases")
        self.dir_list.setMinimumHeight(72)  # (130 high, less in a small window: the databases' tree comes first)
        self.dir_list.setMaximumHeight(130)
        self.dir_list.itemDoubleClicked.connect(lambda it: it.data(Qt.UserRole) and self.add(it.data(Qt.UserRole)))
        v.addWidget(self.dir_list)
        row = QHBoxLayout()
        self.url = QLineEdit()
        self.url.setPlaceholderText("https://example.squig.link/")
        row.addWidget(self.url, 1)
        add = QPushButton("Add")
        icons.put(add, "add")
        add.clicked.connect(lambda: self.add(self.url.text()) and self.url.clear())  # (refused: kept to correct)
        row.addWidget(add)
        v.addLayout(row)
        self.scroll.setWidget(body)
        outer.addWidget(self.scroll, 1)
        row = QHBoxLayout()  # (the bottom row, under the page: always in sight)
        refresh = QPushButton("Refresh the lists now")
        icons.put(refresh, "refresh")
        refresh.setToolTip("Download every list again (online only)")
        refresh.clicked.connect(lambda: self.refresh(force=True))
        row.addWidget(refresh)
        folder = QPushButton("Open the downloads folder")
        icons.put(folder, "folder")
        folder.clicked.connect(lambda: self.svc.call("/api/open", {"what": "downloads"}))
        row.addWidget(folder)
        row.addStretch(1)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        row.addWidget(close)
        outer.addLayout(row)
        self._refresh_soon = QTimer(self, singleShot=True, interval=500, timeout=self.refresh)
        self._poll = QTimer(self, interval=700, timeout=self.poll)
        self._lib_poll = QTimer(self, interval=600, timeout=self.poll_lib)
        self.poll()
        self.poll_lib()
        self.load_dir()

    # ---------------------------------------------------------------- this PC
    def folders_changed(self):
        self.page.S["library"]["folders"] = [l.strip() for l in self.folders.toPlainText().splitlines() if l.strip()]
        self.page.save_settings_soon()

    def rescan(self):
        self.svc.call("/api/settings", {"settings": self.page.S})
        self.svc.call("/api/library/scan", {"settings": self.page.S, "force": True})
        self._lib_poll.start()
        self.poll_lib()

    def poll_lib(self):
        st = self.svc.call("/api/library")
        if st.get("error") and not st.get("folders"):
            self.lib_status.setText(f"Search unavailable: {st['error']}")
            return
        if st.get("scanning"):
            self.lib_status.setText(f"Searching… {st.get('found', 0)} curve files so far")
            self._lib_poll.start()
            return
        self._lib_poll.stop()
        where = ", ".join(f.replace("\\", "/").rstrip("/").split("/")[-1] for f in st.get("folders") or [])
        self.lib_status.setText(f"Search stopped: {st['error']}" if st.get("error") else
                                f"{st.get('found', 0)} curve files in {where}"
                                + (f" ({st['cloud']} files only in OneDrive's cloud left out: reading them would "
                                   "download them)" if st.get("cloud") else ""))

    # ---------------------------------------------------------------- the online databases
    def rows(self):
        S, meta = self.page.S, self.page.meta
        by_url = {s.get("url"): s for s in self.st.get("sites") or []}
        rows = [dict(d, on=(d["name"] not in S["databases"]["disabled"]) if d.get("on", True)
                     else d["name"] in S["databases"]["enabled"], builtin=d.get("on", True), extra=False)
                for d in meta.get("database_sites") or []]
        # (only ones still yours: one just removed or unticked came straight back from the last status)
        mine = {url_key(u) for u in S["databases"]["extra"]}
        rows += [{"name": s["name"], "url": s["url"], "group": s.get("group") or "added", "on": True, "extra": True,
                  "builtin": False} for s in self.st.get("sites") or [] if s.get("extra") and url_key(s["url"]) in mine]
        for u in S["databases"]["extra"]:
            if not any(url_key(r["url"]) == url_key(u) for r in rows):
                rows.append({"name": u.split("://")[-1], "url": u, "group": "added", "on": True, "extra": True,
                             "builtin": False})
        return rows, by_url

    def set_on(self, d, on):
        db = self.page.S["databases"]
        if d["extra"]:
            if not on:
                db["extra"] = [u for u in db["extra"] if url_key(u) != url_key(d["url"])]
            return
        key = "disabled" if d["builtin"] else "enabled"
        names = set(db[key])
        names.discard(d["name"]) if on == d["builtin"] else names.add(d["name"])
        db[key] = sorted(names)

    def changed(self):
        self.page.save_settings_soon()
        self._refresh_soon.start()

    def render(self):
        rows, by_url = self.rows()
        groups = self.page.meta.get("database_groups") or []
        keys = {g for g, _t in groups}
        f = self.filter.text().strip().lower()
        show = self.show_box.currentData()
        self.tree.blockSignals(True)
        self.tree.clear()
        total_on = 0
        for g, title in groups:
            members = [r for r in rows if (r["group"] if r["group"] in keys else "added") == g]
            if not members:
                continue
            on = [r for r in members if r["on"]]
            total_on += len(on)
            n = sum((by_url.get(r["url"]) or {}).get("count", 0) for r in on)
            vis = [r for r in members if (not f or f in r["name"].lower()) and (show == "all" or (show == "on") == r["on"])]
            if not vis:
                continue
            top = QTreeWidgetItem([title, f"{len(on)} of {len(members)} on" + (f" · {n:,}" if n else ""), ""])
            # (its tick set here, not by Qt's auto-tristate: that switched every database off one by one before the
            # group's own change could ask about the ones you added)
            top.setFlags(top.flags() | Qt.ItemIsUserCheckable)
            top.setData(0, Qt.UserRole, ("group", g))
            self.tree.addTopLevelItem(top)
            for d in vis:
                s = by_url.get(d["url"])
                count = ("off" if not d["on"] else "" if not s else "couldn't load" if s.get("error")
                         else f"{s.get('count', 0):,}" + (" · list only" if d.get("browse") else ""))
                if d["on"] and not s and self.st.get("loading"):
                    count = "loading…"
                it = QTreeWidgetItem([d["name"], count, "Remove" if d["extra"] else "↗ site"])
                it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
                it.setCheckState(0, Qt.Checked if d["on"] else Qt.Unchecked)
                it.setData(0, Qt.UserRole, ("site", d))
                if s and s.get("error"):
                    it.setToolTip(1, s["error"])
                top.addChild(it)
            n_on = sum(d["on"] for d in vis)
            top.setCheckState(0, Qt.Checked if n_on == len(vis) else Qt.Unchecked if not n_on else Qt.PartiallyChecked)
            top.setExpanded(True)
        self.tree.blockSignals(False)
        self.db_status.setText("Loading…" if self.st.get("loading") else
                               f"{total_on} on · {self.st.get('count', 0):,} curves")

    def item_changed(self, it, col):
        kind, d = it.data(0, Qt.UserRole)
        if col != 0:
            return
        if kind == "group":  # (every database of the group on or off)
            state = it.checkState(0)
            if state == Qt.PartiallyChecked:
                return
            on = state == Qt.Checked
            rows = [it.child(i).data(0, Qt.UserRole)[1] for i in range(it.childCount())]
            if not on and any(r["extra"] for r in rows) and QMessageBox.question(
                    self, "Databases", "Switching these off removes the ones you added from the list. Continue?") != QMessageBox.Yes:
                # (not inside the item's own signal: render deletes it; the window its owner, so a window closed
                # and deleted meanwhile drops it instead of reaching for its deleted tree)
                QTimer.singleShot(0, self, self.render)
                return
            for r in rows:
                self.set_on(r, on)
        else:
            self.set_on(d, it.checkState(0) == Qt.Checked)
        self.changed()
        QTimer.singleShot(0, self, self.render)

    def item_clicked(self, it, col):
        kind, d = it.data(0, Qt.UserRole)
        if kind != "site" or col != 2:
            return
        if d["extra"]:
            self.set_on(d, False)
            self.changed()
            QTimer.singleShot(0, self, self.render)
        elif net.offline():
            self.page.status("Offline: switch to Online (top right) to open websites.", 6000)
        else:
            QDesktopServices.openUrl(QUrl(d["url"]))

    def refresh(self, force=False):
        self.svc.call("/api/db/refresh", {"settings": self.page.S, "force": force})
        self._poll.start()
        self.poll()

    def poll(self):
        self.st = self.svc.call("/api/db")
        if not self.st.get("loading"):
            self._poll.stop()
        else:
            self._poll.start()
        self.render()

    # ---------------------------------------------------------------- adding one
    def load_dir(self):
        if net.offline():
            self.dir_note.setText("Offline: squig.link's list needs the internet (switch to Online, top right). A "
                                  "page address can still be added.")
            return
        self.dir_note.setText("From squig.link's list (loading…) or by page address.")

        def done(res, err):
            items = (res or {}).get("items") or []
            if err or not items:
                self.dir_note.setText("Couldn't load squig.link's list (no connection?). Try again later, or add a "
                                      "database by its page address below.")
                return
            self.dir = items
            self.dir_note.setText(f"From squig.link's list ({len(items)} databases; double-click one to add it) or by "
                                  "page address.")
            self.render_dir()
        tasks.background(lambda: self.svc.call("/api/db/directory"), done, owner=self)

    def listed(self):
        rows, _ = self.rows()
        return {url_key(r["url"]) for r in rows}

    def render_dir(self):
        self.dir_list.clear()
        if not self.dir:
            return
        have = self.listed()
        ws = self.dir_q.text().lower().split()
        hits = [d for d in self.dir if all(w in (d["name"] + " " + d.get("type", "")).lower() for w in ws)]
        for d in hits[:60]:
            added = url_key(d["url"]) in have
            it = QListWidgetItem(f"{d['name']}  ·  {d.get('type', '')}" + ("   ✓ in the list" if added else "   + Add"))
            if not added:
                it.setData(Qt.UserRole, d["url"])
            self.dir_list.addItem(it)
        if len(hits) > 60:
            self.dir_list.addItem(f"{len(hits) - 60} more: type to narrow the list")

    def add(self, u):
        u = (u or "").strip()
        if not u.startswith(("http://", "https://")):
            QMessageBox.information(self, "Add a database", "Enter the page address, starting with https://")
            return False
        if url_key(u) in self.listed():
            QMessageBox.information(self, "Add a database", "That database is already in the list.")
            return False
        self.page.S["databases"]["extra"].append(u)
        self.changed()
        self.page.status("Added. Its list is loading…", 5000)
        self.render()
        self.render_dir()
        return True

    def done(self, r):
        self.svc.call("/api/settings", {"settings": self.page.S})  # (kept now, not in a moment)
        if self._refresh_soon.isActive():  # (a change still to load: the lists load now, in the background)
            self.svc.call("/api/db/refresh", {"settings": self.page.S})
        for t in (self._refresh_soon, self._poll, self._lib_poll):
            t.stop()
        super().done(r)
