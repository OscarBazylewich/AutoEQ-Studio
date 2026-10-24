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
Everything is drawn in the app's theme (ui\\theme.py: Windows 11's look, light or dark as Windows is, in Windows'
accent colour); what only this window and its screens have is styled in ui\\theme_sheet.py's window_screens(), by the
objectNames and properties set here (the banner's warning sign, the trial's clock, the status line…). On Windows 11
(22H2 or later) the window's own background is Windows' Mica (ui\\winsys.mica: tinted by your desktop picture, as
Windows' own apps; the user's choice from real pictures, 2026-10-23): the window is see-through where nothing is
drawn, and property mica=true tells the stylesheet to leave its background clear; never in a contrast theme.
Where the code is: this file has the shell (the top bar, switching screens, Guide, Help, closing to the tray, the
trial bar) and the banner; each screen is a part of the window's class, in a file of its own: Devices
(ui\\devices_screen.py), Profiles (ui\\profiles_screen.py), Settings (ui\\settings_screen.py; Set up…:
ui\\setup_dialog.py). ui\\window_parts.py has the small helpers they share.
"""
import time

from PySide6.QtCore import Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QCursor, QDesktopServices, QGuiApplication, QKeySequence, QShortcut
from PySide6.QtWidgets import (QButtonGroup, QFrame, QHBoxLayout, QLabel, QMainWindow, QMenu, QPushButton,
                               QScrollArea, QSizePolicy, QStackedWidget, QVBoxLayout, QWidget)

import net
import paths
from switcher.core import shown
from ui import icons, theme, winsys
from ui.devices_screen import DevicesScreen, check_line  # noqa: F401 - (check_line: still taken from here)
from ui.profiles_screen import ProfilesScreen
from ui.settings_screen import SettingsScreen
from ui.setup_dialog import SetUpDialog  # noqa: F401 - (still taken from here, as before the screens had files)
from ui.window_parts import fit_to_screen, glyph, warning_card

PAGES = [("eq", "Make an EQ"), ("devices", "Devices"), ("profiles", "Profiles"), ("settings", "Settings")]


class Window(DevicesScreen, ProfilesScreen, SettingsScreen, QMainWindow):
    """The window: the shell and the banner here, joined with its screens' parts (Devices, Profiles, Settings: plain
    classes in files of their own; Qt's main window comes last). The hotkey_changed signal is here: a signal can't be
    on a plain class."""
    hotkey_changed = Signal(str)   # (the app registers it, and says when Windows refused it)

    def __init__(self, sw, app):
        super().__init__()
        self.sw, self.app = sw, app
        self.setWindowTitle("AutoEQ Studio")
        self.setWindowIcon(icons.app_icon())
        fit_to_screen(self, (1040, 760))  # (within the screen's room: 760 high was under a laptop's taskbar at 150 %)
        self.selected = sw.playing_key or (sw.devices[0].key if sw.devices else None)
        self.eq_page = None
        # Windows 11's Mica: the window made see-through before Windows first draws it (it can't be later); turned on
        # when it first shows (_mica_on), followed when the theme changes
        self._mica = winsys.materials(QGuiApplication.platformName())[0]
        self._mica_hwnd = None
        if self._mica:
            self.setAttribute(Qt.WA_TranslucentBackground)

        central = QWidget()
        lay = QVBoxLayout(central)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self._top_bar())
        # the banner: Windows 11's warning bar (its sign, the words, the action)
        self.banner_btn = QPushButton()
        theme.mark(self.banner_btn, primary=True)
        self.banner_btn.clicked.connect(self._banner_action)
        self.banner, self.banner_text = warning_card("", self.banner_btn)
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
        tl.setContentsMargins(4, 0, 4, 0)
        tl.setSpacing(12)
        clock = glyph("clock", said="Trying an EQ")  # (Windows 11's clock, in the accent's text colour)
        clock.setObjectName("trialGlyph")
        self.trial_text = QLabel()
        self.trial_text.setWordWrap(True)
        keep = QPushButton("Keep it")
        theme.mark(keep, primary=True)
        icons.put(keep, "check")
        keep.setToolTip("Make it a profile of the device, switched on")
        keep.clicked.connect(lambda: self.app.end_trial(True))
        stop = QPushButton("Stop now")
        icons.put(stop, "cancel")  # (✕: Windows 11's square "stop" read as an empty check box beside the words)
        stop.setToolTip("The device's own EQ back now")
        stop.clicked.connect(lambda: self.app.end_trial(False))
        tl.addWidget(clock)
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
                      "profiles": self._padded(self._profiles_tab()), "settings": self._scrolled(self._settings_tab())}
        for key, _ in PAGES:
            self.stack.addWidget(self.pages[key])
        # (the screens scroll when there's no room, so the window may be small, as on a laptop's screen: Settings made
        # it at least 812 px tall; but never so small that a screen shows only a sliver)
        self.stack.setMinimumHeight(360)
        lay.addWidget(self.stack, 1)
        self.setCentralWidget(central)
        # the line at the bottom for messages: its words lined up with the screens', no size grip (Windows 11's)
        bar = self.statusBar()
        bar.setObjectName("windowStatus")
        bar.setSizeGripEnabled(False)
        self.status_text = QLabel()
        # (a long message never widens the window: it's cut at its edge instead, its tooltip whole)
        self.status_text.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        bar.addWidget(self.status_text, 1)
        self._status_timer = QTimer(self, singleShot=True, timeout=lambda: self.status("", 0))

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
            icons.put(b, key)  # (Windows 11's symbol beside each screen's name: eq, devices, profiles, settings)
            b.clicked.connect(lambda _=False, k=key: self.show_page(k))
            group.addButton(b)
            h.addWidget(b)
            self.nav[key] = b
        h.addStretch(1)
        self.presets_btn = QPushButton("Presets")  # (Make an EQ's settings: shown on that screen)
        theme.mark(self.presets_btn, nav=True)
        icons.put(self.presets_btn, "presets")
        self.presets_btn.setToolTip("Save all of Make an EQ's settings under a name, and load them again")
        from ui import help_window
        help_window.tag(self.presets_btn, "#presets")
        # (the menu the button's own, so it shows Windows 11's chevron as every button with a menu does (the theme's
        # picture), beside Use on device's: "▾" was typed in its words, 2026-10-23; made afresh as it opens)
        self.presets_menu = QMenu(self.presets_btn)
        self.presets_menu.aboutToShow.connect(self.fill_presets)
        self.presets_btn.setMenu(self.presets_menu)
        h.addWidget(self.presets_btn)
        guide = QPushButton("Guide")
        theme.mark(guide, nav=True)
        icons.put(guide, "guide")
        guide.setToolTip("A tour of Make an EQ: each part and what it does")
        guide.clicked.connect(self.start_guide)
        h.addWidget(guide)
        self.help_btn = helpb = QPushButton("Help")  # (its symbol is the question mark it had in its words)
        theme.mark(helpb, nav=True)
        icons.put(helpb, "help")
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

    def _scrolled(self, widget):
        """A screen that scrolls when the window is too small for it, as Windows 11's Settings do (its cards and
        buttons keep their size: without it they were squeezed, the hotkey box to half its height)."""
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setFrameShape(QFrame.NoFrame)
        area.setWidget(self._padded(widget))
        return area

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

    def fill_presets(self):
        """Presets' menu (AutoEQ Local's Presets menu), made afresh as it opens from the presets there are now; before
        Make an EQ has opened, a note saying when they're ready."""
        page = self.eq_page
        if page is None or getattr(page, "settings", None) is None:
            self.presets_menu.clear()
            self.presets_menu.addAction("Presets are ready as soon as Make an EQ has opened").setEnabled(False)
            return
        page.fill_presets(self.presets_menu)

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
        """A message in the line at the bottom, for ms milliseconds (0: until the next one)."""
        self.status_text.setText(text)
        self.status_text.setToolTip(text)  # (all of it, when the window is too narrow for it)
        if ms:
            self._status_timer.start(ms)
        else:
            self._status_timer.stop()

    def showEvent(self, e):
        self.render_all()  # (devices plugged in, EQs switched from the tray while it was hidden)
        super().showEvent(e)
        if self._mica and self._mica_hwnd is None:
            self._mica_hwnd = int(self.winId())
            theme.on_change(self._mica_on)
            self._mica_on()
        if getattr(self, "_eq_pending", False) and self.eq_page is None:
            self._eq_pending = False
            self.show_page("eq", remember=False)
        if self.page() == "eq" and self.eq_page:
            self.eq_page.start()

    def _mica_on(self):
        """Mica behind the window, its title bar dark or light with the theme; in a contrast theme the window paints
        its background itself (Windows' own solid colours)."""
        on = winsys.mica(self._mica_hwnd, theme.dark()) and not theme.high_contrast()
        if (self.property("mica") in (True, "true")) != on:
            theme.mark(self, mica=on)

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
