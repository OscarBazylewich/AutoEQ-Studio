"""The Profiles screen of AutoEQ Studio's window (ui\\window.py): every profile (a copy of an EQ file): import,
rename, remove, where each is used.
ProfilesScreen is one part of the window's class (Window, in ui\\window.py): a plain class whose methods work on the
window, so they use the window's own things (sw, and the Settings part's open_folder for Show the files)."""
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QAbstractItemView, QFileDialog, QHBoxLayout, QHeaderView, QInputDialog, QMessageBox,
                               QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

import paths
from switcher import eqfile
from ui import help_window, icons
from ui.window_parts import muted, profile_line


class ProfilesScreen:
    """The Profiles screen's part of the window: the table of profiles, Import EQ files…, Rename, Remove and Show the
    files. A plain class (no __init__, no signals). The Devices screen uses its import_files too (Add a profile ›
    Import an EQ file…)."""

    # ---------------------------------------------------------------- Profiles
    def _profiles_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(muted("A profile is a copy of an EQ file (Equalizer APO's format: AutoEQ Local's \"Equalizer "
                            "APO\" file, AutoEq's ParametricEQ.txt, squig.link's export). Double-click a name to "
                            "rename it."))
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
        for c in (1, 2):
            h.setSectionResizeMode(c, QHeaderView.ResizeToContents)
        self.prof_table.itemChanged.connect(self._renamed)
        lay.addWidget(self.prof_table, 1)
        row = QHBoxLayout()
        for text, fn, symbol in (("Import EQ files…", lambda: self.import_files(), "import"),
                                 ("Edit in Make an EQ", self._edit_by_hand, "edit"),
                                 ("Rename", self._rename, "rename"), ("Remove", self._remove, "remove"),
                                 ("Show the files", lambda: self.open_folder(self.sw.apo.profiles), "folder")):
            b = QPushButton(text)
            icons.put(b, symbol)
            b.clicked.connect(fn)
            row.addWidget(b)
            if symbol == "edit":
                b.setToolTip("Change the chosen profile's filters by hand (on the graph, or as a table); Use on device › "
                             "Update puts it back, its devices keeping it")
                help_window.tag(b, "#prof-edit")
                self.prof_edit_btn = b
        row.addStretch(1)
        lay.addLayout(row)
        return w

    def render_profiles(self):
        t = self.prof_table
        t.blockSignals(True)
        t.setRowCount(0)
        for pid, p in sorted(self.sw.profiles().items(), key=lambda x: x[1]["name"].lower()):
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
                if c == 3:
                    item.setToolTip(p.get("source", ""))
                t.setItem(r, c, item)
        t.blockSignals(False)

    def _selected_profile(self):
        r = self.prof_table.currentRow()
        item = self.prof_table.item(r, 0) if r >= 0 else None
        return item.data(Qt.UserRole) if item else None

    def _renamed(self, item):
        if item.column() == 0:
            pid = item.data(Qt.UserRole)
            if not self.sw.rename_profile(pid, item.text()):
                self.render_profiles()

    def _rename(self):
        pid = self._selected_profile()
        if not pid:
            return
        name, ok = QInputDialog.getText(self, "Rename profile", "Name:", text=self.sw.profile_name(pid))
        if ok:
            self.sw.rename_profile(pid, name)

    def _edit_by_hand(self):
        """The chosen profile in Make an EQ as an EQ by hand (once that has opened): change its filters, then Use on
        device › Update puts it back."""
        pid = self._selected_profile()
        if not pid:
            QMessageBox.information(self, "Edit in Make an EQ", "Choose a profile in the list first.")
            return
        self.show_page("eq")
        self.eq_then(lambda page: page.hand_from_profile(pid), "The profile opens as soon as Make an EQ has opened…")

    def _remove(self):
        pid = self._selected_profile()
        if not pid:
            return
        used = self.sw.used_by(pid)
        if QMessageBox.question(self, "Remove profile", f"Remove “{self.sw.profile_name(pid)}”?"
                                + (f"\n\nIt's taken off {', '.join(used)} too." if used else "")) == QMessageBox.Yes:
            self.sw.remove_profile(pid)

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
            QMessageBox.warning(self, "Not imported", "\n\n".join(refused))
        return added
