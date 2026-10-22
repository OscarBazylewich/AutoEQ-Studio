"""AutoEQ Studio's window: a top bar (the app's name, its screens, Online / Offline) over one screen at a time.
- Make an EQ (ui\\eq_page.py, loaded the first time it's opened, so the tray stays light): AutoEQ Local's part.
- Devices: your playback devices (the one playing first), and for the one chosen: its profiles, the one on (or Off),
  adding and taking off profiles, whether Equalizer APO is installed on it, your name for it (Rename…), and a line
  saying whether its EQ really plays (Equalizer APO asked by itself, switcher\\check.py; again when something changes).
A bar over every screen while an EQ is being tried on a device (Use on device › Try for 5 minutes): time left, Keep
it, Stop now.
- Profiles: every profile (a copy of an EQ file): import, rename, remove, where each is used.
- Settings: starting with Windows, notices, the hotkey, online or offline, Equalizer APO (setting it up for
  AutoEQ Studio, or taking AutoEQ Studio out of it), and Backup (everything of yours in one .zip, and back: backup.py).
Online / Offline (top right, and in Settings): offline, the app never connects to the internet (net.py).
Help (top right; F1 anywhere: at the entry of the setting under the pointer or being typed in): ui\\help_window.py.
Guide (top right): a tour of Make an EQ (ui\\guide.py, shown by ui\\tour.py); the tracer has its own.
A banner over the device screens says when APO isn't installed or isn't using AutoEQ Studio yet. Messages show in
the line at the bottom. Closing the window leaves the app in the tray; Quit is in the tray icon's menu.
Everything is drawn in the app's theme (ui\\theme.py: AutoEQ Local's colours, light or dark as Windows is).
"""
import os
import re
import subprocess
import time

from PySide6.QtCore import Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QCursor, QDesktopServices, QKeySequence, QShortcut
from PySide6.QtWidgets import (QAbstractItemView, QButtonGroup, QCheckBox, QDialog, QDialogButtonBox, QFileDialog,
                               QFrame, QGroupBox, QHBoxLayout, QHeaderView, QInputDialog, QKeySequenceEdit, QLabel,
                               QListWidget, QListWidgetItem, QMainWindow, QMenu, QMessageBox, QPushButton,
                               QRadioButton, QSplitter, QStackedWidget, QTableWidget, QTableWidgetItem, QToolButton,
                               QVBoxLayout, QWidget)

import net
import paths
from switcher import eqfile
from switcher.core import shown
from ui import icons, theme

PAGES = [("eq", "Make an EQ"), ("devices", "Devices"), ("profiles", "Profiles"), ("settings", "Settings")]


def _muted(text=""):
    lab = QLabel(text)
    lab.setWordWrap(True)
    theme.mark(lab, role="muted")
    return lab


def _profile_line(p):
    if not p:
        return ""
    n = p.get("filters", 0)
    what = "GraphicEQ" if p.get("graphic") and not n else f"{n} filter{'' if n == 1 else 's'}"
    return f"{what}, pre-amp {p.get('preamp', 0):g} dB"


def check_line(ok, text):
    """The device's one-line answer from Equalizer APO's check (switcher\\check.explain's words; all of it in the
    tooltip): the first sentence up to its ": " and without a closing "(…)" remark. A profile's name in “ ” is kept
    whole, brackets and all ("Truthear GATe (Diffuse field)" was cut to “Truthear GATe, 2026-10-21)."""
    if ok is None:  # (couldn't ask: "Couldn't ask Equalizer APO: why")
        return text.split(": ")[0]
    names = re.findall(r"“[^”]*”", text)
    masked = re.sub(r"“[^”]*”", "\x00", text)
    first = masked.split(". ")[0].split(": ")[0]
    first = re.sub(r"\s*\([^()]*\)\.?$", "", first).rstrip(".") + "."
    for n in names:
        first = first.replace("\x00", n, 1)
    return first


class Window(QMainWindow):
    hotkey_changed = Signal(str)   # (the app registers it, and says when Windows refused it)

    def __init__(self, sw, app):
        super().__init__()
        self.sw, self.app = sw, app
        self.setWindowTitle("AutoEQ Studio")
        self.setWindowIcon(icons.app_icon())
        self.resize(1040, 760)
        self.selected = sw.playing_key or (sw.devices[0].key if sw.devices else None)
        self.eq_page = None

        central = QWidget()
        lay = QVBoxLayout(central)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self._top_bar())
        self.banner = QFrame()
        theme.mark(self.banner, card="warn")
        bl = QHBoxLayout(self.banner)
        self.banner_text = QLabel()
        self.banner_text.setWordWrap(True)
        self.banner_btn = QPushButton()
        theme.mark(self.banner_btn, primary=True)
        self.banner_btn.clicked.connect(self._banner_action)
        bl.addWidget(self.banner_text, 1)
        bl.addWidget(self.banner_btn)
        holder = QWidget()
        hl = QVBoxLayout(holder)
        hl.setContentsMargins(14, 10, 14, 0)
        hl.addWidget(self.banner)
        self.banner_holder = holder
        lay.addWidget(holder)
        # an EQ being tried on a device: how long is left, Keep it, Stop now
        self.trial_bar = QFrame()
        theme.mark(self.trial_bar, card=True)
        tl = QHBoxLayout(self.trial_bar)
        self.trial_text = QLabel()
        self.trial_text.setWordWrap(True)
        keep = QPushButton("Keep it")
        theme.mark(keep, primary=True)
        keep.setToolTip("Make it a profile of the device, switched on")
        keep.clicked.connect(lambda: self.app.end_trial(True))
        stop = QPushButton("Stop now")
        stop.setToolTip("The device's own EQ back now")
        stop.clicked.connect(lambda: self.app.end_trial(False))
        tl.addWidget(self.trial_text, 1)
        tl.addWidget(keep)
        tl.addWidget(stop)
        holder = QWidget()
        hl = QVBoxLayout(holder)
        hl.setContentsMargins(14, 10, 14, 0)
        hl.addWidget(self.trial_bar)
        self.trial_holder = holder
        holder.hide()
        lay.addWidget(holder)
        self._trial_timer = QTimer(self, interval=1000, timeout=self.render_trial)
        self._trial_timer.start()
        self._checks, self._checking, self._check_after, self.check_label = {}, set(), {}, None

        self.stack = QStackedWidget()
        self.pages = {"eq": QWidget(), "devices": self._padded(self._devices_tab()),
                      "profiles": self._padded(self._profiles_tab()), "settings": self._padded(self._settings_tab())}
        for key, _ in PAGES:
            self.stack.addWidget(self.pages[key])
        lay.addWidget(self.stack, 1)
        self.setCentralWidget(central)

        sw.listeners.append(self._changed)
        # F1 in any of the app's windows: Help, at the setting under the pointer (or the one being typed in)
        QShortcut(QKeySequence(Qt.Key_F1), self, self.help_here, context=Qt.ApplicationShortcut)
        net.on_change(lambda _off: self.render_online())
        self.render_all()
        self.show_page(sw.s.get("page") if sw.s.get("page") in self.pages else "eq", remember=False)

    # ---------------------------------------------------------------- the top bar and the screens
    def _top_bar(self):
        bar = QFrame()
        theme.mark(bar, topbar=True)
        h = QHBoxLayout(bar)
        h.setContentsMargins(14, 8, 14, 8)
        brand = QLabel("AutoEQ Studio")
        theme.mark(brand, role="brand")
        h.addWidget(brand)
        h.addSpacing(18)
        self.nav = {}
        group = QButtonGroup(bar)
        for key, name in PAGES:
            b = QPushButton(name)
            b.setCheckable(True)
            theme.mark(b, nav=True)
            b.clicked.connect(lambda _=False, k=key: self.show_page(k))
            group.addButton(b)
            h.addWidget(b)
            self.nav[key] = b
        h.addStretch(1)
        self.presets_btn = QPushButton("Presets ▾")  # (Make an EQ's settings: shown on that screen)
        theme.mark(self.presets_btn, nav=True)
        self.presets_btn.setToolTip("Save all of Make an EQ's settings under a name, and load them again")
        from ui import help_window
        help_window.tag(self.presets_btn, "#presets")
        self.presets_menu = QMenu(self.presets_btn)
        self.presets_btn.clicked.connect(self.open_presets)
        h.addWidget(self.presets_btn)
        guide = QPushButton("Guide")
        theme.mark(guide, nav=True)
        guide.setToolTip("A tour of Make an EQ: each part and what it does")
        guide.clicked.connect(self.start_guide)
        h.addWidget(guide)
        helpb = QPushButton("? Help")
        theme.mark(helpb, nav=True)
        helpb.setToolTip("Terms, questions and every setting in full (F1: the one under the pointer)")
        helpb.clicked.connect(lambda: self.open_help())
        h.addWidget(helpb)
        self.online_btn = QPushButton()
        self.online_btn.setCheckable(True)
        theme.mark(self.online_btn, online=True)
        self.online_btn.clicked.connect(lambda on: self.app.set_offline(not on))
        h.addWidget(self.online_btn)
        return bar

    @staticmethod
    def _padded(widget):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(14, 12, 14, 14)
        lay.addWidget(widget)
        return w

    def show_page(self, key, remember=True):
        """Show one screen (the EQ screen is made the first time it's seen: that's when the EQ part loads; not while
        the app starts hidden in the tray, which stays light)."""
        if key == "eq" and self.eq_page is None and not self.isVisible():
            self._eq_pending = True
            self.stack.setCurrentWidget(self.pages["eq"])
            self.nav[key].setChecked(True)
            self.presets_btn.show()
            self.render_banner()
            if remember and self.sw.s.get("page") != key:
                self.sw.set("page", key)
            return
        if key == "eq" and self.eq_page is None:
            from ui.eq_page import EqPage
            self.eq_page = EqPage(self.sw, self.status)
            idx = self.stack.indexOf(self.pages["eq"])
            self.stack.removeWidget(self.pages["eq"])
            self.pages["eq"] = self.eq_page
            self.stack.insertWidget(idx, self.eq_page)
        self.stack.setCurrentWidget(self.pages[key])
        self.nav[key].setChecked(True)
        self.presets_btn.setVisible(key == "eq")
        self.render_banner()
        if key == "settings":  # (your files' folder: it may have been chosen since, e.g. when Make an EQ opened)
            self.show_files_folder()
        if key == "eq" and self.isVisible():
            self.eq_page.start()
        if remember and self.sw.s.get("page") != key:
            self.sw.set("page", key)

    def open_presets(self):
        """Presets ▾ (AutoEQ Local's): the menu under the button, made afresh from the presets there are now."""
        page = self.eq_page
        if page is None or getattr(page, "settings", None) is None:
            self.status("Presets are ready as soon as Make an EQ has opened.", 4000)
            return
        page.fill_presets(self.presets_menu)
        self.presets_menu.popup(self.presets_btn.mapToGlobal(self.presets_btn.rect().bottomLeft()))

    @staticmethod
    def open_help(entry=None):
        from ui import help_window
        return help_window.open_at(entry)

    def start_guide(self):
        """Make an EQ's Guide (once its screen has opened: the EQ part loads the first time). One at a time: clicks
        while it waits, or while a tour is on, start nothing more."""
        if getattr(self, "_guide_waiting", False):
            return
        tour = getattr(self, "tour", None)
        try:
            if tour is not None and tour.isVisible():
                return
        except RuntimeError:  # (that tour has ended and gone)
            pass
        self.show_page("eq")
        self._guide_when_ready()

    def _guide_when_ready(self):
        from PySide6.QtCore import QTimer
        page = self.eq_page
        if getattr(page, "settings", None) is None:  # (still opening: started when it's there)
            self._guide_waiting = not page.loading.text().startswith("The EQ part couldn't")
            if self._guide_waiting:
                self.status("The Guide starts as soon as Make an EQ has opened…", 4000)
                QTimer.singleShot(300, self._guide_when_ready)
            return
        self._guide_waiting = False
        from ui import guide
        self.tour = guide.start_eq(page)

    def help_here(self):
        from PySide6.QtWidgets import QApplication
        from ui import help_window
        entry = help_window.entry_of_widget(QApplication.widgetAt(QCursor.pos())) or \
            help_window.entry_of_widget(QApplication.focusWidget())
        self.open_help(entry)

    def page(self):
        return next(k for k, w in self.pages.items() if w is self.stack.currentWidget())

    def status(self, text, ms=6000):
        self.statusBar().showMessage(text, ms)

    def showEvent(self, e):
        self.render_all()  # (devices plugged in, EQs switched from the tray while it was hidden)
        super().showEvent(e)
        if getattr(self, "_eq_pending", False) and self.eq_page is None:
            self._eq_pending = False
            self.show_page("eq", remember=False)
        if self.page() == "eq" and self.eq_page:
            self.eq_page.start()

    def render_online(self):
        off = net.offline()
        self.online_btn.setChecked(not off)
        self.online_btn.setText("● Online" if not off else "○ Offline")
        self.online_btn.setToolTip("Online: the app may use the internet (the online databases). Click for offline: "
                                   "nothing goes to the internet." if not off else
                                   "Offline: the app never connects to the internet, it uses only what's on this PC. "
                                   "Click to go online.")
        if hasattr(self, "chk_offline"):
            self.chk_offline.blockSignals(True)
            self.chk_offline.setChecked(off)
            self.chk_offline.blockSignals(False)
        self.render_banner()

    # ---------------------------------------------------------------- closing: the app stays in the tray
    def closeEvent(self, e):
        e.ignore()
        if self.eq_page:  # (Listen stops with the window)
            self.eq_page.stop_sound()
        self.hide()
        if not self.sw.s.get("told_tray"):
            self.app.tray_message("AutoEQ Studio is still running", "It keeps your devices' EQs in the tray: right-click "
                                  "its icon to switch an EQ or quit.")
            self.sw.set("told_tray", True)

    def show_front(self):
        self.show()
        self.setWindowState(self.windowState() & ~Qt.WindowMinimized)
        self.raise_()
        self.activateWindow()

    def _changed(self, what, info):
        if self.isVisible() or what in ("apo", "profiles"):
            self.render_all()
        if self.eq_page and what in ("active", "devices", "apo", "profiles"):  # (Listen's "own EQ on top" note)
            self.eq_page.listen.render_apo()

    def render_trial(self):
        t = self.sw.trial
        if not t:
            if not self.trial_holder.isHidden():
                self.trial_holder.hide()
            return
        left = max(0, int(t["until"] - time.time()))
        self.trial_text.setText(f"Trying “{t['name']}” on {shown(self.sw.record(t['key']))}, in every app: "
                                f"{left // 60}:{left % 60:02d} left, then its own EQ comes back.")
        self.trial_holder.show()

    def render_all(self):
        self.render_trial()
        self.render_online()
        self.render_banner()
        self.render_devices()
        self.render_profiles()
        self.render_settings()

    # ---------------------------------------------------------------- the banner
    def render_banner(self):
        apo = self.sw.apo
        if hasattr(self, "stack") and self.page() == "eq":  # (APO's set-up matters on the device screens)
            self.banner_holder.hide()
            return
        self.banner_holder.show()
        self.banner_btn.setEnabled(True)
        self.banner_btn.setToolTip("")  # (the offline note, set below, doesn't stay once online)
        if not apo.found:
            text, btn, self._banner_do = ("Equalizer APO isn't installed. AutoEQ Studio works through it: install it, "
                                          "choose your devices in its Configurator, then restart Windows."), \
                "Get Equalizer APO", "download"
        elif not apo.writable():
            text, btn, self._banner_do = ("AutoEQ Studio can't write in Equalizer APO's config folder "
                                          f"({apo.config}). Allow your Windows user to change it, then open "
                                          "AutoEQ Studio again."), "Open the folder", "folder"
        elif not apo.set_up():
            text, btn, self._banner_do = ("Equalizer APO isn't using AutoEQ Studio yet: one line in its config.txt "
                                          "brings in the EQ chosen for each device."), "Set up…", "setup"
        else:
            self.banner_holder.hide()
            return
        self.banner_text.setText(text)
        self.banner_btn.setText(btn)
        if self._banner_do == "download" and net.offline():  # (a website: not while offline)
            self.banner_btn.setEnabled(False)
            self.banner_btn.setToolTip("Offline: go online to open Equalizer APO's website.")
        self.banner_holder.show()
        self.banner.show()

    def _banner_action(self):
        if self._banner_do == "download":
            QDesktopServices.openUrl(QUrl(paths.APO_DOWNLOAD))
        elif self._banner_do == "folder":
            self.open_folder(self.sw.apo.config)
        else:
            self.set_up_dialog()

    # ---------------------------------------------------------------- Devices
    def _devices_tab(self):
        split = QSplitter()
        self.dev_list = QListWidget()
        self.dev_list.setAccessibleName("Devices")
        self.dev_list.setMinimumWidth(240)
        self.dev_list.setTextElideMode(Qt.ElideRight)  # (a long name ends in "…": its tooltip has it whole)
        self.dev_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.dev_list.currentItemChanged.connect(self._pick_device)
        split.addWidget(self.dev_list)
        self.dev_panel = QWidget()
        self.dev_lay = QVBoxLayout(self.dev_panel)
        split.addWidget(self.dev_panel)
        split.setStretchFactor(1, 1)
        split.setSizes([280, 540])
        return split

    def _status(self, key):
        d, rec = self.sw.device(key), self.sw.record(key)
        where = "Playing now" if key == self.sw.playing_key else "Connected" if d and d.connected else "Not connected"
        if self.sw.trial and self.sw.trial["key"] == key:
            return where, f"Trying: {self.sw.trial['name']}"
        name = self.sw.profile_name(rec["active"]) if rec else None
        return where, f"EQ: {name}" if name else "EQ off"

    def render_devices(self):
        self.dev_list.blockSignals(True)
        self.dev_list.clear()
        keys = [d.key for d in self.sw.devices]
        keys += [k for k in self.sw.s["devices"] if k not in keys and self.sw.record(k)["profiles"]]  # (gone, but set)
        for key in keys:
            rec, d = self.sw.record(key), self.sw.device(key)
            where, eq = self._status(key)
            item = QListWidgetItem(f"{shown(rec)}\n{where} · {eq}")
            item.setIcon(icons.dot("playing" if key == self.sw.playing_key else
                                   "connected" if d and d.connected else "away"))
            item.setData(Qt.UserRole, key)
            item.setToolTip(f"{shown(rec)}\n{where} · {eq}" + (f"\nWindows calls it {rec['label']}"
                                                                     if rec.get("nickname") else ""))
            self.dev_list.addItem(item)
            if key == self.selected:
                self.dev_list.setCurrentItem(item)
        if self.dev_list.currentItem() is None and self.dev_list.count():
            self.dev_list.setCurrentRow(0)
            self.selected = self.dev_list.currentItem().data(Qt.UserRole)
        self.dev_list.blockSignals(False)
        self.render_device_panel()

    def _pick_device(self, item, _old=None):
        if item:
            self.selected = item.data(Qt.UserRole)
            self.render_device_panel()

    def render_device_panel(self):
        while self.dev_lay.count():  # (the old panel's parts go at once: deleteLater alone waits for the event loop)
            w = self.dev_lay.takeAt(0).widget()
            if w:
                w.hide()
                w.setParent(None)
                w.deleteLater()
        key, lay = self.selected, self.dev_lay
        rec = self.sw.record(key) if key else None
        if not rec:
            lay.addWidget(_muted("No playback devices found."))
            lay.addStretch(1)
            return
        d = self.sw.device(key)
        head = QWidget()
        hl = QHBoxLayout(head)
        hl.setContentsMargins(0, 0, 0, 0)
        title = QLabel(shown(rec))
        theme.mark(title, role="title")
        title.setWordWrap(True)
        hl.addWidget(title, 1)
        ren = QPushButton("Rename…")
        ren.setToolTip("Your own name for this device (e.g. the IEM you use on it)")
        ren.clicked.connect(lambda: self.rename_device(key))
        from ui import help_window
        help_window.tag(ren, "#dev-rename")
        hl.addWidget(ren, 0, Qt.AlignTop)
        lay.addWidget(head)
        where, _ = self._status(key)
        lay.addWidget(_muted(where + ("" if d else " (Windows doesn't list it any more)")
                             + (f" · Windows calls it {rec['label']}" if rec.get("nickname") else "")))

        if d and not d.apo:
            warn = QFrame()
            theme.mark(warn, card="warn")
            wl = QVBoxLayout(warn)
            wl.addWidget(QLabel("Equalizer APO isn't installed on this device, so no EQ plays on it. In APO's "
                                "Configurator, tick this device, then restart Windows."))
            if self.sw.apo.configurator:
                b = QPushButton("Open APO's Configurator")
                b.clicked.connect(self.open_configurator)
                wl.addWidget(b, 0, Qt.AlignLeft)
            lay.addWidget(warn)

        box = QGroupBox("EQ for this device")
        bl = QVBoxLayout(box)
        group = QButtonGroup(box)
        off = QRadioButton("Off")
        off.setChecked(rec["active"] is None)
        off.toggled.connect(lambda on: on and self.sw.set_active(key, None))
        group.addButton(off)
        bl.addWidget(off)
        for pid in rec["profiles"]:
            p = self.sw.profiles().get(pid)
            row = QHBoxLayout()
            rb = QRadioButton(p["name"])
            rb.setChecked(rec["active"] == pid)
            rb.toggled.connect(lambda on, pid=pid: on and self.sw.set_active(key, pid))
            group.addButton(rb)
            row.addWidget(rb)
            note = _muted(_profile_line(p) + ("  (its file is missing from APO's folder)" if
                                               self.sw.profile_missing(pid) else ""))
            row.addWidget(note, 1)
            x = QToolButton()
            x.setText("✕")
            x.setToolTip("Take it off this device (it stays in Profiles)")
            x.setAccessibleName(f"Take {p['name']} off this device")
            x.clicked.connect(lambda _=False, pid=pid: self.sw.remove_from_device(key, pid))
            row.addWidget(x)
            holder = QWidget()
            holder.setLayout(row)
            row.setContentsMargins(0, 0, 0, 0)
            bl.addWidget(holder)
        add = QPushButton("Add a profile")
        menu = QMenu(add)
        others = [(pid, p) for pid, p in self.sw.profiles().items() if pid not in rec["profiles"]]
        for pid, p in sorted(others, key=lambda x: x[1]["name"].lower()):
            menu.addAction(p["name"], lambda pid=pid: self.sw.add_to_device(key, pid))
        if others:
            menu.addSeparator()
        menu.addAction("Import an EQ file…", lambda: self.import_files(for_device=key))
        add.setMenu(menu)
        bl.addWidget(add, 0, Qt.AlignLeft)
        lay.addWidget(box)
        self.check_label = None
        if self.sw.apo.found and d:
            row = QHBoxLayout()
            self.check_label = QLabel()
            self.check_label.setWordWrap(True)
            help_window.tag(self.check_label, "#dev-check")
            row.addWidget(self.check_label, 1)
            chk = QPushButton("Check again")
            chk.setToolTip("Ask Equalizer APO again (its Benchmark tool, read only), and see all it found")
            chk.clicked.connect(lambda: self.check_device(key))
            help_window.tag(chk, "#dev-check")
            row.addWidget(chk, 0, Qt.AlignTop)
            holder = QWidget()
            holder.setLayout(row)
            row.setContentsMargins(0, 0, 0, 0)
            lay.addWidget(holder)
            self._auto_check(key)
        hk = self.sw.s.get("hotkey")
        lay.addWidget(_muted("Switch between them from the tray icon" + (f", or with {hk} while this device is playing."
                                                                          if hk else ".")))
        lay.addStretch(1)

    def rename_device(self, key):
        rec = self.sw.record(key)
        name, ok = QInputDialog.getText(self, "Rename the device", f"Your name for it (empty: Windows' name, "
                                        f"{rec['label']}):", text=rec.get("nickname", ""))
        if ok:
            self.sw.set_nickname(key, name)
            self.render_all()

    def _check_job(self, key):
        """What asking APO about a device needs: (the work, a function giving (ok, text) from its answer), or None
        when Windows doesn't list the device now."""
        from switcher import check
        from switcher import devices as D
        d, rec = self.sw.device(key), self.sw.record(key)
        if not d or not d.guids:
            return None
        main = [e for e in d.endpoints if not e.conn.endswith(D.HANDS_FREE)] or d.endpoints
        guid = next((e.guid for e in main if e.state == D.ACTIVE), main[0].guid)
        t = self.sw.trial if self.sw.trial and self.sw.trial["key"] == key else None
        p = self.sw.profiles().get(rec["active"]) if rec["active"] else None
        name = t["name"] if t else p and p["name"]
        pfile = self.sw.trial_path() if t else os.path.join(self.sw.apo.profiles, p["file"]) if p else None
        apo, on_device = self.sw.apo, d.apo

        def work():  # (an answer APO's tool couldn't give is said, not logged as a crash)
            try:
                return check.run(apo, guid)
            except (OSError, subprocess.SubprocessError) as e:
                return {"error": str(e) or type(e).__name__}

        def explain(found):
            if found.get("error"):
                return None, f"Couldn't ask Equalizer APO: {found['error']}"
            return check.explain(apo, found, name, pfile, on_device)
        return work, explain

    def _check_sig(self, key):
        """What the answer depends on: when any of it changes, APO is asked again."""
        rec, d = self.sw.record(key), self.sw.device(key)
        files = (self.sw.apo.config_txt, os.path.join(self.sw.apo.own, "switcher.txt"))
        return (rec["active"], bool(self.sw.trial and self.sw.trial["key"] == key), d and d.apo,
                d and d.connected, tuple(os.path.getmtime(f) if os.path.exists(f) else 0 for f in files))

    def _show_check(self, key):
        lab, got = self.check_label, self._checks.get(key)
        if lab is None or key != self.selected:
            return
        try:
            if key in self._checking and not got:
                lab.setText("Asking Equalizer APO whether this EQ plays…")
                lab.setToolTip("")
            elif got:
                ok, text = got[1], got[2]
                lab.setText(("✓ " if ok else "✕ " if ok is False else "") + check_line(ok, text))
                lab.setToolTip(text + "\nF1: more in Help.")
                theme.mark(lab, role="good" if ok else "warn" if ok is False else "muted")
                lab.style().unpolish(lab)
                lab.style().polish(lab)
        except RuntimeError:  # (the panel was drawn again meanwhile)
            pass

    def _auto_check(self, key, force=False, then=None):
        """The line saying whether the device's EQ plays: Equalizer APO asked in the background when something it
        depends on changed (the EQ, a trial, config.txt or switcher.txt written, plugged in), else the last answer."""
        from ui import tasks
        sig = self._check_sig(key)
        got = self._checks.get(key)
        if got and got[0] == sig and not force:
            self._show_check(key)
            if then:
                then(got)
            return
        job = self._check_job(key)
        if job is None:
            self._checks[key] = (sig, None, "Not connected now: plug it in or connect it to check its EQ.")
            self._show_check(key)
            return
        if key in self._checking:  # (asked already: a forced ask goes again after it, with its answer said)
            if force or then:
                self._check_after[key] = then
            return
        self._checking.add(key)
        self._checks.pop(key, None)
        self._show_check(key)
        work, explain = job

        def done(found, err):
            self._checking.discard(key)
            if err is not None:
                self._checks[key] = (sig, None, f"Couldn't ask Equalizer APO: {err}")
            else:
                ok, text = explain(found)
                self._checks[key] = (sig, ok, text)
            # (the EQ changed while APO was asked: that answer is about the one before, so it's asked again and the
            # old answer never shown; a change during an ask was dropped and the line named the previous EQ)
            if key not in self._check_after and self.sw.record(key) and self._check_sig(key) != sig:
                self._checks.pop(key, None)
                self._auto_check(key, then=then)
                return
            self._show_check(key)
            if then:
                then(self._checks[key])
            if key in self._check_after:
                self._auto_check(key, force=True, then=self._check_after.pop(key))
        tasks.background(work, done)

    def check_device(self, key):
        """Check again: APO asked now, and all it found said (switcher\\check.py)."""
        rec = self.sw.record(key)
        if self._check_job(key) is None:
            QMessageBox.information(self, "Check", "Windows doesn't list this device now: plug it in or connect it first.")
            return
        self.status("Asking Equalizer APO…", 4000)

        def said(got):
            (QMessageBox.information if got[1] else QMessageBox.warning)(self, f"Check: {shown(rec)}", got[2])
        self._auto_check(key, force=True, then=said)

    # ---------------------------------------------------------------- Profiles
    def _profiles_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(_muted("A profile is a copy of an EQ file (Equalizer APO's format: AutoEQ Local's \"Equalizer "
                             "APO\" file, AutoEq's ParametricEQ.txt, squig.link's export). Double-click a name to "
                             "rename it."))
        self.prof_table = QTableWidget(0, 4)
        self.prof_table.setAccessibleName("Profiles")
        self.prof_table.setHorizontalHeaderLabels(["Name", "EQ", "Used by", "From"])
        self.prof_table.verticalHeader().hide()
        self.prof_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.prof_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.prof_table.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed)
        h = self.prof_table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.Stretch)
        for c in (1, 2):
            h.setSectionResizeMode(c, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(3, QHeaderView.Interactive)
        self.prof_table.itemChanged.connect(self._renamed)
        lay.addWidget(self.prof_table, 1)
        row = QHBoxLayout()
        for text, fn in (("Import EQ files…", lambda: self.import_files()), ("Rename", self._rename),
                         ("Remove", self._remove), ("Show the files", lambda: self.open_folder(self.sw.apo.profiles))):
            b = QPushButton(text)
            b.clicked.connect(fn)
            row.addWidget(b)
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
            name.setData(Qt.UserRole, pid)
            t.setItem(r, 0, name)
            for c, text in ((1, _profile_line(p) + ("  (file missing)" if self.sw.profile_missing(pid) else "")),
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
        self.hotkey_note = _muted()
        bl.addWidget(self.hotkey_note)
        about = _muted(f"Version {paths.VERSION}" + (" · installed" if paths.INSTALLED
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
        self.btn_unset.clicked.connect(self.take_out)
        self.btn_conf = QPushButton("Open APO's Configurator")
        self.btn_conf.clicked.connect(self.open_configurator)
        self.btn_folder = QPushButton("Open APO's config folder")
        self.btn_folder.clicked.connect(lambda: self.open_folder(self.sw.apo.config))
        for b in (self.btn_setup, self.btn_unset, self.btn_conf, self.btn_folder):
            row.addWidget(b)
        row.addStretch(1)
        bl.addLayout(row)
        lay.addWidget(box)

        box = QGroupBox("Your files")
        bl = QVBoxLayout(box)
        bl.addWidget(_muted("Your targets and measurements (what Make an EQ uses), saved EQs and presets, each in a "
                            f"folder of its own ({paths.TARGETS_NAME}, {paths.MEASUREMENTS_NAME}, "
                            f"{paths.SAVED_EQS_NAME}, {paths.PRESETS_NAME}), in:"))
        self.files_label = QLabel()
        self.files_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.files_label.setWordWrap(True)
        bl.addWidget(self.files_label)
        row = QHBoxLayout()
        self.btn_files_open = QPushButton("Open the folder")
        self.btn_files_open.clicked.connect(self.open_files_folder)
        self.btn_files_change = QPushButton("Change…")
        self.btn_files_change.setToolTip("Keep your files in another folder (they can be moved there for you)")
        self.btn_files_change.clicked.connect(self.change_files_folder)
        from ui import help_window
        for b in (self.btn_files_open, self.btn_files_change):
            help_window.tag(b, "#files-folder")
            row.addWidget(b)
        row.addStretch(1)
        bl.addLayout(row)
        lay.addWidget(box)
        self.show_files_folder()

        box = QGroupBox("Backup")
        bl = QVBoxLayout(box)
        bl.addWidget(_muted("Everything of yours in one .zip: the devices and their profiles, Make an EQ's settings, "
                            "History, EQs to compare, your targets, measurements and saved EQs. For a new PC or a "
                            "reinstall."))
        row = QHBoxLayout()
        self.btn_backup = QPushButton("Back up everything…")
        self.btn_backup.clicked.connect(self.make_backup)
        self.btn_restore = QPushButton("Restore from a backup…")
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
                lay.addWidget(_muted("“Include: EQ Switcher\\switcher.txt” is EQ Switcher's: AutoEQ Studio takes over "
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
                lay.addWidget(_muted(f"The one on now becomes the EQ of {shown(sw.record(key))}, the device "
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
