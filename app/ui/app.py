"""The app itself: the tray icon and its menu, the window, the hotkey, watching the devices, Online / Offline.

It lives in the tray: the icon's menu switches the playing device's EQ (its profiles, Off, "EQ off for now") and
opens the window or quits; a click on the icon opens the window. Every 1.5 s it reads the devices again (plugged in
or out, another one playing): the window, the menu and the icon follow, and a notice says the EQ of a device that
starts playing. The hotkey goes through the playing device's EQs; the on/off hotkey (2026-10-26) switches its EQ off
for now, to compare, and back (level-matched unless Settings says otherwise: switcher\\core.py's compare_toggle).
start.py makes one (one copy runs at a time).
The app lets its window make Make an EQ ahead while it's open, for someone who has used it (preload_worth_it), and
give its memory back to Windows while it waits in the tray (ui\\window.py's allow_preload); AUTOEQSTUDIO_PRELOAD=0
turns both off (the tests' copies of the app).
"""
import os
import time
import traceback

from PySide6.QtCore import QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QMessageBox, QSystemTrayIcon

import net
import paths
import userfiles
from switcher import core
from switcher.core import shown
from ui import icons, theme, winsys

POLL_MS = 1500


class App:
    def __init__(self, qapp, show):
        self.qapp, self.hotkey_problem, self.onoff_problem = qapp, "", ""
        first = not os.path.exists(paths.SETTINGS)
        self.sw = core.make(paths.SETTINGS)
        self.brought = 0
        if first and self.sw.apo.found:  # (the first start: EQ Switcher's profiles and choices, when it was used)
            try:
                self.brought = self.sw.bring_over(paths.EQ_SWITCHER_SETTINGS,
                                                  os.path.join(self.sw.apo.config, paths.EQ_SWITCHER_FOLDER, "profiles"))
            except OSError:
                traceback.print_exc()
            if self.brought:
                print(f"Brought over {self.brought} profiles and the devices' choices from EQ Switcher")
        net.set_offline(self.sw.s.get("offline", False))
        theme.apply(qapp)
        from ui.window import Window
        self.win = Window(self.sw, self)
        self.win.hotkey_changed.connect(self.set_hotkey)
        self.win.onoff_hotkey_changed.connect(self.set_onoff_hotkey)
        if os.environ.get("AUTOEQSTUDIO_PRELOAD") != "0":  # (the tests' copies of the app: 0, never ahead)
            self.win.allow_preload(self.preload_worth_it)

        self.tray = QSystemTrayIcon(icons.app_icon(), qapp)
        self.menu = QMenu()
        # (its headings, the device playing and the EQ being tried, are drawn readable, not in the grey of an item
        # that can't be chosen: theme_sheet's menus rule, for every menu's notes; the name only tells it apart)
        self.menu.setObjectName("tray")
        self.menu.aboutToShow.connect(self.build_menu)
        self.tray.setContextMenu(self.menu)
        self.tray.activated.connect(lambda why: why == QSystemTrayIcon.Trigger and self.win.show_front())
        self.tray.show()

        self.hotkey = winsys.Hotkey(self.on_hotkey)
        self.set_hotkey(self.sw.s.get("hotkey") or "", save=False)
        self.onoff_key = winsys.Hotkey(self.on_onoff)
        self.set_onoff_hotkey(self.sw.s.get("onoff_hotkey") or "", save=False)
        self.sw.listeners.append(self.changed)
        if not self.sw.problem:  # (APO's file as the settings say, in case it was changed or removed; not when the
            self.sw.apply()      # settings couldn't be read: every EQ would go off)
        else:
            QTimer.singleShot(0, lambda: QMessageBox.warning(None, "AutoEQ Studio", self.sw.problem))
        self.show_state()
        self.timer = QTimer()
        self.timer.timeout.connect(self.poll)
        self.timer.start(POLL_MS)
        if show:
            self.win.show_front()

    @staticmethod
    def preload_worth_it():
        """Is Make an EQ made ahead while the window is open (ui\\window.py)? Only for someone who has opened it before
        (its settings file is in the data folder: the EQ part writes it as it first opens, eq\\paths.py SETTINGS_PATH)
        and has no older files waiting to be moved: a first opening's question, AutoEQ Local's files brought over and
        the samples put in your folders stay on the click."""
        try:
            if not os.path.isfile(os.path.join(paths.DATA, "eq", "settings.json")):
                return False
            pairs, sources = userfiles.old_places()
        except OSError:
            return False
        return not pairs and not sources

    # ---------------------------------------------------------------- devices and changes
    def poll(self):
        try:
            self.sw.refresh()
        except Exception:
            traceback.print_exc()
        if self.sw.trial and time.time() >= self.sw.trial["until"]:  # (a trial's time up: its device's own EQ back)
            self.end_trial(False)
        # a hotkey Windows refused (EQ Switcher still running has it, say) is tried again until it's free
        # (only the saved one, while it isn't registered: a new one refused keeps its note, the saved one still works)
        saved = self.sw.s.get("hotkey")
        if self.hotkey_problem and saved and self.hotkey.current != saved and self.hotkey.set(saved):
            self.hotkey_problem = ""
            self.win.render_settings()
        saved = self.sw.s.get("onoff_hotkey")
        if self.onoff_problem and saved and self.onoff_key.current != saved and self.onoff_key.set(saved):
            self.onoff_problem = ""
            self.win.render_settings()

    def changed(self, what, info):
        self.show_state()
        if not self.sw.s["notify"]:
            return
        if what == "devices" and info.get("playing_changed"):
            key, rec = self.sw.playing()
            if key and (rec["profiles"] or rec["active"]):
                self.tray_message(shown(rec), self.eq_text(rec))

    def eq_text(self, rec):
        c = self.sw.compare
        if c and self.sw.record(c["key"]) is rec:
            return "EQ off for now, to compare" + (" (level-matched)" if c["matched"] else "")
        t = self.sw.trial
        if t and self.sw.record(t["key"]) is rec:
            return f"Trying: {t['name']}"
        name = self.sw.profile_name(rec["active"])
        return f"EQ: {name}" if name else "EQ off"

    def end_trial(self, keep=False):
        """A trial over (its time up, or Keep it / Stop now): kept as a profile, or the device's own EQ back."""
        t = self.sw.trial
        if not t:
            return
        try:
            self.sw.end_trial(keep)
        except (OSError, ValueError) as e:
            QMessageBox.warning(self.win, "Try on device", f"Couldn't keep it: {e}")
            self.sw.end_trial(False)
            return
        rec = self.sw.record(t["key"])
        if rec:
            self.tray_message(shown(rec), f"Kept “{t['name']}” as its EQ." if keep else
                              f"The trial of “{t['name']}” is over: {self.eq_text(rec)}.")

    def show_state(self):
        """The tray icon and its tooltip: the device playing and its EQ (blue: an EQ on; grey: off)."""
        key, rec = self.sw.playing()
        name = self.sw.profile_name(rec["active"]) if rec else None
        trying = bool(rec and self.sw.trial and self.sw.trial["key"] == key)  # (a trial plays: blue too)
        off = bool(rec and self.sw.compare and self.sw.compare["key"] == key)  # (off for now: grey)
        self.tray.setIcon(icons.app_icon(on=(bool(name) or trying) and not off))
        self.tray.setToolTip("AutoEQ Studio\n" + (f"{shown(rec)}: {self.eq_text(rec)}" if rec else "No device playing"))

    def tray_message(self, title, text):
        self.tray.showMessage(title, text, icons.app_icon(), 4000)

    # ---------------------------------------------------------------- the tray menu
    def build_menu(self):
        m = self.menu
        m.clear()
        # (Open first, the default (semibold: theme_sheet), as the icon's own click: as Windows' tray menus have it;
        # Quit alone at the end)
        m.setDefaultAction(m.addAction("Open AutoEQ Studio", self.win.show_front))
        m.addSeparator()
        t = self.sw.trial
        if t:
            left = max(0, int(t["until"] - time.time()))
            m.addAction(f"Trying “{t['name']}” on {shown(self.sw.record(t['key']))} ({left // 60}:{left % 60:02d} left)"
                        ).setEnabled(False)
            m.addAction("Keep it", lambda: self.end_trial(True))
            m.addAction("Stop now", lambda: self.end_trial(False))  # (the trial bar's words: one act, UI-RULES 16)
            m.addSeparator()
        key, rec = self.sw.playing()
        if rec:
            head = m.addAction(shown(rec))
            head.setEnabled(False)
            choices = [(None, "Off")] + [(pid, self.sw.profile_name(pid)) for pid in rec["profiles"]]
            for pid, name in choices:
                a = QAction(name, m)
                a.setCheckable(True)
                a.setChecked(rec["active"] == pid)
                a.triggered.connect(lambda _=False, pid=pid, key=key: self.switch(key, pid))
                m.addAction(a)
            if not rec["profiles"]:
                a = m.addAction("Add a profile…")
                a.triggered.connect(lambda: (self.win.show_page("devices"), self.win.show_front()))
            comparing = bool(self.sw.compare and self.sw.compare["key"] == key)
            if comparing or self.sw.eq_file(key):  # (the on/off hotkey's, from the menu too)
                hk = self.sw.s.get("onoff_hotkey")
                a = QAction("EQ off for now, to compare" + (f"\t{hk}" if hk else ""), m)
                a.setCheckable(True)
                a.setChecked(comparing)
                a.triggered.connect(lambda _=False: self.on_onoff())
                m.addAction(a)
        else:
            m.addAction("No device playing").setEnabled(False)
        m.addSeparator()
        m.addAction("Quit", self.quit)

    def switch(self, key, pid):
        if self.sw.set_active(key, pid) and self.sw.s["notify"]:
            rec = self.sw.record(key)
            self.tray_message(shown(rec), self.eq_text(rec))

    def on_hotkey(self):
        key, rec = self.sw.playing()
        if not rec:
            return
        if not rec["profiles"]:
            self.tray_message(shown(rec), "No profiles for this device yet: add one in AutoEQ Studio.")
            return
        self.sw.cycle(key)
        if self.sw.s["notify"]:
            self.tray_message(shown(rec), self.eq_text(rec))

    def on_onoff(self):
        """The on/off hotkey (and the tray's "EQ off for now"): the playing device's EQ off for now, to compare, and
        back; a notice says which (and how much quieter "off" plays, level-matched)."""
        key, rec = self.sw.playing()
        if not rec:
            return
        try:
            got = self.sw.compare_toggle(key)
        except OSError as e:
            self.tray_message(shown(rec), f"Couldn't switch its EQ: {e}")
            return
        if got is None:
            self.tray_message(shown(rec), "No EQ to switch off or on for this device yet: add a profile in AutoEQ Studio.")
        elif self.sw.s["notify"]:
            self.tray_message(shown(rec), self.compare_text(got))

    def compare_text(self, got):
        """The on/off hotkey's notice."""
        if got[0] == "on":
            return f"EQ back on: {got[1]}" if got[1] else "EQ back on"
        c, hk = got[1], self.sw.s.get("onoff_hotkey") or "the on/off hotkey"
        if not c["matched"]:
            return f"EQ off for now. {hk} switches it back on."
        how = f"turned down {abs(c['db']):.1f} dB to the EQ's loudness" if c["db"] else "as loud as the EQ"
        extra = (" The EQ is louder than none: off can't be raised to match without clipping." if c["louder"] else "") \
            + (" (About: parts of this EQ can't be measured.)" if not c["complete"] else "")
        return f"EQ off for now, level-matched ({how}). {hk} switches it back on.{extra}"

    def set_hotkey(self, text, save=True):
        self._set_key("hotkey", self.hotkey, text, save)

    def set_onoff_hotkey(self, text, save=True):
        self._set_key("onoff_hotkey", self.onoff_key, text, save)

    def _set_key(self, setting, hotkey, text, save):
        """A hotkey registered with Windows (the setting "hotkey" or "onoff_hotkey"), its problem said in Settings."""
        ok = hotkey.set(text)
        problem = "" if ok else (
            f"{text} can't be a hotkey on its own: add Ctrl, Alt or Win (it would stop that key working everywhere)."
            if not winsys.to_windows(text) and winsys.to_windows("Ctrl+" + text) else
            f"Windows didn't take {text} as a hotkey: another program (or the other hotkey) may use it. Try another.")
        setattr(self, "hotkey_problem" if setting == "hotkey" else "onoff_problem", problem)
        if save:
            self.sw.set(setting, text if ok else self.sw.s.get(setting, ""))
            if not ok:
                hotkey.set(self.sw.s.get(setting) or "")
        self.win.render_settings()

    # ---------------------------------------------------------------- starting with Windows, quitting
    @staticmethod
    def autostart_on():
        return winsys.autostart_on()

    def set_autostart(self, on):
        try:
            winsys.set_autostart(on)
        except OSError as e:
            QMessageBox.warning(self.win, "Start with Windows", f"Couldn't change it: {e}")
        self.sw.set("autostart", winsys.autostart_on())

    def set_offline(self, on):
        """Online / Offline (the top bar, Settings): saved, and the whole app follows (net.py)."""
        net.set_offline(on)
        self.sw.set("offline", bool(on))
        self.win.status("Offline: AutoEQ Studio won't connect to the internet." if on else
                        "Online: AutoEQ Studio may use the internet (the online databases).", 5000)

    def restart(self):
        """Quit and start again (after a restore: everything loaded changed). The new copy waits for this one."""
        import sys
        from PySide6.QtCore import QProcess
        start = os.path.join(paths.APP, "start.py")
        QProcess.startDetached(sys.executable, [start, "--restarted"] + (["--tray"] if not self.win.isVisible() else []))
        self.quit()

    def quit(self):
        self.sw.compare_end()  # (off for now ends with the app: its device's EQ back in APO's file)
        if self.sw.trial:  # (a trial ends with the app: its device's own EQ back)
            self.sw.end_trial(False)
        self.hotkey.set("")
        self.onoff_key.set("")
        self.tray.hide()
        self.qapp.quit()
