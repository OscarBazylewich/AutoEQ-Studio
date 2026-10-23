"""Use on device on Make an EQ (ui\\eq_page.py over switcher\\core.py): the result becomes the device's profile,
switched on, in Equalizer APO's file; Try for 5 minutes on plays it on the device from APO's file (not as a profile)
and its end puts the device's own EQ back; with every device disconnected there is nothing to try it on. Moved from
eq_checks.py's ui_checks and try_checks: one page for the file (the eq_screen fixture: a stand-in APO folder in the
test's own folder and one stand-in device, Headset (EarPods), connected and playing), with the EQ the old checks had
on the card: a quick run saved as "UI check" and brought back with History's Show."""
import os

import pytest
from PySide6.QtWidgets import QMenu

from helpers import eqpage
from switcher import devices as D


def _read(path):
    with open(path) as fh:
        return fh.read()


@pytest.fixture(scope="module")
def history_eq(eq_screen):
    """The History EQ on the result card (eq_checks.py lines 1528-1532, 1573-1574 and 1583: a quick run, saved as
    "UI check", brought back with History's Show)."""
    page = eq_screen.page
    page.choose_app("apo")  # (your EQ app as the old checks had chosen it before their run, line 1491)
    eqpage.quick_run(eq_screen)  # (raises when the run makes no result)
    entry = eqpage.save_result(eq_screen, "UI check")
    eqpage.show_from_history(eq_screen, entry)
    return entry


def test_use_on_device(eq_screen, history_eq, check):
    sw, said = eq_screen.sw, eq_screen.said
    rec = eqpage.use_on_device(eq_screen, "UI check")  # (lines 1616-1619: the File name yours, Use on the device)
    sw_text = _read(os.path.join(eq_screen.apo_config, "AutoEQ Studio", "switcher.txt"))
    # was eq_checks.py:1622
    check("ui: Use on device makes the result the device's profile, switched on, in APO's file",
          rec["active"] and sw.profile_name(rec["active"]) == "UI check" and "Include: profiles\\UI check.txt" in sw_text
          and "is now on for Headset (EarPods)" in said[-1], (rec, said[-1:]))


def test_try_with_every_device_disconnected(eq_screen, check, monkeypatch):
    # (the old check spoke only when no device was connected, and the stand-in device is: here it is unplugged for
    # this test, so the check runs, then plugged in again for the next)
    sw = eq_screen.sw
    monkeypatch.setattr(sw, "_endpoints", lambda: [D.Endpoint("{5}", "Headset", "EarPods", D.UNPLUGGED, True)])
    try:
        sw.refresh(quiet=True)
        key = next((d.key for d in sw.devices if d.connected), None)  # (line 2609)
    finally:
        monkeypatch.undo()
        sw.refresh(quiet=True)
    # was eq_checks.py:2611
    check("try: Try for 5 minutes on a device (skipped: the test's devices are all disconnected)", key is None, key)


def test_try_for_5_minutes(eq_screen, history_eq, check):
    page, sw = eq_screen.page, eq_screen.sw
    key = next((d.key for d in sw.devices if d.connected), None)  # (line 2609)
    if key is None:
        raise RuntimeError("the stand-in device isn't connected: Try needs a connected device")
    # (lines 2613-2619: the Use on device menu filled, the EQ tried on the device, the trial ended)
    page._fill_use_menu()
    sub = next((a.menu() for a in page.use_menu.actions() if a.menu() is not None), None)
    profiles = len(sw.profiles())
    page.try_on(key)
    swt = os.path.join(sw.apo.config, "AutoEQ Studio", "switcher.txt")
    on = (sw.trial and sw.trial["key"], "_trying.txt" in _read(swt), len(sw.profiles()))
    sw.end_trial()
    # was eq_checks.py:2620
    check("try: Use on device › Try for 5 minutes on plays the result on that device (APO's file), not as a profile; "
          "its end puts the device's own EQ back", isinstance(sub, QMenu) and sub.actions() and on == (key, True, profiles)
          and sw.trial is None and "_trying.txt" not in _read(swt), (on, sub))
