"""A window of a test's own on one stand-in device, for tests\\ui. Before the test audit of 2026-11-25 (candidate 59)
four tests made it each in their own words. The app it talks to: helpers.stand_in_app.StubApp (the stub_app
fixture).

headset()                a stand-in device: the headset "{5}", playing, without APO on it (a new Endpoint each time).
switcher(top, eps=None)  a Switcher on <top>\\s.json, the devices eps (default: headset() alone; the first one plays,
                         none with an empty list), and no Equalizer APO folder (<top>\\no-apo: the window asks APO
                         nothing in the background), on Devices.
window(stub_app, top, eps=None)  a window on that Switcher, not shown.
"""
import os


def headset():
    from switcher import devices as D
    return D.Endpoint("{5}", "Headset", "EarPods", D.ACTIVE, False)


def switcher(top, eps=None):
    from switcher import core
    from switcher.apo import Apo
    eps = [headset()] if eps is None else eps
    sw = core.Switcher(os.path.join(str(top), "s.json"), Apo(os.path.join(str(top), "no-apo")),
                       endpoints=lambda: eps, playing=lambda: eps[0].guid if eps else None)
    sw.s["page"] = "devices"
    return sw


def window(stub_app, top, eps=None):
    from ui.window import Window
    return Window(switcher(top, eps), stub_app)
