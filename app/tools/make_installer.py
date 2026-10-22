"""Makes AutoEQ Studio's installer (the user's ask, 2026-10-11): releases\\AutoEQ Studio Setup <version>.exe, run by
"Make installer.bat" in the main folder. Needs Inno Setup 6 (free: jrsoftware.org, or
"winget install JRSoftware.InnoSetup --scope user").

What's in it (staged in a temporary folder, then packed by Inno Setup with installer.iss beside this file):
  app\\           the program (as in the share zip: without this tools folder), with installed.txt: it then keeps its
                 own data in AppData (paths.py; your files are in Documents\\AutoEQ Studio for every copy)
  runtime\\       its own Python and packages (the ready-to-run zip's: make_share_zip.runtime_entries), started as
                 runtime\\AutoEQ Studio.exe
  samples\\       the sample curves
  first-start\\   what the first start puts in place (paths.first_start): the sample IEM and target in your Targets
                 and Measurements folders, the database lists
  AutoEQ Studio.ico   the app's icon (ui\\icons.app_icon), for the shortcuts, Setup and Windows' list of apps
  runtime\\AutoEQ Studio.exe   the launcher: named AutoEQ Studio, with its version and icon (brand_exe.py)
--zip ("Make zip for friends.bat"): also "AutoEQ Studio <version>.zip" with the installer and READ ME FIRST.txt
(how to install it), to send; --zip-only: only that zip, from this version's installer made before.
--test-build: the same installer as "AutoEQ Studio (test)" with another app id, to install and uninstall when trying
it: it never touches the user's own installation (installer.iss TestBuild). --out FOLDER: where it goes.
Python's compiled files are made in advance (the first start is quicker). The version is paths.VERSION. Like the
zips, it stops before building when the quick self-test fails (--no-test skips it).
"""
import datetime
import os
import shutil
import subprocess
import sys
import tempfile

TOOLS = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(TOOLS)
ROOT = os.path.dirname(APP)
sys.path.insert(0, APP)
sys.path.insert(0, TOOLS)

import brand_exe  # noqa: E402
import make_share_zip as mz  # noqa: E402
import paths  # noqa: E402

ISCC = [os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Inno Setup 6", "ISCC.exe"),
        os.path.join(os.environ.get("ProgramFiles(x86)", ""), "Inno Setup 6", "ISCC.exe"),
        os.path.join(os.environ.get("ProgramFiles", ""), "Inno Setup 6", "ISCC.exe")]
# the zip's parts the installer doesn't take: its launchers and notes (the Start menu starts it; Help explains it),
# its version file (paths.VERSION is the version)
LEFT_OUT = {"AutoEQ Studio.bat", "README.txt", "TESTING.txt", "app/VERSION.txt"}


def iscc():
    found = next((p for p in ISCC if os.path.isfile(p)), None)
    if not found:
        raise SystemExit("Inno Setup 6 isn't installed: winget install JRSoftware.InnoSetup --scope user")
    return found


def staged(entries):
    """The zip's entries as the installer lays them out: [(path in the program's folder, source)]."""
    out = []
    for arc, src in entries:
        rel = arc.split("/", 1)[1]
        if rel in LEFT_OUT:
            continue
        if not rel.startswith(("app/", "samples/", "runtime/", "first-start/")):
            raise SystemExit(f"Not expected in the installer: {rel}")
        out.append((rel, src))
    out.append(("app/installed.txt", b"Installed by AutoEQ Studio's installer: your files are kept out of this folder "
                                     b"(app\\paths.py).\r\n"))
    if "--test-build" in sys.argv:  # (paths.TEST_BUILD: its own folders, channel and mutex; no real APO)
        out.append(("app/test-build.txt", b"A test build of the installer (make_installer.py --test-build).\r\n"))
    return out


def build(stage, out_dir):
    entries = staged(mz.plan(datetime.datetime.now()) + mz.runtime_entries())
    for rel, src in entries:
        dest = os.path.join(stage, *rel.split("/"))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        if isinstance(src, bytes):
            with open(dest, "wb") as fh:
                fh.write(src)
        else:
            shutil.copy2(src, dest)
    brand_exe.icon_file(os.path.join(stage, "AutoEQ Studio.ico"))
    print(f"Staged {len(entries)} files; compiling Python's files …", flush=True)
    subprocess.run([sys.executable, "-m", "compileall", "-q", "-j", "0", os.path.join(stage, "app"),
                    os.path.join(stage, "runtime", "Lib")], check=False, capture_output=True)
    print("Packing with Inno Setup (a few minutes) …", flush=True)
    test = ["/DTestBuild"] if "--test-build" in sys.argv else []
    run = subprocess.run([iscc(), "/Qp", *test, f"/DAppVersion={paths.VERSION}", f"/DStage={stage}", f"/DOutDir={out_dir}",
                          os.path.join(TOOLS, "installer.iss")], capture_output=True, text=True)
    if run.returncode:
        raise SystemExit("Inno Setup failed:\n" + (run.stdout + run.stderr)[-2000:])
    name = "AutoEQ Studio (test)" if test else "AutoEQ Studio"
    return os.path.join(out_dir, f"{name} Setup {paths.VERSION}.exe")


def friends_zip(exe):
    """The zip for friends ("Make zip for friends.bat"): the installer and READ ME FIRST.txt (how to install it, from
    this folder, with the version filled in). Next to the installer: "AutoEQ Studio <version>.zip"."""
    import zipfile
    out = os.path.join(os.path.dirname(exe), f"AutoEQ Studio {paths.VERSION}.zip")
    with open(os.path.join(TOOLS, "READ ME FIRST.txt"), encoding="utf-8") as fh:
        text = fh.read().replace("\r\n", "\n").replace("{version}", paths.VERSION).replace("\n", "\r\n")
    tmp = out + ".part"
    with zipfile.ZipFile(tmp, "w") as z:
        z.writestr("READ ME FIRST.txt", text.encode("utf-8"), compress_type=zipfile.ZIP_DEFLATED)
        z.write(exe, os.path.basename(exe), compress_type=zipfile.ZIP_STORED)  # (already compressed by Setup)
    os.replace(tmp, out)
    return out


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    out_dir = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else os.path.join(ROOT, "releases")
    if "--zip-only" in sys.argv:  # (the installer of this version, made before: only zipped)
        exe = os.path.join(out_dir, f"AutoEQ Studio Setup {paths.VERSION}.exe")
        if not os.path.isfile(exe):
            raise SystemExit(f"No {exe}: make the installer first (Make installer.bat).")
        z = friends_zip(exe)
        print(f"Made {z} ({os.path.getsize(z) / 2**20:.0f} MB): the installer and READ ME FIRST.txt, for friends.")
        return 0
    iscc()  # (said before the self-test's minute, not after)
    if "--no-test" not in sys.argv:
        mz.selftest()
    os.makedirs(out_dir, exist_ok=True)
    stage = tempfile.mkdtemp(prefix="aeqs-setup-")  # (short: the deepest file is 122 characters below it)
    try:
        exe = build(stage, out_dir)
    finally:
        shutil.rmtree(stage, ignore_errors=True)
    print(f"Made {exe} ({os.path.getsize(exe) / 2**20:.0f} MB, version {paths.VERSION}).")
    if "--zip" in sys.argv and "--test-build" not in sys.argv:
        z = friends_zip(exe)
        print(f"Made {z}: the installer and READ ME FIRST.txt, to send to friends.")
    print("Send it, or run it: it installs for the user running it, no administrator needed. Windows may say "
          "\"Windows protected your PC\" the first time (the installer isn't signed): More info, Run anyway.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
