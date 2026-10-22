"""AutoEQ Studio starts here (AutoEQ Studio.bat, its Start menu shortcut when installed, or Windows at sign-in with
--tray).

One copy runs at a time: starting it again shows the running one's window. The app itself is ui\\app.py.
For the installer: --quit asks a running copy to quit (and waits until it has); --uninstall takes AutoEQ Studio out of
Equalizer APO's config.txt and removes this copy's Start with Windows entry (as Settings does), before its files go.

Nothing but main() runs here when the file is loaded: Windows starts the EQ part's fitting workers by loading this
file again in each one (multiprocessing's "spawn"), and they mustn't open the log, load Qt or start an app.

Anything that goes wrong is written to the log (paths.LOG), each line with its time; one that stops the app is also
said in a message box.
"""
import os
import sys
import time
import traceback
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths  # noqa: E402

# one copy per Windows user; a test copy (its own data or APO folder) has a channel of its own, so it can never reach
# the copy the user is running
_TEST = os.environ.get("AUTOEQSTUDIO_DATA") or os.environ.get("AUTOEQSTUDIO_APO_CONFIG") or \
    ("test build" if paths.TEST_BUILD else "")
SERVER = "AutoEQStudio-" + os.environ.get("USERNAME", "user") + \
    (f"-test{zlib.crc32(os.path.normcase(_TEST).encode()):08x}" if _TEST else "")
APP_ID = "AutoEQStudio.AutoEQStudio"  # (Windows' id for the app: the taskbar groups and pins it by this, as the
#                                      Start menu shortcut the installer makes says too)
MUTEX = "AutoEQStudioRunning" + ("-test" if paths.TEST_BUILD else "")  # (held while the app runs: tools\installer.iss
#                                                                        asks for it by this name)
_RUNNING = None


class _Stamped:
    """The log: each line starts with the date and time it was written."""

    def __init__(self, f):
        self.f, self.at_start = f, True

    def write(self, text):
        out = []
        for part in text.splitlines(keepends=True):
            if self.at_start:
                out.append(time.strftime("%Y-%m-%d %H:%M:%S  "))
            out.append(part)
            self.at_start = part.endswith("\n")
        return self.f.write("".join(out))

    def __getattr__(self, name):  # (flush, fileno … as the file's)
        return getattr(self.f, name)


def open_log():
    os.makedirs(paths.DATA, exist_ok=True)
    if os.path.exists(paths.LOG) and os.path.getsize(paths.LOG) > 1_000_000:  # (keeps the log small)
        try:
            os.replace(paths.LOG, paths.LOG + ".old")
        except OSError:  # (held open, e.g. by another copy closing: this one just adds to it)
            pass
    log = _Stamped(open(paths.LOG, "a", encoding="utf-8", buffering=1))
    sys.stdout = sys.stderr = log


def ask_running(message, wait_gone=0.0):
    """Send the running copy a message ("show", "quit"): None when none runs, else True. wait_gone: seconds to wait
    until it has quit (then False when it hasn't by then)."""
    from PySide6.QtNetwork import QLocalSocket
    sock = QLocalSocket()
    sock.connectToServer(SERVER)
    if not sock.waitForConnected(500):
        return None
    sock.write(message)
    sock.waitForBytesWritten(500)
    sock.disconnectFromServer()
    t = time.time()
    while wait_gone and time.time() - t < wait_gone:
        probe = QLocalSocket()
        probe.connectToServer(SERVER)
        if not probe.waitForConnected(300):
            return True
        probe.abort()
        time.sleep(0.3)
    return not wait_gone  # (True: sent; False: still running after wait_gone)


def uninstall():
    """Before the installer removes the program: AutoEQ Studio's line out of APO's config.txt (the lines it turned off
    on again: every device back to APO's own configuration) and this copy's Start with Windows entry (another copy's
    is left). Your files and the profiles' EQ files stay."""
    from switcher.apo import Apo
    from ui import winsys
    install, config = paths.apo_folders()
    apo = Apo(config, install)
    if apo.found and apo.set_up():
        apo.remove_line()
        print("Uninstall: AutoEQ Studio taken out of Equalizer APO's config.txt")
    if winsys.autostart_on():
        winsys.set_autostart(False)
        print("Uninstall: Start with Windows turned off")


def main():
    # the maths libraries' threads, before anything loads numpy (eq\__init__.py says why; the EQ screen imports numpy
    # before the eq package)
    for v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ.setdefault(v, "1")
    if "--quit" in sys.argv or "--uninstall" in sys.argv:  # (the installer's: no window)
        from PySide6.QtCore import QCoreApplication
        QCoreApplication(sys.argv)
        gone = ask_running(b"quit", wait_gone=15) is not False
        if "--uninstall" in sys.argv:
            open_log()
            uninstall()
        return 0 if gone else 1
    import ctypes
    try:  # (the taskbar shows AutoEQ Studio's own icon and pins it as AutoEQ Studio, not as Python)
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    except (AttributeError, OSError):
        pass
    from PySide6.QtNetwork import QLocalServer, QLocalSocket
    from PySide6.QtWidgets import QApplication
    qapp = QApplication(sys.argv)
    qapp.setApplicationName("AutoEQ Studio")
    qapp.setApplicationVersion(paths.VERSION)
    qapp.setQuitOnLastWindowClosed(False)
    # one copy: a second start asks the first to show its window, then ends (before the log is touched: the running
    # copy has it open)
    if "--restarted" in sys.argv:  # (started by the copy that's quitting, after a restore: wait until it's gone)
        t = time.time()
        probe = QLocalSocket()
        probe.connectToServer(SERVER)
        while probe.waitForConnected(300) and time.time() - t < 15:
            probe.abort()
            time.sleep(0.3)
            probe.connectToServer(SERVER)
    if ask_running(b"show"):
        return 0
    open_log()
    from ui.app import App
    server = QLocalServer()
    QLocalServer.removeServer(SERVER)
    server.listen(SERVER)
    if not _TEST or paths.TEST_BUILD:  # (the installer sees by it that AutoEQ Studio runs, and offers to close it:
        #                                tools\installer.iss)
        global _RUNNING
        _RUNNING = ctypes.windll.kernel32.CreateMutexW(None, False, MUTEX)
    app = App(qapp, show="--tray" not in sys.argv)
    try:  # (Start with Windows on: listed as "AutoEQ Studio" in Task Manager, not "pythonw"; ui\winsys.py)
        from ui import winsys
        winsys.autostart_refresh()
    except OSError:
        pass

    def other_start():
        sock = server.nextPendingConnection()
        if sock:  # ("show": another start; "quit": the installer, before it updates or removes the program)
            sock.readyRead.connect(lambda: app.quit() if b"quit" in bytes(sock.readAll()) else app.win.show_front())
    server.newConnection.connect(other_start)
    print(f"AutoEQ Studio {paths.VERSION} started ({'installed' if paths.INSTALLED else 'from its folder'}; "
          f"APO config folder: {app.sw.apo.config})")
    return qapp.exec()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        if not os.environ.get("AUTOEQSTUDIO_NO_MESSAGE_BOX"):  # (the tests' copies: a box nobody clicks would hang them)
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, "AutoEQ Studio couldn't start:\n\n" + traceback.format_exc(limit=3)
                                             + f"\n\nThe details are in {paths.LOG}.", "AutoEQ Studio", 0x10)
        sys.exit(1)
