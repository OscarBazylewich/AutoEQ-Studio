"""Your playback devices as Windows lists them, which of them Equalizer APO is installed on, and which one is playing
now. Everything here only reads: the registry's list of audio endpoints, APO's list of the endpoints it's installed on,
and Windows' audio service for the default playback device.

A device here is what you'd call one. Windows can list one as several endpoints: Bluetooth earbuds twice (music, and
"… Hands-Free" for calls), and an old copy of a device can linger beside the new one (the same name, not present).
Those are one Device with several endpoint ids (guids), and APO's "Device:" section for it names them all.
"""
import _ctypes
import ctypes
import winreg
from dataclasses import dataclass, field

RENDER = r"SOFTWARE\Microsoft\Windows\CurrentVersion\MMDevices\Audio\Render"
APO_CHILDREN = r"SOFTWARE\EqualizerAPO\Child APOs"  # (one key per endpoint APO's Configurator installed it on)
NAME = "{a45c254e-df1c-4efd-8020-67d146a850e0},2"  # what the output is: "Headphones", "Speakers", "Headset"
CONN = "{b3f8fa53-0004-438e-9003-51a46e139bfc},6"  # what it's on: "EarPods", "Realtek(R) Audio", a Bluetooth name
ACTIVE, DISABLED, NOT_PRESENT, UNPLUGGED = 1, 2, 4, 8
HANDS_FREE = " Hands-Free"


@dataclass
class Endpoint:
    guid: str            # "{d3bfcd09-14ce-41c7-b4f5-e83278716021}" (lower case, as Windows names its key)
    name: str            # "Headset"
    conn: str            # "EarPods"
    state: int           # ACTIVE, NOT_PRESENT, UNPLUGGED (DISABLED ones aren't listed)
    apo: bool = False    # Equalizer APO is installed on it


@dataclass
class Device:
    key: str             # "Headset|EarPods": how the settings know it (stays the same when its endpoints change)
    name: str
    conn: str
    endpoints: list = field(default_factory=list)

    @property
    def label(self):
        """As Windows' Sound settings show it: "Headset (EarPods)"."""
        return f"{self.name} ({self.conn})" if self.conn else self.name

    @property
    def guids(self):
        return [e.guid for e in self.endpoints]

    @property
    def connected(self):
        return any(e.state == ACTIVE for e in self.endpoints)

    @property
    def apo(self):
        """Is APO installed where it matters: on the endpoints connected now (else on any), not counting a Bluetooth
        device's Hands-Free one (calls: music never plays there)."""
        main = [e for e in self.endpoints if not e.conn.endswith(HANDS_FREE)] or self.endpoints
        now = [e for e in main if e.state == ACTIVE] or main
        return all(e.apo for e in now)


def _value(key, name):
    try:
        return winreg.QueryValueEx(key, name)[0]
    except OSError:
        return None


def apo_endpoints():
    """The endpoint guids Equalizer APO is installed on (lower case)."""
    out = set()
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, APO_CHILDREN) as k:
            for i in range(winreg.QueryInfoKey(k)[0]):
                out.add(winreg.EnumKey(k, i).lower())
    except OSError:
        pass
    return out


def endpoints():
    """Every playback endpoint Windows knows that could be used (not disabled ones, nor the hidden ones whose state
    carries Windows' extra flags), with whether APO is on it."""
    out, apo = [], apo_endpoints()
    try:
        root = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, RENDER)
    except OSError:
        return out
    with root:
        for i in range(winreg.QueryInfoKey(root)[0]):
            guid = winreg.EnumKey(root, i)
            try:
                with winreg.OpenKey(root, guid) as k:
                    state = _value(k, "DeviceState")
                with winreg.OpenKey(root, guid + r"\Properties") as p:
                    name, conn = _value(p, NAME), _value(p, CONN)
            except OSError:
                continue
            if not isinstance(state, int) or state not in (ACTIVE, NOT_PRESENT, UNPLUGGED) or not name:
                continue
            out.append(Endpoint(guid.lower(), str(name), str(conn or ""), state, guid.lower() in apo))
    return out


def group(eps):
    """Endpoints as devices: the same name and connection is one device; a "… Hands-Free" endpoint joins the device
    it belongs to (the same connection without " Hands-Free"). Connected devices first, then by name."""
    devs = {}
    for e in sorted(eps, key=lambda e: e.conn.endswith(HANDS_FREE)):  # (the music endpoints first)
        key = f"{e.name}|{e.conn}"
        if e.conn.endswith(HANDS_FREE):
            base = e.conn[:-len(HANDS_FREE)]
            owner = next((d for d in devs.values() if d.conn == base), None)
            if owner:
                owner.endpoints.append(e)
                continue
        devs.setdefault(key, Device(key, e.name, e.conn)).endpoints.append(e)
    return sorted(devs.values(), key=lambda d: (not d.connected, d.label.lower()))


# ---------------------------------------------------------------- the device playing now
_enumerator = None


def _com():
    """Windows' audio device service (IMMDeviceEnumerator), made once."""
    global _enumerator
    if _enumerator is None:
        import comtypes
        from comtypes import GUID, IUnknown, COMMETHOD, HRESULT
        from ctypes import POINTER, c_uint
        from ctypes.wintypes import LPWSTR

        class IMMDevice(IUnknown):
            _iid_ = GUID("{D666063F-1587-4E43-81F1-B948E807363F}")
            _methods_ = [COMMETHOD([], HRESULT, "Activate"), COMMETHOD([], HRESULT, "OpenPropertyStore"),
                         COMMETHOD([], HRESULT, "GetId", (["out"], POINTER(LPWSTR), "id")),
                         COMMETHOD([], HRESULT, "GetState")]

        class IMMDeviceEnumerator(IUnknown):
            _iid_ = GUID("{A95664D2-9614-4F35-A746-DE8DB63617E6}")
            _methods_ = [COMMETHOD([], HRESULT, "EnumAudioEndpoints"),
                         COMMETHOD([], HRESULT, "GetDefaultAudioEndpoint", (["in"], c_uint, "flow"),
                                   (["in"], c_uint, "role"), (["out"], POINTER(POINTER(IMMDevice)), "device"))]

        try:
            comtypes.CoInitialize()
        except OSError:
            pass  # (already set up on this thread, e.g. by Qt)
        _enumerator = comtypes.CoCreateInstance(GUID("{BCDE0395-E52F-467C-8E3D-C4579291692E}"),
                                                IMMDeviceEnumerator, comtypes.CLSCTX_ALL)
    return _enumerator


def playing():
    """The guid of the device playing now (Windows' default playback device, lower case), or None (none, or Windows'
    audio service didn't answer)."""
    try:
        dev_id = _com().GetDefaultAudioEndpoint(0, 1)  # (render, multimedia: where music and videos play)
        dev_id = dev_id.GetId()
    except (OSError, ctypes.ArgumentError, ValueError):
        return None
    except _ctypes.COMError:  # (no playback device at all: E_NOTFOUND; or the audio service restarted)
        global _enumerator
        _enumerator = None
        return None
    return dev_id[dev_id.rfind(".") + 1:].lower() if dev_id else None
