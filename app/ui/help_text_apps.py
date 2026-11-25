"""Help's entry “Load the EQ in your EQ app”: the steps to put a made EQ into each app or device of the Your EQ app
list (the user, 2026-11-24: the steps left the ⓘ after Your EQ app with the text survey, and belong in Help).

LOAD_EQ is the only place that has the steps: [(platform, [(key of eq\\eq_apps.py APPS, the app's name, its
steps)])]. The names of buttons and menus of the other app in the steps are facts (from eq_apps.py's "how" texts of
before 2026-11-23, each app's "source" there): do not reword them. An app is in the list of its first platform in
eq_apps.py. The name is a copy of APPS[key]["name"]: this file cannot import the EQ part (nothing of it loads while
the app is only in the tray, and the Help texts load then), so tests\\eq_screen\\test_help_tags.py compares the
keys, the names and the platforms with eq_apps.py. An app added there gets its steps here.
"""

LOAD_EQ = [
    ("Web", [
        ("squiglink", "squig.link (the website's EQ)",
         "The Website methods make the same EQ as its AutoEQ. You can also import the saved file in its EQ (maximum "
         "20 filters)."),
    ]),
    ("Windows", [
        ("apo", "Equalizer APO",
         "Click “Save filters”. Then add the file in its “Configuration Editor” (or copy the file into its config "
         "folder and add it to config.txt with “Include”)."),
        ("peace", "Peace (for Equalizer APO)", "Click “Save filters”. Then import the file in Peace."),
        ("fxsound", "FxSound", "Set the number of bands of FxSound to the band count of the EQ, and Filter Q to 1.0. "
                               "With 5 or 10 bands, set each band to the frequency in the filter table. Then set "
                               "its sliders to the gains in the filter table."),
        ("sonar", "SteelSeries Sonar", "Manually enter the filters from the filter table in its parametric EQ."),
        ("voicemeeter", "Voicemeeter (Banana, Potato)",
         "Open the EQ of a bus. Right-click its top bar. Click “Load EQ Settings”."),
        ("foobar2000", "foobar2000 (its equalizer)", "Set its 18 sliders to the gains in the filter table."),
        ("roon", "Roon (MUSE parametric EQ)",
         "Manually enter the filters from the filter table in “MUSE › Parametric EQ”."),
        ("boom3d", "Boom 3D", "Set its 31 sliders to the gains in the filter table."),
    ]),
    ("macOS", [
        ("soundsource", "SoundSource", "In “Headphone EQ › Add Other Profile…”, select the saved file."),
        ("eqmac_expert", "eqMac (Expert equalizer)",
         "Manually enter the filters from the filter table on the “Expert” tab."),
        ("eqmac_advanced", "eqMac (Advanced equalizer)", "Set its 10 sliders to the gains in the filter table."),
        ("apple_music", "Apple Music (Mac)",
         "In “Window › Equalizer”, set its 10 sliders to the gains in the filter table and “Preamp” to the pre-amp."),
        ("aunbandeq", "AUNBandEQ (AU Lab)",
         "Manually enter the filters from the filter table in AUNBandEQ (widths from Q)."),
    ]),
    ("Linux", [
        ("easyeffects", "EasyEffects", "In “Equalizer › Import Preset › APO”, select the saved file."),
        ("pipewire", "PipeWire parametric equalizer",
         "In a module-parametric-equalizer config, set equalizer.filepath to the saved file (PipeWire 1.0.6 or "
         "higher)."),
        ("jamesdsp_linux", "JamesDSP for Linux",
         "In “Arbitrary response equalizer”, paste or import the GraphicEQ line."),
    ]),
    ("Android", [
        ("wavelet", "Wavelet", "In “AutoEq › Import”, select the saved GraphicEQ file."),
        ("poweramp", "Poweramp / Poweramp Equalizer",
         "Copy the file to the Android device. Then use “Presets › Import” in its equalizer (parametric mode)."),
        ("rootlessjamesdsp", "RootlessJamesDSP / JamesDSP",
         "In “Arbitrary response equalizer › Magnitude response”, import the GraphicEQ file."),
        ("viper4android", "Viper4Android", "In “Convolver”, select the saved impulse response (.wav)."),
        ("neutron", "Neutron Music Player",
         "In “Settings › Playback › DSP Effect › Equalizer”, set the number of bands. Then set the type, frequency, "
         "Q and gain of each band."),
        ("uapp", "USB Audio Player PRO", "Copy the file into the TBEQPresets folder in the folder of UAPP."),
        ("hiby", "HiBy Music (and HiBy devices)",
         "In “PEQ”, manually enter the filters from the filter table (peaking, low and high shelf)."),
        ("spotify", "Spotify", "In “Settings › Equalizer”, set its 6 sliders to the gains in the filter table."),
        ("soundcore", "Soundcore (Anker)", "In “Custom EQ”, set its 8 sliders to the gains in the filter table."),
    ]),
    ("Devices", [
        ("qudelix_5k", "Qudelix-5K",
         "In the PEQ of the Qudelix app, enter the filters from the filter table (PEAK, LSHELF, HSHELF)."),
        ("qudelix_t71", "Qudelix-T71", "In the PEQ of the Qudelix app, enter the filters from the filter table."),
        ("fiio", "FiiO Control (KA17, KA15, BTR13, JA11…)",
         "In the PEQ of FiiO Control (“Advanced settings”), enter the filters from the filter table."),
        ("moondrop_free_dsp", "Moondrop Free DSP",
         "In the PEQ of the Moondrop app, enter the filters from the filter table."),
        ("minidsp_2x4hd", "miniDSP 2x4 HD",
         "In the PEQ of the miniDSP plug-in, enter the filters from the filter table."),
        ("minidsp_il_dsp", "miniDSP IL-DSP", "In the PEQ of the miniDSP app, enter the filters from the filter table."),
        ("rockbox", "Rockbox (music devices)",
         "Copy the file onto the device. Then use “Sound Settings › Equalizer › Browse EQ Presets”."),
    ]),
]

# (the entry: a line for each platform, then its apps, each one "name: steps". What each saved file is, and which
# apps read it, is in the entry Saved file formats: not said again here)
LOAD_EQ_TERM = {
    "id": "load-eq",
    "title": "Load the EQ in your EQ app",
    "body": ["Select the app as Your EQ app before you make the EQ. Then do the steps of the app below. “The saved "
             "file” is the file that Save filters writes to your Saved EQs folder (refer to Saved file formats). The "
             "filter table is on the result card.",
             "An app for more than one platform is in the list of its first platform (the Your EQ app list shows "
             "the platforms after each name). To find an app quickly, type its name in Search Help…",
             *[part for platform, apps in LOAD_EQ
               for part in (f"{platform}:", [f"{name}: {steps}" for _key, name, steps in apps])]],
    "see": ["eq-app", "file-formats", "preamp"],
}
