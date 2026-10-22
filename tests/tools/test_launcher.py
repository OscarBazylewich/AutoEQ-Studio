"""The launcher the installer and the ready-to-run zip start the app with (app\\tools\\brand_exe.py, through
make_share_zip.launcher): named AutoEQ Studio with the app's version (Task Manager's Startup apps said "Python"),
Python's signature taken off rather than left broken, and it still runs Python (beside Python's DLLs, its library
found through PYTHONHOME). Made in the test folder. Moved from selftest.py's launcher_checks."""
import os
import shutil
import subprocess
import sys

import paths
from helpers import paths as project
from helpers import qt, session

# (for app\tools\relevant_tests.py: the tools this test imports through helpers.paths.import_tool, and the icon they
# draw. It reads no other file of the project's: only this Python's own)
COVERS = ("brand_exe", "make_share_zip", "paths", "ui.icons")


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
    run = subprocess.run([exe, "-c", f"open(r'{said}', 'w').write('ran')"],
                         env=session.child_env(PYTHONHOME=sys.base_prefix), timeout=qt.time_limit(60))
    info = brand_exe.describe(exe)
    signed = subprocess.run(["powershell", "-NoProfile", "-Command", f"(Get-AuthenticodeSignature '{exe}').Status"],
                            capture_output=True, text=True, env=session.child_env(),
                            timeout=qt.time_limit(60)).stdout.strip()
    # was selftest.py:1076
    check("launcher: named AutoEQ Studio with the app's version, no broken signature, and it runs Python",
          info.get("FileDescription") == "AutoEQ Studio" and info.get("ProductName") == "AutoEQ Studio"
          and info.get("FileVersion") == paths.VERSION and signed == "NotSigned" and run.returncode == 0
          and os.path.isfile(said), (info, signed, run.returncode))
