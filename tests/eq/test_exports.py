"""The EQ files (eq\\exports.py): the text of each EQ app's file (Equalizer APO, SoundSource, Poweramp, USB Audio
Player PRO, Voicemeeter, Rockbox, the convolution WAV), what each app can't hold refused and said, the notes on how
much an app's limits change the EQ, your filters read from pasted text, filters that can't be used named, file names,
and every file written in one step. Moved from eq_checks.py's module_checks and review2_maths_checks (the names and
the conditions as they were)."""
import os
import types

import pytest

from eq import engines, exports, settings
from helpers.checks import raises  # (eq_checks.py's raises, line 50: the message of a ValueError, or None)


def shelf_and_peak():
    """F in the old checks (eq_checks.py line 164): a low shelf and a peak. Made new for each test (no function here
    changes the filters it's given, so this is the same as the old checks' one list)."""
    return [{"type": "LSQ", "freq": 105, "gain": 3.5, "q": 0.7}, {"type": "PK", "freq": 1000, "gain": -2.3, "q": 1.41}]


def test_apo_text(eq_cfg, check):
    cfg, F = eq_cfg, shelf_and_peak()
    # was eq_checks.py:165
    check("formats: Equalizer APO text", exports.apo_text(cfg, F, -3.5).splitlines()[1] == "Filter 1: ON LSC Fc 105 Hz Gain 3.5 dB Q 0.700")


def test_uapp_refuses_shelves(check):
    F = shelf_and_peak()
    notes = []
    # was eq_checks.py:167
    check("formats: USB Audio Player PRO refuses shelves (and says why)", exports.uapp_xml(F, 0, "x", notes) is None and notes)


def test_preamp_rounded_down(eq_cfg, check):
    cfg = eq_cfg
    # was eq_checks.py:168
    check("formats: pre-amp rounded down", exports.preamp_value(cfg, -3.55) == -3.6)


def test_soundsource_text(eq_cfg, check):
    cfg, F = eq_cfg, shelf_and_peak()
    # was eq_checks.py:169
    check("formats: SoundSource text", exports.soundsource_text(cfg, F, -3.5).splitlines()[1] == "Filter 1: ON LS Fc 105 Hz Gain 3.5 dB Q 0.700")


def test_soundsource_refuses_more_than_32(eq_cfg, check):
    cfg, F = eq_cfg, shelf_and_peak()
    notes = []
    # was eq_checks.py:171
    check("formats: SoundSource refuses more than 32 filters (and says why)",
          exports.soundsource_text(cfg, F * 17, 0, notes) is None and notes, notes)


def test_frequency_decimals_kept(eq_cfg, check):
    cfg = eq_cfg
    # was eq_checks.py:173
    check("formats: a frequency typed with decimals keeps them in the file",
          "Fc 100.25 Hz" in exports.apo_text(cfg, [{"type": "PK", "freq": 100.25, "gain": 1, "q": 1}], -1))


def test_every_file_holds_the_methods_values(check):
    grid = [{"type": "PK", "freq": 20 + 37 * i, "gain": round(-6 + 0.7 * i, 1), "q": round(0.5 + 0.37 * i, 2)} for i in range(16)]
    grid.insert(0, {"type": "LSQ", "freq": 105, "gain": 4.5, "q": 0.71})
    same = {a: exports.for_app(a, grid)[0] == grid for a in ("apo", "soundsource", "poweramp", "uapp", "voicemeeter")}
    # was eq_checks.py:178
    check("formats: every file holds the EQ methods' values (whole Hz, 0.1 dB, Q 0.01) exactly, but Rockbox's Q",
          all(same.values()) and exports.for_app("rockbox", grid)[0] != grid, same)


def test_rockbox_q_limit_said(check):
    notes = []
    exports.rockbox_cfg([{"type": "PK", "freq": 6000, "gain": 6, "q": 8.44}], -6, notes)
    # was eq_checks.py:182
    check("formats: Rockbox says how much its Q limit (6.4) changes the EQ", any("Q goes from 0.1 to 6.4" in n for n in notes), notes)


def test_poweramp_gain_limit_said(check):
    notes = []
    exports.poweramp_json([{"type": "PK", "freq": 1000, "gain": 16, "q": 1}], -16, "x", notes)
    # was eq_checks.py:185
    check("formats: Poweramp says how much its gain limit changes the EQ, and no clipping note (the cut is safe)",
          len(notes) == 1 and "+15 dB" in notes[0], notes)


def test_small_preamp_by_hand_not_blamed(eq_cfg, check):
    cfg = eq_cfg
    notes = []
    exports.apo_text(cfg, [{"type": "PK", "freq": 1000, "gain": 6, "q": 1}], -3, notes)
    # was eq_checks.py:189
    check("formats: a pre-amp set too small by hand isn't blamed on the app", notes == [], notes)


def test_your_filters_read(check):
    got = exports.parse_filters("Preamp: -6 dB\nFilter 1: ON LSC Fc 105 Hz Gain 5,5 dB Q 0.70\nFilter 2: OFF PK Fc 2000 Hz "
                                "Gain 3 dB Q 2\nFilter: ON HS Fc 8000 Hz Gain -3 dB\n# mine\n200 3 1\nLSQ 50 2 0.6")
    # was eq_checks.py:192
    check("formats: your filters read from Equalizer APO lines and frequency-gain-Q lines (off ones skipped)",
          [(f["type"], f["freq"], f["gain"], f["q"]) for f in got]
          == [("LSQ", 105, 5.5, 0.7), ("HSQ", 8000, -3, 0.71), ("PK", 200, 3, 1), ("LSQ", 50, 2, 0.6)], got)


def test_rockbox_fills_ten_bands(check):
    F = shelf_and_peak()
    rb = exports.rockbox_cfg(F, -3.5).splitlines()
    # was eq_checks.py:196
    check("formats: Rockbox fills all 10 bands (tenths)", len(rb) == 12 and rb[1] == "eq precut: 35"
          and rb[2] == "eq low shelf filter: 105, 7, 35" and rb[3] == "eq peak filter 1: 1000, 14, -23", rb)


def test_voicemeeter_refuses_more_than_6(check):
    F = shelf_and_peak()
    notes = []
    # was eq_checks.py:199
    check("formats: Voicemeeter refuses more than 6 filters (and says why)", exports.voicemeeter_xml(F * 4, 0, notes) is None and notes)


def test_voicemeeter_cells(check):
    F = shelf_and_peak()
    notes = []  # (the old check passed the list the refusal above had filled: what's in it doesn't change the file)
    vm = exports.voicemeeter_xml(F, -3.5, notes)
    # was eq_checks.py:201
    check("formats: Voicemeeter: 8 channels x 6 cells, unused off", vm.count("<Bus ") == 48 and vm.count('EQon="1"') == 16, vm[:200])


@pytest.fixture(scope="module")
def impulse():
    """The filters F as an impulse response at 48 kHz (eq_checks.py lines 202-203): one test checks its sound, the
    next its WAV."""
    fs = 48000
    return exports.impulse_response(shelf_and_peak(), -3.5, fs), fs


def test_convolution_sounds_like_the_filters(impulse, check):
    h, fs = impulse
    F = shelf_and_peak()
    spec = engines.np.fft.rfft(h, 1 << 20)
    fr = engines.np.fft.rfftfreq(1 << 20, 1 / fs)
    fq = engines.np.geomspace(20, 20000, 200)
    off = engines.np.interp(fq, fr, 20 * engines.np.log10(engines.np.abs(spec))) - engines.eq_gain(fq, F, fs) + 3.5
    # was eq_checks.py:208
    check("formats: convolution impulse response sounds like the filters (within 0.05 dB)", abs(off).max() < 0.05, abs(off).max())


def test_convolution_wav(impulse, check):
    h, fs = impulse
    wav = exports.wav_bytes(h, fs)
    # was eq_checks.py:210
    check("formats: convolution WAV: float, stereo, the rate", wav[:4] == b"RIFF" and wav[8:12] == b"WAVE"
          and engines.np.frombuffer(wav[20:28], "<u2").tolist()[:2] == [3, 2]
          and int.from_bytes(wav[24:28], "little") == fs)


def test_convolution_refuses_too_high(check):
    notes = []
    # was eq_checks.py:214
    check("formats: convolution refuses a filter above the sample rate's limit (and says why)",
          exports.impulse_response([{"type": "PK", "freq": 23000, "gain": 2, "q": 1}], -2, 44100, notes) is None and notes)


def test_filters_not_numbers_named(check):
    # was eq_checks.py:216
    check("formats: filters that aren't numbers are named", raises(exports.clean_filters, [{"freq": 100, "gain": "x", "q": 1}])
          == "Filter 1: its gain isn't a number.")


def test_filters_outside_limits_named(check):
    # was eq_checks.py:218
    check("formats: filters outside the filter table's limits are named (Q 0 would break an EQ app)",
          raises(exports.clean_filters, [{"freq": 100, "gain": 1, "q": 0}]) == "Filter 1: its Q (0) is outside 0.03 to 27.")


def test_long_names_keep_the_method(check):
    long_name = "D" * 60 + " to " + "T" * 60 + " - best fit 10f"
    b = exports.file_base(long_name)
    # was eq_checks.py:222
    check("formats: long file names keep the method", len(b) <= exports.NAME_MAX and b.endswith(" - best fit 10f"), b)


def test_retry_filters_written_as_they_are(check):
    # Retry from these filters keeps them exactly (they were written like a saved file: Q to the Q decimals, gain 0.1 dB)
    own = [{"type": "PK", "freq": 105.5, "gain": 3.25, "q": 1.26, "enabled": True},
           {"type": "LSQ", "freq": 80, "gain": -1.05, "q": 0.707, "enabled": True}]
    # was eq_checks.py:253
    check("retry: your filters written as they are (Q 1.26 stays 1.26 with Q decimals 1)",
          exports.parse_filters(exports.filters_text(own)) == [dict(f) for f in own], exports.filters_text(own))


def test_uapp_preamp_too_low_said(check):
    notes = []
    exports.uapp_xml([{"type": "PK", "freq": 100, "gain": 15, "q": 1}, {"type": "PK", "freq": 120, "gain": 12, "q": 1}],
                     -24.0, "x", notes)
    # was eq_checks.py:2197
    check("files: USB Audio Player PRO's file says when its pre-amp can't go low enough (it can clip)",
          any("can clip" in n for n in notes), notes)


def test_tiny_q_written_as_smallest_step(check):
    # saved files: a Q never rounds down to 0 (Q decimals 1 wrote "Q 0.0")
    c1 = settings.with_auto({"export": {"q_decimals": 1}})
    notes_q = []
    q_text = exports.apo_text(c1, [{"type": "PK", "freq": 1000, "gain": 2, "q": 0.04}], -2.0, notes_q)
    # was eq_checks.py:335
    check("formats: a Q under half a step is written as the smallest step, not 0 (and said)",
          "Q 0.1" in q_text and "Q 0.0" not in q_text and notes_q, (q_text, notes_q))


def test_apo_width_and_slopes_read(check):
    # Equalizer APO's width in octaves and shelf slopes are read; its other filter types are named
    apo_lines = ("Filter 1: ON PK Fc 3000 Hz Gain -2 dB BW Oct 1\nFilter 2: ON LSC 12 dB Fc 100 Hz Gain 4 dB Q 0.7\n"
                 "Filter 3: OFF LP Fc 18000 Hz")
    read_apo = exports.parse_filters(apo_lines)
    # was eq_checks.py:341
    check("formats: APO's \"BW Oct\" and shelf slopes are read (an OFF line of another type is skipped)",
          [(f["type"], f["freq"], round(f["q"], 3)) for f in read_apo] == [("PK", 3000, 1.414), ("LSQ", 100, 0.7)], read_apo)


def test_other_apo_type_named(check):
    # was eq_checks.py:343
    check("formats: another APO filter type is named as not supported",
          "“HP” filters aren't supported" in (raises(exports.parse_filters, "Filter 1: ON HP Fc 30 Hz") or ""))


def test_unknown_format_refused(eq_cfg, check):
    cfg = eq_cfg
    # was eq_checks.py:346
    check("formats: an unknown file format is refused by name",
          raises(exports.file_names, cfg, "x", ["APO"]) == "Unknown file format: APO")


@pytest.fixture(scope="module")
def atomic(tmp_path_factory, sample_curves):
    """eq_checks.py lines 349-357: every file format switched on, an EQ written into a folder of its own (made by
    exports.write, as the old checks' "Saved EQs\\atomic" was) with textfile.write_atomic wrapped to note each file's
    name, and the report written beside it. The next two tests use what it leaves: the names written in one step,
    and the folder with its files."""
    import textfile
    curves = sample_curves[0]
    cfg = settings.with_auto({})
    out_tmp = os.path.join(str(tmp_path_factory.mktemp("saved_eqs")), "atomic")
    names, real_write = [], textfile.write_atomic
    all_on = settings.with_auto({"export": {k: True for k in exports.FORMATS}})
    with pytest.MonkeyPatch.context() as m:
        m.setattr(textfile, "write_atomic", lambda p, text, **k: (names.append(os.path.basename(p)), real_write(p, text, **k)))
        wrote, _ = exports.write(all_on, [{"type": "PK", "freq": 1000, "gain": 2, "q": 1}], -2.0, "Atomic", out_dir=out_tmp)
        exports.write_report(curves, cfg["scoring"]["band_hz"], "Dev", "Tgt", 1, [], out_dir=out_tmp)
    return types.SimpleNamespace(out_tmp=out_tmp, all_on=all_on, names=names, wrote=wrote)


def test_every_file_written_in_one_step(atomic, check):
    wrote = atomic.wrote
    # every file written in one step (Equalizer APO reloads a file it uses as soon as it changes)
    # was eq_checks.py:358
    check("formats: every file (the WAV and the report too) is written in one step",
          sorted(atomic.names) == sorted([os.path.basename(p) for p in wrote.values()] + ["Dev to Tgt - report.html"]),
          atomic.names)


def test_not_asked_about_a_file_it_wont_write(atomic, check):
    # not asked about a file this EQ can't be written in (UAPP holds no shelves)
    out_tmp, all_on = atomic.out_tmp, atomic.all_on
    shelf = [{"type": "LSQ", "freq": 100, "gain": 3, "q": 0.7}]
    open(os.path.join(out_tmp, "Atomic - UAPP.xml"), "a").close()
    asked = exports.existing(all_on, "Atomic", ["apo", "uapp"], out_dir=out_tmp, filters=shelf)
    # was eq_checks.py:364
    check("formats: saving doesn't ask about an app's file it won't write", asked == ["Atomic - filters.txt"], asked)
