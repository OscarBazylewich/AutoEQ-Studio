"""The help words for Make an EQ and its windows (Find…, Which measurement, Listen, History, Run several,
Compare…, the target's Adjust): HELP_EQ, each setting's or control's line by its key (its tooltip, with the ids
of its "See also" entries in Help), and SETTINGS_EQ, their groups in Help's "Every setting" (the first 18, in the
page's order). help_texts.py joins them with the other screens'. Words only: nothing is imported here.
"""
# flake8: noqa

HELP_EQ = {'slot:target': ['The curve you want your earphone to sound like.', 'target', 'rig'],
 'slot:measurement': ["Your IEM or headphone's measured frequency response.",
                      'measurement',
                      'seatings',
                      'compare-measurements'],
 'eq_app': ['The app or device that will play the EQ: its limits and file format are used.',
            'eq-app',
            'layout',
            'file-formats'],
 'slot:method': ['How the EQ filters are worked out.', 'best-fit', 'website-autoeq', 'q-which-method'],
 'sa': ['What the next run tries, and how long it takes on this PC.', 'speed-accuracy', 'best-fit'],
 '#auto-on': ['Fits the settings to your measurement and target.', 'automatic-settings', 'q-yours'],
 'rig_convert.enabled': ['Adjusts the target for the rig your measurement was made on.',
                         'rig-conversion',
                         'rig',
                         'q-rigs'],
 'target_adjust.tilt': ['Tilts the whole target darker (−) or brighter (+).', 'target-adjustments'],
 'target_adjust.bass_gain': ['Adds (+) or removes (−) bass from the target.', 'target-adjustments', 'shelf'],
 'target_adjust.bass_freq': ['Where the bass change starts.', 'shelf'],
 'target_adjust.bass_q': ['How steep the bass change is.', 'shelf', 'q'],
 'target_adjust.halftilt_gain': ['Gently raises (+) or lowers (−) everything above its frequency.',
                                 'target-adjustments'],
 'target_adjust.halftilt_freq': 'Where the half-tilt is centred.',
 'target_adjust.ear_gain': ['Raises (+) or lowers (−) the 2–5 kHz presence region.', 'target-adjustments'],
 'target_adjust.ear_freq': 'The centre of the ear-gain change.',
 'target_adjust.ear_q': ['How wide the ear-gain change is.', 'q'],
 'target_adjust.treble_gain': ['Adds (+) or removes (−) treble from the target.', 'target-adjustments', 'shelf'],
 'target_adjust.treble_freq': 'Where the treble change starts.',
 'target_adjust.treble_q': ['How steep the treble change is.', 'shelf'],
 'target_adjust.air_gain': ['Adds (+) or removes (−) “air” above about 10 kHz.', 'treble-limit'],
 'target_adjust.air_freq': 'Where the air change starts.',
 'target_adjust.air_q': ['How steep the air change is.', 'shelf'],
 'best_fit.filter_counts': ['How many filters to try.', 'simplest', 'peaking-filter', 'q-filters'],
 'best_fit.low_shelf': ['Also fits a low shelf: a broad bass change.', 'shelf'],
 'best_fit.freq_range': ['Where filters may be placed.', 'scored-range'],
 'best_fit.gain_min': ['The deepest cut a filter may have.', 'db'],
 'best_fit.gain_max': ['The biggest boost a filter may have.', 'preamp'],
 'best_fit.q_min': ['The broadest filter allowed.', 'q'],
 'best_fit.q_max': ['The narrowest filter allowed.', 'q', 'unit-variation'],
 'best_fit.low_shelf_freq': ["Where the low shelf's corner may go.", 'shelf'],
 'best_fit.fight_penalty': ['Discourages filters that cancel each other out.', 'penalties'],
 'best_fit.start_keep': ['Keeps your filters as they are and adds to them.', 'own-filters'],
 'best_fit.start_filters': ['An EQ you already have, for Best fit to start from.', 'own-filters', 'q-have-eq'],
 'best_fit.layout': ['What kind of EQ the filters are made for.', 'layout', 'fixed-bands'],
 'best_fit.bands.freqs': ["Your graphic EQ's slider frequencies.", 'fixed-bands'],
 'best_fit.bands.q': ["How wide each slider's band is.", 'q', 'fixed-bands'],
 'best_fit.bands.gain_min': "The sliders' lowest setting.",
 'best_fit.bands.gain_max': "The sliders' highest setting.",
 'best_fit.bands.step': ["The sliders' step size.", 'fixed-bands'],
 'scoring.band_hz': ['The frequency range the match is judged over.', 'scored-range', 'q-treble'],
 'scoring.pick': ['How the winning result is chosen.', 'simplest'],
 'scoring.ear_db': ['How far a result may sound from the target and still count as the same.', 'simplest'],
 'site_single.rows': ["The most filters the website's AutoEQ may use.", 'website-autoeq'],
 'site_single.freq_low': ["Where the website's AutoEQ may place filters.", 'website-autoeq'],
 'site_single.gain_min': ['The largest cut and boost per filter.', 'db'],
 'site_single.q_min': ['From how broad to how narrow filters may be.', 'q'],
 'site_sweep.filter_rows': ['The filter counts to try.', 'sweep'],
 'site_sweep.freq_low': "Where every run's frequency range starts.",
 'site_sweep.freq_high': ['The frequency-range ends to try.', 'treble-limit'],
 'site_sweep.gain_ranges': ['The gain ranges to try.', 'sweep'],
 'site_sweep.q_min': ["Where every run's Q range starts.", 'q'],
 'site_sweep.q_max': ['The Q-range ends to try.', 'q'],
 'res.error': ["How far the EQ'd curve is from the target: lower is closer.", 'error', 'q-error'],
 'res.preamp': ["The volume cut this EQ needs so it can't clip.", 'preamp', 'q-preamp'],
 'res.maxq': ['How narrow the narrowest filter is.', 'q'],
 'res.boost': ['The biggest boost of any one filter.', 'preamp'],
 'fcounts': ["This run's best result for each number of filters.", 'simplest', 'q-filters'],
 'f_retry': ['Runs Best fit again, starting from the filters shown.', 'retry'],
 'x_name': ['The name the saved files get.', 'file-formats'],
 'export.apo': ['A text file for Equalizer APO, Peace, EasyEffects and squiglink.', 'file-formats'],
 'export.graphic': ['A GraphicEQ line for Wavelet and similar apps.', 'file-formats'],
 'export.poweramp': ['A preset for Poweramp Equalizer (Android).', 'file-formats'],
 'export.uapp': ['A preset for USB Audio Player PRO (Android).', 'file-formats'],
 'export.soundsource': ['A profile for SoundSource (macOS).', 'file-formats'],
 'export.voicemeeter': ['An EQ file for a Voicemeeter bus (Windows).', 'file-formats', 'preamp'],
 'export.rockbox': ['An EQ preset for Rockbox music players.', 'file-formats'],
 'export.convolution': ['The EQ as an impulse response, for convolution EQs.', 'impulse-response'],
 'export.convolution_rate': ['Must match the sample rate your player uses.', 'sample-rate'],
 'export.report': ['An HTML page with the graph and the filters.', 'file-formats'],
 'export.preamp_rounding': ['How the pre-amp is rounded in saved files.', 'preamp'],
 'export.extra_headroom': ['An extra volume cut on top of the pre-amp.', 'preamp'],
 'export.q_decimals': 'How many decimals Q gets in saved files.',
 '#opt-view': ['Shows the curves as they are, or as the difference from the target.', 'error'],
 '#opt-y': 'How tall the dB scale is.',
 '#opt-ch': ["Also shows each of the measurement's files.", 'seatings'],
 '#snd-src': 'What to play.',
 '#tone-from': "The tone's frequency range.",
 '#snd-vol': 'Playback volume: start low.',
 '#snd-lm': ['Plays every version equally loud.', 'match-loudness'],
 '#snd-blind': ['Hides which version is which until you reveal it.', 'blind-test'],
 '#snd-abx': ['Whether you can really tell two versions apart: X is A or B at random, you say which.', 'abx',
              'match-loudness'],
 '#snd-ears': 'The same version in both ears, or a different one in each.',
 '#snd-left': 'What your left ear hears.',
 '#snd-right': 'What your right ear hears.',
 'snd_list': ['EQs you want to hear side by side on this IEM or headphone.', 'eqs-to-compare'],
 '#pk-anykind': 'Also lists files of the other kind.',
 'pk_filters': ['Narrows the list by rig, type or source; type in its list to find one.', 'rig-tags', 'databases'],
 '#pk-f-sure': ['Hides entries whose rig is only a guess.', 'rig-tags'],
 '#pk-f-dl': 'Hides entries that only open on their own site.',
 '#cmp-q': 'The model to look for.',
 '#cmp-rig': ['The rig your target was made for.', 'rig', 'rig-conversion'],
 '#hist-this': ['Only the EQs for the measurement you have now.', 'history'],
 'history.keep': ['Which EQs History keeps between sessions.', 'history'],
 'history.eqd_before': ["Says under Measurement when you've EQ'd it before.", 'history'],
 'site.profile': ['Which squiglink website is copied exactly.', 'website-autoeq'],
 'site.normalization': ['How curves are lined up in level.', 'level-matching', 'phon'],
 'site.norm_hz': ['The frequency curves are lined up at.', 'level-matching'],
 'site.norm_db': ['The loudness curves are set to in dB mode.', 'phon'],
 'site.treble_start_from': ["A hidden detail of the website's AutoEQ.", 'website-autoeq'],
 'site.sample_rate': ['The sample rate the filter maths assumes.', 'sample-rate'],
 'site.smooth_level': ['How much curves are smoothed.', 'smoothing'],
 'site.scale_smoothing': ["The website's smoothing scale.", 'smoothing'],
 'site.phon_table': ['Which equal-loudness tables dB mode uses.', 'phon'],
 'library.folders': ['Folders on this PC searched for curve files.', 'databases'],
 'databases': ['The online databases the search list uses.', 'databases', 'rig-tags'],
 'performance.cores': 'How many CPU threads a run uses.',
 '#target-adjust': ['Shapes the target to taste: tilt, bass, half-tilt, ear gain, treble and air, each with − and +.',
                    'target-adjustments'],
 '#target-save': 'Keeps the target as adjusted as a target of your own, in use; the adjustments go back to 0.',
 '#compare-results': 'Two EQs side by side: on the graph, their numbers and their filters.',
 '#queue': 'EQs for several IEMs or targets in one go, each saved and kept in History.',
 '#eq-graph': ["The EQ itself: drag a filter's handle for its frequency and gain, the mouse wheel for its Q.",
               'by-hand',
               'q'],
 '#by-hand': ['Make the EQ yourself: empty, a copy of the selected EQ, an EQ file, pasted filters or a profile.',
              'by-hand',
              'peaking-filter',
              'shelf'],
 '#hand-close': ['Back to what was shown before this EQ by hand: the run you had, or none.', 'by-hand'],
 '#use-try': ['Plays the EQ on a device for 5 minutes in every app, then Keep it or let its own EQ come back.',
              'q-try']}

SETTINGS_EQ = [{'title': 'Choosing and running',
                'items': [{'key': 'slot:target',
                           'title': 'Target',
                           'body': ['The sound you want your earphone to have: a target curve (Harman, diffuse field, '
                                    "a reviewer's own). Pick one from the app, this PC or the online databases; the "
                                    'EQ is fitted to match it.']},
                          {'key': 'slot:measurement',
                           'title': 'Measurement',
                           'body': ["Your IEM or headphone's frequency response, from the app, this PC or the online "
                                    'databases (press / to search). Its ticked files (left, right, seatings) are '
                                    'averaged. Several to choose from? “Other measurements of this model” ranks '
                                    'them.']},
                          {'key': 'eq_app',
                           'title': 'Your EQ app',
                           'body': ['The app or device that will play the EQ. Its own limits are kept (how many '
                                    "bands; the gain, Q and frequency ranges; a graphic EQ's sliders) and Save "
                                    'filters writes exactly the file it imports. The line below says how to load the '
                                    'EQ, with a link to where its limits come from. Not listed, or not sure: any '
                                    'filters, saved as an Equalizer APO file, which many apps read.']},
                          {'key': 'slot:method',
                           'title': 'EQ method',
                           'body': ['How the filters are found. Best fit (for any EQ app) fits them directly to the '
                                    "target. The Website methods reproduce squig.link's AutoEQ exactly, for typing "
                                    'into the site. Your EQ app chooses it for you.']},
                          {'key': 'sa',
                           'title': 'Search',
                           'body': ['What the next run tries and how long it should take on this PC. Best fit adds '
                                    'filters one at a time under every boost and Q limit that suits your curves, each '
                                    'with two fighting-filter penalties, until the EQ sounds the same as the target. '
                                    'Seconds for most IEMs, up to about a minute and a half when the target is out of '
                                    'reach.']},
                          {'key': '#auto-on',
                           'title': 'Automatic settings',
                           'body': ["Fits the method's settings to your measurement and target: the scored range, "
                                    'filter counts, boost and cut, Q limits, shelves. A setting you change is marked '
                                    '“yours” and kept. Off: every setting is used exactly as it is.',
                                    'Advanced has the rest, all set for you the same way.']},
                          {'key': 'rig_convert.enabled',
                           'title': "Convert the target to the measurement's rig",
                           'body': ['Your measurement and target come from different rigs, which measure the same '
                                    'earphone differently (mostly above 2 kHz). On: the target is converted to the '
                                    "measurement's rig, so the EQ fixes the earphone, not the difference between "
                                    'rigs. Off: the target is used as made.']}]},
               {'title': 'Target › Adjust',
                'items': [{'key': 'target_adjust.tilt',
                           'title': 'Tilt (dB/oct)',
                           'body': ['Tilts the whole target, in dB per octave. Negative makes it darker (more bass '
                                    'against the treble), positive brighter. Small values go far: −0.5 shifts the two '
                                    'ends of the graph about 5 dB apart.']},
                          {'key': 'target_adjust.bass_gain',
                           'title': 'Bass shelf (dB)',
                           'body': ['Adds a bass shelf to the target: + for more bass, − for less. The adjustment '
                                    'most people change first; +2 to +6 dB is common.']},
                          {'key': 'target_adjust.bass_freq',
                           'title': 'Bass shelf: Freq (Hz)',
                           'body': ["The bass shelf's corner: the bass below it is raised or lowered. Lower (e.g. 60 "
                                    'Hz) changes only the deepest bass; higher (e.g. 150 Hz) reaches into the upper '
                                    'bass.']},
                          {'key': 'target_adjust.bass_q',
                           'title': 'Bass shelf: Q',
                           'body': ["How steep the bass shelf's step is. 0.707 is a standard, gentle shelf; higher "
                                    'values make a sharper step with a small bump at the corner.']},
                          {'key': 'target_adjust.halftilt_gain',
                           'title': 'Half-tilt (dB)',
                           'body': ['A gentle shelf that raises (+) or lowers (−) everything above its frequency by '
                                    'this much: a softer way to brighten or darken the upper half of the sound than '
                                    'Tilt.']},
                          {'key': 'target_adjust.halftilt_freq',
                           'title': 'Half-tilt: Freq (Hz)',
                           'body': ['Where the half-tilt shelf is centred: everything well above it moves by its '
                                    'gain.']},
                          {'key': 'target_adjust.ear_gain',
                           'title': 'Ear gain (dB)',
                           'body': ['Raises (+) or lowers (−) the ear-gain region, the 2-5 kHz rise every target has. '
                                    'Lower it if voices and instruments sound shouty, raise it if they sound '
                                    'distant.']},
                          {'key': 'target_adjust.ear_freq',
                           'title': 'Ear gain: Freq (Hz)',
                           'body': ['The centre of the ear-gain change, usually around 3 kHz.']},
                          {'key': 'target_adjust.ear_q',
                           'title': 'Ear gain: Q',
                           'body': ['How wide the ear-gain change is: a higher Q is a narrower band around its '
                                    'frequency.']},
                          {'key': 'target_adjust.treble_gain',
                           'title': 'Treble (dB)',
                           'body': ['A treble shelf added to the target: + for brighter and more detail, − for '
                                    'smoother and less sharp.']},
                          {'key': 'target_adjust.treble_freq',
                           'title': 'Treble: Freq (Hz)',
                           'body': ['Where the treble shelf starts: the treble above it is raised or lowered.']},
                          {'key': 'target_adjust.treble_q',
                           'title': 'Treble: Q',
                           'body': ["How steep the treble shelf's step is (0.707 is a standard shelf)."]},
                          {'key': 'target_adjust.air_gain',
                           'title': 'Air (dB)',
                           'body': ['A shelf for the “air” above about 10 kHz: sparkle and a sense of space. '
                                    'Measurements up there are unreliable, so judge it by ear.']},
                          {'key': 'target_adjust.air_freq',
                           'title': 'Air: Freq (Hz)',
                           'body': ['Where the air shelf starts.']},
                          {'key': 'target_adjust.air_q',
                           'title': 'Air: Q',
                           'body': ["How steep the air shelf's step is (0.707 is a standard shelf)."]}]},
               {'title': 'Best fit',
                'items': [{'key': 'best_fit.filter_counts',
                           'title': 'Filter counts to try',
                           'body': ['How many peaking filters to try, e.g. 1-10 or 4, 6, 8: each count is a result '
                                    '(made one filter at a time up to the most), and Scoring picks the simplest that '
                                    'sounds the same as the target. With your own filters kept: '
                                    'how many to add. Automatic settings go up to where fits stop improving.']},
                          {'key': 'best_fit.low_shelf',
                           'title': 'Low shelf',
                           'body': ['Also fit a low shelf: a broad lift or cut of the bass below a corner frequency. '
                                    'It helps when the bass is off as a whole; automatic settings turn it on when '
                                    "it's 3 dB or more off."]},
                          {'key': 'best_fit.freq_range',
                           'title': 'Filters from … to (Hz)',
                           'body': ['Where peaking filters may go (from … to). Filters outside the scored range '
                                    "aren't judged, so this usually reaches above it."]},
                          {'key': 'best_fit.gain_min',
                           'title': 'Max cut (dB)',
                           'body': ['The deepest cut a filter may have, in dB.']},
                          {'key': 'best_fit.gain_max',
                           'title': 'Max boost values (dB)',
                           'body': ['The biggest boost a filter may have, in dB. Each value listed is tried, e.g. 6, '
                                    '9: smaller boosts need less pre-amp.']},
                          {'key': 'best_fit.q_min',
                           'title': 'Q from',
                           'body': ['The broadest filter allowed (the lowest Q). Q 0.5 spans several octaves.']},
                          {'key': 'best_fit.q_max',
                           'title': 'Q max values',
                           'body': ['The narrowest filter allowed (the highest Q). Each value listed is tried, e.g. '
                                    '3, 5. Narrow filters match sharp peaks but can miss them when your fit differs '
                                    "from the measurement's."]},
                          {'key': 'best_fit.low_shelf_freq',
                           'title': 'Low shelf (Hz)',
                           'body': ["The range the low shelf's corner may move in while fitting (from … to)."]},
                          {'key': 'best_fit.fight_penalty',
                           'title': 'Fighting-filter penalties',
                           'body': ['Makes filters that cancel each other (a boost on top of a cut) count against a '
                                    'result: they add sensitivity, not accuracy. 0 = off. Each value listed is tried '
                                    'with every boost and Q limit (automatic: 0.003 and 0.01; a lighter penalty leaves '
                                    'the fit freer, which found fewer filters for most IEMs but not all).']},
                          {'key': 'best_fit.start_keep',
                           'title': 'Keep them exactly as they are (your own filters)',
                           'body': ['On: your filters stay exactly as they are and Best fit adds filters to them. '
                                    'Off: yours are where the fit starts, and it may move them too. Either way one '
                                    'more result shows yours alone.']}]},
               {'title': "Advanced › Layout and a graphic EQ's bands",
                'items': [{'key': 'best_fit.layout',
                           'title': 'Layout',
                           'body': ['What the EQ is for, so Best fit keeps to it. Any filters: an app that takes any '
                                    "(Equalizer APO, Peace…). Fixed bands: a graphic EQ's sliders, only their gains "
                                    "fitted. An EQ app's own: its number of filters and its ranges. Your EQ app sets "
                                    'this.']},
                          {'key': 'best_fit.bands.freqs',
                           'title': 'Band frequencies (Hz)',
                           'body': ["Your graphic EQ's slider frequencies in Hz, as printed under its sliders, e.g. "
                                    '31, 62, 125, 250, 500, 1000, 2000, 4000, 8000, 16000.']},
                          {'key': 'best_fit.bands.q',
                           'title': 'Q of each band',
                           'body': ['How wide every band is (Q): 1.41 for octave-spaced sliders (10 bands), 2.15 for '
                                    "2/3-octave (15), 4.32 for 1/3-octave (31). Use your app's own value if its "
                                    'manual gives one.']},
                          {'key': 'best_fit.bands.gain_min',
                           'title': 'Sliders from (dB)',
                           'body': ["The sliders' lowest setting, in dB (e.g. −12)."]},
                          {'key': 'best_fit.bands.gain_max',
                           'title': 'Sliders to (dB)',
                           'body': ["The sliders' highest setting, in dB (e.g. +12)."]},
                          {'key': 'best_fit.bands.step',
                           'title': 'Slider step (dB)',
                           'body': ["The sliders' step in dB (1, 0.5 or 0.1): every gain is a whole number of steps, "
                                    'so what you set is exactly what was scored.']}]},
               {'title': 'Scoring',
                'items': [{'key': 'scoring.band_hz',
                           'title': 'Score from … to (Hz)',
                           'body': ['The frequency range the error is measured over (from … to); outside it the EQ is '
                                    "free. Automatic settings stop where the measurement's seatings stop agreeing, "
                                    'often about 10 kHz.']},
                          {'key': 'scoring.pick',
                           'title': 'Pick',
                           'body': ['Which result wins. Simplest that sounds the same as the target (the automatic '
                                    "settings' choice): the simplest result whose sound is within the audible limit "
                                    "of the target everywhere, judged as the ear hears it (the difference smoothed to "
                                    "the ear's resolution, the overall level left out). When none can get that close "
                                    "(your EQ app's limits, or a measurement filters can't follow), the simplest that "
                                    'sounds the same as the closest result, and the result card says how far off it '
                                    'is and where.',
                                    'Lowest error: the closest match, however many filters it takes.']},
                          {'key': 'scoring.ear_db',
                           'title': 'Audible limit (dB)',
                           'body': ['How far, in dB, a result may sound from the target (or from the closest result, '
                                    'when the target is out of reach) and still count as the same: the largest '
                                    'difference anywhere, smoothed to the ear\'s resolution. 0.25 dB is about the '
                                    'smallest broad change listeners noticed in pink noise (Toole and Olive, 1988), so '
                                    'below it nothing should be audible; with music about 0.5 dB.']}]},
               {'title': 'Website AutoEQ: one run',
                'items': [{'key': 'site_single.rows',
                           'title': 'Filter rows',
                           'body': ["The site's “Filter rows”: the most filters its AutoEQ may use. More rows match "
                                    'closer but mean more to type in.']},
                          {'key': 'site_single.freq_low',
                           'title': 'Frequency from … to',
                           'body': ["The site's “Frequency Range” (from … to): where its AutoEQ may place filters. "
                                    'Type the same values on the site.']},
                          {'key': 'site_single.gain_min',
                           'title': 'Gain from … to (dB)',
                           'body': ["The site's “Gain Range” (from … to): the largest cut and boost each filter may "
                                    'have, in dB.']},
                          {'key': 'site_single.q_min',
                           'title': 'Q from … to',
                           'body': ["The site's “Q Range” (from … to): from how broad (low Q) to how narrow (high Q) "
                                    'its filters may be. The site stops at Q 5.']}]},
               {'title': 'Website AutoEQ: find best settings',
                'items': [{'key': 'site_sweep.filter_rows',
                           'title': 'Filter rows to try',
                           'body': ['Filter-row counts to try, e.g. 4-10 or 4, 6, 8. Each is run with every '
                                    'combination of the lists below; Scoring picks the winner.']},
                          {'key': 'site_sweep.freq_low',
                           'title': 'Frequency from',
                           'body': ["Where every run's “Frequency Range” starts."]},
                          {'key': 'site_sweep.freq_high',
                           'title': 'Frequency “to” values',
                           'body': ['Where the “Frequency Range” ends, a list to try, e.g. 8000, 12000. Lower ends '
                                    'keep filters out of the unreliable treble.']},
                          {'key': 'site_sweep.gain_ranges',
                           'title': 'Gain ranges',
                           'body': ['Gain ranges to try, each as min..max, e.g. -12..6, -12..9: each is a “Gain '
                                    'Range” to type into the site.']},
                          {'key': 'site_sweep.q_min',
                           'title': 'Q from',
                           'body': ["Where every run's “Q Range” starts (the broadest filter allowed)."]},
                          {'key': 'site_sweep.q_max',
                           'title': 'Q “to” values',
                           'body': ['Where the “Q Range” ends, a list to try (the narrowest filter allowed). The site '
                                    'stops at Q 5.']}]},
               {'title': 'The result',
                'items': [{'key': 'res.error',
                           'title': 'Error',
                           'body': ["How far the EQ'd curve is from the target over the scored range (dB, root mean "
                                    'square). Under about 0.5 dB is a very close match.']},
                          {'key': 'res.preamp',
                           'title': 'Pre-amp',
                           'body': ["The volume cut this EQ needs so its boosts can't clip. Set it in your EQ app; "
                                    'most saved files include it.']},
                          {'key': 'res.maxq',
                           'title': 'Max Q',
                           'body': ["The narrowest filter's Q. Above about 5, a filter is sensitive to how the "
                                    'earphone sits.']},
                          {'key': 'res.boost', 'title': 'Max boost', 'body': ['The biggest boost of any one filter.']},
                          {'key': 'fcounts',
                           'title': 'Fewer or more filters',
                           'body': ["This run's best result for each number of filters: fewer filters (simpler to "
                                    'enter) or a closer match, one click away.']},
                          {'key': 'f_retry',
                           'title': 'Retry from these filters',
                           'body': ['Runs Best fit again from the filters shown, for this run only. Fine-tune them: '
                                    'each moves a little to match closer. Keep them, add filters: yours stay exactly '
                                    'and more are added.']},
                          {'key': '#eq-graph',
                           'title': 'The EQ graph: editing on the curve',
                           'body': ["Under the graph: the EQ shown, with a handle for each of its filters, numbered "
                                    "as in the table, on the filter's own curve at its frequency (a shelf's handle "
                                    'half way up its shelf). Drag one: left and right moves its frequency, up and '
                                    'down its gain. The mouse wheel over it: its Q (up: narrower). Right-click it: '
                                    'Peak, Low shelf or High shelf, Switched on, Remove. Double-click where there is '
                                    'no handle: a new filter there (with no EQ shown, an EQ by hand begins with it).',
                                    'While you drag, the curves, the numbers, the table and what Listen plays follow; '
                                    'the scale stays put until you let go. An EQ you are trying on a device (Use on '
                                    'device › Try for 5 minutes on) plays each change there too, in every app. The '
                                    'table and the sliders do the same by keyboard.']},
                          {'key': '#by-hand',
                           'title': 'By hand',
                           'body': ['Beside Run: an EQ you make yourself, shown on the result card as a run of its '
                                    'own, so Save filters, Copy, Use on device, Listen and the rest work as for any '
                                    'result. Start empty, as a copy of the selected EQ, or from an EQ you have: an EQ '
                                    "file (Equalizer APO, AutoEq, squig.link, Room EQ Wizard's export, a Peace preset), "
                                    "pasted filters or a device's profile. Files are read as Equalizer APO plays them; "
                                    "what an EQ here can't have (other filter types, a graphic EQ…) is said, never "
                                    'left out without a word.',
                                    'A measurement and target are optional: chosen, the graph shows your IEM with the '
                                    'EQ and the error. Begun from a profile, Use on device › Update puts it back into '
                                    'that profile. Close, on its result card, goes back to what was shown before.']},
                          {'key': '#hand-close',
                           'title': 'Close (an EQ by hand)',
                           'body': ['On an EQ by hand\'s result card, at the right of its title: back to '
                                    'what was shown before you began it, the run you had, or none, the page as it '
                                    'was.',
                                    'An EQ by hand you changed stays in Runs this session, to come back to as you '
                                    'left it (Remove there takes it off); one empty or as it began just goes, as there '
                                    'is nothing in it to lose. Save filters keeps it for good.']},
                          {'key': 'x_name',
                           'title': 'File name',
                           'body': ['The name of the saved files; each adds its own ending (“ - filters.txt”, “ - '
                                    'Poweramp.json”…). At first it names the measurement, the target, the method and '
                                    'the filter count; type your own to change it (empty the box for the automatic '
                                    'name again). It names the report too. A file of that name already in your Saved '
                                    'EQs folder is only replaced if you say so.']}]},
               {'title': 'Saved files',
                'items': [{'key': 'export.apo',
                           'title': 'Equalizer APO / squiglink filters (.txt)',
                           'body': ['A plain text EQ file, the most widely read: Equalizer APO and Peace (Windows), '
                                    'EasyEffects (Linux: Equalizer › Import Preset › APO; up to 32 filters) and '
                                    "squiglink's Import (up to 20)."]},
                          {'key': 'export.graphic',
                           'title': 'GraphicEQ (.txt)',
                           'body': ['A GraphicEQ line (the EQ as a whole curve): Wavelet and RootlessJamesDSP '
                                    '(Android) and other apps that take a response curve.']},
                          {'key': 'export.poweramp',
                           'title': 'Poweramp preset (.json)',
                           'body': ['Poweramp or Poweramp Equalizer (Android): copy it to the phone, then Presets › '
                                    'Import in the equalizer. Bands reach ±15 dB and Q 12; pre-amp included.']},
                          {'key': 'export.uapp',
                           'title': 'USB Audio Player PRO preset (.xml)',
                           'body': ["USB Audio Player PRO's parametric EQ (Android): copy it into the TBEQPresets "
                                    "folder in UAPP's folder. At most 10 peaking filters and no shelves: an EQ beyond "
                                    'that gets no file.']},
                          {'key': 'export.soundsource',
                           'title': 'SoundSource (.txt)',
                           'body': ['SoundSource (macOS): add it with Headphone EQ › Add Other Profile… (up to 32 '
                                    'filters; pre-amp included).']},
                          {'key': 'export.voicemeeter',
                           'title': 'Voicemeeter (.xml)',
                           'body': ["A Voicemeeter bus (Windows): open the bus's EQ, right-click its top bar › Load "
                                    'EQ Settings. 6 filters, boosts up to +18 dB. No pre-amp in the file: lower the '
                                    "bus's gain by it."]},
                          {'key': 'export.rockbox',
                           'title': 'Rockbox preset (.cfg)',
                           'body': ['Music players running Rockbox: copy it onto the player, then Sound Settings › '
                                    'Equalizer › Browse EQ Presets. A low shelf, 8 peaking filters and a high shelf; '
                                    'Q up to 6.4, ±24 dB.']},
                          {'key': 'export.convolution',
                           'title': 'Convolution impulse response (.wav)',
                           'body': ['The EQ as an impulse response (.wav, 32-bit float, stereo) for any convolution '
                                    "EQ: Viper4Android, JamesDSP, EasyEffects' Convolver, Roon, foobar2000, HQPlayer, "
                                    "Equalizer APO. Exactly the filters' sound, any number of them, pre-amp "
                                    'included.']},
                          {'key': 'export.convolution_rate',
                           'title': 'Impulse response sample rate',
                           'body': ['Must match the rate your player or device plays at (most often 48000 or 44100), '
                                    'or the EQ lands at slightly wrong frequencies.']},
                          {'key': 'export.report',
                           'title': 'An HTML report',
                           'body': ['An HTML page with the graph and the filters: handy for typing the filters into '
                                    'an app by hand, or as a record.']},
                          {'key': 'export.preamp_rounding',
                           'title': 'Pre-amp rounding',
                           'body': ['How the pre-amp is rounded to 0.1 dB in saved files. Safe: always down, so it '
                                    'can never clip. Like squiglink: as the site rounds it (up to 0.05 dB short).']},
                          {'key': 'export.extra_headroom',
                           'title': 'Extra headroom (dB)',
                           'body': ['An extra cut on top of the pre-amp, in dB, e.g. when your player or another '
                                    'effect also boosts. 0 = none.']},
                          {'key': 'export.q_decimals',
                           'title': 'Q decimals in saved files',
                           'body': ['How many decimals Q gets in saved files. 3 is plenty: a 4th changes an EQ by at '
                                    'most 0.003 dB.']}]},
               {'title': 'The graph and Listen',
                'items': [{'key': '#opt-view',
                           'title': 'View',
                           'body': ["Absolute: the curves as they are. Relative to target: each curve's difference "
                                    "from the target, so 0 dB is a perfect match and what's left is easy to see."]},
                          {'key': '#opt-y',
                           'title': 'Y range',
                           'body': ['How tall the dB scale is: a smaller range shows more detail. Auto fits the '
                                    'curves.']},
                          {'key': '#opt-ch',
                           'title': 'Channels',
                           'body': ["Also draws each of the measurement's files (channels, seatings) behind their "
                                    'average, to see how much they differ.']},
                          {'key': '#snd-src',
                           'title': 'Sound',
                           'body': ['What to play: a short synth groove, pink or white noise, a 20 Hz-20 kHz sweep, a '
                                    'tone (its frequency shows on the graph) or your own file (Your own file…: mp3, '
                                    'flac, wav, ogg …).']},
                          {'key': '#tone-from',
                           'title': 'Tone: from … to',
                           'body': ["The tone's range: the slider beside them moves the tone between these "
                                    'frequencies (Hz).']},
                          {'key': '#snd-vol',
                           'title': 'Volume',
                           'body': ["Start low: an EQ's boosts can make things much louder."]},
                          {'key': '#snd-lm',
                           'title': 'Level-matched (Listen)',
                           'body': ['Plays every version equally loud, so you compare tone, not volume (louder tends '
                                    'to sound better).']},
                          {'key': '#snd-blind',
                           'title': 'Blind test',
                           'body': ["Hides which version is which until you press Reveal, so expectations don't "
                                    'decide what you hear.']},
                          {'key': '#snd-abx',
                           'title': 'ABX test',
                           'body': ['Whether you can really hear a difference between two versions: choose A and B '
                                    '(EQ off, the selected EQ, any EQ to compare) and how many trials, then Start '
                                    'ABX. Each trial X is A or B at random; Listen to A, B and X as often as you '
                                    'like, then say X is A or X is B. Nothing says whether you were right until '
                                    'the end.',
                                    'Then: how many you got right, and how often guessing alone gets that many '
                                    'or more. Under 5 %, you can tell them apart; above it, that score could be '
                                    'luck (a longer test can show a small difference). While it runs Listen is '
                                    'level-matched with both ears the same, and the version buttons and keys 1–9 '
                                    'are put away (they would give X away). Stop the test says what you answered '
                                    'so far; so does changing A or B while it runs (an edit, another result shown), '
                                    'which ends it. The results are kept until you close AutoEQ Studio.']},
                          {'key': '#snd-ears',
                           'title': 'Ears',
                           'body': ['The same version in both ears (switch with the buttons or keys 1–9), or a '
                                    'different version in each ear, e.g. no EQ on the left and the EQ on the right. '
                                    'Swap sides too: your two ears differ.']},
                          {'key': '#snd-left', 'title': 'Left', 'body': ['What your left ear hears.']},
                          {'key': '#snd-right',
                           'title': 'Right',
                           'body': ['What your right ear hears. Swap swaps the sides.']},
                          {'key': 'snd_list',
                           'title': 'Your EQs to compare',
                           'body': ['EQs to hear side by side on this IEM or headphone: each is a version above (keys '
                                    '1–9) and, while Graph is ticked, a curve on the graph. Add the EQ on the result '
                                    'card (Keep to compare, or “The selected EQ” under the list), one from History '
                                    '(Keep to compare), an EQ file (read as By hand reads it: Equalizer APO, Room EQ '
                                    'Wizard, Peace) or pasted filters. Edit a name to rename it. Each '
                                    'measurement has its own list, kept between sessions (up to 12).']}]},
               {'title': 'Finding curves and History',
                'items': [{'key': '#pk-anykind',
                           'title': 'Targets and measurements',
                           'body': ['Also lists files that look like the other kind (a measurement while you choose a '
                                    'target, or the other way round), in case one was taken for the wrong kind.']},
                          {'key': 'pk_filters',
                           'title': 'Rig, Type and Source filters',
                           'body': ['Narrow a long list. Rig: one rig only (for a measurement, first “Fits your '
                                    "target's rig”). Type: IEM, headphone or earbud. Source: one database, the app or "
                                    "this PC. Each choice shows how many results it leaves; they're remembered. The "
                                    "choices are A to Z, and each list opens with a search box: type part of a name "
                                    "(every word must be there), then click it or press Enter."]},
                          {'key': '#pk-f-sure',
                           'title': 'Stated rig',
                           'body': ['Hides entries whose rig is only a guess (their tag ends in “?”).']},
                          {'key': '#pk-f-dl',
                           'title': 'Downloadable',
                           'body': ["Hides entries that only open on their own site (Hangout.Audio doesn't let other "
                                    'programs download its files).']},
                          {'key': '#cmp-q',
                           'title': 'Model (which measurement to use)',
                           'body': ['The model to look for. Every word must be in a name, so fewer words find more '
                                    '(e.g. “Blessing 2” rather than the full name).']},
                          {'key': '#cmp-rig',
                           'title': 'Target is made for',
                           'body': ['The rig your target was made for, worked out from its name or source. Change it '
                                    "if that's wrong: the ranking counts how well each measurement's rig converts to "
                                    'it.']},
                          {'key': '#hist-this',
                           'title': 'This IEM only',
                           'body': ['Only the EQs made for the measurement you have now.']},
                          {'key': 'history.keep',
                           'title': 'History keeps',
                           'body': ["What History (by the graph's title) keeps between sessions: the EQs you save or "
                                    "copy, or every run's result as well."]},
                          {'key': 'history.eqd_before',
                           'title': "Say under Measurement when you've EQ'd it before",
                           'body': ["Under Measurement, a line says how often you've EQ'd that IEM or headphone "
                                    'before, with a link to those EQs.']}]},
               {'title': 'Advanced › Website',
                'items': [{'key': 'site.profile',
                           'title': 'Which website to copy',
                           'body': ["Which squiglink site's graph tool is copied exactly (its smoothing, level "
                                    "matching and AutoEQ details). Choose the one you'll type results into: "
                                    'listener800 or squig.link.',
                                    'Changing one of the details below it makes the choice “Custom”.']},
                          {'key': 'site.normalization',
                           'title': 'Level matching',
                           'body': ["How curves are lined up in level before they're compared. Hz~: the average over "
                                    '4 octaves around a frequency (listener800). Hz: one frequency. dB: the same '
                                    'loudness in phon (squig.link).']},
                          {'key': 'site.norm_hz',
                           'title': 'Around (Hz)',
                           'body': ['The frequency curves are lined up at (Hz and Hz~ modes), usually 500 Hz.']},
                          {'key': 'site.norm_db',
                           'title': 'Loudness (phon)',
                           'body': ['The loudness every curve is set to in dB mode, in phon; squig.link uses 60, a '
                                    'normal listening level.']},
                          {'key': 'site.treble_start_from',
                           'title': 'AutoEQ TrebleStartFrom (Hz)',
                           'body': ["A hidden detail of the site's AutoEQ: its first pass ignores filters above this "
                                    'frequency (listener800 15000, squig.link 7000). Change it only to copy another '
                                    'site.']},
                          {'key': 'site.sample_rate',
                           'title': 'Sample rate',
                           'body': ['The sample rate the filter maths assumes. The site uses 48000; it changes only '
                                    'the very top of the treble, slightly.']},
                          {'key': 'site.smooth_level',
                           'title': 'Smoothing level',
                           'body': ['How much the site smooths curves before lining them up; 0 = none. Copy your '
                                    "site's value."]},
                          {'key': 'site.scale_smoothing',
                           'title': 'Smoothing scale',
                           'body': ["The site's smoothing scale (listener800: 0.2). Copy your site's value."]},
                          {'key': 'site.phon_table',
                           'title': 'Loudness tables',
                           'body': ["The equal-loudness tables used in dB mode: listener800's ISO 226:2023 or "
                                    "squig.link's ISO 226:2003."]}]},
               {'title': 'Advanced › This PC',
                'items': [{'key': 'performance.cores',
                           'title': 'CPU cores',
                           'body': ['How many CPU threads a run uses. 0 = all but one, never more than the free '
                                    'memory allows. Lower it to keep the PC responsive during long runs.']}]},
               {'title': 'Find… › Sources',
                'items': [{'key': 'library.folders',
                           'title': 'Folders to search',
                           'body': ['Folders searched for curve files, one per line, with their subfolders. Empty: '
                                    "your Downloads, Documents, Desktop and Music. The app's own downloads folder "
                                    'is left out: those curves are the online databases\' entries, which use the '
                                    'copy on this PC (offline too).']},
                          {'key': 'databases',
                           'title': 'Online databases',
                           'body': ['Every online database the search list uses. Turn one off to leave it out; the '
                                    'lists refresh every few days by themselves. Add a database: one from '
                                    "squig.link's list, or any squig.link-style page."]}]},
               {'title': 'Run several',
                'items': [{'key': '#queue',
                           'title': 'Run several… (a queue)',
                           'body': ['Tick IEMs and targets: an EQ is made for each IEM with each target, one after '
                                    'another, with the settings and method you have now (the automatic settings worked '
                                    'out for each). Each picked result is saved into your Saved EQs folder under its '
                                    'automatic name (never over a file), kept in History and in Runs this session. '
                                    'Cancel stops the run going on and the rest; your own choice of files stays as it was.']}]},
               {'title': 'Your result: comparing',
                'items': [{'key': '#compare-results',
                           'title': 'Compare… (two EQs side by side)',
                           'body': ['Any two of: the result shown now (as edited), the best result for each filter '
                                    'count of this session\'s runs, and this IEM\'s History. Both are drawn with the '
                                    'EQ on your measurement and target as they are now, with their error in the scored '
                                    'range, filters, pre-amp, biggest boost and Q, how far apart they are, and their '
                                    'filters side by side. Show A / Show B put a result of this session back on the '
                                    'result card.']}]},
               {'title': 'Target › Adjust: your own target',
                'items': [{'key': '#target-adjust',
                           'title': 'Adjust (on the Target card)',
                           'body': ['Opens the target adjustments under the target: tilt, bass, half-tilt, ear gain, '
                                    'treble and air (listener800\'s Custom DF), one row each. Amount: how much (+ '
                                    'raises, − lowers; for the tilt, − is darker and + brighter); − and + (or ↑ ↓ and '
                                    'the mouse wheel in the box) change it a step at a time, and the graph follows. '
                                    'Hz: where it acts (a shelf from there on, the ear gain around it). Q: how steep '
                                    'a shelf is, or how wide the ear gain. Hz and Q are greyed while the amount is 0, '
                                    'since they do nothing then. Beside Adjust, what is adjusted. Reset adjustments '
                                    'puts them all back to 0 (Undo, beside the message at the bottom of the window, '
                                    'brings them back).'],
                           'see': ['target-adjustments']},
                          {'key': '#target-save',
                           'title': 'Save as a target…',
                           'body': ['Shown once the target is adjusted (tilt, bass, ear gain, treble …). It saves the '
                                    'target as adjusted as a target of your own (in the app\'s targets, under the name '
                                    'you give), puts it in use and sets the adjustments back to 0, since they are in it '
                                    'now. It is made for the original target\'s rig and converted for a measurement '
                                    'the same way. Undo, beside the message at the bottom of the window, puts '
                                    'everything back.']}]},
               {'title': 'Presets',
                'items': [{'key': '#presets',
                           'title': 'Presets (top bar, on Make an EQ)',
                           'body': ['A preset keeps every setting of Make an EQ under a name: your EQ app, the method, '
                                    'the automatic settings and your own values, the target adjustments, '
                                    'scoring, Advanced. Not your files: the target and measurement stay as they are. '
                                    'Keep one per use, e.g. one for the website and one for Equalizer APO.',
                                    'Save current settings as… asks for a name (the same name again replaces that '
                                    'preset); click a preset to load all its settings, and Undo, beside the message at the bottom, puts the '
                                    'ones before back. Delete a preset removes one; Reset all settings… puts every '
                                    'setting back to its default (your files and presets are kept). Presets are files '
                                    'in your Presets folder (Settings › Your files).']}]}]
