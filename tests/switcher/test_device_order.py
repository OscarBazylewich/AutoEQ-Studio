"""The devices' order in lists (Switcher.order, 2026-10-27: the Devices screen and Use on device): connected ones
first, then A to Z by the name shown (your name for a device, or Windows'), numbers as numbers. It was by Windows'
name, so a device you'd renamed sat out of order. On a stand-in APO folder and settings in the test's own folder."""
import os

from helpers import apo as stand_in
from switcher import core
from switcher import devices as D
from switcher.apo import Apo


def test_connected_first_then_by_the_name_shown(tmp_path, check):
    top = str(tmp_path)
    eps = [D.Endpoint("{1}", "Speakers", "Realtek", D.ACTIVE, True),
           D.Endpoint("{2}", "Headphones", "Buds", D.NOT_PRESENT, True),
           D.Endpoint("{3}", "Headphones", "KA17", D.ACTIVE, True),
           D.Endpoint("{4}", "Headphones", "Dongle 10", D.ACTIVE, True),
           D.Endpoint("{5}", "Headphones", "Dongle 9", D.ACTIVE, True)]
    sw = core.Switcher(os.path.join(top, "s.json"), Apo(stand_in.fake_apo(top)), endpoints=lambda: eps,
                       playing=lambda: "{1}")
    sw.set_nickname("Headphones|KA17", "Zz amp")
    names = [core.shown(sw.record(k)) for k in sorted((d.key for d in sw.devices), key=sw.order)]
    check("core: devices are listed connected ones first, then A to Z by the name shown (your name for one too), "
          "numbers as numbers", names == ["Headphones (Dongle 9)", "Headphones (Dongle 10)", "Speakers (Realtek)",
                                          "Zz amp", "Headphones (Buds)"], names)
