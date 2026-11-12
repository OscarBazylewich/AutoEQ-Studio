"""The Profiles screen of AutoEQ Studio's window (ui\\window.py): every profile (a copy of an EQ file): import,
rename, delete, where each is used. Its commands are a table's (.claude/notes/UI-RULES.md 19): in a row above the
table, those for the chosen profile off until one is chosen (File Explorer's way), Delete… last and apart (14), with
the bin (10; it deletes the profile's file) and No as the question's default (17).
ProfilesScreen is one part of the window's class (Window, in ui\\window.py): a plain class whose methods work on the
window, so they use the window's own things (sw, and the Settings part's open_folder for Open the profiles folder)."""
import os

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtWidgets import (QAbstractItemView, QFileDialog, QFrame, QHBoxLayout, QHeaderView, QMessageBox,
                               QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

import paths
from switcher import eqfile
from ui import help_window, icons, theme
from ui.search_combo import natural_key
from ui.window_parts import EmptyText, muted, profile_line


USED_BY_MOST = 0.3  # (the "Used by" column's largest part of the table's width: the name keeps its room)


class UsedByWidth(QObject):
    """The "Used by" column as wide as its words, but never more than USED_BY_MOST of the table: with a profile on
    many devices it took all the room, and the Name column became too narrow to read. Its cells end in "…" then, and
    their tooltips have all the devices. Measured again when the table changes size and after it is filled (fit())."""

    COLUMN = 2

    def __init__(self, table):
        super().__init__(table)
        self.table = table
        table.horizontalHeader().setSectionResizeMode(self.COLUMN, QHeaderView.Fixed)
        table.viewport().installEventFilter(self)

    def fit(self):
        t, h, c = self.table, self.table.horizontalHeader(), self.COLUMN
        words = max(t.sizeHintForColumn(c), h.sectionSizeHint(c))
        most = int(t.viewport().width() * USED_BY_MOST)
        h.resizeSection(c, max(h.sectionSizeHint(c), min(words, most)))

    def eventFilter(self, obj, e):
        if e.type() == QEvent.Resize:
            self.fit()
        return False


class ProfilesScreen:
    """The Profiles screen's part of the window: the table of profiles, Import EQ files…, Edit in Make an EQ, Rename…,
    Open the profiles folder and Delete…. A plain class (no __init__, no signals). The Devices screen uses its
    import_files too (Add a profile › Import EQ files…)."""

    # ---------------------------------------------------------------- Profiles
    def _profiles_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)  # (lined up with the top bar, as every screen: UI-RULES 5)
        lay.addWidget(muted("A profile is a copy of an EQ file in the Equalizer APO format (the “Equalizer APO” file "
                            "of AutoEQ Local, ParametricEQ.txt of AutoEq, an EQ file that squig.link exports). To "
                            "rename a profile, double-click its name."))
        # (the table's commands above it, near the rows they act on: under a table that fills the screen they were
        # 750 px from its one row)
        # (the general commands first, then a thin line and those for the selected profile, Delete… last and apart: as
        # File Explorer's command bar, New first; the UI audit, 2026-11-08: they were mixed, on, off, off, on, off)
        row = QHBoxLayout()
        self.prof_needs_one = []
        for text, fn, symbol in (("Import EQ files…", lambda: self.import_files(), "import"),
                                 ("Open the profiles folder", lambda: self.open_folder(self.sw.apo.profiles), "folder"),
                                 ("Edit in Make an EQ", self._edit_in_make_eq, "edit"),
                                 ("Rename…", self._rename_profile, "rename"),
                                 ("Delete…", self._delete_profile, "delete")):
            b = QPushButton(text)
            icons.put(b, symbol)
            b.clicked.connect(fn)
            if text == "Delete…":
                row.addStretch(1)  # (last and apart: UI-RULES 14)
                b.setToolTip("Delete the selected profile and its file, and remove it from its devices")
            if text == "Edit in Make an EQ":
                line = QFrame()
                theme.mark(line, vline=True)
                line.setFixedSize(1, 20)
                row.addSpacing(4)
                row.addWidget(line)
                row.addSpacing(4)
            row.addWidget(b)
            if symbol in ("edit", "rename", "delete"):  # (for the chosen profile: off until one is chosen)
                self.prof_needs_one.append(b)
            if symbol == "edit":
                b.setToolTip("Change the filters of the selected profile manually (on the graph, or in the table). Use "
                             "on device › Update saves them in the profile, and its devices keep it.")
                help_window.tag(b, "#prof-edit")
                self.prof_edit_btn = b
        lay.addLayout(row)
        self.prof_table = QTableWidget(0, 4)
        self.prof_table.setObjectName("profileTable")  # (its cells' words under their headings: window_screens)
        self.prof_table.setAccessibleName("Profiles")
        self.prof_table.setHorizontalHeaderLabels(["Name", "EQ", "Used by", "From"])
        self.prof_table.verticalHeader().hide()
        self.prof_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.prof_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.prof_table.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed)
        # as Windows 11 draws a table: headings at the left, no grid, rows with room for the 10.5 pt text
        self.prof_table.setShowGrid(False)
        self.prof_table.setWordWrap(False)
        self.prof_table.verticalHeader().setDefaultSectionSize(36)
        h = self.prof_table.horizontalHeader()
        h.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        h.setHighlightSections(False)
        # (the name and the file it came from share the room left: neither is cut while the other has plenty)
        for c in (0, 3):
            h.setSectionResizeMode(c, QHeaderView.Stretch)
        h.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.prof_used_by = UsedByWidth(self.prof_table)  # ("Used by": as wide as its words, to a limit)
        # (no profiles: one gray line that tells the next step, as every empty list: UI-RULES 21)
        self.prof_empty = EmptyText(self.prof_table, "No profiles. Click “Import EQ files…”, or make an EQ in Make an EQ "
                                    "and click Use on device.")
        self.prof_table.itemChanged.connect(self._renamed)
        self.prof_table.itemSelectionChanged.connect(self._update_profile_commands)
        lay.addWidget(self.prof_table, 1)
        self._update_profile_commands()
        return w

    def _update_profile_commands(self):
        """The chosen profile's commands on with a profile chosen, off without."""
        one = self._selected_profile() is not None
        for b in self.prof_needs_one:
            b.setEnabled(one)

    def render_profiles(self):
        t = self.prof_table
        chosen = self._selected_profile()  # (chosen again once the table is drawn again: its commands stay on)
        t.blockSignals(True)
        t.setRowCount(0)
        for pid, p in sorted(self.sw.profiles().items(), key=lambda x: natural_key(x[1]["name"])):  # (UI-RULES 22)
            r = t.rowCount()
            t.insertRow(r)
            name = QTableWidgetItem(p["name"])
            name.setToolTip(p["name"])  # (whole, when the column is too narrow for it)
            name.setData(Qt.UserRole, pid)
            t.setItem(r, 0, name)
            for c, text in ((1, profile_line(p) + ("  (file missing)" if self.sw.profile_missing(pid) else "")),
                            (2, ", ".join(self.sw.used_by(pid)) or "–"),
                            (3, os.path.basename(p.get("source", "")))):
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                if c == 2:
                    item.setToolTip(text)  # (whole, when the column is too narrow for it)
                if c == 3:
                    item.setToolTip(p.get("source", ""))
                t.setItem(r, c, item)
            if pid == chosen:
                t.selectRow(r)
        t.blockSignals(False)
        self.prof_used_by.fit()
        self._update_profile_commands()

    def _selected_profile(self):
        rows = self.prof_table.selectionModel().selectedRows() if self.prof_table.selectionModel() else []
        item = self.prof_table.item(rows[0].row(), 0) if rows else None
        return item.data(Qt.UserRole) if item else None

    def _renamed(self, item):
        if item.column() == 0:
            pid = item.data(Qt.UserRole)
            if not self.sw.rename_profile(pid, item.text()):
                self.render_profiles()

    def _rename_profile(self):
        pid = self._selected_profile()
        if not pid:
            return
        from ui.window_parts import ask_text  # (looked up here: the tests answer it)
        name, ok = ask_text(self, "Rename the profile", "Its name", self.sw.profile_name(pid), "Rename")
        if ok:
            self.sw.rename_profile(pid, name)

    def _edit_in_make_eq(self):
        """The chosen profile in Make an EQ as an EQ by hand (once that has opened): change its filters, then Use on
        device › Update puts it back."""
        pid = self._selected_profile()
        if not pid:  # (off then: UI-RULES 19)
            return
        self.show_page("eq")
        self.when_eq_opens(lambda page: page.manual_from_profile(pid), "The profile opens after Make an EQ opens…")

    def _delete_profile(self):
        pid = self._selected_profile()
        if not pid:
            return
        used = self.sw.used_by(pid)
        if QMessageBox.question(self, "Delete", f"Delete “{self.sw.profile_name(pid)}” and its file?"
                                + (f"\n\nAutoEQ Studio also removes it from {', '.join(used)}." if used else ""),
                                QMessageBox.Yes | QMessageBox.No, QMessageBox.No) == QMessageBox.Yes:
            self.sw.remove_profile(pid)  # (No the default: it can't be undone, UI-RULES 17)

    def import_files(self, for_device=None):
        """Import EQ files as profiles (starting in your Saved EQs folder, where Save filters writes;
        else AutoEQ Local's when it's beside this app; else APO's config folder); for_device: also add them to that
        device (the first one switched on)."""
        own = paths.SAVED_EQS
        start = own if os.path.isdir(own) else paths.AUTOEQ_OUTPUT if os.path.isdir(paths.AUTOEQ_OUTPUT) else \
            (self.sw.apo.config or "")
        files, _ = QFileDialog.getOpenFileNames(self, "Import EQ files", start, "EQ files (*.txt);;All files (*)")
        added, refused = [], []
        for f in files:
            try:
                added.append(self.sw.import_profile(f))
            except (eqfile.NotAnEqFile, OSError) as e:
                refused.append(f"{os.path.basename(f)}: {e}")
        if for_device:
            for i, pid in enumerate(added):
                self.sw.add_to_device(for_device, pid, switch_on=i == 0)
        if refused:
            QMessageBox.warning(self, "Import EQ files", "\n\n".join(refused))
        return added
