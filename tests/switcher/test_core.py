"""What AutoEQ Studio knows and does without a window (switcher\\core.py's Switcher), on a stand-in APO folder and
settings files in the test's own folder, with two stand-in playback devices the tests change: settings with junk in
them, other parts' settings kept, a damaged or a locked settings file (nothing written over), profiles imported, put
on devices and switched with the hotkey, a device starting to play, a profile removed or renamed, the settings read
back, setting APO up, and importing without APO. Moved from selftest.py's core_checks.

core_checks was one long chain on one Switcher. Here its state is in module-wide fixtures, made in the old order, and
the tests run in the chain's order (pytest runs a file's tests in the order written): `start` is the Switcher and
what it works on; `locked`, `imported`, `on_devices` and `started_playing` each do the old steps a later check needs,
so the whole file does exactly what core_checks did, and a test run alone still has what it needs.

textfile keeps a list of the files it set aside (a damaged one kept as .bad), and a Switcher takes it as it starts:
it's emptied before each Switcher whose start the checks depend on, and after the damaged start, so nothing another
test left reaches these checks and nothing of theirs reaches another test."""
import os
import types

import pytest

import textfile
from helpers import apo as stand_in
from switcher import core
from switcher import devices as D
from switcher.apo import Apo

EP, BUDS = "Headset|EarPods", "Headphones|Buds"  # (the two devices' keys, selftest.py line 202)


def _read(path, **kw):
    """A file's text (the old checks read with open(path, ...).read())."""
    with open(path, **kw) as fh:
        return fh.read()


@pytest.fixture(scope="module")
def start(tmp_path_factory):
    """core_checks' start (selftest.py lines 136-143): a stand-in APO folder, a settings file with junk in it, two
    stand-in endpoints (the headset {5} connected, the earbuds {1} not) that tests change, a holder for the device
    playing ({5}), and the Switcher on them (it saves the cleaned settings and writes APO's switcher.txt)."""
    top = str(tmp_path_factory.mktemp("core"))
    conf = stand_in.fake_apo(top)
    data = os.path.join(top, "data", "settings.json")
    os.makedirs(os.path.dirname(data))
    with open(data, "w") as fh:  # (a hand-edited file with junk: what can't be used is dropped)
        fh.write('{"profiles": {"x": 5}, "devices": {"k": {"profiles": "no", "active": "x"}}, "notify": "yes"}')
    eps = [D.Endpoint("{5}", "Headset", "EarPods", D.ACTIVE, True), D.Endpoint("{1}", "Headphones", "Buds", D.NOT_PRESENT, True)]
    now = {"playing": "{5}"}
    textfile.take_set_aside()  # (nothing another test set aside: the Switcher would take it as its own)
    sw = core.Switcher(data, Apo(conf), endpoints=lambda: list(eps), playing=lambda: now["playing"])
    return types.SimpleNamespace(top=top, conf=conf, data=data, eps=eps, now=now, sw=sw)


def test_junk_dropped(start, check):
    sw = start.sw
    # was selftest.py:144
    check("core: settings with junk in them load (what can't be used dropped)",
          sw.s["profiles"] == {} and sw.s["notify"] is True and sw.s["devices"]["k"]["profiles"] == [])


def test_other_parts_kept(start, check):
    c, sw = start, start.sw
    # (review #29: other parts' choices, e.g. Listen's, kept from one start to the next)
    sw.s["listen"] = {"vol": -40}
    sw.save()
    again = core.Switcher(c.data, Apo(c.conf), endpoints=lambda: list(c.eps), playing=lambda: c.now["playing"])
    # was selftest.py:150
    check("core: other parts' settings (Listen's, the tracer's) are kept from one start to the next",
          again.s.get("listen") == {"vol": -40}, again.s.get("listen"))


def test_damaged_settings(start, check):
    c = start
    # (review #5: a settings file that can't be read is never written over)
    bad = os.path.join(c.top, "bad", "settings.json")
    os.makedirs(os.path.dirname(bad))
    with open(bad, "w") as fh:
        fh.write('{"profiles": {"a": {"name": "Mine", "file": "x.txt"}}, "dev')  # (cut off)
    own = os.path.join(c.conf, "AutoEQ Studio", "switcher.txt")
    with open(own, "w", encoding="utf-8") as fh:
        fh.write("Device: x\nInclude: profiles\\x.txt\n")  # (an EQ on: still on after the damaged start)
    apo_before = _read(own, encoding="utf-8")
    try:
        broken = core.Switcher(bad, Apo(c.conf), endpoints=lambda: list(c.eps), playing=lambda: c.now["playing"])
    finally:
        textfile.take_set_aside()  # (the Switcher took its own notice; none is left for another test)
    apo_after = _read(own, encoding="utf-8") if os.path.isfile(own) else None
    # was selftest.py:164
    check("core: a damaged settings file is kept as .bad and said; the app starts fresh; APO's file isn't written "
          "(every EQ would go off: review 2)", os.path.exists(bad + ".bad") and "couldn't be read" in broken.problem
          and not broken.read_only and broken.s["profiles"] == {} and apo_after == apo_before,
          (broken.problem, apo_before, apo_after))


def _in_use(path, kind):
    """textfile.read_json_kept's stand-in: the settings file held by another program."""
    raise PermissionError(13, "in use")


@pytest.fixture(scope="module")
def locked(start):
    """A Switcher started while another program holds the settings file (selftest.py lines 168-175): APO's file says
    "kept" first, and textfile.read_json_kept raises PermissionError while the Switcher starts (a stand-in, put back
    at once)."""
    c = start
    with open(os.path.join(c.conf, "AutoEQ Studio", "switcher.txt"), "w") as fh:
        fh.write("kept")
    textfile.take_set_aside()  # (nothing another test set aside: it would take the place of the "in use" problem)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(textfile, "read_json_kept", _in_use)
        return core.Switcher(c.data, Apo(c.conf), endpoints=lambda: list(c.eps), playing=lambda: c.now["playing"])


def test_locked_settings(start, locked, check):
    c = start
    before = _read(c.data, encoding="utf-8")
    locked.set("notify", False)
    locked.apply()
    apo_now = _read(os.path.join(c.conf, "AutoEQ Studio", "switcher.txt"))
    # was selftest.py:181
    check("core: a settings file another program holds makes nothing change: neither it nor APO's file is written",
          locked.read_only and "in use" in locked.problem and _read(c.data, encoding="utf-8") == before
          and apo_now == "kept", (locked.read_only, locked.problem))


def test_locked_refuses_apo(locked, check):
    refused = []
    for act in (locked.set_up_apo, locked.remove_from_apo):
        try:
            act()
        except OSError:
            refused.append(act.__name__)
    # was selftest.py:190
    check("core: read-only, setting APO up or taking it out is refused too (review 2)",
          refused == ["set_up_apo", "remove_from_apo"], refused)


@pytest.fixture(scope="module")
def imported(start):
    """A listener noting what the Switcher tells (and whether the device playing changed), then EarPods.txt,
    Samson.txt and EarPods.txt again imported as profiles (selftest.py lines 192-196): their ids."""
    c = start
    told = []
    c.sw.listeners.append(lambda what, info: told.append((what, info.get("playing_changed"))))
    ear = c.sw.import_profile(os.path.join(c.conf, "EarPods.txt"))
    sam = c.sw.import_profile(os.path.join(c.conf, "Samson.txt"))
    again = c.sw.import_profile(os.path.join(c.conf, "EarPods.txt"))
    return types.SimpleNamespace(told=told, ear=ear, sam=sam, again=again)


def test_profiles_imported(start, imported, check):
    sw, ear, sam, again = start.sw, imported.ear, imported.sam, imported.again
    names = [sw.profile_name(i) for i in (ear, sam, again)]
    # was selftest.py:198
    check("core: profiles imported (the same file twice: its own name and file)",
          names == ["EarPods", "Samson", "EarPods (2)"] and len(set(p["file"] for p in sw.profiles().values())) == 3, names)


def test_profile_is_the_files_bytes(start, imported, check):
    sw = start.sw
    with open(os.path.join(sw.apo.profiles, sw.profiles()[imported.sam]["file"]), "rb") as fh:
        # was selftest.py:201
        check("core: a profile is the file's bytes as they were (UTF-16 kept)", fh.read() == stand_in.SAMSON)


@pytest.fixture(scope="module")
def on_devices(start, imported):
    """EarPods and Samson (not switched on) put on the headset, Samson on the earbuds (selftest.py lines 202-205)."""
    sw = start.sw
    sw.add_to_device(EP, imported.ear)
    sw.add_to_device(EP, imported.sam, switch_on=False)
    sw.add_to_device(BUDS, imported.sam)
    return imported


def test_apo_file_has_each_profile(start, on_devices, check):
    with open(os.path.join(start.sw.apo.own, "switcher.txt")) as fh:
        text = fh.read()
    # was selftest.py:208
    check("core: APO's file has each device's profile",
          "Device: {5}\nInclude: profiles\\EarPods.txt" in text and "Device: {1}\nInclude: profiles\\Samson.txt" in text, text)


def test_hotkey_cycles(start, on_devices, check):
    sw, ear, sam = start.sw, on_devices.ear, on_devices.sam
    order = [sw.cycle()[1] for _ in range(3)]
    # was selftest.py:211
    check("core: the hotkey goes through the playing device's profiles, then Off", order == [sam, None, ear], order)


def test_profile_not_on_device_refused(start, on_devices, check):
    # was selftest.py:212
    check("core: switching to a profile the device doesn't have is refused", not start.sw.set_active(EP, on_devices.again))


@pytest.fixture(scope="module")
def started_playing(start, on_devices):
    """The earbuds start to play (selftest.py lines 213-217): what was told forgotten, their Hands-Free endpoint {2}
    appears, {1} plays and is connected, and the devices are read again. Whether that changed something."""
    c = start
    on_devices.told.clear()
    c.eps.append(D.Endpoint("{2}", "Headset", "Buds Hands-Free", D.NOT_PRESENT, True))
    c.now["playing"] = "{1}"
    c.eps[1].state = D.ACTIVE
    return c.sw.refresh()


def test_device_starts_playing(start, on_devices, started_playing, check):
    sw, told, changed = start.sw, on_devices.told, started_playing
    # was selftest.py:218
    check("core: a device starting to play is told (with playing_changed), its new endpoint remembered",
          changed and ("devices", True) in told and sw.record(BUDS)["guids"] == ["{1}", "{2}"]
          and sw.playing_key == BUDS, (told, sw.record(BUDS)))


def test_nothing_changed(start, started_playing, check):
    # was selftest.py:221
    check("core: nothing changed, nothing told", not start.sw.refresh())


def test_profile_removed(start, on_devices, check):
    sw, sam = start.sw, on_devices.sam
    file = os.path.join(sw.apo.profiles, sw.profiles()[sam]["file"])
    sw.remove_profile(sam)
    # was selftest.py:224
    check("core: removing a profile takes it off every device (those it was on are off) and deletes its copy",
          sw.record(BUDS)["active"] is None and sam not in sw.record(EP)["profiles"] and not os.path.exists(file))


def test_rename_to_a_name_in_use(start, imported, check):
    sw, again = start.sw, imported.again
    sw.rename_profile(again, "EarPods")
    # was selftest.py:227
    check("core: a rename to a name in use gets its own", sw.profile_name(again) == "EarPods (2)")


def test_settings_read_back(start, on_devices, started_playing, check):
    c = start
    sw2 = core.Switcher(c.data, Apo(c.conf), endpoints=lambda: list(c.eps), playing=lambda: "{1}")
    # was selftest.py:229
    check("core: settings saved and read back",
          sw2.record(EP)["active"] == on_devices.ear and sw2.record(BUDS)["guids"] == ["{1}", "{2}"])


def test_setting_up_apo(start, check):
    sw = start.sw
    off = sw.set_up_apo()
    # was selftest.py:231
    check("core: setting up APO", off == ["Include: EarPods.txt"] and sw.apo.set_up())


def test_without_apo(start, check):
    c = start
    gone = core.Switcher(os.path.join(c.top, "d2.json"), Apo(os.path.join(c.top, "nowhere")), endpoints=lambda: [],
                         playing=lambda: None)
    try:
        gone.import_profile(os.path.join(c.conf, "EarPods.txt"))
        said = ""
    except OSError as e:
        said = str(e)
    # was selftest.py:239
    check("core: without APO, importing says so and nothing is written", "isn't installed" in said and not gone.apply(), said)
