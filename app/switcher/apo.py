"""Equalizer APO's side: its config folder, AutoEQ Studio's file there, and the one line in config.txt that brings it in.

AutoEQ Studio keeps what it writes in one folder inside APO's config folder ("AutoEQ Studio\\"): the profiles (copies of
your EQ files, in "profiles\\") and switcher.txt, with a "Device:" section per device and the profile chosen for it:

    Device: {d3bfcd09-14ce-41c7-b4f5-e83278716021}
    Include: profiles\\EarPods.txt

APO applies the lines after "Device:" only while sound plays through a device it names, so plugging a device in
switches its EQ with nothing else running. The file ends with "Device: all", so whatever comes after it in config.txt
applies to every device again, as before. config.txt gets one line, "Include: AutoEQ Studio\\switcher.txt" (APO reads
an Include relative to the file it's in), and APO applies a change to a file in its config folder at once: switching
is writing switcher.txt again.

Lines already on in config.txt (an Include of an EQ file, filters, a pre-amp) apply to every device on top of EQ
Switcher's. Setting up turns them off with "# (AutoEQ Studio) " in front, after keeping a copy of config.txt; removing
AutoEQ Studio from APO turns them on again and takes its line out.
"""
import os
import re

import textfile

OWN = "AutoEQ Studio"                       # its folder in APO's config folder
SWITCHER = "switcher.txt"
PROFILES = "profiles"
INCLUDE_LINE = "Include: AutoEQ Studio\\switcher.txt"
OFF_MARK = "# (AutoEQ Studio) "             # in front of a line of config.txt that setting up turned off
BACKUP = "config.txt.autoeq-studio-backup"
_OURS = re.compile(r"^\s*Include\s*:\s*AutoEQ Studio[\\/]switcher\.txt\s*$", re.I)
# an Include, on or off: "# Include: x.txt", and "# (EQ Switcher) Include: x.txt" (a line another app turned off)
_INCLUDE = re.compile(r"^\s*#*\s*(?:\([^)]*\)\s*)?Include\s*:\s*(.+?)\s*$", re.I)


class Apo:
    """APO's config folder (config: its path; None when APO isn't installed)."""

    def __init__(self, config, install=None):
        self.config, self.install = config, install

    # ---------------------------------------------------------------- where things are
    @property
    def found(self):
        return bool(self.config) and os.path.isfile(self.config_txt)

    @property
    def config_txt(self):
        return os.path.join(self.config or "", "config.txt")

    @property
    def own(self):
        return os.path.join(self.config or "", OWN)

    @property
    def profiles(self):
        return os.path.join(self.own, PROFILES)

    @property
    def configurator(self):
        exe = os.path.join(self.install or "", "Configurator.exe")
        return exe if self.install and os.path.isfile(exe) else None

    def writable(self):
        """Can this Windows user write in APO's config folder? (APO's installer lets every user, usually.)"""
        probe = os.path.join(self.config, f".autoeq-studio-probe-{os.getpid()}")
        try:
            with open(probe, "w"):
                pass
            os.remove(probe)
            return True
        except OSError:
            return False

    # ---------------------------------------------------------------- config.txt
    def read_config(self):
        return textfile.read(self.config_txt) if self.found else ""

    def set_up(self):
        """Is config.txt including AutoEQ Studio's file (the line on)?"""
        return any(_OURS.match(line) for line in self.read_config().splitlines())

    @staticmethod
    def others_on(text):
        """config.txt's lines that are on and aren't AutoEQ Studio's: they'd apply to every device on top of it."""
        return [line.strip() for line in text.splitlines()
                if line.strip() and not line.strip().startswith("#") and not _OURS.match(line)]

    def referenced_files(self):
        """The EQ files config.txt includes, on or off ("# Include: x.txt"), that are in APO's config folder: the ones
        you switched by hand, offered as profiles when setting up. A file that isn't an EQ (EQ Switcher's per-device
        file, say) isn't offered."""
        from .eqfile import NotAnEqFile, summary
        out = []
        for line in self.read_config().splitlines():
            m = _INCLUDE.match(line[len(OFF_MARK):] if line.startswith(OFF_MARK) else line)
            if not m or _OURS.match("Include: " + m.group(1)):
                continue
            path = os.path.join(self.config, m.group(1).strip().strip('"'))
            if not os.path.isfile(path) or os.path.normcase(path) in map(os.path.normcase, out):
                continue
            try:
                summary(textfile.read(path))
            except (NotAnEqFile, OSError):
                continue
            out.append(path)
        return out

    def _write_config(self, text):
        textfile.write_atomic(self.config_txt, text, encoding=textfile.encoding_of(self.config_txt), newline="")

    def install_line(self, turn_off=True):
        """Set up: keep a copy of config.txt (the first one is never replaced), turn its other lines off (turn_off),
        and add AutoEQ Studio's line at the end. Returns the lines turned off."""
        text = self.read_config()
        backup = os.path.join(self.config, BACKUP)
        if not os.path.exists(backup):
            with open(self.config_txt, "rb") as fh:
                textfile.write_atomic(backup, fh.read())
        nl = "\r\n" if "\r\n" in text else "\n"
        lines, off = text.splitlines(), []
        for i, line in enumerate(lines):
            if _OURS.match(line):
                lines[i] = None
            elif turn_off and line.strip() and not line.strip().startswith("#"):
                off.append(line.strip())
                lines[i] = OFF_MARK + line
        lines = [x for x in lines if x is not None]
        while lines and not lines[-1].strip():
            lines.pop()
        lines.append(INCLUDE_LINE)
        self._write_config(nl.join(lines) + nl)
        return off

    def remove_line(self):
        """Take AutoEQ Studio out of config.txt: its line goes, the lines it turned off are on again."""
        text = self.read_config()
        nl = "\r\n" if "\r\n" in text else "\n"
        lines = [line[len(OFF_MARK):] if line.startswith(OFF_MARK) else line
                 for line in text.splitlines() if not _OURS.match(line)]
        self._write_config(nl.join(lines) + (nl if lines else ""))

    # ---------------------------------------------------------------- AutoEQ Studio's file
    @staticmethod
    def switcher_text(sections):
        """switcher.txt for sections [(label, guids, profile file name or None)]."""
        out = ["# Written by AutoEQ Studio: one section per device, with the EQ chosen for it. Change it in AutoEQ Studio",
               "# (this file is written again each time). APO applies the lines after \"Device:\" only on that device.",
               ""]
        for label, guids, profile in sections:
            if not guids:
                continue
            out.append(f"# {label}: {profile[:-4] if profile else 'off'}")
            # (each id as Windows names it, "{…}": APO compares whole words with "<device> <connection> <id>", so
            # an id without its { } never matches: seen in APO's Benchmark.exe trace, 2026-10-05)
            out.append("Device: " + "; ".join("{" + g.strip("{}") + "}" for g in guids))
            if profile:
                out.append(f"Include: {PROFILES}\\{profile}")
            out.append("")
        out += ["# everything after this in config.txt applies to every device again", "Device: all", ""]
        return "\r\n".join(out)

    def write_switcher(self, sections):
        """Write switcher.txt when it changed (APO reloads it). Returns whether it was written."""
        text = self.switcher_text(sections)
        path = os.path.join(self.own, SWITCHER)
        try:
            if textfile.read(path) == text:
                return False
        except OSError:
            pass
        os.makedirs(self.profiles, exist_ok=True)
        textfile.write_atomic(path, text, newline="")
        # APO reloads when it sees a file in its folder written; writing the temporary file can tell it before the
        # rename puts the new text in place. Touching the file afterwards tells it again, with the text there.
        os.utime(path)
        return True
