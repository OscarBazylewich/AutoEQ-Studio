"""What AutoEQ Studio knows and does, without any window: your profiles, the devices and the profiles each one has,
the one switched on for each, and keeping APO's file (apo.py) in step with them.

Settings (data\\settings.json):
- profiles: {id: {"name", "file" (its copy in APO's "AutoEQ Studio\\profiles"), "filters", "preamp", "source"}}
- devices: {key ("Headset|EarPods"): {"label" (Windows' name), "nickname" (yours, or none: shown(rec) is the name
  to show), "guids" (every endpoint seen for it), "profiles" [ids], "active" id or None}}. A device is remembered once seen, so its EQ is in APO's file even while it's not plugged in: plugging
  it in then switches by itself, with or without AutoEQ Studio running.
- notify (a notice when the EQ changes), hotkey ("Ctrl+Alt+E": switch the playing device's EQ), autostart,
  offline (the whole app: net.py), page (the screen the window shows).

Trying an EQ (try_eq): it plays on a device for a few minutes from a file of its own in APO's profiles folder
(TRIAL_FILE), never saved in the settings; end_trial() keeps it as a profile or puts the device's own EQ back. A
start removes a trial left by a crash (APO's file is written again without it).

Listeners (on_change) are told after every change, with what changed: "devices" (plugged in or out, another one
playing), "profiles", "active" (an EQ switched), "settings", "apo".
"""
import os
import time
import uuid

import textfile

from . import devices as devices_mod
from . import eqfile
from .apo import Apo

TRIAL_FILE = "_trying.txt"


def shown(rec):
    """A device's name to show: your nickname, or Windows' name."""
    return (rec.get("nickname") or rec["label"]) if rec else ""


DEFAULTS = {"profiles": {}, "devices": {}, "notify": True, "hotkey": "Ctrl+Alt+E", "autostart": False,
            "told_tray": False, "offline": False, "page": "eq"}


class Switcher:
    def __init__(self, settings_path, apo, endpoints=devices_mod.endpoints, playing=devices_mod.playing):
        self.path, self.apo = settings_path, apo
        self._endpoints, self._playing = endpoints, playing
        self.s = self._load()
        self.devices, self.playing_key, self.listeners = [], None, []
        self.trial = None  # {"key", "name", "until"}: an EQ being tried on a device (try_eq)
        self.refresh(quiet=True)
        if os.path.isfile(self.trial_path()) and not self.hold:  # (a trial the app didn't end: APO's file without it, the file gone)
            self.apply()
            try:
                os.remove(self.trial_path())
            except OSError:
                pass

    # ---------------------------------------------------------------- settings
    def _load(self):
        """The settings, checked. One that can't be read isn't written over: a damaged one is kept as .bad (and said:
        `problem`), a locked one (another program has it open) makes the switcher read-only until the next start, so
        neither the settings nor APO's file are changed."""
        self.problem, self.read_only, self.hold = "", False, False
        try:
            s = textfile.read_json_kept(self.path, dict)
        except OSError as e:
            s, self.read_only = {}, True
            self.problem = (f"AutoEQ Studio's settings couldn't be read ({e}), so nothing is changed this time: your "
                            "devices' EQs stay as they are. Close what has the file open and start AutoEQ Studio again.")
        aside = textfile.take_set_aside()
        if aside:  # (APO's file not written until you change a device's EQ: from empty settings every EQ would go off)
            self.hold = True
            self.problem = (aside + " Your devices' EQs were left as they were; the profiles' EQ files are still in "
                            "Equalizer APO's \"AutoEQ Studio\" folder (Import them again in Profiles).")
        # (keys of other parts, e.g. Listen's and the tracer's choices, kept as they are)
        out = {k: v for k, v in s.items() if k not in DEFAULTS}
        out.update({k: s.get(k, v) if isinstance(s.get(k, v), type(v)) else v for k, v in DEFAULTS.items()})
        out["profiles"] = {k: p for k, p in out["profiles"].items()
                           if isinstance(p, dict) and isinstance(p.get("name"), str) and isinstance(p.get("file"), str)}
        devs = {}
        for k, d in out["devices"].items():
            if not isinstance(d, dict):
                continue
            ids = [i for i in d.get("profiles", []) if i in out["profiles"]] if isinstance(d.get("profiles"), list) else []
            devs[k] = {"label": str(d.get("label") or k), "guids": [g for g in d.get("guids", []) if isinstance(g, str)]
                       if isinstance(d.get("guids"), list) else [], "profiles": ids,
                       "active": d.get("active") if d.get("active") in ids else None}
            if isinstance(d.get("nickname"), str) and d["nickname"].strip():
                devs[k]["nickname"] = d["nickname"].strip()[:60]
        out["devices"] = devs
        return out

    def save(self):
        if self.read_only:  # (the file couldn't be read: never written over)
            return
        textfile.write_json(self.path, self.s, indent=1, quiet=False)

    def set(self, key, value, tell=True):
        """A setting changed and saved; the listeners told, unless tell is False (a setting nothing shows: the
        window's last screen, whose telling had the window draw every screen again at each tab's click)."""
        self.s[key] = value
        self.save()
        if tell:
            self._tell("settings")

    def _tell(self, what, **info):
        for fn in list(self.listeners):
            fn(what, info)

    # ---------------------------------------------------------------- devices
    def refresh(self, quiet=False):
        """Read the devices again: new ones are remembered, endpoints seen are added to their device. Tells the
        listeners when something they show changed (returns that too)."""
        devs = devices_mod.group(self._endpoints())
        playing = self._playing()
        key = next((d.key for d in devs if playing and playing in d.guids), None)
        before = [(d.key, d.connected, d.apo) for d in self.devices], self.playing_key
        changed_settings = False
        for d in devs:
            rec = self.s["devices"].setdefault(d.key, {"label": d.label, "guids": [], "profiles": [], "active": None})
            new = [g for g in d.guids if g not in rec["guids"]]
            if new or rec["label"] != d.label:
                rec["guids"] += new
                rec["label"] = d.label
                changed_settings = True
        self.devices, old_key, self.playing_key = devs, self.playing_key, key
        if changed_settings:
            self.save()
            self.apply(auto=True)
        changed = before != ([(d.key, d.connected, d.apo) for d in devs], key)
        if changed and not quiet:
            self._tell("devices", playing_changed=old_key != key)
        return changed

    def device(self, key):
        return next((d for d in self.devices if d.key == key), None)

    def record(self, key):
        return self.s["devices"].get(key)

    def set_nickname(self, key, name):
        """Your name for a device (empty: Windows' name again)."""
        rec = self.record(key)
        if not rec:
            return
        name = (name or "").strip()[:60]
        if name and name != rec["label"]:
            rec["nickname"] = name
        else:
            rec.pop("nickname", None)
        self.save()
        self._tell("devices")

    def playing(self):
        """(device key, its record) of the device playing now, or (None, None)."""
        return (self.playing_key, self.record(self.playing_key)) if self.playing_key else (None, None)

    # ---------------------------------------------------------------- profiles
    def profiles(self):
        return self.s["profiles"]

    def profile_name(self, pid):
        p = self.s["profiles"].get(pid)
        return p["name"] if p else None

    def _unique_name(self, name, but=None):
        taken = {p["name"].lower() for i, p in self.s["profiles"].items() if i != but}
        base, n = name, 2
        while name.lower() in taken:
            name, n = f"{base} ({n})", n + 1
        return name

    def import_profile(self, path, name=None):
        """Copy an EQ file into APO's profiles folder as a new profile. Returns its id. Raises eqfile.NotAnEqFile
        (said as it is) or OSError (couldn't read or write)."""
        if not self.apo.found:
            raise OSError("Equalizer APO isn't installed, so there's nowhere to keep profiles yet.")
        self._writable()
        raw, info = eqfile.read_eq(path)
        name = self._unique_name((name or eqfile.name_from_file(path)).strip() or "EQ")
        file = textfile.safe_name(name, "EQ", 80) + ".txt"
        n = 2
        while os.path.exists(os.path.join(self.apo.profiles, file)):
            file, n = textfile.safe_name(f"{name} {n}", "EQ", 80) + ".txt", n + 1
        os.makedirs(self.apo.profiles, exist_ok=True)
        textfile.write_atomic(os.path.join(self.apo.profiles, file), raw)
        pid = uuid.uuid4().hex[:10]
        self.s["profiles"][pid] = {"name": name, "file": file, "filters": info["filters"], "preamp": info["preamp"],
                                   "graphic": info["graphic"], "source": os.path.abspath(path),
                                   "added": time.strftime("%Y-%m-%d %H:%M")}
        self.save()
        self._tell("profiles")
        return pid

    def update_profile(self, pid, path):
        """A profile's EQ replaced by this file's (Make an EQ's EQ by hand, begun from it): its name, the devices that
        have it and where it's switched on stay; Equalizer APO reads its file again, so they hear it at once. Raises
        eqfile.NotAnEqFile (said as it is) or OSError."""
        p = self.s["profiles"].get(pid)
        if not p:
            raise OSError("That profile isn't there any more.")
        self._writable()
        raw, info = eqfile.read_eq(path)
        os.makedirs(self.apo.profiles, exist_ok=True)
        textfile.write_atomic(os.path.join(self.apo.profiles, p["file"]), raw)
        p.update(filters=info["filters"], preamp=info["preamp"], graphic=info["graphic"],
                 changed=time.strftime("%Y-%m-%d %H:%M"))
        self.save()
        self.apply()
        self._tell("profiles")

    def rename_profile(self, pid, name):
        name = (name or "").strip()[:80]
        if pid not in self.s["profiles"] or not name:
            return False
        self.s["profiles"][pid]["name"] = self._unique_name(name, but=pid)
        self.save()
        self.apply()
        self._tell("profiles")
        return True

    def remove_profile(self, pid):
        """Remove a profile everywhere (its copy in APO's folder too). A device that had it on is off."""
        p = self.s["profiles"].pop(pid, None)
        if not p:
            return
        for d in self.s["devices"].values():
            if pid in d["profiles"]:
                d["profiles"].remove(pid)
            if d["active"] == pid:
                d["active"] = None
        self.save()
        self.apply()
        try:
            os.remove(os.path.join(self.apo.profiles, p["file"]))
        except OSError:
            pass
        self._tell("profiles")

    def profile_missing(self, pid):
        p = self.s["profiles"].get(pid)
        return bool(p) and not os.path.isfile(os.path.join(self.apo.profiles, p["file"]))

    def has_profile_like(self, path):
        """Is there a profile of this file already: made from it, or with the same contents (brought over from EQ
        Switcher, or imported from a copy)?"""
        try:
            with open(path, "rb") as fh:
                raw = fh.read()
        except OSError:
            return False
        for p in self.s["profiles"].values():
            if os.path.normcase(p.get("source", "")) == os.path.normcase(os.path.abspath(path)):
                return True
            try:
                with open(os.path.join(self.apo.profiles, p["file"]), "rb") as fh:
                    if fh.read() == raw:
                        return True
            except OSError:
                pass
        return False

    def used_by(self, pid):
        return [shown(d) for d in self.s["devices"].values() if pid in d["profiles"]]

    # ---------------------------------------------------------------- a device's profiles
    def add_to_device(self, key, pid, switch_on=True):
        d = self.record(key)
        if not d or pid not in self.s["profiles"]:
            return
        if pid not in d["profiles"]:
            d["profiles"].append(pid)
        if switch_on or d["active"] is None and len(d["profiles"]) == 1:
            d["active"] = pid
        self.save()
        self.apply()
        self._tell("active", key=key)

    def remove_from_device(self, key, pid):
        d = self.record(key)
        if not d or pid not in d["profiles"]:
            return
        d["profiles"].remove(pid)
        if d["active"] == pid:
            d["active"] = None
        self.save()
        self.apply()
        self._tell("active", key=key)

    def set_active(self, key, pid):
        """Switch a device's EQ to one of its profiles, or off (None)."""
        d = self.record(key)
        if self.trial and self.trial["key"] == key:  # (an EQ chosen by hand ends a trial on that device)
            self.end_trial()
        if not d or (pid is not None and pid not in d["profiles"]) or d["active"] == pid:
            return False
        d["active"] = pid
        self.save()
        self.apply()
        self._tell("active", key=key)
        return True

    def cycle(self, key=None):
        """The next of a device's choices (its profiles, then off), for the hotkey. The playing device when key is
        None. Returns (key, the profile id now or None) or None when there's nothing to switch between."""
        key = key or self.playing_key
        d = self.record(key)
        if not d or not d["profiles"]:
            return None
        order = d["profiles"] + [None]
        nxt = order[(order.index(d["active"]) + 1) % len(order)]
        self.set_active(key, nxt)
        return key, nxt

    # ---------------------------------------------------------------- trying an EQ for a few minutes
    def trial_path(self):
        return os.path.join(self.apo.profiles, TRIAL_FILE)

    def try_eq(self, key, apo_text, name, minutes=5):
        """Play an EQ (Equalizer APO text) on a device for a few minutes, in every app, without making it a profile.
        Its own EQ comes back by itself (end_trial, from the app's clock). Raises OSError when it can't."""
        self._writable()
        if not self.apo.found:
            raise OSError("Equalizer APO isn't installed, so there's nothing to play it through.")
        if not self.record(key):
            raise OSError("That device isn't known any more.")
        os.makedirs(self.apo.profiles, exist_ok=True)
        textfile.write_atomic(self.trial_path(), apo_text)
        self.trial = {"key": key, "name": name, "until": time.time() + minutes * 60}
        self.apply()
        self._tell("active", key=key)

    def end_trial(self, keep=False):
        """The trial over: kept as a profile of its device, switched on (keep), or the device's own EQ back. Returns
        the profile id kept, or None."""
        t, pid = self.trial, None
        if not t:
            return None
        if keep and self.record(t["key"]):
            pid = self.import_profile(self.trial_path(), t["name"])
            self.trial = None
            self.add_to_device(t["key"], pid, switch_on=True)
        self.trial = None
        self.apply()
        try:
            os.remove(self.trial_path())
        except OSError:
            pass
        self._tell("active", key=t["key"])
        return pid

    # ---------------------------------------------------------------- APO's file
    def sections(self):
        out = []
        for key, d in self.s["devices"].items():
            p = self.s["profiles"].get(d["active"])
            file = TRIAL_FILE if self.trial and self.trial["key"] == key else p["file"] if p else None
            out.append((d["label"], d["guids"], file))
        return out

    def apply(self, auto=False):
        """Write APO's per-device file when APO is there (it changes nothing until config.txt includes it). Not by
        itself (auto: devices seen) after the settings were set aside (hold), until you change something."""
        if not self.apo.found or self.read_only or (auto and self.hold):
            return False
        self.hold = False
        try:
            return self.apo.write_switcher(self.sections())
        except OSError as e:
            print(f"Couldn't write {self.apo.own}\\switcher.txt: {e}")
            self._tell("apo", error=str(e))
            return False

    def _writable(self):
        """Read-only (the settings file held by another program): nothing of APO's is changed either (review 2: set-up
        and imports still wrote while the settings couldn't be)."""
        if self.read_only:
            raise OSError(self.problem or "AutoEQ Studio's settings couldn't be read, so nothing is changed this time.")

    def set_up_apo(self, turn_off=True):
        self._writable()
        off = self.apo.install_line(turn_off)
        self.apply()
        self._tell("apo")
        return off

    def remove_from_apo(self):
        self._writable()
        self.apo.remove_line()
        self._tell("apo")

    # ---------------------------------------------------------------- from EQ Switcher
    def bring_over(self, old_settings, old_profiles):
        """EQ Switcher's profiles (their files copied from old_profiles) and devices' choices, when this app has none
        yet (its first start). Returns how many profiles came over (0: nothing to bring, or already done)."""
        old = textfile.read_json(old_settings, None)
        if not isinstance(old, dict) or self.s["profiles"] or not isinstance(old.get("profiles"), dict):
            return 0
        os.makedirs(self.apo.profiles, exist_ok=True)
        for pid, p in old["profiles"].items():
            if not (isinstance(p, dict) and isinstance(p.get("file"), str) and isinstance(p.get("name"), str)):
                continue
            src = os.path.join(old_profiles, p["file"])
            if not os.path.isfile(src):
                continue
            with open(src, "rb") as fh:
                textfile.write_atomic(os.path.join(self.apo.profiles, p["file"]), fh.read())
            self.s["profiles"][pid] = dict(p)
        for key, d in (old.get("devices") or {}).items():
            if not isinstance(d, dict):
                continue
            rec = self.s["devices"].setdefault(key, {"label": str(d.get("label") or key), "guids": [], "profiles": [],
                                                     "active": None})
            rec["guids"] += [g for g in d.get("guids") or [] if isinstance(g, str) and g not in rec["guids"]]
            rec["profiles"] = [i for i in d.get("profiles") or [] if i in self.s["profiles"]]
            rec["active"] = d.get("active") if d.get("active") in rec["profiles"] else None
        for k in ("notify", "hotkey"):
            if isinstance(old.get(k), type(DEFAULTS[k])):
                self.s[k] = old[k]
        self.save()
        self.apply()
        self._tell("profiles")
        return len(self.s["profiles"])


def make(settings_path, config=None, install=None):
    """The Switcher for this PC (or for the APO folder given: tests)."""
    import paths
    if config is None:
        install, config = paths.apo_folders()
    return Switcher(settings_path, Apo(config, install))
