"""Set up Equalizer APO for AutoEQ Studio (Set up… in Settings and in the window's banner: ui\\settings_screen.py,
ui\\window.py): the one line it adds to APO's config.txt (the lines on now can be turned off), EQ Switcher's Start
with Windows turned off and EQ Switcher asked to quit (AutoEQ Studio takes over from it), and the EQ files config.txt
uses offered as profiles (the one on now becomes the playing device's)."""
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QDialog, QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
                               QMessageBox, QPushButton, QVBoxLayout, QWidget)

from switcher import eqfile
from switcher.core import shown
from ui import theme
from ui.window_parts import muted


def _words(text):
    """A line of the dialog's words, wrapping (one long line made the dialog a thousand pixels wide)."""
    lab = QLabel(text)
    lab.setWordWrap(True)
    return lab


def _fit(lst, most):
    """A list as tall as its rows, up to `most` of them (more: it scrolls). Its height is fixed: Windows opens a
    dialog no taller than two thirds of the screen, and a list that could shrink was squeezed to a row and a half."""
    lst.ensurePolished()  # (the theme's row height, with its text size: the list is in the dialog by now)
    rows = sum(lst.sizeHintForRow(i) for i in range(min(lst.count(), most)))
    lst.setFixedHeight(rows + 2 * lst.frameWidth() + 6)


class SetUpDialog(QDialog):
    """Setting APO up for AutoEQ Studio: what changes in config.txt (its lines on now, turned off), and the EQ files it
    uses offered as profiles (the one on now becomes the playing device's)."""

    def __init__(self, sw, parent):
        super().__init__(parent)
        self.sw = sw
        self.setWindowTitle("Set up Equalizer APO")
        self.setObjectName("setUp")  # (Windows 11's dialog: the words on the card colour, the buttons on a band below)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        body = QWidget()
        # (the words wrap at this width at least; set on the dialog itself, it would switch off its layout's own
        # minimum, and the longest tick box's words were cut)
        body.setMinimumWidth(520)
        lay = QVBoxLayout(body)
        lay.setContentsMargins(24, 18, 24, 18)
        lay.setSpacing(8)
        outer.addWidget(body, 1)
        text = sw.apo.read_config()
        self.others = sw.apo.others_on(text)
        lay.addWidget(_words("AutoEQ Studio adds one line to APO's config.txt, which brings in the EQ chosen for each "
                             "device. A copy of config.txt is kept first (config.txt.autoeq-studio-backup)."))
        self.chk_off = None
        if self.others:
            lay.addWidget(_words("These lines in config.txt are on now. They apply to every device, on top of each "
                                 "device's EQ:"))
            lst = QListWidget()
            lst.setAccessibleName("Lines on in config.txt")  # (what a screen reader says for it)
            lst.addItems(self.others)
            lay.addWidget(lst)
            _fit(lst, 3)
            self.chk_off = QCheckBox("Turn them off (they stay in config.txt with # in front; taking AutoEQ Studio out "
                                     "turns them on again)")
            self.chk_off.setChecked(True)
            lay.addWidget(self.chk_off)
            if any("EQ Switcher" in line for line in self.others):
                lay.addWidget(muted("“Include: EQ Switcher\\switcher.txt” is EQ Switcher's: AutoEQ Studio takes over "
                                    "from it" + (" (your EQ Switcher profiles and choices are already here)"
                                                 if sw.profiles() else
                                                 " (its profiles weren't brought over: their EQ files are in Equalizer "
                                                 "APO's “EQ Switcher\\profiles” folder, for Import in Profiles)")
                                    + "."))
        # EQ Switcher, which AutoEQ Studio takes over from: its Start with Windows off, and it asked to quit
        from ui import winsys
        self.chk_es_auto = self.chk_es_quit = None
        if winsys.eq_switcher_autostart():
            self.chk_es_auto = QCheckBox("Turn off EQ Switcher's Start with Windows (AutoEQ Studio does its job now)")
            self.chk_es_auto.setChecked(True)
            lay.addWidget(self.chk_es_auto)
        if winsys.eq_switcher_running():
            self.chk_es_quit = QCheckBox("Quit EQ Switcher (it's running now; two apps switching EQs would fight)")
            self.chk_es_quit.setChecked(True)
            lay.addWidget(self.chk_es_quit)
        self.files = [f for f in sw.apo.referenced_files() if not sw.has_profile_like(f)]
        self.file_list = None
        if self.files:
            lay.addWidget(_words("EQ files config.txt uses (on or off). Add them as profiles?"))
            self.file_list = QListWidget()
            self.file_list.setAccessibleName("EQ files to add as profiles")
            for f in self.files:
                it = QListWidgetItem(os.path.basename(f))
                it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
                it.setCheckState(Qt.Checked)
                self.file_list.addItem(it)
            lay.addWidget(self.file_list)
            _fit(self.file_list, 4)
            key, _ = sw.playing()
            if key:
                lay.addWidget(muted(f"The one on now becomes the EQ of {shown(sw.record(key))}, the device "
                                    "playing now."))
        # the buttons, as Windows 11's dialogs have them: on a band in the window's colour, the main one (Set up,
        # Enter's) in the accent, sharing the width
        footer = QFrame()
        footer.setObjectName("dialogFooter")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(24, 16, 24, 16)
        fl.setSpacing(8)
        self.go_btn = QPushButton("Set up")
        theme.mark(self.go_btn, primary=True)
        self.go_btn.setDefault(True)
        self.go_btn.clicked.connect(self._go)
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        fl.addWidget(self.go_btn, 1)
        fl.addWidget(cancel, 1)
        outer.addWidget(footer)
        # its size, fixed as Windows 11's dialogs are: as wide as its widest tick box's words (a tick box gives way
        # when there's less room: its words were cut), and as tall as its wrapping words need at that width (Windows
        # opens a dialog no bigger than two thirds of the screen: squeezed, its words overlapped the lists)
        self.ensurePolished()  # (the theme's text size, paddings and rows)
        width = self.sizeHint().width()
        height = outer.totalHeightForWidth(width) if outer.hasHeightForWidth() else self.sizeHint().height()
        self.setFixedSize(width, max(height, self.sizeHint().height()))

    def _go(self):
        import re
        on_now = {os.path.normcase(os.path.join(self.sw.apo.config, m.group(1).strip().strip('"')))
                  for line in self.others for m in [re.match(r"^\s*Include\s*:\s*(.+?)\s*$", line, re.I)] if m}
        added_on = []
        problems = []
        for i, f in enumerate(self.files):
            if self.file_list and self.file_list.item(i).checkState() == Qt.Checked:
                try:
                    pid = self.sw.import_profile(f)
                except (eqfile.NotAnEqFile, OSError) as e:
                    problems.append(f"{os.path.basename(f)}: {e}")
                    continue
                if os.path.normcase(f) in on_now:
                    added_on.append(pid)
        try:
            self.sw.set_up_apo(turn_off=self.chk_off is None or self.chk_off.isChecked())
        except OSError as e:
            QMessageBox.warning(self, "Couldn't set up", f"Couldn't change config.txt: {e}")
            return
        key, rec = self.sw.playing()
        if key and added_on and not rec["profiles"]:
            for j, pid in enumerate(added_on):
                self.sw.add_to_device(key, pid, switch_on=j == 0)
        from ui import winsys
        if self.chk_es_auto is not None and self.chk_es_auto.isChecked():
            try:
                winsys.eq_switcher_autostart_off()
            except OSError as e:
                problems.append(f"Couldn't turn off EQ Switcher's Start with Windows: {e}")
        if self.chk_es_quit is not None and self.chk_es_quit.isChecked() and not winsys.eq_switcher_quit():
            problems.append("EQ Switcher is still running (this version can't be asked to quit): quit it from its "
                            "tray icon's menu.")
        if problems:
            QMessageBox.warning(self, "Not done", "\n\n".join(problems))
        self.accept()
