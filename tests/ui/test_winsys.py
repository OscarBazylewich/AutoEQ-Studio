"""The bits of Windows the app uses directly (ui\\winsys.py): the hotkey written as Windows takes it (and Windows
taking one), Start with Windows (the command, the launcher named AutoEQ Studio, which entries count as on), APO's
Configurator started without this app's Qt on PATH (moved from selftest.py's qt_checks), and Windows 11's window
materials asked of Windows' DWM as it takes them (Mica, rounded pop-ups, the title bar's dark or light: 2026-10-23,
with Windows stood in, since the tests draw off-screen)."""
import ctypes
import filecmp
import os
import shutil
import sys

from helpers import capabilities
from ui import winsys

ERROR_HOTKEY_ALREADY_REGISTERED = 1409  # (another program holds that key: Windows understood it, though)
NO_DESKTOP = (1459, 5)  # (ERROR_REQUIRES_INTERACTIVE_WINDOWSTATION, access denied: no desktop to take a hotkey)


def test_ctrl_alt_e(qapp, check):
    k = winsys.to_windows("Ctrl+Alt+E")
    # was selftest.py:290
    check("hotkey: Ctrl+Alt+E as Windows takes it", k == (winsys.MOD_NOREPEAT | winsys.MOD_CONTROL | winsys.MOD_ALT, 0x45), k)


def test_f13_shift_win_9_none(qapp, check):
    got = (winsys.to_windows("F13"), winsys.to_windows("Shift+Meta+9"), winsys.to_windows(""))
    # was selftest.py:291
    check("hotkey: F13, Shift+Win+9, none", winsys.to_windows("F13") == (winsys.MOD_NOREPEAT, 0x7C)
          and winsys.to_windows("Shift+Meta+9") == (winsys.MOD_NOREPEAT | winsys.MOD_SHIFT | winsys.MOD_WIN, 0x39)
          and winsys.to_windows("") is None, got)


def test_typing_keys_need_ctrl_alt_or_win(qapp, check):
    alone = [winsys.to_windows(t) for t in ("E", "Shift+E", "Space", "Down")]
    # was selftest.py:294
    check("hotkey: a typing key without Ctrl, Alt or Win refused (it would be taken from every program); F-keys and "
          "media keys alone are fine", alone == [None] * 4
          and winsys.to_windows("Ctrl+Space") and winsys.to_windows("Media Play"),
          (alone, winsys.to_windows("Ctrl+Space"), winsys.to_windows("Media Play")))


def test_windows_takes_the_key(qapp, check):
    # (Windows registers a hotkey for a real window; the off-screen test window has none, so the key itself is tried:
    # a key nobody uses, registered for this thread, then let go at once. Hotkeys are machine-wide: another program,
    # or a second test run at the same moment, may hold Ctrl+Alt+Shift+F24, so F23 down to F13 are tried after it.
    # Windows answering "held by another program" still means it understood the key as written.)
    name = "hotkey: Windows takes the key as written"
    capabilities.require(capabilities.interactive_desktop, check, name)
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    taken = []
    for n in range(24, 12, -1):
        text = f"Ctrl+Alt+Shift+F{n}"
        k = winsys.to_windows(text)
        if user32.RegisterHotKey(None, 0xBEE, *k):
            freed = bool(user32.UnregisterHotKey(None, 0xBEE))
            # was selftest.py:302
            check(name, freed, f"{text} was registered, but Windows didn't let it go")
            return
        err = ctypes.get_last_error()
        if err == ERROR_HOTKEY_ALREADY_REGISTERED:
            taken.append(text)
            continue
        if err in NO_DESKTOP:
            check.skipped(f"no interactive desktop here: Windows refused every hotkey (error {err})", name)
        # (the same check, another outcome)
        check(name, False, f"Windows refused {text} (error {err})")
        return
    print(f"(every key tried is held by another program, so Windows understood each one: {', '.join(taken)})")
    # (the same check, another outcome)
    check(name, True, f"every key tried is held by another program: {taken}")


def test_start_command(check):
    cmd = winsys.start_command()
    # was selftest.py:316
    check("start with Windows: the command runs the app's own Python without a console, in the tray",
          cmd.endswith('start.py" --tray') and any(n in cmd for n in ("pythonw.exe", winsys.LAUNCHER)), cmd)


def test_launcher_named_and_which_entries_count(check, tmp_path):
    # (Task Manager names a startup entry by its program's file: a copy of pythonw.exe called "AutoEQ Studio.exe";
    # made here in the test's own folder, not the app's environment)
    pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    lt = str(tmp_path / "launcher")
    os.makedirs(lt)
    shutil.copy(pyw, lt)
    made = winsys.make_launcher(lt)
    cmd = f'"{made}" "{winsys.START}" --tray'
    # was selftest.py:327
    check("start with Windows: listed as AutoEQ Studio (\"AutoEQ Studio.exe\", the same file as pythonw.exe); an "
          "older entry (by pythonw.exe) still counts as on, another program's or copy's doesn't",
          made == os.path.join(lt, "AutoEQ Studio.exe") and filecmp.cmp(pyw, made, shallow=False)
          and winsys.make_launcher(lt) == made and winsys.autostart_on(cmd)
          and winsys.autostart_on(f'"{pyw}" "{winsys.START}" --tray')
          and not winsys.autostart_on('"C:\\x\\pythonw.exe" "C:\\x\\start.py" --tray') and not winsys.autostart_on(""),
          made)


def test_configurator_starts_without_our_qt(check, monkeypatch, tmp_path):
    # (started as from its Start menu shortcut: in its own folder, without this app's Qt on PATH; it found our Qt
    # first and stopped with "no Qt platform plugin could be initialized")
    real_path = os.environ.get("PATH", "")
    ours = os.path.join(sys.prefix, "Lib", "site-packages", "PySide6")
    other = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "System32")
    monkeypatch.setenv("PATH", os.pathsep.join([ours, other, real_path]))
    given = os.environ["PATH"]
    exe = os.path.join(str(tmp_path), "EqualizerAPO", "DeviceSelector.exe")
    calls = []
    winsys.start_program(exe, opener=lambda path, cwd: calls.append((path, cwd, os.environ["PATH"])))
    after = os.environ["PATH"]
    passed = calls[0][2].split(os.pathsep) if calls else []
    # was selftest.py:456
    check("APO's Configurator starts in its own folder without this app's Qt on PATH (its own Qt is found); the app's "
          "PATH is as before after",
          calls and calls[0][:2] == (exe, os.path.dirname(exe)) and other in passed
          and not any(os.path.normcase(p).startswith(os.path.normcase(sys.prefix)) for p in passed) and after == given,
          calls)


class _Dwm:
    """Windows' DWM stood in: what it was asked, answering as Windows does (0: done) or refusing (another number)."""

    def __init__(self, answer=0):
        self.answer, self.asked = answer, []

    def DwmSetWindowAttribute(self, hwnd, attribute, value, size):  # noqa: N802 - (Windows' own name)
        self.asked.append((attribute, value._obj.value))
        return self.answer

    def DwmExtendFrameIntoClientArea(self, hwnd, margins):  # noqa: N802 - (Windows' own name)
        m = margins._obj
        self.asked.append(("frame", m.left, m.right, m.top, m.bottom))
        return self.answer


def test_windows_11_materials(monkeypatch, check):
    dwm = _Dwm()
    monkeypatch.setattr(ctypes.windll, "dwmapi", dwm)
    took = (winsys.mica(1, True), winsys.round_corners(2), winsys.dark_title(3, False))
    refused = _Dwm(0x80070057)  # (E_INVALIDARG: a Windows without these)
    monkeypatch.setattr(ctypes.windll, "dwmapi", refused)
    not_taken = (winsys.mica(1, False), winsys.round_corners(2))
    builds = {b: winsys.materials("windows", b) for b in (19045, 22000, 22621, 26300)}
    off = winsys.materials("offscreen", 26300)
    check("winsys: Windows 11's materials asked of Windows as it takes them (Mica: the frame over the whole window, "
          "the title bar dark or light, the Mica backdrop; rounded pop-ups), refused by an older Windows, and only on "
          "Windows' own screen: Mica from Windows 11 22H2, rounded corners from 21H2",
          took == (True, True, True) and dwm.asked == [("frame", -1, -1, -1, -1), (20, 1), (38, 2), (33, 2), (20, 0)]
          and not_taken == (False, False) and refused.asked == [("frame", -1, -1, -1, -1), (33, 2)]
          and builds == {19045: (False, False), 22000: (False, True), 22621: (True, True), 26300: (True, True)}
          and off == (False, False), (took, dwm.asked, not_taken, refused.asked, builds, off))
