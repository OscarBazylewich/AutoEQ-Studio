"""The Settings screen of AutoEQ Studio's window (ui\\window.py): starting with Windows, notices, the hotkeys (the
playing device's EQs one by one; its EQ off for now and back, to compare, level-matched or not), online or offline, Equalizer APO (setting it up for AutoEQ Studio: ui\\setup_dialog.py; taking AutoEQ Studio out of it; its
Configurator and config folder), your files' folder (paths.py, ui\\your_files.py), and Backup (everything of yours in
one .zip, and back: backup.py).
SettingsScreen is one part of the window's class (Window, in ui\\window.py): a plain class whose methods work on the
window, so they use the window's own things (sw, app, status(), and its hotkey_changed signal)."""
import os

from PySide6.QtCore import QEvent, QObject, Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QKeySequence
from PySide6.QtWidgets import (QCheckBox, QFileDialog, QGridLayout, QGroupBox, QHBoxLayout, QKeySequenceEdit, QLabel,
                               QLineEdit, QMessageBox, QPushButton, QVBoxLayout, QWidget)

import paths
from ui import help_window, icons, placed, theme
from ui.setup_dialog import SetUpDialog
from ui.window_parts import glyph_label, muted


def _count(n, word):
    """"1 file", "2 files", "0 profiles": the backup messages' counts. The owner's words (the text survey,
    2026-11-24) are "{n} files" and "{n} profiles"; a count of 1 takes the word without its "s"."""
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


class _KeyWatch(QObject):
    """A hotkey box's watch: typing is True from a key press until the key is complete (Qt empties the box at the
    first key press); cleared is True when the box was emptied on purpose."""

    def __init__(self, box):
        super().__init__(box)
        self.typing = self.cleared = False
        box.installEventFilter(self)

    def eventFilter(self, obj, e):
        if e.type() == QEvent.KeyPress:
            self.typing = True
        elif e.type() == QEvent.FocusOut:
            self.typing = False
        return False


MATCHED_WORDS = "Same level: “off” has the same loudness as the EQ (with a lower volume)"


class _TickWords(QLabel):
    """The words after a tick box, on more lines when the window is narrow (a tick box's own words stay on one line).
    A click on them ticks or clears the box, as a click on its own words does."""

    def __init__(self, words, box):
        super().__init__(words)
        self.box = box
        self.setWordWrap(True)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self.box.isEnabled() and self.rect().contains(e.position().toPoint()):
            self.box.toggle()
        super().mouseReleaseEvent(e)


class SettingsScreen:
    """The Settings screen's part of the window: AutoEQ Studio's own settings, Equalizer APO (its state, Add AutoEQ
    Studio to APO…, Remove AutoEQ Studio from APO…, its Configurator and folder: the banner and Profiles use these
    actions too), your files' folder and Backup. A plain class (no __init__, no signals: the two hotkeys' signals are
    the window's)."""

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

        # the hotkeys, as a form (UI-RULES 26): their labels in one column, their boxes lined up in the next, each
        # with its ✕ at its right end (as the search boxes'; the Clear buttons went); a problem with a hotkey is said
        # in the warning colour under its box. (The labels had an ⓘ each until the text survey, 2026-11-24: the user
        # removed them, as the boxes' tooltips and their Help entries give the same facts.)
        box = QGroupBox("Hotkeys")
        g = QGridLayout(box)
        g.setHorizontalSpacing(10)  # (as forms.py's: UI-RULES 26)
        g.setVerticalSpacing(6)
        g.setColumnStretch(2, 1)

        def key_box(name, changed, setting):
            e = QKeySequenceEdit()
            e.setMaximumSequenceLength(1)
            e.setClearButtonEnabled(True)
            e.setAccessibleName(name)
            e.setMinimumWidth(200)
            # (Qt empties the box when you press the first key of a new hotkey: that empty value is not a change.
            # Only the box's ✕, or the box emptied while you do not type in it, asks for no hotkey. Before, the first
            # key press saved "no hotkey", so a key that Windows then refused could not put the old key back.)
            watch = _KeyWatch(e)

            def say():  # (each new key said once: when typing ends, and at once when the box's ✕ empties it)
                watch.typing = False
                text = e.keySequence().toString(QKeySequence.PortableText)
                if text == e.property("said"):
                    return
                if not text and not watch.cleared:  # (typing ended with no key, e.g. Ctrl only: the key before stays)
                    self._show_key(e, e.property("said") or "")
                    return
                watch.cleared = False
                e.setProperty("said", text)
                changed.emit(text)
                kept = QKeySequence(self.sw.s.get(setting) or "").toString(QKeySequence.PortableText)
                if kept != text:  # (Windows refused it: the box shows the key that the app kept)
                    self._show_key(e, kept)

            def emptied():
                watch.cleared = True
                say()
            e.editingFinished.connect(say)
            e.keySequenceChanged.connect(lambda seq: seq.isEmpty() and not watch.typing and emptied())
            e.findChild(QLineEdit).textEdited.connect(lambda text: not text and emptied())  # (the box's ✕)
            return e
        g.addWidget(QLabel("Change the EQ of the active device"), 0, 0)
        self.hotkey_edit = key_box("Hotkey to change the EQ of the active device", self.hotkey_changed, "hotkey")
        g.addWidget(self.hotkey_edit, 0, 1)
        self.hotkey_note = QLabel()
        self.hotkey_note.setWordWrap(True)
        theme.mark(self.hotkey_note, role="warn")
        g.addWidget(self.hotkey_note, 1, 1, 1, 2)
        help_window.tag(self.hotkey_edit, "#hotkey")
        g.addWidget(QLabel("Disable and enable its EQ, to compare"), 2, 0)
        self.onoff_edit = key_box("Hotkey to disable the EQ and enable it again", self.onoff_hotkey_changed,
                                  "onoff_hotkey")
        g.addWidget(self.onoff_edit, 2, 1)
        help_window.tag(self.onoff_edit, "#onoff-hotkey")
        # (Same level's words wrap: a tick box's words stay on one line, and in one line they made the card about
        # 777 px wide, so the window's smallest width went from 788 to 805 px once Settings showed; 2026-11-10. The
        # tick box's words are a label of their own beside it that wraps, each line under the first, as Windows wraps
        # a tick box's words; a click on them ticks the box, as on its own words)
        same = QWidget()
        sl = QHBoxLayout(same)
        sl.setContentsMargins(0, 0, 0, 0)
        sl.setSpacing(1)  # (a tick box with no words keeps 8 px after its box: its words 9 px from it, as the others')
        self.chk_matched = QCheckBox()
        self.chk_matched.setAccessibleName(MATCHED_WORDS)
        self.chk_matched.toggled.connect(lambda on: self.sw.set("onoff_matched", bool(on)))
        help_window.tag(self.chk_matched, "#onoff-matched")
        sl.addWidget(self.chk_matched, 0, Qt.AlignTop)
        self.matched_words = _TickWords(MATCHED_WORDS, self.chk_matched)
        help_window.tag(self.matched_words, "#onoff-matched")
        sl.addWidget(self.matched_words, 1)
        g.addWidget(same, 3, 1, 1, 2)
        self.onoff_note = QLabel()
        self.onoff_note.setWordWrap(True)
        theme.mark(self.onoff_note, role="warn")
        g.addWidget(self.onoff_note, 4, 1, 1, 2)
        lay.addWidget(box)

        # (the condition first, with its symbol and colour, as the line about the EQ on Devices; the folder's path under
        # it in gray: the UI audit, 2026-11-08, the condition came second, after a long path)
        box = QGroupBox("Equalizer APO")
        bl = QVBoxLayout(box)
        state = placed(bl, QHBoxLayout())
        state.setSpacing(8)
        self.apo_mark = glyph_label("warning", role="warn")
        state.addWidget(self.apo_mark, 0, Qt.AlignTop)
        self.apo_state = QLabel()
        self.apo_state.setWordWrap(True)
        state.addWidget(self.apo_state, 1)
        self.apo_path = muted()
        self.apo_path.setTextInteractionFlags(Qt.TextSelectableByMouse)
        bl.addWidget(self.apo_path)
        row = placed(bl, QHBoxLayout())
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
        row.addStretch(1)  # (Remove AutoEQ Studio from APO… last and apart: UI-RULES 14)
        row.addWidget(self.btn_unset)
        lay.addWidget(box)

        box = QGroupBox("Your files")
        bl = QVBoxLayout(box)
        bl.addWidget(muted("Targets, measurements, saved EQs, and presets are stored in:"))
        self.files_label = QLabel()
        self.files_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.files_label.setWordWrap(True)
        bl.addWidget(self.files_label)
        row = placed(bl, QHBoxLayout())
        self.btn_files_open = QPushButton("Open the folder")
        icons.put(self.btn_files_open, "folder")
        self.btn_files_open.clicked.connect(self.open_files_folder)
        self.btn_files_change = QPushButton("Change…")
        icons.put(self.btn_files_change, "change_folder")
        # (no tooltip of its own: the text survey, 2026-11-24. Its tooltip is the Help line of Your files, as Open
        # the folder's, from help_window.tag below)
        self.btn_files_change.clicked.connect(self.change_files_folder)
        for b in (self.btn_files_open, self.btn_files_change):
            help_window.tag(b, "#files-folder")
            row.addWidget(b)
        row.addStretch(1)
        lay.addWidget(box)
        self.render_files_folder()

        box = QGroupBox("Backup")
        bl = QVBoxLayout(box)
        bl.addWidget(muted("Back up your devices, profiles, settings, History, and files to a single .zip"))
        row = placed(bl, QHBoxLayout())
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
        lay.addWidget(box)

        # the version, last, in a card of its own, as Windows 11's apps' About (it read as the hotkeys' last note)
        box = QGroupBox("About AutoEQ Studio")
        bl = QVBoxLayout(box)
        about = muted(f"Version {paths.VERSION}" + (" · installed" if paths.INSTALLED
                                                     else f" · portable ({paths.PROGRAM})"))
        about.setTextInteractionFlags(Qt.TextSelectableByMouse)
        about.setWordWrap(True)
        bl.addWidget(about)
        lay.addWidget(box)
        lay.addStretch(1)
        return w

    # ---------------------------------------------------------------- Your files (paths.py, userfiles.py)
    def render_files_folder(self):
        self.files_label.setText(paths.ROOT + ("   (default)" if os.path.normcase(paths.ROOT) ==
                                               os.path.normcase(paths.DEFAULT_FILES) else "   (custom)"))

    def open_files_folder(self):
        try:
            os.makedirs(paths.ROOT, exist_ok=True)
        except OSError as e:
            QMessageBox.warning(self, "Your files", f"Couldn't open {paths.ROOT}: {e}")
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
            QMessageBox.warning(self, "Backup", f"Couldn't save backup: {e}")
            return
        self.status(f"Saved {_count(info['files'], 'file')} ({_count(info['profiles'], 'profile')}) to {dest}", 10000)

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
                self, "Load a backup", f"Restore backup from {info['made']} ({_count(info['files'], 'file')}, "
                f"{_count(info['profiles'], 'profile')})?\n\nThis replaces your current settings, History, profiles, and "
                "matching files (other files are kept). Your current data is backed up first, then the app "
                "restarts.") != QMessageBox.Yes:
            return
        if self.eq_page:
            self.eq_page.stop_sound()
        try:
            got = backup.restore(src, self.sw.apo.profiles if self.sw.apo.found else None)
        except (ValueError, OSError) as e:
            QMessageBox.warning(self, "Load a backup", f"Couldn't restore backup: {e}")
            return
        # (nothing written over what was just restored before the restart: the devices' poll, Listen's and the
        # tracer's choices saved as the app quits)
        self.sw.read_only = True
        self.app.timer.stop()
        extra = ("\n\nProfile EQ files weren't restored because Equalizer APO isn't installed. Install Equalizer APO, "
                 "then restore the backup again." if got["skipped"] else "")
        QMessageBox.information(self, "Load a backup", f"Restored {_count(got['files'], 'file')}. Your previous data was backed "
                                f"up to {got['kept']}.{extra}\n\nAutoEQ Studio will now restart.")
        self.app.restart()

    def render_settings(self):
        for chk, on in ((self.chk_autostart, self.app.autostart_on()), (self.chk_notify, self.sw.s["notify"])):
            chk.blockSignals(True)
            chk.setChecked(on)
            chk.blockSignals(False)
        if not self.hotkey_edit.hasFocus():
            self._show_key(self.hotkey_edit, self.sw.s.get("hotkey") or "")
        self.hotkey_note.setText(self.app.hotkey_problem or "")
        self.hotkey_note.setVisible(bool(self.app.hotkey_problem))
        if not self.onoff_edit.hasFocus():
            self._show_key(self.onoff_edit, self.sw.s.get("onoff_hotkey") or "")
        self.chk_matched.blockSignals(True)
        self.chk_matched.setChecked(bool(self.sw.s.get("onoff_matched", True)))
        self.chk_matched.blockSignals(False)
        problem = getattr(self.app, "onoff_problem", "")
        self.onoff_note.setText(problem or "")
        self.onoff_note.setVisible(bool(problem))
        apo = self.sw.apo
        good = apo.found and apo.includes_studio()
        if not apo.found:
            state = "Equalizer APO isn't installed, or its config folder couldn't be found"
        else:
            state = "✓ Connected to Equalizer APO (linked in config.txt)" if good else "Not connected to Equalizer APO"
        self.apo_state.setText(state)
        role = "good" if good else "warn"
        if self.apo_state.property("role") != role:
            theme.mark(self.apo_state, role=role)
        self.apo_mark.setVisible(not good)
        self.apo_path.setText(f"Config folder: {apo.config}" if apo.found else "")
        self.apo_path.setVisible(apo.found)
        setup_on, unset_on = apo.found and not apo.includes_studio(), good  # (never both)
        # (the button that comes shows first, and takes the focus of the one that goes: hidden with the focus, Remove
        # AutoEQ Studio from APO… gave it to the next control in the window's order, Your files' Open the folder, and
        # the screen scrolled to it, 2026-11-13)
        focus = self.window().focusWidget()
        for came, came_on, gone in ((self.btn_setup, setup_on, self.btn_unset),
                                    (self.btn_unset, unset_on, self.btn_setup)):
            if came_on:
                came.setVisible(True)
                if focus is gone:
                    came.setFocus(Qt.OtherFocusReason)
                    # (and in sight once laid out: the banner over the screens shows or goes with this change, and
                    # the screen's room changes, 46 px or more)
                    area = self.pages.get("settings")
                    if area is not None:
                        QTimer.singleShot(0, area, lambda a=area, b=came: a.ensureWidgetVisible(b, 0, 0))
        self.btn_setup.setVisible(setup_on)
        self.btn_unset.setVisible(unset_on)
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
        # (Add AutoEQ Studio to APO… puts it back)
        if QMessageBox.question(
                self, "Remove AutoEQ Studio from APO",
                "Remove AutoEQ Studio from Equalizer APO?\n\nThis removes its line from config.txt and re-enables any "
                "lines it disabled. Your profiles are kept.") == QMessageBox.Yes:
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
                    QMessageBox.warning(self, "APO's Configurator", f"Couldn't open APO Configurator: {e}")

    def open_folder(self, folder):
        if folder and os.path.isdir(folder):
            os.startfile(folder)
        elif folder:
            QMessageBox.information(self, "Open the folder", f"Folder not found: {folder}")
