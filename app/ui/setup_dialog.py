"""Set up Equalizer APO for AutoEQ Studio (Set up… in Settings and in the window's banner: ui\\settings_screen.py,
ui\\window.py): the one line it adds to APO's config.txt (the lines on now can be turned off), EQ Switcher's Start
with Windows turned off and EQ Switcher asked to quit (AutoEQ Studio takes over from it), and the EQ files config.txt
uses offered as profiles (the one on now becomes the playing device's)."""
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QDialog, QDialogButtonBox, QLabel, QListWidget, QListWidgetItem, QMessageBox,
                               QVBoxLayout)

from switcher import eqfile
from switcher.core import shown
from ui.window_parts import muted


class SetUpDialog(QDialog):
    """Setting APO up for AutoEQ Studio: what changes in config.txt (its lines on now, turned off), and the EQ files it
    uses offered as profiles (the one on now becomes the playing device's)."""

    def __init__(self, sw, parent):
        super().__init__(parent)
        self.sw = sw
        self.setWindowTitle("Set up Equalizer APO")
        lay = QVBoxLayout(self)
        text = sw.apo.read_config()
        self.others = sw.apo.others_on(text)
        lay.addWidget(QLabel("AutoEQ Studio adds one line to APO's config.txt, which brings in the EQ chosen for each "
                             "device. A copy of config.txt is kept first (config.txt.autoeq-studio-backup)."))
        self.chk_off = None
        if self.others:
            lay.addWidget(QLabel("These lines in config.txt are on now. They apply to every device, on top of each "
                                 "device's EQ:"))
            lst = QListWidget()
            lst.addItems(self.others)
            lst.setMaximumHeight(110)
            lay.addWidget(lst)
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
            lay.addWidget(QLabel("EQ files config.txt uses (on or off). Add them as profiles?"))
            self.file_list = QListWidget()
            for f in self.files:
                it = QListWidgetItem(os.path.basename(f))
                it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
                it.setCheckState(Qt.Checked)
                self.file_list.addItem(it)
            self.file_list.setMaximumHeight(130)
            lay.addWidget(self.file_list)
            key, _ = sw.playing()
            if key:
                lay.addWidget(muted(f"The one on now becomes the EQ of {shown(sw.record(key))}, the device "
                                    "playing now."))
        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Ok).setText("Set up")
        btns.accepted.connect(self._go)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

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
