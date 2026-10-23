"""The installer's script (app\\tools\\installer.iss) compiles with Inno Setup, as the real build and as the test build
(make_installer.py --test-build), on a tiny stand-in program in the test folder (seconds, not the real installer's
minutes). Needs Inno Setup 6: without it the check says it's skipped and why. Moved from selftest.py's
installed_checks."""
import os
import subprocess

from helpers import capabilities, qt, session
from helpers import paths as project

# (for app\tools\relevant_tests.py: the tools this test imports through helpers.paths.import_tool, the icon they
# draw, and the script it compiles)
COVERS = ("make_installer", "brand_exe", "make_share_zip", "ui.icons")
COVERS_FILES = ("app/tools/installer.iss",)

NAME = "installer: installer.iss compiles (the real build and the test build)"


def test_installer_script_compiles(qapp, tmp_path, check):
    # (the stand-in program's icon is drawn: the tests' QApplication (qapp) is made first, or the drawing would make a
    # plain one and no window could be made in this process afterwards)
    brand_exe = project.import_tool("brand_exe")
    project.import_tool("make_installer")  # (as the old check: it imports; Inno Setup is found below, not by its list)
    # (Inno Setup is looked for where make_installer.ISCC looks, but in the folders the run started with: on this PC
    # it's installed for the user only, under the real AppData, which the tests' session replaces)
    capabilities.require("iscc", check, NAME)
    iscc = capabilities.iscc_path()
    top = str(tmp_path)
    stage = os.path.join(top, "iss", "stage")
    os.makedirs(stage)
    brand_exe.icon_file(os.path.join(stage, "AutoEQ Studio.ico"))
    with open(os.path.join(stage, "readme.txt"), "w") as fh:
        fh.write("stand-in")
    bad = []
    for extra in ([], ["/DTestBuild"]):
        r = subprocess.run([iscc, "/Q", *extra, "/DAppVersion=0.0.0", f"/DStage={stage}",
                            f"/DOutDir={os.path.join(top, 'iss', 'out')}", os.path.join(project.TOOLS, "installer.iss")],
                           capture_output=True, text=True, errors="replace", env=session.child_env(),
                           timeout=qt.time_limit(300))
        if r.returncode:
            bad.append(((extra or ["real"])[0], (r.stdout + r.stderr)[-400:]))
    # was selftest.py:1256
    check(NAME, not bad, bad)
