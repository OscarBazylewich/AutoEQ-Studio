"""Does the EQ apply? Equalizer APO's own Benchmark tool (Benchmark.exe, in APO's folder) is asked, read only, what the
real configuration does for one device: which sections match it and which files it loads. Its words, said plainly:
AutoEQ Studio's file read or not (config.txt's line), this device found in it, the EQ chosen for it loaded or not, and
what config.txt loads for every device on top. Nothing is changed; its test sound is written to a temporary folder.
No Qt here (the window runs it off its own thread).
"""
import os
import re
import subprocess
import tempfile

LOADED = re.compile(r"Loading configuration from (.+?)\s*$")
MATCHED = re.compile(r'Matching pattern "(.*?)" with device')


def parse(out):
    """Benchmark's -v lines: {"loaded": [files], "matched": [patterns, but "all"]}."""
    loaded = [m.group(1) for m in (LOADED.search(l) for l in out.splitlines()) if m]
    matched = [m.group(1) for m in (MATCHED.search(l) for l in out.splitlines()) if m and m.group(1).strip() != "all"]
    return {"loaded": loaded, "matched": matched}


def explain(apo, found, profile_name=None, profile_file=None, apo_on_device=True):
    """The plain words for what Benchmark found (found: parse()'s answer)."""
    same = lambda a, b: os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))
    ours = os.path.join(apo.config, "AutoEQ Studio", "switcher.txt")
    lines, ok = [], False
    if not any(same(f, ours) for f in found["loaded"]):
        lines.append("Equalizer APO doesn't read AutoEQ Studio's file: config.txt has no line for it (Set up… at the "
                     "top of Devices), so no EQ chosen here applies.")
    elif not found["matched"]:
        lines.append("APO reads AutoEQ Studio's file, but no section in it matches this device: its EQ doesn't apply.")
    elif not profile_name:
        lines.append("AutoEQ Studio's EQ is off for this device (APO finds its section, with no EQ in it).")
        ok = True
    elif profile_file and any(same(f, profile_file) for f in found["loaded"]):
        lines.append(f"“{profile_name}” applies on this device: APO finds its section and loads its file.")
        ok = True
    else:
        lines.append(f"AutoEQ Studio chose “{profile_name}”, but APO doesn't load its file for this device"
                     + (" (the file is missing from APO's folder)." if profile_file and not os.path.isfile(profile_file)
                        else "."))
    others = [f for f in found["loaded"] if not same(f, ours) and not same(f, apo.config_txt)
              and not (profile_file and same(f, profile_file))]
    if others:
        lines.append("config.txt also loads, on top: " + ", ".join(os.path.basename(f) for f in others) + ".")
    if not apo_on_device:
        lines.append("But Equalizer APO isn't installed on this device, so nothing plays through it whatever the "
                     "configuration says (APO's Configurator).")
        ok = False
    return ok, " ".join(lines)


def run(apo, guid, timeout=60):
    """Benchmark for one endpoint (its {guid}): parse()'s answer, or raises OSError with a plain message."""
    exe = os.path.join(apo.install, "Benchmark.exe") if apo.install else ""
    if not exe or not os.path.isfile(exe):
        raise OSError("Equalizer APO's Benchmark tool isn't there (it comes with APO 1.3 and later).")
    with tempfile.TemporaryDirectory(prefix="aeqstudio-check-") as d:
        p = subprocess.run([exe, "--guid", guid, "-v", "--nopause", "-l", "1", "-o", os.path.join(d, "test.wav")],
                           capture_output=True, text=True, errors="replace", timeout=timeout,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), cwd=d)
    return parse((p.stdout or "") + "\n" + (p.stderr or ""))
