"""The Settings screen of AutoEQ Studio's window (ui\\window.py): starting with Windows, notices, the hotkeys (the
playing device's EQs one by one; its EQ off for now and back, to compare, level-matched or not), online or offline, Equalizer APO (setting it up for AutoEQ Studio: ui\\setup_dialog.py; taking AutoEQ Studio out of it; its
Configurator and config folder), your files' folder (paths.py, ui\\your_files.py), and Backup (everything of yours in
one .zip, and back: backup.py).
SettingsScreen is one part of the window's class (Window, in ui\\window.py): a plain class whose methods work on the
window, so they use the window's own things (sw, app, status(), and its hotkey_changed signal)."""
import os

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QKeySequence
from PySide6.QtWidgets import (QCheckBox, QFileDialog, QGridLayout, QGroupBox, QHBoxLayout, QKeySequenceEdit, QLabel,
                               QMessageBox, QPushButton, QVBoxLayout, QWidget)

import paths
from ui import help_window, icons, theme
from ui.bubble import InfoMark
from ui.setup_dialog import SetUpDialog
from ui.window_parts import glyph_label, muted


class SettingsScreen:
    """The Settings screen's part of the window: AutoEQ Studio's own settings, Equalizer APO (its state, Set up…, Take
    AutoEQ Studio out, its Configurator and folder: the banner and Profiles use these actions too), your files' folder
    and Backup. A plain class (no __init__, no signals: the hotkey's signal is the window's)."""

    # ---------------------------------------------------------------- Settings
    def _settings_tab(self):
        w = QWidget()
        # (at most about 900 px wide, at the left, as Windows 11's Settings: on a wide window a card's buttons were far
        # from its words; the UI audit, 2026-11-08)
        w.setMaximumWidth(900)
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)  # (lined up with the top bar, as every screen: .claude/notes/UI-RULES.md 5)
        lay.setSpacing(12)  # (its cards as far apart as Make an EQ's: Qt's 6 px)
        box = QGroupBox("AutoEQ Studio")
        bl = QVBoxLayout(box)
        self.chk_autostart = QCheckBox("Start with Windows (in the tray)")
        self.chk_autostart.toggled.connect(self.app.set_autostart)
        self.chk_notify = QCheckBox("Show a notification when the EQ changes")
        self.chk_notify.toggled.connect(lambda on: self.sw.set("notify", on))
        self.chk_offline = QCheckBox("Offline: do not connect to the internet (use only the data on this PC)")
        self.chk_offline.toggled.connect(lambda on: self.app.set_offline(on))
        bl.addWidget(self.chk_autostart)
        bl.addWidget(self.chk_notify)
        bl.addWidget(self.chk_offline)
        lay.addWidget(box)

        # the hotkeys, as a form (UI-RULES 26): their labels in one column, each with its ⓘ (the words about it: the
        # gray notes under the boxes went behind it, the UI audit, 2026-11-08), their boxes lined up in the next, each
        # with its ✕ at its right end (as the search boxes'; the Clear buttons went); a problem with a hotkey is said
        # in the warning colour under its box
        box = QGroupBox("Hotkeys")
        g = QGridLayout(box)
        g.setHorizontalSpacing(10)  # (as forms.py's: UI-RULES 26)
        g.setVerticalSpacing(6)
        g.setColumnStretch(2, 1)

        def label(words, info):
            w = QWidget()
            h = QHBoxLayout(w)
            h.setContentsMargins(0, 0, 0, 0)
            h.setSpacing(4)
            h.addWidget(QLabel(words))
            mark = InfoMark(info, words)
            h.addWidget(mark)
            h.addStretch(1)
            return w, mark

        def key_box(name, changed):
            e = QKeySequenceEdit()
            e.setMaximumSequenceLength(1)
            e.setClearButtonEnabled(True)
            e.setAccessibleName(name)
            e.setMinimumWidth(200)
            def say():  # (each new key said once: when typing ends, and at once when the box's ✕ empties it)
                text = e.keySequence().toString(QKeySequence.PortableText)
                if text != e.property("said"):
                    e.setProperty("said", text)
                    changed.emit(text)
            e.editingFinished.connect(say)
            e.keySequenceChanged.connect(lambda seq: seq.isEmpty() and say())
            return e
        lab, self.hotkey_info = label("Change the EQ of the active device", "")
        g.addWidget(lab, 0, 0)
        self.hotkey_edit = key_box("Hotkey to change the EQ of the active device", self.hotkey_changed)
        g.addWidget(self.hotkey_edit, 0, 1)
        self.hotkey_note = QLabel()
        self.hotkey_note.setWordWrap(True)
        theme.mark(self.hotkey_note, role="warn")
        g.addWidget(self.hotkey_note, 1, 1, 1, 2)
        help_window.tag(self.hotkey_edit, "#hotkey")
        # the on/off hotkey (2026-10-26): the playing device's EQ off for now, to compare, and back
        lab, self.onoff_info = label("Disable and enable its EQ, to compare", "")
        g.addWidget(lab, 2, 0)
        self.onoff_edit = key_box("Hotkey to disable the EQ and enable it again", self.onoff_hotkey_changed)
        g.addWidget(self.onoff_edit, 2, 1)
        help_window.tag(self.onoff_edit, "#onoff-hotkey")
        self.chk_matched = QCheckBox("Same level: “off” has the same loudness as the EQ (with a lower volume)")
        self.chk_matched.toggled.connect(lambda on: self.sw.set("onoff_matched", bool(on)))
        help_window.tag(self.chk_matched, "#onoff-matched")
        g.addWidget(self.chk_matched, 3, 1, 1, 2)
        self.onoff_note = QLabel()
        self.onoff_note.setWordWrap(True)
        theme.mark(self.onoff_note, role="warn")
        g.addWidget(self.onoff_note, 4, 1, 1, 2)
        lay.addWidget(box)

        # (the condition first, with its symbol and colour, as the line about the EQ on Devices; the folder's path under
        # it in gray: the UI audit, 2026-11-08, the condition came second, after a long path)
        box = QGroupBox("Equalizer APO")
        bl = QVBoxLayout(box)
        state = QHBoxLayout()
        state.setSpacing(8)
        self.apo_mark = glyph_label("warning", role="warn")
        state.addWidget(self.apo_mark, 0, Qt.AlignTop)
        self.apo_state = QLabel()
        self.apo_state.setWordWrap(True)
        state.addWidget(self.apo_state, 1)
        bl.addLayout(state)
        self.apo_path = muted()
        self.apo_path.setTextInteractionFlags(Qt.TextSelectableByMouse)
        bl.addWidget(self.apo_path)
        row = QHBoxLayout()
        self.btn_setup = QPushButton("Add AutoEQ Studio to APO…")
        theme.mark(self.btn_setup, primary=True)  # (the card's main command when APO does not use it: UI-RULES 8)
        icons.put(self.btn_setup, "tools")  # (every button in the row with its symbol: UI-RULES 9)
        self.btn_setup.clicked.connect(self.add_studio_to_apo)
        self.btn_unset = QPushButton("Remove AutoEQ Studio from APO…")
        icons.put(self.btn_unset, "remove")
        self.btn_unset.clicked.connect(self.remove_studio_from_apo)
        self.btn_conf = QPushButton("Open APO's Configurator")
        icons.put(self.btn_conf, "open_new")
        self.btn_conf.clicked.connect(self.open_configurator)
        self.btn_folder = QPushButton("Open APO's config folder")
        icons.put(self.btn_folder, "folder")
        self.btn_folder.clicked.connect(lambda: self.open_folder(self.sw.apo.config))
        for b in (self.btn_setup, self.btn_conf, self.btn_folder):
            row.addWidget(b)
        row.addStretch(1)  # (taking it out last and apart, never first beside Set up…: UI-RULES 14)
        row.addWidget(self.btn_unset)
        bl.addLayout(row)
        lay.addWidget(box)

        box = QGroupBox("Your files")
        bl = QVBoxLayout(box)
        bl.addWidget(muted("Your targets and measurements (for Make an EQ), saved EQs and presets, each in a "
                           f"different folder ({paths.TARGETS_NAME}, {paths.MEASUREMENTS_NAME}, "
                           f"{paths.SAVED_EQS_NAME}, {paths.PRESETS_NAME}), in:"))
        self.files_label = QLabel()
        self.files_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.files_label.setWordWrap(True)
        bl.addWidget(self.files_label)
        row = QHBoxLayout()
        self.btn_files_open = QPushButton("Open the folder")
        icons.put(self.btn_files_open, "folder")
        self.btn_files_open.clicked.connect(self.open_files_folder)
        self.btn_files_change = QPushButton("Change…")
        icons.put(self.btn_files_change, "change_folder")
        self.btn_files_change.setToolTip("Keep your files in a different folder (AutoEQ Studio can move them there)")
        self.btn_files_change.clicked.connect(self.change_files_folder)
        for b in (self.btn_files_open, self.btn_files_change):
            help_window.tag(b, "#files-folder")
            row.addWidget(b)
        row.addStretch(1)
        bl.addLayout(row)
        lay.addWidget(box)
        self.render_files_folder()

        box = QGroupBox("Backup")
        bl = QVBoxLayout(box)
        bl.addWidget(muted("One .zip file keeps all your data. It has the devices and their profiles, the settings of "
                           "Make an EQ, History, EQs to compare, your targets, measurements and saved EQs. It is for a new "
                           "PC, or if you install AutoEQ Studio again."))
        row = QHBoxLayout()
        self.btn_backup = QPushButton("Save a backup…")
        icons.put(self.btn_backup, "backup")
        self.btn_backup.clicked.connect(self.make_backup)
        self.btn_restore = QPushButton("Load a backup…")
        icons.put(self.btn_restore, "restore")
        self.btn_restore.clicked.connect(self.load_backup)
        for b in (self.btn_backup, self.btn_restore):
            help_window.tag(b, "#backup")
            row.addWidget(b)
        row.addStretch(1)
        bl.addLayout(row)
        lay.addWidget(box)

        # the version, last, in a card of its own, as Windows 11's apps' About (it read as the hotkeys' last note)
        box = QGroupBox("About AutoEQ Studio")
        bl = QVBoxLayout(box)
        about = muted(f"Version {paths.VERSION}" + (" · installed" if paths.INSTALLED
                                                     else f" · started from its folder ({paths.PROGRAM})"))
        about.setTextInteractionFlags(Qt.TextSelectableByMouse)
        about.setWordWrap(True)
        bl.addWidget(about)
        lay.addWidget(box)
        lay.addStretch(1)
        return w

    # ---------------------------------------------------------------- Your files (paths.py, userfiles.py)
    def render_files_folder(self):
        self.files_label.setText(paths.ROOT + ("   (the usual folder)" if os.path.normcase(paths.ROOT) ==
                                               os.path.normcase(paths.DEFAULT_FILES) else "   (your selection)"))

    def open_files_folder(self):
        try:
            os.makedirs(paths.ROOT, exist_ok=True)
        except OSError as e:
            QMessageBox.warning(self, "Your files", f"AutoEQ Studio cannot open {paths.ROOT}: {e}")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(paths.ROOT))

    def change_files_folder(self):
        from ui import your_files
        your_files.change_location(self, self.sw.set, self.app.restart)

    # ---------------------------------------------------------------- Backup (backup.py)
    def make_backup(self):
        import backup
        # (Windows' Documents as paths finds it: it may be in OneDrive)
        start = os.path.join(os.path.dirname(paths.DEFAULT_FILES), backup.default_name())
        dest, _ = QFileDialog.getSaveFileName(self, "Save a backup", start, "Backup (*.zip)")
        if not dest:
            return
        try:
            info = backup.make(dest, self.sw.apo.profiles if self.sw.apo.found else None)
        except OSError as e:
            QMessageBox.warning(self, "Backup", f"AutoEQ Studio cannot save the backup: {e}")
            return
        self.status(f"AutoEQ Studio saved {info['files']} files ({info['profiles']} profiles) in the backup {dest}.",
                    10000)

    def load_backup(self):
        import backup
        src, _ = QFileDialog.getOpenFileName(self, "Load a backup", os.path.dirname(paths.DEFAULT_FILES),
                                             "Backup (*.zip)")
        if not src:
            return
        try:
            info = backup.read(src)
        except (ValueError, OSError) as e:
            QMessageBox.warning(self, "Load a backup", str(e))
            return
        if QMessageBox.question(
                self, "Load a backup", f"Load the backup from {info['made']} ({info['files']} files, "
                f"{info['profiles']} profiles)?\n\nIts settings, History and profiles replace the settings, History "
                "and profiles on this PC. Its files replace the files that have the same names. AutoEQ Studio does "
                "not delete other files. First, AutoEQ Studio saves a backup of the data that is on this PC "
                "(data\\backups). Then AutoEQ Studio starts again.") != QMessageBox.Yes:
            return
        if self.eq_page:
            self.eq_page.stop_sound()
        try:
            got = backup.restore(src, self.sw.apo.profiles if self.sw.apo.found else None)
        except (ValueError, OSError) as e:
            QMessageBox.warning(self, "Load a backup", f"AutoEQ Studio cannot load the backup: {e}")
            return
        # (nothing written over what was just restored before the restart: the devices' poll, Listen's and the
        # tracer's choices saved as the app quits)
        self.sw.read_only = True
        self.app.timer.stop()
        extra = ("\n\nAutoEQ Studio did not load the EQ files of the profiles: Equalizer APO is not installed on "
                 "this PC." if got["skipped"] else "")
        QMessageBox.information(self, "Load a backup", f"AutoEQ Studio loaded {got['files']} files. The backup of "
                                f"your previous data is in {got['kept']}.{extra}\n\nAutoEQ Studio starts again.")
        self.app.restart()

    def render_settings(self):
        for chk, on in ((self.chk_autostart, self.app.autostart_on()), (self.chk_notify, self.sw.s["notify"])):
            chk.blockSignals(True)
            chk.setChecked(on)
            chk.blockSignals(False)
        if not self.hotkey_edit.hasFocus():
            self._show_key(self.hotkey_edit, self.sw.s.get("hotkey") or "")
        self.hotkey_info.set_text("It operates in all programs. It selects the next profile of the active device each "
                                  "time, and Off after the last profile.")
        self.hotkey_note.setText(self.app.hotkey_problem or "")  # (a problem with the hotkey: said under its box)
        self.hotkey_note.setVisible(bool(self.app.hotkey_problem))
        if not self.onoff_edit.hasFocus():
            self._show_key(self.onoff_edit, self.sw.s.get("onoff_hotkey") or "")
        self.chk_matched.blockSignals(True)
        self.chk_matched.setChecked(bool(self.sw.s.get("onoff_matched", True)))
        self.chk_matched.blockSignals(False)
        problem = getattr(self.app, "onoff_problem", "")
        self.onoff_info.set_text("It operates in all programs. It disables the EQ of the active device, and then it "
                                 "enables the EQ again. With Same level, “off” and the EQ have the same loudness. Thus, "
                                 "you compare the sound and not the volume.")
        self.onoff_note.setText(problem or "")
        self.onoff_note.setVisible(bool(problem))
        apo = self.sw.apo
        good = apo.found and apo.includes_studio()
        if not apo.found:
            state = "Equalizer APO is not installed (or AutoEQ Studio did not find its config folder)."
        else:
            state = ("✓ APO uses AutoEQ Studio: config.txt has a line for the AutoEQ Studio file." if good
                     else "APO does not use AutoEQ Studio.")
        self.apo_state.setText(state)
        role = "good" if good else "warn"
        if self.apo_state.property("role") != role:
            theme.mark(self.apo_state, role=role)
        self.apo_mark.setVisible(not good)
        self.apo_path.setText(f"Its config folder: {apo.config}" if apo.found else "")
        self.apo_path.setVisible(apo.found)
        self.btn_setup.setVisible(apo.found and not apo.includes_studio())
        self.btn_unset.setVisible(apo.found and apo.includes_studio())
        self.btn_conf.setVisible(bool(apo.configurator))
        self.btn_folder.setVisible(apo.found)

    @staticmethod
    def _show_key(box, text):
        """A hotkey box shows the saved key (not said back as a change)."""
        box.blockSignals(True)
        box.setKeySequence(QKeySequence(text))
        box.blockSignals(False)
        box.setProperty("said", QKeySequence(text).toString(QKeySequence.PortableText))

    # ---------------------------------------------------------------- APO actions
    def add_studio_to_apo(self):
        SetUpDialog(self.sw, self).exec()

    def remove_studio_from_apo(self):
        if QMessageBox.question(
                self, "Remove AutoEQ Studio from APO",
                "AutoEQ Studio removes its line from config.txt and enables the lines that it disabled. Then APO "
                "operates as it did before you added AutoEQ Studio. AutoEQ Studio keeps your profiles (if you add "
                "AutoEQ Studio to APO again).") == QMessageBox.Yes:  # (Set up… puts it back)
            try:
                self.sw.remove_from_apo()
            except OSError as e:
                QMessageBox.warning(self, "Remove AutoEQ Studio from APO", str(e))

    def open_configurator(self):
        exe = self.sw.apo.configurator
        if exe:
            from ui import winsys
            try:
                winsys.start_program(exe)
            except OSError as e:  # (Windows' "allow changes?" answered No, among others)
                if getattr(e, "winerror", None) != 1223:
                    QMessageBox.warning(self, "APO's Configurator", f"AutoEQ Studio cannot open the Configurator: {e}")

    def open_folder(self, folder):
        if folder and os.path.isdir(folder):
            os.startfile(folder)
        elif folder:
            QMessageBox.information(self, "Open the folder", f"The folder {folder} is not on this PC.")
