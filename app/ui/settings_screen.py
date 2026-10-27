"""The Settings screen of AutoEQ Studio's window (ui\\window.py): starting with Windows, notices, the hotkeys (the
playing device's EQs one by one; its EQ off for now and back, to compare, level-matched or not), online or offline, Equalizer APO (setting it up for AutoEQ Studio: ui\\setup_dialog.py; taking AutoEQ Studio out of it; its
Configurator and config folder), your files' folder (paths.py, ui\\your_files.py), and Backup (everything of yours in
one .zip, and back: backup.py).
SettingsScreen is one part of the window's class (Window, in ui\\window.py): a plain class whose methods work on the
window, so they use the window's own things (sw, app, status(), and its hotkey_changed signal)."""
import os

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QKeySequence
from PySide6.QtWidgets import (QCheckBox, QFileDialog, QGroupBox, QHBoxLayout, QKeySequenceEdit, QLabel, QMessageBox,
                               QPushButton, QVBoxLayout, QWidget)

import paths
from ui import help_window, icons, theme
from ui.setup_dialog import SetUpDialog
from ui.window_parts import muted


class SettingsScreen:
    """The Settings screen's part of the window: AutoEQ Studio's own settings, Equalizer APO (its state, Set up…, Take
    AutoEQ Studio out, its Configurator and folder: the banner and Profiles use these actions too), your files' folder
    and Backup. A plain class (no __init__, no signals: the hotkey's signal is the window's)."""

    # ---------------------------------------------------------------- Settings
    def _settings_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        box = QGroupBox("AutoEQ Studio")
        bl = QVBoxLayout(box)
        self.chk_autostart = QCheckBox("Start with Windows (in the tray)")
        self.chk_autostart.toggled.connect(self.app.set_autostart)
        self.chk_notify = QCheckBox("Show a notice when the EQ switches")
        self.chk_notify.toggled.connect(lambda on: self.sw.set("notify", on))
        self.chk_offline = QCheckBox("Offline: never connect to the internet (use only what's on this PC)")
        self.chk_offline.toggled.connect(lambda on: self.app.set_offline(on))
        bl.addWidget(self.chk_autostart)
        bl.addWidget(self.chk_notify)
        bl.addWidget(self.chk_offline)
        row = QHBoxLayout()
        row.addWidget(QLabel("Hotkey to switch the playing device's EQ:"))
        self.hotkey_edit = QKeySequenceEdit()
        self.hotkey_edit.setMaximumSequenceLength(1)
        self.hotkey_edit.editingFinished.connect(lambda: self.hotkey_changed.emit(
            self.hotkey_edit.keySequence().toString(QKeySequence.PortableText)))
        row.addWidget(self.hotkey_edit)
        clear = QPushButton("None")
        clear.clicked.connect(lambda: (self.hotkey_edit.clear(), self.hotkey_changed.emit("")))
        row.addWidget(clear)
        row.addStretch(1)
        bl.addLayout(row)
        self.hotkey_note = muted()
        bl.addWidget(self.hotkey_note)
        help_window.tag(self.hotkey_edit, "#hotkey")
        # the on/off hotkey (2026-10-26): the playing device's EQ off for now, to compare, and back
        row = QHBoxLayout()
        row.addWidget(QLabel("Hotkey to switch the EQ off for now and back on, to compare:"))
        self.onoff_edit = QKeySequenceEdit()
        self.onoff_edit.setMaximumSequenceLength(1)
        self.onoff_edit.setAccessibleName("Hotkey to switch the EQ off for now and back on")
        self.onoff_edit.editingFinished.connect(lambda: self.onoff_hotkey_changed.emit(
            self.onoff_edit.keySequence().toString(QKeySequence.PortableText)))
        row.addWidget(self.onoff_edit)
        clear = QPushButton("None")
        clear.setAccessibleName("No hotkey to switch the EQ off and on")
        clear.clicked.connect(lambda: (self.onoff_edit.clear(), self.onoff_hotkey_changed.emit("")))
        row.addWidget(clear)
        row.addStretch(1)
        bl.addLayout(row)
        help_window.tag(self.onoff_edit, "#onoff-hotkey")
        self.chk_matched = QCheckBox("Level-matched: “off” plays as loud as the EQ (turned down to its loudness)")
        self.chk_matched.toggled.connect(lambda on: self.sw.set("onoff_matched", bool(on)))
        help_window.tag(self.chk_matched, "#onoff-matched")
        bl.addWidget(self.chk_matched)
        self.onoff_note = muted()
        bl.addWidget(self.onoff_note)
        about = muted(f"Version {paths.VERSION}" + (" · installed" if paths.INSTALLED
                                                     else f" · run from its folder ({paths.PROGRAM})"))
        about.setTextInteractionFlags(Qt.TextSelectableByMouse)
        about.setWordWrap(True)
        bl.addWidget(about)
        lay.addWidget(box)

        box = QGroupBox("Equalizer APO")
        bl = QVBoxLayout(box)
        self.apo_state = QLabel()
        self.apo_state.setWordWrap(True)
        self.apo_state.setTextInteractionFlags(Qt.TextSelectableByMouse)
        bl.addWidget(self.apo_state)
        row = QHBoxLayout()
        self.btn_setup = QPushButton("Set up…")
        self.btn_setup.clicked.connect(self.set_up_dialog)
        self.btn_unset = QPushButton("Take AutoEQ Studio out of APO…")
        icons.put(self.btn_unset, "cancel")
        self.btn_unset.clicked.connect(self.take_out)
        self.btn_conf = QPushButton("Open APO's Configurator")
        icons.put(self.btn_conf, "open_new")
        self.btn_conf.clicked.connect(self.open_configurator)
        self.btn_folder = QPushButton("Open APO's config folder")
        icons.put(self.btn_folder, "folder")
        self.btn_folder.clicked.connect(lambda: self.open_folder(self.sw.apo.config))
        for b in (self.btn_setup, self.btn_unset, self.btn_conf, self.btn_folder):
            row.addWidget(b)
        row.addStretch(1)
        bl.addLayout(row)
        lay.addWidget(box)

        box = QGroupBox("Your files")
        bl = QVBoxLayout(box)
        bl.addWidget(muted("Your targets and measurements (what Make an EQ uses), saved EQs and presets, each in a "
                           f"folder of its own ({paths.TARGETS_NAME}, {paths.MEASUREMENTS_NAME}, "
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
        self.btn_files_change.setToolTip("Keep your files in another folder (they can be moved there for you)")
        self.btn_files_change.clicked.connect(self.change_files_folder)
        for b in (self.btn_files_open, self.btn_files_change):
            help_window.tag(b, "#files-folder")
            row.addWidget(b)
        row.addStretch(1)
        bl.addLayout(row)
        lay.addWidget(box)
        self.show_files_folder()

        box = QGroupBox("Backup")
        bl = QVBoxLayout(box)
        bl.addWidget(muted("Everything of yours in one .zip: the devices and their profiles, Make an EQ's settings, "
                           "History, EQs to compare, your targets, measurements and saved EQs. For a new PC or a "
                           "reinstall."))
        row = QHBoxLayout()
        self.btn_backup = QPushButton("Back up everything…")
        icons.put(self.btn_backup, "backup")
        self.btn_backup.clicked.connect(self.make_backup)
        self.btn_restore = QPushButton("Restore from a backup…")
        icons.put(self.btn_restore, "restore")
        self.btn_restore.clicked.connect(self.restore_backup)
        for b in (self.btn_backup, self.btn_restore):
            help_window.tag(b, "#backup")
            row.addWidget(b)
        row.addStretch(1)
        bl.addLayout(row)
        lay.addWidget(box)
        lay.addStretch(1)
        return w

    # ---------------------------------------------------------------- Your files (paths.py, userfiles.py)
    def show_files_folder(self):
        self.files_label.setText(paths.ROOT + ("   (the usual place)" if os.path.normcase(paths.ROOT) ==
                                               os.path.normcase(paths.DEFAULT_FILES) else "   (your choice)"))

    def open_files_folder(self):
        try:
            os.makedirs(paths.ROOT, exist_ok=True)
        except OSError as e:
            QMessageBox.warning(self, "Your files", f"Couldn't open {paths.ROOT}: {e}")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(paths.ROOT))

    def change_files_folder(self):
        from ui import your_files
        your_files.change(self, self.sw.set, self.app.restart)

    # ---------------------------------------------------------------- Backup (backup.py)
    def make_backup(self):
        import backup
        # (Windows' Documents as paths finds it: it may be in OneDrive)
        start = os.path.join(os.path.dirname(paths.DEFAULT_FILES), backup.default_name())
        dest, _ = QFileDialog.getSaveFileName(self, "Back up everything", start, "Backup (*.zip)")
        if not dest:
            return
        try:
            info = backup.make(dest, self.sw.apo.profiles if self.sw.apo.found else None)
        except OSError as e:
            QMessageBox.warning(self, "Backup", f"Couldn't write the backup: {e}")
            return
        self.status(f"Backed up {info['files']} files ({info['profiles']} profiles) to {dest}.", 10000)

    def restore_backup(self):
        import backup
        src, _ = QFileDialog.getOpenFileName(self, "Restore from a backup", os.path.dirname(paths.DEFAULT_FILES),
                                             "Backup (*.zip)")
        if not src:
            return
        try:
            info = backup.read(src)
        except (ValueError, OSError) as e:
            QMessageBox.warning(self, "Restore", str(e))
            return
        if QMessageBox.question(
                self, "Restore", f"Restore the backup made {info['made']} ({info['files']} files, {info['profiles']} "
                "profiles)?\n\nIts settings, History and profiles replace the ones here; files with the same name are "
                "replaced, nothing else is deleted. How things are now is kept first (data\\backups). AutoEQ Studio "
                "starts again after it.") != QMessageBox.Yes:
            return
        if self.eq_page:
            self.eq_page.stop_sound()
        try:
            got = backup.restore(src, self.sw.apo.profiles if self.sw.apo.found else None)
        except (ValueError, OSError) as e:
            QMessageBox.warning(self, "Restore", f"Couldn't restore it: {e}")
            return
        # (nothing written over what was just restored before the restart: the devices' poll, Listen's and the
        # tracer's choices saved as the app quits)
        self.sw.read_only = True
        self.app.timer.stop()
        extra = ("\n\nIts profiles' EQ files weren't put back: Equalizer APO isn't installed here." if got["skipped"]
                 else "")
        QMessageBox.information(self, "Restore", f"Restored {got['files']} files. How things were is kept in "
                                f"{got['kept']}.{extra}\n\nAutoEQ Studio starts again now.")
        self.app.restart()

    def render_settings(self):
        for chk, on in ((self.chk_autostart, self.app.autostart_on()), (self.chk_notify, self.sw.s["notify"])):
            chk.blockSignals(True)
            chk.setChecked(on)
            chk.blockSignals(False)
        if not self.hotkey_edit.hasFocus():
            self.hotkey_edit.setKeySequence(QKeySequence(self.sw.s.get("hotkey") or ""))
        self.hotkey_note.setText(self.app.hotkey_problem or "Works in any program. It goes through the playing "
                                 "device's profiles, then Off.")
        role = "warn" if self.app.hotkey_problem else "muted"  # (a problem with the hotkey is said as a warning)
        if self.hotkey_note.property("role") != role:
            theme.mark(self.hotkey_note, role=role)
        if not self.onoff_edit.hasFocus():
            self.onoff_edit.setKeySequence(QKeySequence(self.sw.s.get("onoff_hotkey") or ""))
        self.chk_matched.blockSignals(True)
        self.chk_matched.setChecked(bool(self.sw.s.get("onoff_matched", True)))
        self.chk_matched.blockSignals(False)
        problem = getattr(self.app, "onoff_problem", "")
        self.onoff_note.setText(problem or "Works in any program: the playing device's EQ off for now, then back on. "
                                "Level-matched, “off” isn't louder than the EQ, so neither seems better for being "
                                "louder.")
        role = "warn" if problem else "muted"
        if self.onoff_note.property("role") != role:
            theme.mark(self.onoff_note, role=role)
        apo = self.sw.apo
        if not apo.found:
            state = "Not installed (or its config folder wasn't found)."
        else:
            state = f"Config folder: {apo.config}\n" + ("AutoEQ Studio is set up: config.txt includes its file."
                                                       if apo.set_up() else "Not using AutoEQ Studio yet.")
        self.apo_state.setText(state)
        self.btn_setup.setVisible(apo.found and not apo.set_up())
        self.btn_unset.setVisible(apo.found and apo.set_up())
        self.btn_conf.setVisible(bool(apo.configurator))
        self.btn_folder.setVisible(apo.found)

    # ---------------------------------------------------------------- APO actions
    def set_up_dialog(self):
        SetUpDialog(self.sw, self).exec()

    def take_out(self):
        if QMessageBox.question(
                self, "Take AutoEQ Studio out of APO",
                "config.txt's AutoEQ Studio line goes, and the lines it turned off are on again: APO works as it did "
                "before. Your profiles stay (for setting up again).") == QMessageBox.Yes:
            try:
                self.sw.remove_from_apo()
            except OSError as e:
                QMessageBox.warning(self, "Take AutoEQ Studio out of APO", str(e))

    def open_configurator(self):
        exe = self.sw.apo.configurator
        if exe:
            from ui import winsys
            try:
                winsys.start_program(exe)
            except OSError as e:  # (Windows' "allow changes?" answered No, among others)
                if getattr(e, "winerror", None) != 1223:
                    QMessageBox.warning(self, "APO's Configurator", f"Couldn't open it: {e}")

    def open_folder(self, folder):
        if folder and os.path.isdir(folder):
            os.startfile(folder)
        elif folder:
            QMessageBox.information(self, "Not there yet", f"{folder} isn't there yet.")
