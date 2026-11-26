"""The EQ apps and devices the EQ can be made for (settings "eq_app"), with each one's limits as its maker states them.

Each app is one of:
  "parametric"  filters anywhere, within the app's limits (a number of bands, gain, Q, frequency): Best fit keeps
                within them (the app becomes a layout: layouts.DEVICES "app:<key>")
  "graphic"     fixed bands: only their gains are fitted, within the app's range and steps (layouts.FIXED "app:<key>")
  "curve"       the app takes a whole response curve (a GraphicEQ line or an impulse response): any filters
  "site"        squig.link's own EQ: the Website methods make exactly what its AutoEQ makes
and says which of the app's files it takes (exports.FORMATS; None: typed in by hand from the filter table).

Limits are only what the app's maker (its source code, manual, help pages or store listing) states, with the source
in "source". A limit nobody states is left out, so the app's own measured limits (settings.LIMITS) apply there.
Checked September 2026. "approx": the band shapes (Q) aren't stated, so the fit uses the usual ones for that spacing
and the result can differ a little in the app (the ⓘ after Your EQ app says so, after "note": ui/eq_page.py).

"note" is the whole text of the ⓘ after Your EQ app for that app: one line of limits, in the user's own words (the
text survey, 2026-11-23): "Up to N" for a parametric EQ, "N fixed bands" for a graphic EQ, or "No limits". By the
user's decision it has no steps to load the EQ, no words about what the maker does not state and no end period, so
do not add them back (the sentence about band shapes of "approx" is not part of it: the page adds that one). A
number in a note that differs from the limit the fit uses (Poweramp "5–32 bands", Neutron "4–130 bands") is what the
app can be set to, not what Best fit does.

"band_sets": a graphic EQ app with more than one band count (FxSound): {count: (centre frequencies, each band's Q)},
and "band_default", the count the app starts with. Best fit fits every count in one run (engines.graphic_run) and
Best result selects one; the user selects another in Number of filters. There is no setting for the counts (the
user, 2026-11-24: no new control).

The steps to load the EQ in each app are in Help (ui/help_text_apps.py LOAD_EQ, by the key and the name of the app
here; the user, 2026-11-24): an app added, renamed or moved to another first platform here changes there too
(tests/eq_screen/test_help_tags.py compares them).
"""

PLATFORMS = ("Web", "Windows", "macOS", "Linux", "Android", "iOS", "Devices")

# The fixed-band layouts apps share (layouts.FIXED is made from these): key: (name, centre frequencies, each band's Q).
# AutoEq's presets (vendor/autoeq/constants.py PEQ_CONFIGS), and 15 bands at ISO 266's 2/3-octave centres.
BAND_LAYOUTS = {
    "graphic_10": ("10-band graphic EQ", [31.25 * 2 ** i for i in range(10)], 1.41),
    "graphic_15": ("15-band graphic EQ", [25, 40, 63, 100, 160, 250, 400, 630, 1000, 1600, 2500, 4000, 6300, 10000,
                                          16000], 2.15),
    "graphic_31": ("31-band graphic EQ", [20, 25, 31.5, 40, 50, 63, 80, 100, 125, 160, 200, 250, 315, 400, 500, 630,
                                          800, 1000, 1250, 1600, 2000, 2500, 3150, 4000, 5000, 6300, 8000, 10000,
                                          12500, 16000, 20000], 4.32),
    "spotify": ("Spotify (6 bands)", [60, 150, 400, 1000, 2400, 15000], 1.0),
}

APPS = {
    # ---------------------------------------------------------------- the web
    "squiglink": {
        "name": "squig.link (the website's EQ)", "platforms": ["Web"], "kind": "site", "file": "apo",
        "source": "https://squig.link/",
        "note": "Up to 20 bands · -20 to +20 dB (integers) · Q 0.1–5"},
    # ---------------------------------------------------------------- Windows
    "apo": {
        "name": "Equalizer APO", "platforms": ["Windows"], "kind": "parametric", "file": "apo",
        "source": "https://sourceforge.net/p/equalizerapo/wiki/Configuration%20reference/",
        "note": "No limits"},
    "peace": {
        "name": "Peace (for Equalizer APO)", "platforms": ["Windows"], "kind": "parametric", "file": "apo",
        # 31 bands: Peace wiki, Features FAQ, "Maximum number of sliders", the source below, fetched 2026-11-24.
        # ±30 dB: Peace's default "Maximum dB" (tab Sizes and Amounts of its settings), ticket 94, answer of the
        # developer of 2021-08-22, https://sourceforge.net/p/peace-equalizer-apo-extension/tickets/94/, fetched
        # 2026-11-24. The note has no "(±60 dB max)": no source of Peace states that number
        "bands": 31, "gain": (-30, 30),
        "source": "https://sourceforge.net/p/peace-equalizer-apo-extension/wiki/Features%20FAQ/",
        "note": "Up to 31 bands · ±30 dB"},
    "fxsound": {
        "name": "FxSound", "platforms": ["Windows"], "kind": "graphic", "file": None, "approx": True,
        # The band counts 5, 10, 15, 20, 31 and the default 10: fxsound-app docs/COMMAND_LINE_OPTIONS.md line 27 (--num_bands), main, fetched 2026-11-24.
        # The frequencies and the Q of each count: fxsound-app dsp/ptutil/DspUtil/GraphicEq/GraphicEqSet.cpp lines 106-250 and 430-524 (file commit 5246dbd9, 2026-08-22), fetched 2026-11-24. One Q for all bands: Q = max(1, sqrt(r)/(r-1)), r = (highest/lowest frequency)^(1/(bands-1)), at Filter Q 1.0 of FxSound (calculated; tests/eq/test_layouts.py calculates it again).
        # Valid for FxSound 1.2.14.0 and later (releases API, https://api.github.com/repos/fxsound2/fxsound-app/releases, v1.2.14.0 of 2026-08-22 changed the 10-band frequencies; fetched 2026-11-24), with Filter Q 1.0 and, at 5 or 10 bands, the band frequencies at their defaults. The shape of its filter for a Q is not confirmed ("approx").
        "band_sets": {
            5: ([62.5, 250, 1000, 4000, 16000], 1.0),
            10: ([62.5, 115.734, 214.311, 396.85, 734.867, 1360.79, 2519.84, 4666.12, 8640.48, 16000], 1.598),
            15: ([25, 40, 63, 100, 160, 250, 400, 630, 1000, 1600, 2500, 4000, 6300, 10000, 16000], 2.148),
            20: ([20, 31.5, 40, 63, 80, 125, 160, 250, 315, 500, 630, 1000, 1250, 2000, 2500, 4000, 5000, 8000, 10000,
                  16000], 2.828),
            31: (list(BAND_LAYOUTS["graphic_31"][1]), 4.333)},
        "band_default": 10,
        # ±12 dB: COMMAND_LINE_OPTIONS.md line 33 (--set_band_gain); 1 dB steps: fxsound/Source/GUI/FxEqualizer.cpp lines 48 and 98; main, fetched 2026-11-24
        "gain": (-12, 12), "step": 1,
        "source": "https://github.com/fxsound2/fxsound-app/blob/main/docs/COMMAND_LINE_OPTIONS.md",
        "note": "5, 10, 15, 20, or 31 fixed bands · ±12 dB (1 dB steps) · shared Q"},
    "sonar": {
        "name": "SteelSeries Sonar", "platforms": ["Windows"], "kind": "parametric", "file": None, "bands": 10,
        "source": "https://support.steelseries.com/hc/en-us/articles/5570622280077-How-do-I-add-or-delete-a-band-to-Sonar-Parametric-EQ",
        "note": "Up to 10 bands"},
    "voicemeeter": {
        "name": "Voicemeeter (Banana, Potato)", "platforms": ["Windows"], "kind": "parametric", "file": "voicemeeter",
        "bands": 6, "gain": (-36, 18), "freq": (20, 20000),
        "source": "https://vb-audio.com/Voicemeeter/VoicemeeterPotato_UserManual.pdf",
        "note": "Up to 6 bands per bus · 20 Hz–20 kHz · -36 to +18 dB"},
    "foobar2000": {
        "name": "foobar2000 (its equalizer)", "platforms": ["Windows"], "kind": "graphic", "file": None,
        "approx": True,
        "freqs": [55, 77, 110, 156, 220, 311, 440, 622, 880, 1245, 1760, 2489, 3520, 4978, 7040, 9956, 14080, 19912],
        "q": 2.87, "gain": (-20, 20), "step": 1,
        "source": "https://www.foobar2000.org/equalizer",
        "note": "18 fixed bands (0.5-octave) · ±20 dB (1 dB steps)"},
    # ---------------------------------------------------------------- Windows and macOS
    "roon": {
        "name": "Roon (MUSE parametric EQ)", "platforms": ["Windows", "macOS", "Linux"], "kind": "parametric",
        "file": None, "gain": (-24, 24),
        "source": "https://help.roonlabs.com/portal/en/kb/articles/dsp-engine-parametric-equalizer",
        "note": "±24 dB"},
    "boom3d": {
        "name": "Boom 3D", "platforms": ["Windows", "macOS"], "kind": "graphic", "file": None, "approx": True,
        "layout": "graphic_31",
        "source": "https://blog.globaldelight.com/boom-3d-mac/why-do-you-need-a-31-band-equalizer",
        "note": "31 fixed bands (ISO) · 20 Hz–20 kHz"},
    # ---------------------------------------------------------------- macOS
    "soundsource": {
        "name": "SoundSource", "platforms": ["macOS"], "kind": "parametric", "file": "soundsource", "bands": 32,
        "source": "https://rogueamoeba.com/support/knowledgebase/?showArticle=SoundSource-Custom-HPEQ",
        "note": "Up to 32 bands (peaking, low/high shelf)"},
    "eqmac_expert": {
        "name": "eqMac (Expert equalizer)", "platforms": ["macOS"], "kind": "parametric", "file": None,
        "source": "https://github.com/bitgapp/eqMac",
        "note": "No limits"},
    "eqmac_advanced": {
        "name": "eqMac (Advanced equalizer)", "platforms": ["macOS"], "kind": "graphic", "file": None,
        "freqs": [32, 64, 125, 250, 500, 1000, 2000, 4000, 8000, 16000], "q": 2.87, "gain": (-24, 24), "step": 0.1,
        "source": "https://github.com/bitgapp/eqMac/blob/master/native/app/Source/Audio/Effects/Equalizers/Advanced/AdvancedEqualizer.swift",
        "note": "10 fixed bands (0.5-octave) · ±24 dB · Q 2.87"},
    "apple_music": {
        "name": "Apple Music (Mac)", "platforms": ["macOS"], "kind": "graphic", "file": None, "approx": True,
        "freqs": [32, 64, 125, 250, 500, 1000, 2000, 4000, 8000, 16000], "q": 1.41, "gain": (-12, 12),
        "source": "https://support.apple.com/guide/music/adjust-the-sound-quality-museb684a3de/mac",
        "note": "10 fixed bands · 32 Hz–16 kHz · ±12 dB"},
    "aunbandeq": {
        "name": "AUNBandEQ (AU Lab)", "platforms": ["macOS"], "kind": "parametric", "file": None,
        "peaks": 8, "shelves": True, "q": (0.18, 10),
        "source": "https://github.com/jaakkopasanen/AutoEq/blob/master/webapp/ui/src/equalizers.js",
        "note": "Up to 8 peaking + low/high shelf · Q 0.18–10"},
    # ---------------------------------------------------------------- Linux
    "easyeffects": {
        "name": "EasyEffects", "platforms": ["Linux"], "kind": "parametric", "file": "apo", "bands": 32,
        "gain": (-36, 36), "q": (0.03, 100), "freq": (10, 24000),
        "source": "https://github.com/wwmm/easyeffects/blob/master/src/contents/kcfg/easyeffects_db_equalizer_channel.kcfg",
        "note": "Up to 32 bands · 10 Hz–24 kHz · ±36 dB · Q 0.03–100"},
    "pipewire": {
        "name": "PipeWire parametric equalizer", "platforms": ["Linux"], "kind": "parametric", "file": "apo",
        "source": "https://docs.pipewire.org/page_module_parametric_equalizer.html",
        "note": "No limits (peaking, low/high shelf)"},
    "jamesdsp_linux": {
        "name": "JamesDSP for Linux", "platforms": ["Linux"], "kind": "curve", "file": "graphic",
        "source": "https://github.com/Audio4Linux/JDSP4Linux",
        "note": "No limits"},
    # ---------------------------------------------------------------- Android
    "wavelet": {
        "name": "Wavelet", "platforms": ["Android"], "kind": "curve", "file": "graphic",
        "source": "https://pittvandewitt.github.io/Wavelet/Import/",
        "note": "No limits"},
    "poweramp": {
        "name": "Poweramp / Poweramp Equalizer", "platforms": ["Android"], "kind": "parametric", "file": "poweramp",
        "bands": 32, "gain": (-15, 15), "q": (0.1, 12),
        "source": "https://play.google.com/store/apps/details?id=com.maxmpz.equalizer",
        "note": "5–32 bands · ±15 dB · Q 0.1–12"},
    "rootlessjamesdsp": {
        "name": "RootlessJamesDSP / JamesDSP", "platforms": ["Android"], "kind": "curve", "file": "graphic",
        "source": "https://github.com/ThePBone/RootlessJamesDSP",
        "note": "No limits"},
    "viper4android": {
        "name": "Viper4Android", "platforms": ["Android"], "kind": "curve", "file": "convolution",
        "source": "https://github.com/jaakkopasanen/AutoEq/wiki/Choosing-an-Equalizer-App",
        "note": "No limits"},
    "neutron": {
        "name": "Neutron Music Player", "platforms": ["Android", "iOS"], "kind": "parametric", "file": None,
        # 130: "Parametric equalizer (PEQ): 4-130 bands, per channel" (its store pages: this source and https://play.google.com/store/apps/details?id=com.neutroncode.mp, fetched 2026-11-24). Best fit tries 32 filters at most (settings.LIMITS)
        "bands": 130,
        "source": "https://apps.apple.com/us/app/neutron-music-player/id766858884",
        "note": "4–130 bands"},
    "uapp": {
        "name": "USB Audio Player PRO", "platforms": ["Android"], "kind": "parametric", "file": "uapp",
        "peaks": 10, "shelves": False, "gain": (-20, 20), "q": (0.1, 10), "freq": (20, 20000),
        "source": "https://github.com/jaakkopasanen/AutoEq/blob/master/webapp/ui/src/equalizers.js",
        "note": "Up to 10 peaking (no shelves) · 20 Hz–20 kHz · ±20 dB · Q 0.1–10"},
    "hiby": {
        "name": "HiBy Music (and HiBy devices)", "platforms": ["Android", "iOS", "Devices"], "kind": "parametric",
        "file": None, "bands": 10, "gain": (-12, 12), "q": (0.2, 20), "freq": (20, 20000),
        "source": "https://guide.hiby.com/en/docs/guides/audioprocess/peq/",
        "note": "Up to 10 bands (peaking, low/high shelf) · 20 Hz–20 kHz · ±12 dB · Q 0.2–20"},
    "spotify": {
        "name": "Spotify", "platforms": ["Android", "iOS", "Windows", "macOS"], "kind": "graphic", "file": None,
        "approx": True, "layout": "spotify",
        "source": "https://github.com/jaakkopasanen/AutoEq/blob/master/autoeq/constants.py",
        "note": "6 fixed bands · 60 Hz–15 kHz"},
    "soundcore": {
        "name": "Soundcore (Anker)", "platforms": ["Android", "iOS"], "kind": "graphic", "file": None, "approx": True,
        "freqs": [100, 200, 400, 800, 1600, 3200, 6400, 12800], "q": 1.41,
        "source": "https://github.com/jaakkopasanen/AutoEq/issues/786",
        "note": "8 fixed bands (1-octave)"},
    # ---------------------------------------------------------------- devices (set up from their apps)
    "qudelix_5k": {
        "name": "Qudelix-5K", "platforms": ["Devices", "Android", "iOS"], "kind": "parametric", "file": None,
        "bands": 10, "gain": (-12, 12), "q": (0.1, 7),
        "source": "https://www.qudelix.com/blogs/5k-dac-amp/equalizer",
        "note": "Up to 10 bands (peaking, low/high shelf) · ±12 dB · Q 0.1–7"},
    "qudelix_t71": {
        "name": "Qudelix-T71", "platforms": ["Devices", "Android", "iOS"], "kind": "parametric", "file": None,
        "bands": 20,
        "source": "https://www.qudelix.com/blogs/t71/qudelix-t71",
        "note": "Up to 20 bands"},
    "fiio": {
        "name": "FiiO Control (KA17, KA15, BTR13, JA11…)", "platforms": ["Devices", "Android", "iOS"],
        "kind": "parametric", "file": None, "bands": 10, "gain": (-12, 12), "freq": (20, 20000),
        "source": "https://fiio-file.fiio.net/70%E4%B8%8A%E4%BC%A0%E7%9A%84%E6%96%87%E4%BB%B6/PEQ%20Settings%20Instructions%20for%20FiiO%20Portable%20DAC&AMP.pdf",
        "note": "Up to 10 bands · 20 Hz–20 kHz · ±12 dB · Q 0–100"},
    "moondrop_free_dsp": {
        "name": "Moondrop Free DSP", "platforms": ["Devices", "Android", "iOS"], "kind": "parametric", "file": None,
        "peaks": 9, "shelves": False, "gain": (-12, 3), "q": (0.2, 10), "freq": (40, 10000),
        "source": "https://headphones.com/blogs/reviews/moondrop-free-dsp-review-measurements",
        "note": "Up to 9 peaking (no shelves) · 40 Hz–10 kHz · -12 to +3 dB · Q 0.2–10"},
    "minidsp_2x4hd": {
        "name": "miniDSP 2x4 HD", "platforms": ["Devices"], "kind": "parametric", "file": None,
        "bands": 10, "gain": (-16, 16), "q": (0.5, 6),
        "source": "https://docs.minidsp.com/product-manuals/2x4-hd/dsp-reference/peq.html",
        "note": "Up to 10 bands per channel · ±16 dB · Q 0.5–6"},
    "minidsp_il_dsp": {
        "name": "miniDSP IL-DSP", "platforms": ["Devices"], "kind": "parametric", "file": None,
        "peaks": 8, "shelves": True, "gain": (-16, 16), "q": (0.5, 6),
        "source": "https://github.com/jaakkopasanen/AutoEq/blob/master/webapp/ui/src/equalizers.js",
        "note": "Up to 8 peaking + low/high shelf · ±16 dB · Q 0.5–6"},
    "rockbox": {
        "name": "Rockbox (music devices)", "platforms": ["Devices"], "kind": "parametric", "file": "rockbox",
        "peaks": 8, "shelves": True, "gain": (-24, 24), "q": (0.1, 6.4), "freq": (20, 22040),
        "source": "https://git.rockbox.org/cgit/rockbox.git/tree/apps/menus/eq_menu.h",
        "note": "Up to 8 peaking + low/high shelf · 20 Hz–22.04 kHz · ±24 dB · Q 0.1–6.4"},
}
OTHER = "other"  # not listed / not sure: any filters, the Equalizer APO file


def app(key):
    return APPS.get(key)


def layout_key(key):
    """The Best fit layout the app sets (layouts.py): "any" for apps without limits or that take a curve, a fixed
    band layout, or the app's own."""
    a = APPS.get(key)
    if not a:
        return "any"
    if a.get("layout"):
        return a["layout"]
    if a["kind"] in ("curve", "site") or (a["kind"] == "parametric" and not any(k in a for k in ("bands", "peaks", "gain", "q", "freq"))):
        return "any"
    return "app:" + key


def band_sets(key):
    """{band count: (centre frequencies, each band's Q)} of a graphic EQ app with more than one band count, else {}."""
    return {n: (list(f), q) for n, (f, q) in (APPS.get(key) or {}).get("band_sets", {}).items()}


def summary(key):
    """What the app takes, in a line."""
    a = APPS.get(key)
    if not a:
        return "No limits on the filters. The app saves an Equalizer APO file (most apps can read it)."
    if a["kind"] == "curve":
        return "It uses a full response curve: no limits on the filters."
    if a["kind"] == "site":
        return "The AutoEQ of the website (the Website methods), or a maximum of 20 imported filters."
    if a["kind"] == "graphic":
        # (an app with more than one band count: the count it starts with)
        n = (a["band_default"] if "band_sets" in a else
             len(a["freqs"] if "freqs" in a else BAND_LAYOUTS[a["layout"]][1]))
        parts = [f"{n} graphic EQ bands"]
    else:
        n = a.get("bands") or a.get("peaks")
        parts = ([f"maximum {a['bands']} bands" if "bands" in a else
                  f"{a['peaks']} peaking filters" + (" and two shelves" if a.get("shelves") else ", no shelves")]
                 if n else ["no limit on the number of filters"])
    if "gain" in a:
        parts.append(f"{a['gain'][0]:+g} to {a['gain'][1]:+g} dB")
    if "step" in a:
        parts.append(f"{a['step']:g} dB steps")
    if "q" in a and a["kind"] == "parametric":
        parts.append(f"Q {a['q'][0]:g}-{a['q'][1]:g}")
    if "freq" in a:
        f = lambda v: f"{v / 1000:g} kHz" if v >= 1000 else f"{v:g} Hz"
        parts.append(f"{f(a['freq'][0])}-{f(a['freq'][1])}")
    text = ", ".join(parts) + "."
    return text[0].upper() + text[1:]


def listing():
    """For the page: [{key, name, platforms, kind, layout, file, summary, note, source, approx, bands_gain,
    bands_step}]."""
    return [{"key": k, "name": a["name"], "platforms": a["platforms"], "kind": a["kind"], "layout": layout_key(k),
             "file": a.get("file"), "summary": summary(k), "note": a.get("note", ""),
             "source": a.get("source", ""), "approx": bool(a.get("approx")),
             "bands_gain": list(a["gain"]) if a["kind"] == "graphic" and "gain" in a else None,
             "bands_step": a.get("step")} for k, a in APPS.items()]
