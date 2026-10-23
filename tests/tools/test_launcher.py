"""The launcher the installer and the ready-to-run zip start the app with (app\\tools\\brand_exe.py, through
make_share_zip.launcher): named AutoEQ Studio with the app's version (Task Manager's Startup apps said "Python"),
Python's signature taken off rather than left broken, and it still runs Python (beside Python's DLLs, its library
found through PYTHONHOME). Made in the test folder. Moved from selftest.py's launcher_checks."""
import os
import shutil
import struct
import subprocess
import sys

import paths
from helpers import paths as project
from helpers import qt, session

# (for app\tools\relevant_tests.py: the tools this test imports through helpers.paths.import_tool, and the icon they
# draw. It reads no other file of the project's: only this Python's own)
COVERS = ("brand_exe", "make_share_zip", "paths", "ui.icons")


def certificate_table(path):
    """Where a program's signature is kept (its certificate table: the header's fifth data directory) and its size,
    read here independently of brand_exe.py; (0, 0) when it has none, which Windows' signature check reads as "Not
    signed". Read from the file rather than asked of PowerShell: on GitHub's machine, Windows PowerShell started
    under PowerShell 7 said nothing at all."""
    with open(path, "rb") as fh:
        data = fh.read()
    pe = struct.unpack_from("<I", data, 0x3C)[0]  # (where the PE header starts)
    if data[pe:pe + 4] != b"PE\0\0":
        return None
    opt = pe + 24  # (the optional header: after the signature, 4 bytes, and the file header, 20)
    wide = struct.unpack_from("<H", data, opt)[0] == 0x20B  # (PE32+, a 64-bit program: its directories start later)
    return struct.unpack_from("<II", data, opt + (112 if wide else 96) + 4 * 8)


def test_launcher_named_unsigned_and_runs_python(qapp, tmp_path, check):
    # (making it draws the app's icon: the tests' QApplication (qapp) is made first, or the drawing would make a plain
    # one and no window could be made in this process afterwards)
    brand_exe = project.import_tool("brand_exe")
    mz = project.import_tool("make_share_zip")
    folder = os.path.join(tmp_path, "launcher")
    os.makedirs(folder)
    exe = os.path.join(folder, "AutoEQ Studio.exe")
    with open(exe, "wb") as fh:
        fh.write(mz.launcher())
    for n in os.listdir(sys.base_prefix):
        if n.lower().endswith(".dll"):
            shutil.copy2(os.path.join(sys.base_prefix, n), folder)
    said = os.path.join(folder, "ran.txt")
    # (without PYTHONFAULTHANDLER, which run_tests.py and GitHub's run set to report a crash: the launcher is a
    # pythonw, a program without a console, so it has nowhere to write one, and Python then refuses to start at all,
    # silently, with exit code 1. The app's own start never has it set, nor had the old self-test's run of it)
    run = subprocess.run([exe, "-c", f"open(r'{said}', 'w').write('ran')"],
                         env=session.child_env(PYTHONHOME=sys.base_prefix, PYTHONFAULTHANDLER=None),
                         timeout=qt.time_limit(60))
    info = brand_exe.describe(exe)
    # (Python's own pythonw.exe is signed: its table, for the detail, shows there was one to take off)
    table, before = certificate_table(exe), certificate_table(os.path.join(sys.base_prefix, "pythonw.exe"))
    # was selftest.py:1076
    check("launcher: named AutoEQ Studio with the app's version, no broken signature, and it runs Python",
          info.get("FileDescription") == "AutoEQ Studio" and info.get("ProductName") == "AutoEQ Studio"
          and info.get("FileVersion") == paths.VERSION and table == (0, 0) and run.returncode == 0
          and os.path.isfile(said), (info, {"signature": table, "pythonw.exe's": before}, run.returncode))
