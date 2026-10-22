"""The EQ apps and devices the EQ can be made for (settings "eq_app"), with each one's limits as its maker states them.

Each app is one of:
  "parametric"  filters anywhere, within the app's limits (a number of bands, gain, Q, frequency): Best fit keeps
                within them (the app becomes a layout: layouts.DEVICES "app:<key>")
  "graphic"     fixed bands: only their gains are fitted, within the app's range and steps (layouts.FIXED "app:<key>")
  "curve"       the app takes a whole response curve (a GraphicEQ line or an impulse response): any filters
  "site"        squig.link's own EQ: the Website methods make exactly what its AutoEQ makes
and says which of the app's files it takes (exports.FORMATS; None: typed in by hand from the filter table) and how.

Limits are only what the app's maker (its source code, manual, help pages or store listing) states, with the source
in "source". A limit nobody states is left out, so the app's own measured limits (settings.LIMITS) apply there;
"note" says what isn't known. Checked September 2026. "approx": the band shapes (Q) aren't stated, so the fit uses
the usual ones for that spacing and the result can differ a little in the app.
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
        "how": "The Website methods give what its AutoEQ gives; or save the file and use Import in its EQ (up to 20 filters).",
        "source": "https://squig.link/",
        "note": "Its AutoEQ: 20 filter rows, whole dB from -20 to +20, Q 0.1-5 (settings.LIMITS, from its code)."},
    # ---------------------------------------------------------------- Windows
    "apo": {
        "name": "Equalizer APO", "platforms": ["Windows"], "kind": "parametric", "file": "apo",
        "how": "Save filters, then add the file in its Configuration Editor (or copy it into its config folder and Include it in config.txt).",
        "source": "https://sourceforge.net/p/equalizerapo/wiki/Configuration%20reference/",
        "note": "No limits stated: any number of filters, any gain, Q and frequency."},
    "peace": {
        "name": "Peace (for Equalizer APO)", "platforms": ["Windows"], "kind": "parametric", "file": "apo",
        "bands": 31, "gain": (-30, 30),
        "how": "Save filters, then Import in Peace.",
        "source": "https://sourceforge.net/p/peace-equalizer-apo-extension/wiki/Features%20FAQ/",
        "note": "31 sliders; ±30 dB by default (its Settings can widen it to 60). Q and frequency as in Equalizer APO."},
    "fxsound": {
        "name": "FxSound", "platforms": ["Windows"], "kind": "graphic", "file": None, "approx": True,
        "freqs": [20.0, 43.1, 92.8, 200.0, 430.9, 928.3, 2000.0, 4308.9, 9283.2, 20000.0], "q": 1.0,
        "gain": (-12, 12), "step": 1,
        "how": "Set its 10 sliders to the gains in the filter table.",
        "source": "https://github.com/fxsound2/fxsound-app/blob/main/docs/COMMAND_LINE_OPTIONS.md",
        "note": "Its default 10 bands (5-31 can be set), ±12 dB in 1 dB steps, one Q for all (1.0 by default)."},
    "sonar": {
        "name": "SteelSeries Sonar", "platforms": ["Windows"], "kind": "parametric", "file": None, "bands": 10,
        "how": "Enter the filter table's filters in its parametric EQ by hand.",
        "source": "https://support.steelseries.com/hc/en-us/articles/5570622280077-How-do-I-add-or-delete-a-band-to-Sonar-Parametric-EQ",
        "note": "Up to 10 bands. SteelSeries doesn't publish its gain or Q range."},
    "voicemeeter": {
        "name": "Voicemeeter (Banana, Potato)", "platforms": ["Windows"], "kind": "parametric", "file": "voicemeeter",
        "bands": 6, "gain": (-36, 18), "freq": (20, 20000),
        "how": "Open a bus's EQ, right-click its top bar › Load EQ Settings.",
        "source": "https://vb-audio.com/Voicemeeter/VoicemeeterPotato_UserManual.pdf",
        "note": "6 cells per bus; peaks -36 to +18 dB, 20 Hz-20 kHz. Its Q range isn't stated clearly."},
    "foobar2000": {
        "name": "foobar2000 (built-in equalizer)", "platforms": ["Windows"], "kind": "graphic", "file": None,
        "approx": True,
        "freqs": [55, 77, 110, 156, 220, 311, 440, 622, 880, 1245, 1760, 2489, 3520, 4978, 7040, 9956, 14080, 19912],
        "q": 2.87, "gain": (-20, 20), "step": 1,
        "how": "Set its 18 sliders to the gains in the filter table.",
        "source": "https://www.foobar2000.org/equalizer",
        "note": "18 bands half an octave apart, ±20 dB in 1 dB steps (its source code). Its bands blend into each "
                "other (SuperEQ), so the fit's half-octave bells are close, not exact."},
    # ---------------------------------------------------------------- Windows and macOS
    "roon": {
        "name": "Roon (MUSE parametric EQ)", "platforms": ["Windows", "macOS", "Linux"], "kind": "parametric",
        "file": None, "gain": (-24, 24),
        "how": "Enter the filter table's filters in MUSE › Parametric EQ by hand.",
        "source": "https://help.roonlabs.com/portal/en/kb/articles/dsp-engine-parametric-equalizer",
        "note": "Gains past ±24 dB are clamped. Band count and Q range aren't stated."},
    "boom3d": {
        "name": "Boom 3D", "platforms": ["Windows", "macOS"], "kind": "graphic", "file": None, "approx": True,
        "layout": "graphic_31",
        "how": "Set its 31 sliders to the gains in the filter table.",
        "source": "https://blog.globaldelight.com/boom-3d-mac/why-do-you-need-a-31-band-equalizer",
        "note": "31 bands at the ISO frequencies, 20 Hz-20 kHz. Its gain range isn't stated."},
    # ---------------------------------------------------------------- macOS
    "soundsource": {
        "name": "SoundSource", "platforms": ["macOS"], "kind": "parametric", "file": "soundsource", "bands": 32,
        "how": "Headphone EQ › Add Other Profile… and pick the saved file.",
        "source": "https://rogueamoeba.com/support/knowledgebase/?showArticle=SoundSource-Custom-HPEQ",
        "note": "Up to 32 filters (peaking, low and high shelf). No ranges stated."},
    "eqmac_expert": {
        "name": "eqMac (Expert equalizer)", "platforms": ["macOS"], "kind": "parametric", "file": None,
        "how": "Enter the filter table's filters on the Expert tab by hand.",
        "source": "https://github.com/bitgapp/eqMac",
        "note": "Unlimited bands; ranges aren't stated."},
    "eqmac_advanced": {
        "name": "eqMac (Advanced equalizer)", "platforms": ["macOS"], "kind": "graphic", "file": None,
        "freqs": [32, 64, 125, 250, 500, 1000, 2000, 4000, 8000, 16000], "q": 2.87, "gain": (-24, 24), "step": 0.1,
        "how": "Set its 10 sliders to the gains in the filter table.",
        "source": "https://github.com/bitgapp/eqMac/blob/master/native/app/Source/Audio/Effects/Equalizers/Advanced/AdvancedEqualizer.swift",
        "note": "10 bands, each half an octave wide (Q 2.87), ±24 dB (its source code)."},
    "apple_music": {
        "name": "Apple Music (Mac)", "platforms": ["macOS"], "kind": "graphic", "file": None, "approx": True,
        "freqs": [32, 64, 125, 250, 500, 1000, 2000, 4000, 8000, 16000], "q": 1.41, "gain": (-12, 12),
        "how": "Window › Equalizer: set its 10 sliders to the gains in the filter table, Preamp to the pre-amp.",
        "source": "https://support.apple.com/guide/music/adjust-the-sound-quality-museb684a3de/mac",
        "note": "10 bands 32 Hz-16 kHz and a pre-amp. Apple doesn't state the range (the sliders show ±12 dB) or the "
                "band shapes. (On iPhone and iPad it has presets only: no custom EQ.)"},
    "aunbandeq": {
        "name": "AUNBandEQ (AU Lab)", "platforms": ["macOS"], "kind": "parametric", "file": None,
        "peaks": 8, "shelves": True, "q": (0.18, 10),
        "how": "Enter the filter table's filters in AUNBandEQ by hand (widths from Q).",
        "source": "https://github.com/jaakkopasanen/AutoEq/blob/master/webapp/ui/src/equalizers.js",
        "note": "AutoEq's preset for it (8 peaking filters and shelves, Q 0.18-10); Apple doesn't state its limits."},
    # ---------------------------------------------------------------- Linux
    "easyeffects": {
        "name": "EasyEffects", "platforms": ["Linux"], "kind": "parametric", "file": "apo", "bands": 32,
        "gain": (-36, 36), "q": (0.03, 100), "freq": (10, 24000),
        "how": "Equalizer › Import Preset › APO, and pick the saved file.",
        "source": "https://github.com/wwmm/easyeffects/blob/master/src/contents/kcfg/easyeffects_db_equalizer_channel.kcfg",
        "note": "Up to 32 bands, ±36 dB, 10 Hz-24 kHz, Q up to 100 (its settings' own limits)."},
    "pipewire": {
        "name": "PipeWire parametric equalizer", "platforms": ["Linux"], "kind": "parametric", "file": "apo",
        "how": "Point equalizer.filepath in a module-parametric-equalizer config at the saved file (PipeWire 1.0.6+).",
        "source": "https://docs.pipewire.org/page_module_parametric_equalizer.html",
        "note": "Reads the Equalizer APO file (peaking, low and high shelf); no limits stated."},
    "jamesdsp_linux": {
        "name": "JamesDSP for Linux", "platforms": ["Linux"], "kind": "curve", "file": "graphic",
        "how": "Arbitrary response equalizer: paste or import the GraphicEQ line.",
        "source": "https://github.com/Audio4Linux/JDSP4Linux",
        "note": "Takes a whole response curve (GraphicEQ), so any filters."},
    # ---------------------------------------------------------------- Android
    "wavelet": {
        "name": "Wavelet", "platforms": ["Android"], "kind": "curve", "file": "graphic",
        "how": "AutoEq › Import, and pick the saved GraphicEQ file.",
        "source": "https://pittvandewitt.github.io/Wavelet/Import/",
        "note": "Takes a GraphicEQ curve (any filters); it levels imported curves itself."},
    "poweramp": {
        "name": "Poweramp / Poweramp Equalizer", "platforms": ["Android"], "kind": "parametric", "file": "poweramp",
        "bands": 32, "gain": (-15, 15), "q": (0.1, 12),
        "how": "Copy the file to the phone, then Presets › Import in its equalizer (parametric mode).",
        "source": "https://play.google.com/store/apps/details?id=com.maxmpz.equalizer",
        "note": "5-32 bands (its store listing), ±15 dB, Q 0.1-12 (as autoeq.app has them)."},
    "rootlessjamesdsp": {
        "name": "RootlessJamesDSP / JamesDSP", "platforms": ["Android"], "kind": "curve", "file": "graphic",
        "how": "Arbitrary response equalizer › Magnitude response: import the GraphicEQ file.",
        "source": "https://github.com/ThePBone/RootlessJamesDSP",
        "note": "Takes a whole response curve (GraphicEQ), so any filters."},
    "viper4android": {
        "name": "Viper4Android", "platforms": ["Android"], "kind": "curve", "file": "convolution",
        "how": "Convolver: pick the saved impulse response (.wav).",
        "source": "https://github.com/jaakkopasanen/AutoEq/wiki/Choosing-an-Equalizer-App",
        "note": "Plays an impulse response, so any filters, exactly."},
    "neutron": {
        "name": "Neutron Music Player", "platforms": ["Android", "iOS"], "kind": "parametric", "file": None,
        "bands": 60,
        "how": "Settings › Playback › DSP Effect › Equalizer: set the band count, then each band's type, frequency, Q and gain.",
        "source": "https://apps.apple.com/us/app/neutron-music-player/id766858884",
        "note": "4-60 bands, all filter types, no limits on gain or Q."},
    "uapp": {
        "name": "USB Audio Player PRO", "platforms": ["Android"], "kind": "parametric", "file": "uapp",
        "peaks": 10, "shelves": False, "gain": (-20, 20), "q": (0.1, 10), "freq": (20, 20000),
        "how": "Copy the file into the TBEQPresets folder in UAPP's folder.",
        "source": "https://github.com/jaakkopasanen/AutoEq/blob/master/webapp/ui/src/equalizers.js",
        "note": "Its ToneBoosters parametric EQ as its preset files hold it: 10 peaking filters, no shelves, ±20 dB, Q 0.1-10."},
    "hiby": {
        "name": "HiBy Music (and HiBy players)", "platforms": ["Android", "iOS", "Devices"], "kind": "parametric",
        "file": None, "bands": 10, "gain": (-12, 12), "q": (0.2, 20), "freq": (20, 20000),
        "how": "PEQ: enter the filter table's filters (peaking, low and high shelf) by hand.",
        "source": "https://guide.hiby.com/en/docs/guides/audioprocess/peq/",
        "note": "10 bands, 20 Hz-20 kHz, ±12 dB, Q 0.2-20."},
    "spotify": {
        "name": "Spotify", "platforms": ["Android", "iOS", "Windows", "macOS"], "kind": "graphic", "file": None,
        "approx": True, "layout": "spotify",
        "how": "Settings › Equalizer: set its 6 sliders to the gains in the filter table.",
        "source": "https://github.com/jaakkopasanen/AutoEq/blob/master/autoeq/constants.py",
        "note": "6 bands (60 Hz-15 kHz). Spotify doesn't state its range or band shapes (AutoEq's are used)."},
    "soundcore": {
        "name": "Soundcore (Anker)", "platforms": ["Android", "iOS"], "kind": "graphic", "file": None, "approx": True,
        "freqs": [100, 200, 400, 800, 1600, 3200, 6400, 12800], "q": 1.41,
        "how": "Custom EQ: set its 8 sliders to the gains in the filter table.",
        "source": "https://github.com/jaakkopasanen/AutoEq/issues/786",
        "note": "8 bands, an octave apart. Anker doesn't state the range or band shapes."},
    # ---------------------------------------------------------------- devices (set up from their apps)
    "qudelix_5k": {
        "name": "Qudelix-5K", "platforms": ["Devices", "Android", "iOS"], "kind": "parametric", "file": None,
        "bands": 10, "gain": (-12, 12), "q": (0.1, 7),
        "how": "In the Qudelix app's PEQ, enter the filter table's filters (PEAK, LSHELF, HSHELF).",
        "source": "https://www.qudelix.com/blogs/5k-dac-amp/equalizer",
        "note": "10-band PEQ, ±12 dB (Qudelix). Q 0.1-7 is AutoEq's preset; Qudelix doesn't state it."},
    "qudelix_t71": {
        "name": "Qudelix-T71", "platforms": ["Devices", "Android", "iOS"], "kind": "parametric", "file": None,
        "bands": 20,
        "how": "In the Qudelix app's PEQ, enter the filter table's filters.",
        "source": "https://www.qudelix.com/blogs/t71/qudelix-t71",
        "note": "20-band PEQ with 7 filter types; its gain and Q ranges aren't stated."},
    "fiio": {
        "name": "FiiO Control (KA17, KA15, BTR13, JA11…)", "platforms": ["Devices", "Android", "iOS"],
        "kind": "parametric", "file": None, "bands": 10, "gain": (-12, 12), "freq": (20, 20000),
        "how": "In FiiO Control's PEQ (Advanced settings), enter the filter table's filters.",
        "source": "https://fiio-file.fiio.net/70%E4%B8%8A%E4%BC%A0%E7%9A%84%E6%96%87%E4%BB%B6/PEQ%20Settings%20Instructions%20for%20FiiO%20Portable%20DAC&AMP.pdf",
        "note": "10 bands, 20 Hz-20 kHz, ±12 dB, Q 0-100, 7 filter types (FiiO's PEQ instructions)."},
    "moondrop_free_dsp": {
        "name": "Moondrop Free DSP", "platforms": ["Devices", "Android", "iOS"], "kind": "parametric", "file": None,
        "peaks": 9, "shelves": False, "gain": (-12, 3), "q": (0.2, 10), "freq": (40, 10000),
        "how": "In the Moondrop app's PEQ, enter the filter table's filters.",
        "source": "https://headphones.com/blogs/reviews/moondrop-free-dsp-review-measurements",
        "note": "9 bands, 40 Hz-10 kHz, -12 to +3 dB, Q 0.2-10."},
    "minidsp_2x4hd": {
        "name": "miniDSP 2x4 HD", "platforms": ["Devices"], "kind": "parametric", "file": None,
        "bands": 10, "gain": (-16, 16), "q": (0.5, 6),
        "how": "In the miniDSP plug-in's PEQ, enter the filter table's filters.",
        "source": "https://docs.minidsp.com/product-manuals/2x4-hd/dsp-reference/peq.html",
        "note": "10 PEQ bands per channel, ±16 dB (miniDSP). Q 0.5-6 is AutoEq's preset; miniDSP doesn't state it here."},
    "minidsp_il_dsp": {
        "name": "miniDSP IL-DSP", "platforms": ["Devices"], "kind": "parametric", "file": None,
        "peaks": 8, "shelves": True, "gain": (-16, 16), "q": (0.5, 6),
        "how": "In the miniDSP app's PEQ, enter the filter table's filters.",
        "source": "https://github.com/jaakkopasanen/AutoEq/blob/master/webapp/ui/src/equalizers.js",
        "note": "AutoEq's preset for it (8 peaking filters and shelves, ±16 dB, Q 0.5-6); miniDSP doesn't state them."},
    "rockbox": {
        "name": "Rockbox (music players)", "platforms": ["Devices"], "kind": "parametric", "file": "rockbox",
        "peaks": 8, "shelves": True, "gain": (-24, 24), "q": (0.1, 6.4), "freq": (20, 22040),
        "how": "Copy the file onto the player, then Sound Settings › Equalizer › Browse EQ Presets.",
        "source": "https://git.rockbox.org/cgit/rockbox.git/tree/apps/menus/eq_menu.h",
        "note": "A low shelf, 8 peaking filters and a high shelf; ±24 dB, Q 0.1-6.4 (its source code)."},
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


def summary(key):
    """What the app takes, in a line."""
    a = APPS.get(key)
    if not a:
        return "Any filters, as many as needed; saved as an Equalizer APO file (most apps can read it)."
    if a["kind"] == "curve":
        return "Takes a whole response curve: any filters."
    if a["kind"] == "site":
        return "The website's own AutoEQ (the Website methods), or up to 20 imported filters."
    if a["kind"] == "graphic":
        n = len(a["freqs"] if "freqs" in a else BAND_LAYOUTS[a["layout"]][1])
        parts = [f"{n} fixed bands"]
    else:
        n = a.get("bands") or a.get("peaks")
        parts = ([f"up to {a['bands']} bands" if "bands" in a else
                  f"{a['peaks']} peaking filters" + (" and two shelves" if a.get("shelves") else ", no shelves")]
                 if n else ["any number of filters"])
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
    """For the page: [{key, name, platforms, kind, layout, file, summary, how, note, source, approx}]."""
    return [{"key": k, "name": a["name"], "platforms": a["platforms"], "kind": a["kind"], "layout": layout_key(k),
             "file": a.get("file"), "summary": summary(k), "how": a["how"], "note": a.get("note", ""),
             "source": a.get("source", ""), "approx": bool(a.get("approx")),
             "bands_gain": list(a["gain"]) if a["kind"] == "graphic" and "gain" in a else None,
             "bands_step": a.get("step")} for k, a in APPS.items()]
