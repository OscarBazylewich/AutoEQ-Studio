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


def explain(apo, found, profile_name=None, profile_file=None, apo_on_device=True, said_on_card=False):
    """The plain words for what Benchmark found (found: parse()'s answer): (ok, text). On a device without APO
    (apo_on_device False) the text says so too and ok is False. said_on_card: the device's card already says that
    APO isn't installed on it (Devices: its own warning bar), so that sentence is left out and ok is the
    configuration's own: the line below it shows only the other findings (the owner, 2026-11-25)."""
    same = lambda a, b: os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))
    ours = os.path.join(apo.config, "AutoEQ Studio", "switcher.txt")
    lines, ok = [], False
    if not any(same(f, ours) for f in found["loaded"]):
        lines.append("Equalizer APO isn't loading AutoEQ Studio: config.txt doesn't include it. Click Add AutoEQ "
                     "Studio to APO… at the top of Devices.")
    elif not found["matched"]:
        lines.append("No APO section for this device: APO reads AutoEQ Studio's config, but doesn't apply EQ to this "
                     "device")
    elif not profile_name:
        lines.append("EQ is off for this device (APO sees its section with no active profile)")
        ok = True
    elif profile_file and any(same(f, profile_file) for f in found["loaded"]):
        lines.append(f"APO is using “{profile_name}”: device section found and EQ file loaded")
        ok = True
    else:
        lines.append(f"“{profile_name}” is selected, but APO isn't loading it"
                     + (" (file missing from APO folder)" if profile_file and not os.path.isfile(profile_file)
                        else ""))
    others = [f for f in found["loaded"] if not same(f, ours) and not same(f, apo.config_txt)
              and not (profile_file and same(f, profile_file))]
    if others:
        lines.append("config.txt also loads these files for this device: "
                     + ", ".join(os.path.basename(f) for f in others))
    if not apo_on_device and not said_on_card:
        # (for all of the answer, Examine again's message box: first when the configuration is right, so that the
        # box opens with the reason EQ won't apply; after a problem with the configuration itself, which comes first)
        missing = ("Equalizer APO isn't installed on this device, so EQ won't apply. Enable it in APO Configurator, "
                   "then restart Windows.")
        if ok:
            lines.insert(0, missing)
        else:
            lines.append(missing.replace("Equalizer APO isn't installed", "Also, Equalizer APO isn't installed", 1))
        ok = False
    return ok, join(lines)


def join(lines):
    """explain's sentences as one text (the tooltip and the message box Examine show all of it). The owner's words of
    the text survey (2026-11-24) end some sentences without a full stop; one is put between two sentences, so that
    the next does not run on ("… to this device config.txt also loads …"), and the last keeps the owner's end."""
    return " ".join(s if i == len(lines) - 1 or s.endswith((".", "!", "?")) else s + "."
                    for i, s in enumerate(lines))


def run(apo, guid, timeout=60):
    """Benchmark for one endpoint (its {guid}): parse()'s answer, or raises OSError with a plain message."""
    exe = os.path.join(apo.install, "Benchmark.exe") if apo.install else ""
    if not exe or not os.path.isfile(exe):
        raise OSError("Benchmark tool not found. Install Equalizer APO 1.3 or newer.")
    with tempfile.TemporaryDirectory(prefix="aeqstudio-check-") as d:
        p = subprocess.run([exe, "--guid", guid, "-v", "--nopause", "-l", "1", "-o", os.path.join(d, "test.wav")],
                           capture_output=True, text=True, errors="replace", timeout=timeout,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), cwd=d)
    return parse((p.stdout or "") + "\n" + (p.stderr or ""))
