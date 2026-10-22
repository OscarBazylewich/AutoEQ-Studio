"""Listen's sound (ui\\audio.py), made without a sound card (Engine.render: no Qt, no page): each version through its
own filters, level matching, a switch faded (no click), a different version in each ear, a filter the sound card
can't play left out, the music loop; and the review's fixes: a changed EQ crossfaded, the volume glided. Moved from
eq_checks.py's listen_checks, review_checks and review_low_checks.

The first four tests are a chain on one engine, as the old checks were (listen_checks, lines 2894-2920): the engine
is the module's `engine` fixture, and the tests run in the order written."""
import numpy as np
import pytest

from ui import audio

COVERS = ("eq.engines",)  # (each version's filters as biquads, and their loudness: reached through ui.audio)

BOOST = [{"type": "PK", "freq": 1000, "gain": 6, "q": 1}]


def rms(x):
    """A sound's level in dB (eq_checks.py line 2892)."""
    return 20 * np.log10(np.sqrt(np.mean(np.asarray(x, float) ** 2)) + 1e-12)


@pytest.fixture(scope="module")
def engine():
    """One engine for the chain below (eq_checks.py lines 2894-2899): at full volume, EQ off and +6 dB at 1 kHz, no
    level matching, a 1 kHz tone."""
    eng = audio.Engine(48000)
    eng.volume_db = 0
    eng.set_versions([("off", "EQ off", []), ("sel", "+6 dB at 1 kHz", BOOST)])
    eng.set_level_match(False)
    eng.set_source("tone")
    eng.tone_hz = 1000
    return eng


def test_each_version_its_own_filters(engine, check):
    eng = engine
    lv = {}
    for k in ("off", "sel"):
        eng.active = k
        eng.render(4800)
        lv[k] = rms(eng.render(4800)[:, 0])
    # was eq_checks.py:2905
    check("listen: each version plays through its own filters (+6 dB at 1 kHz, turned down by its boost: the same level)",
          abs(lv["off"] - lv["sel"]) < 0.1 and abs(lv["off"] + 16.99) < 0.1, lv)


def test_level_matched(engine, check):
    eng = engine
    eng.set_level_match(True)
    g = {s["key"]: s["gain_db"] for s in eng.slots}
    peak, loud = audio.levels(BOOST, 48000)
    # was eq_checks.py:2910
    check("listen: level-matched, every version at the same A-weighted loudness, none above full scale",
          abs((g["off"] - g["sel"]) - loud) < 0.01 and max(g["sel"] + peak, g["off"]) <= 1e-9, (g, peak, loud))


def test_switch_fades_then_silent(engine, check):
    eng = engine
    eng.active = "nothing"
    y = eng.render(4800)[:, 0]
    # was eq_checks.py:2914
    check("listen: a switch fades over a block (no click), then it's silent",
          rms(y[:1200]) > rms(y[-1200:]) + 6 and abs(y[-1]) < 0.01 and rms(eng.render(4800)) < -200,
          (rms(y[:1200]), rms(y[-1200:])))


def test_version_in_each_ear(engine, check):
    eng = engine
    eng.ears, eng.left, eng.right = "split", "off", "sel"
    eng.render(4800)
    y = eng.render(4800)
    # was eq_checks.py:2919
    check("listen: a different version in each ear (left EQ off, right the EQ: louder at 1 kHz, level-matched)",
          rms(y[:, 1]) - rms(y[:, 0]) > 1, (rms(y[:, 0]), rms(y[:, 1])))


def test_filter_above_card_and_music_loop(check):
    # was eq_checks.py:2921
    check("listen: a filter above what the sound card can play is left out; the music loop at 44.1 and 48 kHz",
          len(audio.sos_of([{"freq": 30000, "gain": 3, "q": 1}], 48000)) == 0
          and all(audio.groove(sr).shape == (int(np.ceil(sr * 9.6)), 2) for sr in (44100, 48000)))


def test_changed_eq_crossfades(check):
    # (its own engine, eq_checks.py lines 1728-1738: the EQ heard, then its filter changed while it plays)
    eng = audio.Engine(48000)
    eng.volume_db = 0
    eng.set_versions([("off", "EQ off", []), ("sel", "EQ", [{"type": "PK", "freq": 1000, "gain": 6, "q": 1}])])
    eng.set_level_match(False)
    eng.set_source("tone")
    eng.tone_hz = 1000
    eng.active = "sel"
    for _ in range(3):
        eng.render(4800)
    eng.set_versions([("off", "EQ off", []), ("sel", "EQ", [{"type": "PK", "freq": 1000, "gain": 5, "q": 1}])])
    y = eng.render(480)[:, 0]
    peaks = np.abs(y).reshape(-1, 48).max(1)
    # was eq_checks.py:1740
    check("review: changing the EQ being heard crossfades to the new one (no dip), and the old one goes after",
          peaks.min() > 0.9 * peaks.max() and not any(s.get("fading") for s in eng.slots), np.round(peaks, 3))


def test_volume_glides(check):
    # (its own engine, eq_checks.py lines 1935-1943: a tone at -40 dB, then the volume turned up to 0 dB)
    eng = audio.Engine(48000)
    eng.set_versions([("off", "EQ off", [])])
    eng.set_source("tone")
    eng.tone_hz = 1000
    eng.active, eng.volume_db = "off", -40
    for _ in range(3):
        eng.render(4800)
    eng.volume_db = 0
    y = np.abs(eng.render(4800)[:, 0])
    # was eq_checks.py:1944
    check("review: Listen's volume glides to a new value over a block (no step, no click)",
          y[:200].max() < 0.2 * y[-200:].max(), (y[:200].max(), y[-200:].max()))
