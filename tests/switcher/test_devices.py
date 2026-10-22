"""Playback devices (switcher\\devices.py): Windows' endpoints grouped as the devices you'd name (Bluetooth's
Hands-Free and an old copy of a device join it), this PC's playback devices read from the registry, and the device
playing now asked of Windows' audio service. Everything here only reads, as before: this PC's devices are taken as
they are, and a PC with no playback device at all passes too. Moved from selftest.py's device_checks."""
import winreg

import pytest

from switcher import devices as D


def test_endpoints_grouped(check):
    E = D.Endpoint
    eps = [E("{1}", "Headphones", "Buds", D.NOT_PRESENT, True), E("{2}", "Headset", "Buds Hands-Free", D.NOT_PRESENT, False),
           E("{3}", "Speakers", "Realtek", D.NOT_PRESENT, False), E("{4}", "Speakers", "Realtek", D.ACTIVE, True),
           E("{5}", "Headset", "EarPods", D.ACTIVE, False)]
    devs = D.group(eps)
    got = [(d.label, d.guids, d.connected, d.apo) for d in devs]
    # was selftest.py:73
    check("devices: Bluetooth's Hands-Free and an old copy of a device join it; connected ones first; APO is judged "
          "on the endpoints in use, not Hands-Free", got == [
              ("Headset (EarPods)", ["{5}"], True, False), ("Speakers (Realtek)", ["{3}", "{4}"], True, True),
              ("Headphones (Buds)", ["{1}", "{2}"], False, True)], got)


@pytest.fixture(scope="module")
def this_pc():
    """This PC's playback endpoints, read once (selftest.py line 77: read only). The device playing is then compared
    with this same list, as the old check did."""
    return D.endpoints()


def test_this_pc_read(this_pc, check):
    eps = this_pc
    try:  # (Windows' list of playback devices: when it has any, endpoints() must find them)
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\MMDevices\Audio\Render") as k:
            listed = winreg.QueryInfoKey(k)[0]
    except OSError:
        listed = 0
    # was selftest.py:84
    check("devices: this PC's playback devices are read", isinstance(eps, list) and all(e.guid.startswith("{") for e in eps)
          and (eps or not listed), (len(eps), listed))


def test_playing_is_the_default(this_pc, check):
    eps = this_pc
    playing = D.playing()  # (Windows' default playback device, through comtypes: read only)
    # was selftest.py:87
    check("devices: the device playing is Windows' default one, one of this PC's (or none)",
          playing is None or (playing.startswith("{") and any(e.guid == playing for e in eps)), playing)
