"""The bits of Windows the app uses directly: a hotkey that works in any program (RegisterHotKey), and starting with
Windows (the "Run" list in your user's registry, as Task Manager's Startup apps shows it).

Task Manager names a startup entry by its program's file, not the entry's name: run by pythonw.exe it would say
"pythonw" (as EQ Switcher's does). So Start with Windows runs "AutoEQ Studio.exe", a copy of the environment's
pythonw.exe made beside it (the same signed file under another name: it starts the same Python with the same
packages)."""
import ctypes
import os
import sys
import winreg
from ctypes import wintypes

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QWidget

# ---------------------------------------------------------------- the hotkey
WM_HOTKEY = 0x0312
MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_WIN, MOD_NOREPEAT = 0x1, 0x2, 0x4, 0x8, 0x4000
_user32 = ctypes.windll.user32
_SPECIAL = {Qt.Key_Space: 0x20, Qt.Key_PageUp: 0x21, Qt.Key_PageDown: 0x22, Qt.Key_End: 0x23, Qt.Key_Home: 0x24,
            Qt.Key_Left: 0x25, Qt.Key_Up: 0x26, Qt.Key_Right: 0x27, Qt.Key_Down: 0x28, Qt.Key_Insert: 0x2D,
            Qt.Key_Delete: 0x2E, Qt.Key_Pause: 0x13, Qt.Key_ScrollLock: 0x91,
            Qt.Key_VolumeMute: 0xAD, Qt.Key_MediaNext: 0xB0, Qt.Key_MediaPrevious: 0xB1, Qt.Key_MediaPlay: 0xB3}


def to_windows(text):
    """(modifiers, virtual key) for a key sequence written like "Ctrl+Alt+E", or None when Windows can't take it as
    a hotkey (no key, a key without a Windows code here, or a typing key without Ctrl, Alt or Win: it would be taken
    from every program). F-keys, media keys, Pause and Scroll Lock can be one on their own."""
    seq = QKeySequence(text or "")
    if seq.isEmpty():
        return None
    combo = seq[0]
    key, mods = combo.key(), combo.keyboardModifiers()
    if Qt.Key_A <= key <= Qt.Key_Z or Qt.Key_0 <= key <= Qt.Key_9:
        vk = int(key)  # (Qt's codes for letters and digits are their ASCII, as Windows' are)
    elif Qt.Key_F1 <= key <= Qt.Key_F24:
        vk = 0x70 + int(key) - int(Qt.Key_F1)
    else:
        vk = _SPECIAL.get(key)
    if vk is None:
        return None
    m = MOD_NOREPEAT
    m |= MOD_CONTROL if mods & Qt.ControlModifier else 0
    m |= MOD_ALT if mods & Qt.AltModifier else 0
    m |= MOD_SHIFT if mods & Qt.ShiftModifier else 0
    m |= MOD_WIN if mods & Qt.MetaModifier else 0
    alone = Qt.Key_F1 <= key <= Qt.Key_F24 or key in (Qt.Key_VolumeMute, Qt.Key_MediaNext, Qt.Key_MediaPrevious,
                                                      Qt.Key_MediaPlay, Qt.Key_Pause, Qt.Key_ScrollLock)
    if not alone and not m & (MOD_CONTROL | MOD_ALT | MOD_WIN):
        return None
    return m, vk


class Hotkey(QWidget):
    """A window never shown, that Windows tells when the hotkey is pressed (in any program); calls on_press."""

    ID = 1

    def __init__(self, on_press):
        super().__init__()
        self.on_press, self.current = on_press, None
        self.winId()  # (the window Windows sends the key to)

    def set(self, text):
        """Use this hotkey instead (None or "": none). Returns False when Windows refused it (another program has
        it, or it can't be a hotkey)."""
        if self.current:
            _user32.UnregisterHotKey(wintypes.HWND(int(self.winId())), self.ID)
            self.current = None
        if not text:
            return True
        k = to_windows(text)
        if not k or not _user32.RegisterHotKey(wintypes.HWND(int(self.winId())), self.ID, k[0], k[1]):
            return False
        self.current = text
        return True

    def nativeEvent(self, kind, message):
        if kind == b"windows_generic_MSG" or kind == "windows_generic_MSG":
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == WM_HOTKEY and msg.wParam == self.ID:
                self.on_press()
                return True, 0
        return False, 0


# ---------------------------------------------------------------- starting with Windows
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_NAME = "AutoEQ Studio"


LAUNCHER = "AutoEQ Studio.exe"
START = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "start.py")


def _pythonw(folder=None):
    exe = os.path.join(folder or os.path.dirname(sys.executable), "pythonw.exe")
    return exe if os.path.isfile(exe) else sys.executable


def make_launcher(folder=None):
    """"AutoEQ Studio.exe" beside the environment's pythonw.exe (folder: where it is, for checks), copied again when
    pythonw.exe changed (setup made the environment again). Its path, or None when it can't be made."""
    import filecmp
    import shutil
    import paths
    if paths.INSTALLED and folder is None:  # (installed: the installer's own launcher, named and with the app's icon
        exe = os.path.join(os.path.dirname(sys.executable), LAUNCHER)  # (tools\brand_exe.py): never copied over)
        return exe if os.path.isfile(exe) else None
    src = _pythonw(folder)
    if os.path.basename(src).lower() != "pythonw.exe":
        return None
    dst = os.path.join(os.path.dirname(src), LAUNCHER)
    try:
        if not os.path.isfile(dst) or not filecmp.cmp(src, dst, shallow=False):
            shutil.copy2(src, dst)
    except OSError:  # (in use: it's running, from an earlier start; or the folder can't be written)
        pass
    return dst if os.path.isfile(dst) else None


def start_command(make=False):
    """The command Windows runs at sign-in: the app's own Python without a console window (as "AutoEQ Studio.exe"
    when it's there, or made: make), starting in the tray."""
    exe = make_launcher() if make else None
    if not exe:
        exe = os.path.join(os.path.dirname(_pythonw()), LAUNCHER)
        exe = exe if os.path.isfile(exe) else _pythonw()
    return f'"{exe}" "{START}" --tray'


def _run_value():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            return winreg.QueryValueEx(k, RUN_NAME)[0]
    except OSError:
        return None


# ---------------------------------------------------------------- EQ Switcher (AutoEQ Studio takes over from it)
EQ_SWITCHER_RUN = "EQ Switcher"  # (its Run value, as EQ Switcher\app\winsys.py names it)
EQ_SWITCHER_SERVER = "EQSwitcher-" + os.environ.get("USERNAME", "user")  # (its one-copy channel, EQ Switcher\app\start.py)


def eq_switcher_autostart():
    """Does EQ Switcher start with Windows?"""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            winreg.QueryValueEx(k, EQ_SWITCHER_RUN)
            return True
    except OSError:
        return False


def eq_switcher_autostart_off():
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
        try:
            winreg.DeleteValue(k, EQ_SWITCHER_RUN)
        except FileNotFoundError:
            pass


def eq_switcher_running():
    from PySide6.QtNetwork import QLocalSocket
    s = QLocalSocket()
    s.connectToServer(EQ_SWITCHER_SERVER)
    ok = s.waitForConnected(300)
    s.abort()
    return ok


def eq_switcher_quit(wait=2.0):
    """Ask a running EQ Switcher to quit. Returns whether it has (an older EQ Switcher doesn't know the message)."""
    import time
    from PySide6.QtNetwork import QLocalSocket
    s = QLocalSocket()
    s.connectToServer(EQ_SWITCHER_SERVER)
    if not s.waitForConnected(300):
        return True
    s.write(b"quit")
    s.waitForBytesWritten(300)
    s.disconnectFromServer()
    t = time.time()
    while time.time() - t < wait:
        if not eq_switcher_running():
            return True
        time.sleep(0.2)
    return False


def autostart_on(value=None):
    """Does this copy of the app start with Windows? (Its entry runs this start.py, by whichever Python.)"""
    v = _run_value() if value is None else value
    return isinstance(v, str) and os.path.normcase(v).endswith(os.path.normcase(f'"{START}" --tray'))


def autostart_refresh():
    """Start with Windows on: its command brought up to date (an older one ran pythonw.exe, listed as "pythonw"; the
    launcher made again after setup made the environment again). Nothing when it's off."""
    if autostart_on():
        cmd = start_command(make=True)
        if _run_value() != cmd:
            set_autostart(True, cmd)


def set_autostart(on, cmd=None):
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
        if on:
            winreg.SetValueEx(k, RUN_NAME, 0, winreg.REG_SZ, cmd or start_command(make=True))
        else:
            try:
                winreg.DeleteValue(k, RUN_NAME)
            except FileNotFoundError:
                pass


# ---------------------------------------------------------------- starting another program
def start_program(exe, opener=None):
    """Start another program (APO's Configurator) as from its Start menu shortcut: in its own folder, and without
    this app's folders on PATH. A program started from here inherits both, and Qt programs load their parts from
    them: APO's Configurator (Qt 6.7) then found this app's Qt 6.11 before its own and stopped with "no Qt platform
    plugin could be initialized" (2026-10-21). opener: os.startfile, or a stand-in for the checks."""
    opener = opener or os.startfile
    mine = os.path.normcase(os.path.abspath(sys.prefix))
    before = os.environ.get("PATH", "")
    keep = [p for p in before.split(os.pathsep)
            if p and not os.path.normcase(os.path.abspath(p)).startswith(mine)
            and "pyside6" not in p.lower() and "shiboken6" not in p.lower()]
    os.environ["PATH"] = os.pathsep.join(keep)
    try:
        opener(exe, cwd=os.path.dirname(exe))
    finally:
        os.environ["PATH"] = before
