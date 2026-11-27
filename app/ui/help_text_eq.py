"""The help words for Make an EQ and its windows (Find…, Other measurements of this model, Listen, History, Queue,
Compare…, the target's Adjust): HELP_EQ, each setting's or control's line by its key (its tooltip, with the ids
of its "See also" entries in Help), and SETTINGS_EQ, their groups in Help's All settings (the first 18, in the
page's order). help_texts.py joins them with the other screens'. Words only: nothing is imported here.
"""
# flake8: noqa

HELP_EQ = {'slot:target': ['Desired frequency response for your IEM or headphone', 'target', 'rig'],
 'slot:measurement': ['Measured frequency response of your IEM or headphone',
                      'measurement',
                      'seatings',
                      'compare-measurements'],
 'eq_app': ['Sets filter limits and export format for your EQ app or device',
            'eq-app',
            'layout',
            'file-formats'],
 'slot:method': ['How EQ filters are calculated', 'best-fit', 'website-autoeq', 'q-which-method'],
 'sa': ['', 'speed-accuracy', 'best-fit'],
 '#auto-on': ['Auto-sets frequency range, filter counts, and gain/Q limits; preserves your manual edits', 'automatic-settings', 'q-yours'],
 'rig_convert.enabled': ['Compensates for rig differences so the EQ corrects the device, not the rig', 'rig-conversion', 'rig', 'q-rigs'],
 'target_adjust.tilt': ['Tilts the full target: − gives more bass, + gives more treble', 'target-adjustments'],
 'target_adjust.bass_gain': ['Boosts (+) or cuts (−) bass on the target', 'target-adjustments', 'shelf'],
 'target_adjust.bass_freq': ['Corner frequency for the bass shelf', 'shelf'],
 'target_adjust.bass_q': ['Slope of the bass shelf', 'shelf', 'q'],
 'target_adjust.halftilt_gain': ['Gradually boosts (+) or cuts (−) everything above the set frequency',
                                 'target-adjustments'],
 'target_adjust.halftilt_freq': 'Center frequency of the half-tilt',
 'target_adjust.ear_gain': ['Boosts (+) or cuts (−) ear gain around 2–5 kHz', 'target-adjustments'],
 'target_adjust.ear_freq': 'Center frequency of the ear-gain filter',
 'target_adjust.ear_q': ['Width of the ear-gain filter', 'q'],
 'target_adjust.treble_gain': ['Boosts (+) or cuts (−) treble on the target', 'target-adjustments', 'shelf'],
 'target_adjust.treble_freq': 'Corner frequency for the treble shelf',
 'target_adjust.treble_q': ['Slope of the treble shelf', 'shelf'],
 'target_adjust.air_gain': ['Boosts (+) or cuts (−) upper treble (“air”) above ~10 kHz', 'treble-limit'],
 'target_adjust.air_freq': 'Corner frequency for the air shelf',
 'target_adjust.air_q': ['Slope of the air shelf', 'shelf'],
 'best_fit.filter_counts': ['', 'simplest', 'peaking-filter', 'q-filters'],
 'best_fit.low_shelf': ['Include a low-shelf filter; useful when the entire bass region needs adjustment', 'shelf'],
 'best_fit.freq_range': ['', 'scored-range'],
 'best_fit.gain_min': ['', 'db'],
 'best_fit.gain_max': ['', 'preamp'],
 'best_fit.q_min': ['', 'q'],
 'best_fit.q_max': ['', 'q', 'unit-variation'],
 'best_fit.low_shelf_freq': ['', 'shelf'],
 'best_fit.fight_penalty': ['Penalizes overlapping boost and cut filters (0 = off)', 'penalties'],
 'best_fit.start_keep': ['Off: Best fit starts from your filters and may adjust them', 'own-filters'],
 'best_fit.start_filters': ['', 'own-filters', 'q-have-eq'],
 'best_fit.layout': ['', 'layout', 'fixed-bands'],
 'best_fit.bands.freqs': ['Center frequencies for each graphic EQ slider', 'fixed-bands'],
 'best_fit.bands.q': ['Bandwidth (Q) of each graphic EQ slider', 'q', 'fixed-bands'],
 'best_fit.bands.gain_min': 'Minimum slider gain (dB)',
 'best_fit.bands.gain_max': 'Maximum slider gain (dB)',
 'best_fit.bands.step': ['Smallest gain increment each slider can move', 'fixed-bands'],
 'scoring.band_hz': ['Frequency range used to measure EQ error', 'scored-range', 'q-treble'],
 'scoring.pick': ['', 'simplest'],
 'scoring.ear_db': ['Maximum deviation from target where the EQ still sounds the same', 'simplest'],
 'site_single.rows': ['Maximum number of filters for Website AutoEQ', 'website-autoeq'],
 'site_single.freq_low': ['', 'website-autoeq'],
 'site_single.gain_min': ['Minimum and maximum allowed gain per filter', 'db'],
 'site_single.q_min': ['Minimum and maximum allowed Q per filter', 'q'],
 'site_sweep.filter_rows': ['Filter counts to test across every combination below', 'sweep'],
 'site_sweep.freq_low': '',
 'site_sweep.freq_high': ['', 'treble-limit'],
 'site_sweep.gain_ranges': ['Min to max gain ranges to test, in whole dB', 'sweep'],
 'site_sweep.q_min': ['', 'q'],
 'site_sweep.q_max': ['', 'q'],
 'res.error': ['', 'error', 'q-error'],
 'res.preamp': ['', 'preamp', 'q-preamp'],
 'res.maxq': ['', 'q'],
 'res.boost': ['', 'preamp'],
 'fcounts': ['', 'simplest', 'q-filters'],
 'f_retry': ['', 'retry'],
 'x_name': ['Base name for exported files', 'file-formats'],
 'export.apo': ['', 'file-formats'],
 'export.graphic': ['', 'file-formats'],
 'export.poweramp': ['', 'file-formats'],
 'export.uapp': ['', 'file-formats'],
 'export.soundsource': ['', 'file-formats'],
 'export.voicemeeter': ['', 'file-formats', 'preamp'],
 'export.rockbox': ['', 'file-formats'],
 'export.convolution': ['', 'impulse-response'],
 'export.convolution_rate': ["Must match your playback device or player's sample rate", 'sample-rate'],
 'export.report': ['Standalone HTML report with the response graph and filter table', 'file-formats'],
 'export.preamp_rounding': ['Rounds pre-amp to 0.1 dB in exports, copied text, and Use on device', 'preamp'],
 'export.extra_headroom': ['Extra negative pre-amp applied for more clipping headroom', 'preamp'],
 'export.q_decimals': 'Decimal places for Q in exported files, copied text, and Use on device',
 '#opt-view': ['', 'error'],
 '#opt-y': 'Vertical range of the dB scale',
 '#opt-ch': ['Overlay individual measurement files (left, right, seatings) behind the average', 'seatings'],
 '#snd-src': '',
 '#tone-from': '',
 '#snd-vol': '',
 '#snd-lm': ['', 'match-loudness'],
 '#snd-blind': ['', 'blind-test'],
 '#snd-abx': ['Blind test to see if you can tell two versions apart', 'abx', 'match-loudness'],
 '#snd-ears': '',
 '#snd-left': '',
 '#snd-right': '',
 'snd_list': ['', 'eqs-to-compare'],
 '#pk-src': ['', 'databases'],
 '#pk-anykind': '',
 'pk_filters': ['', 'rig-tags', 'databases'],
 '#pk-f-sure': ['Hide entries with an unknown, guessed, or mixed rig', 'rig-tags'],
 '#pk-f-dl': 'Shows only entries that can be downloaded directly',
 '#pw-paste': ['', 'tracer', 'databases'],
 '#cmp-q': 'All words must match the measurement name',
 '#cmp-rig': ['', 'rig', 'rig-conversion'],
 '#hist-this': ['Show only EQs for the selected measurement', 'history'],
 'history.keep': ['Which EQs are kept after closing the app', 'history'],
 'history.eqd_before': ['Shows saved EQ count and latest date for this measurement', 'history'],
 'site.profile': ['Squiglink site whose AutoEQ calculation settings to match', 'website-autoeq'],
 'site.normalization': ['Method used to align curves to the same volume level', 'level-matching', 'phon'],
 'site.norm_hz': ['Reference frequency where curves are aligned to the same level', 'level-matching'],
 'site.norm_db': ['Reference loudness level for dB mode', 'phon'],
 'site.treble_start_from': ['Hidden web AutoEQ setting: skips placing filters above this frequency on the first pass', 'website-autoeq'],
 'site.sample_rate': ['', 'sample-rate'],
 'site.smooth_level': ['', 'smoothing'],
 'site.scale_smoothing': ['Multiplier applied to the smoothing level to match the website', 'smoothing'],
 'site.phon_table': ['Equal-loudness contour tables used in dB mode', 'phon'],
 'library.folders': ['', 'databases'],
 'databases': ['', 'databases', 'rig-tags'],
 'performance.cores': '',
 '#target-adjust': ["Fine-tune the target's tilt, bass, half-tilt, ear gain, treble, and air",
                    'target-adjustments'],
 '#target-save': '',
 '#compare-results': '',
 '#queue': 'Batch-generate EQs for multiple IEMs or targets; saves each to History',
 '#live-graph': ['Show a copy of the graph when the main graph is out of view',
                 'by-hand'],
 '#eq-graph': ['Drag handle: frequency & gain · Scroll on handle: Q · Right-click: filter type or remove · '
               'Double-click graph: add filter',
               'by-hand',
               'q'],
 '#make-way': ['', 'by-hand'],
 '#by-hand': ['', 'by-hand', 'peaking-filter', 'shelf'],
 '#hand-start': ['', 'by-hand'],
 '#hand-add': ['Add a 1 kHz filter to the manual EQ on the result card (starts one if needed)', 'by-hand'],
 '#hand-paste': ['', 'by-hand'],
 '#hand-close': ['Return to previous EQ (edits stay in the list)', 'by-hand'],
 '#use-device': ['', 'set-use-update', 'set-use-try'],
 '#use-try': ['', 'q-try', 'set-use-device', 'set-use-update'],
 '#use-update': ['', 'set-use-device', 'set-use-try', 'set-prof-edit']}

SETTINGS_EQ = [{'title': 'Select and calculate',
                'items': [{'key': 'slot:target',
                           'title': 'Target',
                           'body': ['The sound that you want for your IEM or headphone: a target curve (Harman, '
                                    "diffuse field, a person's target). Select one from the app, this PC or the online "
                                    'databases. The app adjusts the EQ to this target.']},
                          {'key': 'slot:measurement',
                           'title': 'Measurement',
                           'body': ['The frequency response of your IEM or headphone, from the app, this PC or the '
                                    'online databases (press / to search). The app uses the average of its selected '
                                    'files (left, right, seatings). “Other measurements of this model” sorts the '
                                    'measurements of one model.']},
                          {'key': '#make-way',
                           'title': 'Automatically or Manually (Make the EQ)',
                           'body': ['The first selection in Make the EQ, as two tabs. Automatically: AutoEQ adjusts '
                                    'the filters to the target for your EQ app. You select the method and click '
                                    'Calculate (or Queue… for many EQs). Manually: you set the filters. You select the '
                                    'start (Start from) and click Start (Import an EQ file… for an EQ file). Then you '
                                    'change the filters on the EQ graph or in the table.',
                                    'Your EQ app, below the tabs, is for the two tabs: the EQ stays in its limits, and '
                                    'Save filters writes its file. The card opens on the tab that you selected last. A '
                                    'manual EQ from Profiles shows Manually, and Calculate shows Automatically.']},
                          {'key': 'eq_app',
                           'title': 'Your EQ app',
                           'body': ['The app or device that will use the EQ. The EQ stays in its limits (the number of '
                                    'bands, the gain, Q and frequency ranges, the sliders of a graphic EQ). Save '
                                    'filters writes the file that the app imports. The ⓘ after the label Your EQ app '
                                    'tells its limits, with a link to their source. Not in the '
                                    'list, or '
                                    'not sure: no limits, and an Equalizer APO file, which many apps can read.']},
                          {'key': 'slot:method',
                           'title': 'EQ method',
                           'body': ['How the app finds the filters. Best fit (for all EQ apps) adjusts them directly '
                                    'to the target. The Website methods give the same result as the AutoEQ of '
                                    'squig.link, for you to type into the website. Your EQ app selects the method.']},
                          {'key': 'sa',
                           'title': 'Settings to try',
                           'body': ['The settings that Calculate tries, and the time that is necessary on this PC. '
                                    'Best fit adds filters one at a time, until the EQ has the same sound as the '
                                    'target. It does this for each maximum gain and Q limit that agrees with your '
                                    'curves, with two penalties for opposite filters. For most IEMs, this is some '
                                    'seconds. If no EQ can have the same sound as the target, it is up to '
                                    'approximately 90 seconds.']},
                          {'key': '#auto-on',
                           'title': 'Automatic settings',
                           'body': ['Adjusts the settings of the method for your measurement and target. These are the '
                                    'error range, the filter counts, the minimum and maximum gain, the Q limits and '
                                    'the shelves. A setting that you change shows “custom”, and the app keeps it. '
                                    'Off: the app uses each setting as it is.',
                                    'More settings has the other settings, and the app sets them for you too.']},
                          {'key': 'rig_convert.enabled',
                           'title': "Change the target for the measurement's rig",
                           'body': ['Your measurement and target come from different rigs, and different rigs measure '
                                    'the same IEM or headphone differently (usually above 2 kHz). On: the app changes '
                                    'the target for the rig of the measurement. Thus, the EQ corrects the IEM or '
                                    'headphone, not the difference between the rigs. Off: the app uses the target as '
                                    'it is.']}]},
               {'title': 'Target › Adjust',
                'items': [{'key': 'target_adjust.tilt',
                           'title': 'Tilt (dB/oct)',
                           'body': ['Tilts the full target, in dB in each octave. A value below 0 gives more bass than '
                                    'treble, and a value above 0 gives more treble than bass. A small value has a '
                                    'large effect: −0.5 moves the two ends of the graph approximately 5 dB apart.']},
                          {'key': 'target_adjust.bass_gain',
                           'title': 'Bass shelf (dB)',
                           'body': ['Adds a bass shelf to the target: + for more bass, − for less bass. Most persons '
                                    'change this adjustment first. Usual values are +2 to +6 dB.']},
                          {'key': 'target_adjust.bass_freq',
                           'title': 'Bass shelf: frequency (Hz)',
                           'body': ['The corner of the bass shelf: the shelf changes the bass below it. A lower value '
                                    '(for example, 60 Hz) changes only the lowest bass. A higher value (for example, '
                                    '150 Hz) also changes the higher bass.']},
                          {'key': 'target_adjust.bass_q',
                           'title': 'Bass shelf: Q',
                           'body': ['The slope of the step of the bass shelf. 0.707 is a standard shelf with a small '
                                    'slope. Higher values make a sharper step, with a small peak at the corner.']},
                          {'key': 'target_adjust.halftilt_gain',
                           'title': 'Half-tilt (dB)',
                           'body': ['A shelf with a small slope: it increases (+) or decreases (−) all the sound above '
                                    'its frequency by this value. It changes the treble more gradually than Tilt.']},
                          {'key': 'target_adjust.halftilt_freq',
                           'title': 'Half-tilt: frequency (Hz)',
                           'body': ['The center of the half-tilt shelf. All the sound at frequencies much higher '
                                    'than it changes by its gain.']},
                          {'key': 'target_adjust.ear_gain',
                           'title': 'Ear gain (dB)',
                           'body': ['Increases (+) or decreases (−) the ear gain: the higher level at 2-5 kHz that all '
                                    'targets have. If voices and instruments are too strong, decrease it. If they are '
                                    'too weak, increase it.']},
                          {'key': 'target_adjust.ear_freq',
                           'title': 'Ear gain: frequency (Hz)',
                           'body': ['The center of the ear-gain change, usually at approximately 3 kHz.']},
                          {'key': 'target_adjust.ear_q',
                           'title': 'Ear gain: Q',
                           'body': ['How wide the ear-gain change is: a higher Q gives a smaller band around its '
                                    'frequency.']},
                          {'key': 'target_adjust.treble_gain',
                           'title': 'Treble (dB)',
                           'body': ['Adds a treble shelf to the target: + for more treble, − for a smoother and less '
                                    'sharp sound.']},
                          {'key': 'target_adjust.treble_freq',
                           'title': 'Treble: frequency (Hz)',
                           'body': ['Where the treble shelf starts: the shelf changes the treble above it.']},
                          {'key': 'target_adjust.treble_q',
                           'title': 'Treble: Q',
                           'body': ['The slope of the step of the treble shelf (0.707 is a standard shelf).']},
                          {'key': 'target_adjust.air_gain',
                           'title': 'Air (dB)',
                           'body': ['A shelf for the “air” above approximately 10 kHz: the sound of space. The '
                                    'measurements at these frequencies are not accurate. Thus, listen to find the '
                                    'correct value.']},
                          {'key': 'target_adjust.air_freq',
                           'title': 'Air: frequency (Hz)',
                           'body': ['Where the air shelf starts.']},
                          {'key': 'target_adjust.air_q',
                           'title': 'Air: Q',
                           'body': ['The slope of the step of the air shelf (0.707 is a standard shelf).']}]},
               {'title': 'Best fit',
                'items': [{'key': 'best_fit.filter_counts',
                           'title': 'Filter counts to try',
                           'body': ['How many peaking filters to try, for example 1-10 or 4, 6, 8. Each count gives a '
                                    'result (the app adds one filter at a time, to the maximum). Then Error and '
                                    'selection selects the minimum number of filters for the same sound as the target. '
                                    'If you keep your filters: how many filters to add. Automatic settings stop where '
                                    'more filters do not make the result better.']},
                          {'key': 'best_fit.low_shelf',
                           'title': 'Low shelf',
                           'body': ['Best fit also adjusts a low shelf: a wide change (+ or −) of the bass below a '
                                    'corner frequency. It helps if all the bass is too high or too low. Automatic '
                                    'settings enable it if the bass is 3 dB or more from the target.']},
                          {'key': 'best_fit.freq_range',
                           'title': 'Filters from … to (Hz)',
                           'body': ['Where the app can put peaking filters (from … to). The app calculates the error '
                                    'only in the error range. Thus, this range usually continues above it.']},
                          {'key': 'best_fit.gain_min',
                           'title': 'Minimum gain (dB)',
                           'body': ['The lowest gain that a filter can have, in dB.']},
                          {'key': 'best_fit.gain_max',
                           'title': 'Maximum gain values (dB)',
                           'body': ['The highest gain that a filter can have, in dB. The app tries each value in the '
                                    'list, for example 6, 9. With a lower gain, a smaller pre-amp is necessary.']},
                          {'key': 'best_fit.q_min',
                           'title': 'Q from',
                           'body': ['The lowest permitted Q (the widest filter). A filter with Q 0.5 is more than two '
                                    'octaves wide.']},
                          {'key': 'best_fit.q_max',
                           'title': 'Maximum Q values',
                           'body': ['The highest permitted Q. The app tries each value in the list, for example 3, 5. '
                                    'A high Q can correct a sharp peak. But if the position of your IEM in your '
                                    'ear is different from the measurement, the filter can be at an incorrect '
                                    'frequency.']},
                          {'key': 'best_fit.low_shelf_freq',
                           'title': 'Low shelf (Hz)',
                           'body': ['The range in which Best fit can move the corner of the low shelf (from … to).']},
                          {'key': 'best_fit.fight_penalty',
                           'title': 'Penalties for opposite filters',
                           'body': ['The penalty makes the error larger for a result with opposite filters (a '
                                    'filter with + gain on a filter with − gain). These filters make the EQ more '
                                    'sensitive, not more accurate. 0 = off. The app tries each value in the list with '
                                    'each maximum gain and Q limit (automatic: 0.003 and 0.01). For most IEMs, but not all, a smaller penalty '
                                    'gave a smaller number of filters.']},
                          {'key': 'best_fit.start_keep',
                           'title': 'Keep them as they are (your filters)',
                           'body': ['On: your filters do not change, and Best fit adds filters to them. Off: Best fit '
                                    'starts from your filters, and it can move them. In the two conditions, one more '
                                    'result shows only your filters.']}]},
               {'title': 'More settings › Layout and the bands of a graphic EQ',
                'items': [{'key': 'best_fit.layout',
                           'title': 'Layout',
                           'body': ['The type of EQ, for Best fit. Parametric filters: an app with no limits '
                                    '(Equalizer APO…). Graphic EQ: the sliders of a graphic EQ, and Best fit '
                                    'adjusts only their gains. The layout of an EQ app: its number of filters and its '
                                    'ranges. Your EQ app sets this.']},
                          {'key': 'best_fit.bands.freqs',
                           'title': 'Band frequencies (Hz)',
                           'body': ['The slider frequencies of your graphic EQ in Hz, as the EQ shows them below its '
                                    'sliders. For example: 31, 62, 125, 250, 500, 1000, 2000, 4000, 8000, 16000.']},
                          {'key': 'best_fit.bands.q',
                           'title': 'Q of each band',
                           'body': ['How wide each band is (Q): 1.41 for sliders 1 octave apart (10 bands), 2.15 for '
                                    '2/3 octave (15), 4.32 for 1/3 octave (31). If your app gives a Q for its bands, '
                                    'use that value.']},
                          {'key': 'best_fit.bands.gain_min',
                           'title': 'Sliders from (dB)',
                           'body': ['The lowest value of the sliders, in dB (for example, −12).']},
                          {'key': 'best_fit.bands.gain_max',
                           'title': 'Sliders to (dB)',
                           'body': ['The highest value of the sliders, in dB (for example, +12).']},
                          {'key': 'best_fit.bands.step',
                           'title': 'Slider step (dB)',
                           'body': ['The step of the sliders in dB (1, 0.5 or 0.1). Each gain is an integer number of '
                                    'steps. Thus, the app calculates the error with the values that you set.']}]},
               {'title': 'Error and selection',
                'items': [{'key': 'scoring.band_hz',
                           'title': 'Fit from … to (Hz)',
                           'body': ['The frequency range in which the app calculates the error (from … to). At other '
                                    'frequencies, the EQ has no limits. Automatic settings stop where the seatings of '
                                    'the measurement do not agree, frequently at approximately 10 kHz.']},
                          {'key': 'scoring.pick',
                           'title': 'Best result',
                           'body': ['The result that the app selects. Minimum number of filters for the same sound: '
                                    'the automatic settings use this selection. It selects the minimum '
                                    'number of filters with a difference less than “Same sound below” at all '
                                    'frequencies. The app calculates the difference as the ear hears it: it makes it '
                                    'smooth for the ear and ignores the total level.',
                                    'The limits of your EQ app, or a measurement that filters cannot follow, can '
                                    'prevent this. Then the app selects the minimum number of filters for the same '
                                    'sound as the nearest result. The result card shows how far it is from the target, '
                                    'and where.',
                                    'Lowest error: the nearest result, with no limit on the number of filters.']},
                          {'key': 'scoring.ear_db',
                           'title': 'Same sound below (dB)',
                           'body': ['The maximum difference in dB from the target for the same sound. If no EQ can have '
                                    'the same sound as the target, it is the difference from the nearest result. The app uses the largest '
                                    'difference, smooth for the ear. With pink noise, 0.25 dB was approximately the '
                                    'smallest wide change that persons heard (Toole and Olive, 1988). Thus, you '
                                    'usually cannot hear a smaller difference. With music, it is approximately 0.5 '
                                    'dB.']}]},
               {'title': 'Website AutoEQ: one set',
                'items': [{'key': 'site_single.rows',
                           'title': 'Filter rows',
                           'body': ['“Filter rows” on the website: the maximum number of filters for its AutoEQ. More '
                                    'rows give a nearer result, but you must type more values.']},
                          {'key': 'site_single.freq_low',
                           'title': 'Frequency from … to',
                           'body': ['“Frequency Range” on the website (from … to): where its AutoEQ can put filters. '
                                    'Type the same values on the website.']},
                          {'key': 'site_single.gain_min',
                           'title': 'Gain from … to (dB)',
                           'body': ['“Gain Range” on the website (from … to): the lowest and the highest gain of each '
                                    'filter, in dB.',
                                    'A website with no gain boxes always uses its own range: the boxes are off and '
                                    'show it (Which website to copy).']},
                          {'key': 'site_single.q_min',
                           'title': 'Q from … to',
                           'body': ['“Q Range” on the website (from … to): the lowest Q (the widest filter) and the '
                                    'highest Q of its filters. The website stops at Q 5.',
                                    'A website with no Q boxes always uses its own range: the boxes are off and show '
                                    'it (Which website to copy).']}]},
               {'title': 'Website AutoEQ: find the best settings',
                'items': [{'key': 'site_sweep.filter_rows',
                           'title': 'Filter rows to try',
                           'body': ['The numbers of filter rows to try, for example 4-10 or 4, 6, 8. The app tries '
                                    'each number with each set of values from the lists that follow. Error and '
                                    'selection selects the best result.']},
                          {'key': 'site_sweep.freq_low',
                           'title': 'Frequency from',
                           'body': ['The start of the “Frequency Range”, for all the settings to try.']},
                          {'key': 'site_sweep.freq_high',
                           'title': 'Frequency “to” values',
                           'body': ['The ends of the “Frequency Range” to try, as a list, for example 8000, 12000. '
                                    'With a lower end, the filters stay out of the treble, where measurements are not '
                                    'accurate.']},
                          {'key': 'site_sweep.gain_ranges',
                           'title': 'Gain ranges',
                           'body': ['The gain ranges to try. Each row is one range: the lowest gain in the first box and '
                                    'the highest in the second, in whole dB. Add a range adds a row, and ✕ removes '
                                    'one. Each is a “Gain Range” to type on the website.',
                                    'A website with no gain boxes always uses its own range: the app tries only that '
                                    'one, and the rows are off.']},
                          {'key': 'site_sweep.q_min',
                           'title': 'Q from',
                           'body': ['The start of the “Q Range”, for all the settings to try (the lowest permitted '
                                    'Q).']},
                          {'key': 'site_sweep.q_max',
                           'title': 'Q “to” values',
                           'body': ['The ends of the “Q Range” to try, as a list (the highest permitted Q). The '
                                    'website stops at Q 5.',
                                    'A website with no Q boxes always uses its own range: the app tries only that '
                                    'one, and Q from and this box are off.']}]},
               {'title': 'The result',
                'items': [{'key': 'res.error',
                           'title': 'Error',
                           'body': ['The difference between the curve with the EQ and the target, in the error range '
                                    '(dB, root mean square). Less than approximately 0.5 dB is very near.']},
                          {'key': 'res.preamp',
                           'title': 'Pre-amp',
                           'body': ['How much this EQ must decrease the volume, to prevent clipping from its gains. '
                                    'You set it in your EQ app. Most saved files include it.']},
                          {'key': 'res.maxq',
                           'title': 'Maximum Q',
                           'body': ['The highest Q of the filters. Above approximately 5, a filter is sensitive to the '
                                    'position of the IEM in the ear.']},
                          {'key': 'res.boost', 'title': 'Maximum gain', 'body': ['The highest gain of the filters.']},
                          {'key': 'fcounts',
                           'title': 'Number of filters',
                           'body': ['The best result for each number of filters. With one click, you get a smaller '
                                    'number of filters (easier to enter) or a nearer result. For a graphic EQ app '
                                    'with more than one band count (FxSound), the list has the best result for each '
                                    'band count.']},
                          {'key': 'f_retry',
                           'title': 'Calculate from these filters',
                           'body': ['Calculates again with Best fit, from the filters on the result card, for this '
                                    'result only. Adjust them: each filter moves a small distance, nearer to the '
                                    'target. Keep them and add filters: your filters do not change, and Best fit adds '
                                    'more filters.']},
                          {'key': '#live-graph',
                           'title': 'Show the graph while you edit',
                           'body': ['This tick box is adjacent to the tools of the filters (on at the start). If you '
                                    'cannot see the graph, the page shows a copy of it while you change the '
                                    'filters. This occurs with the table, the sliders, Add filter, Sort or Undo all.',
                                    'The copy shows the target, your IEM and, in blue, your IEM with the EQ, with the '
                                    'error and the pre-amp. It is not on the control that you change. It is at the top '
                                    'of the window, or at the bottom if the control is at the top. It follows each '
                                    'change. It closes when you scroll to the graph or to a part with no filters. Its '
                                    '✕ or this tick box disables it.',
                                    'While the app calculates, the copy does not show if it is on Cancel.']},
                          {'key': '#eq-graph',
                           'title': 'The EQ graph: edit on the curve',
                           'body': ['Below the graph: the EQ on the result card, with a handle for each filter. Each '
                                    'handle has the number of its filter in the table. It is on the curve of its '
                                    'filter, at its frequency (for a shelf, at the center of the shelf).',
                                    'Drag a handle horizontally to change its frequency. Drag it vertically to change '
                                    'its gain. Turn the mouse wheel on a handle to change its Q (up: a higher Q). '
                                    'Right-click a handle for Peak, Low shelf, High shelf and Remove (the On tick box of the '
                                    'table turns a filter off). Double-click where there is no handle to add a filter. With '
                                    'no EQ, a manual EQ starts with it (the EQ graph tells you this).',
                                    'While you drag, the curves, the values, the table and the sound of Listen change. '
                                    'The scale does not change until you release the handle. An EQ that you use on a '
                                    'device (Use on device › Use for 5 minutes on) changes there too, in all apps. The '
                                    'table and the sliders do the same with the keyboard.']},
                          {'key': '#by-hand',
                           'title': 'Manually',
                           'body': ['The Manually tab of Make the EQ: an EQ that you make. The result card shows it as '
                                    'a result. Thus, Save filters, Copy, Use on device, Listen and the other controls '
                                    'operate as for all results.',
                                    'You start from an empty EQ, a copy of the selected EQ, or an EQ that you have. '
                                    "This can be an EQ file (Equalizer APO, AutoEq, squig.link, Room EQ Wizard's "
                                    "export, a Peace preset), pasted filters or a device's profile.",
                                    'An empty EQ: click Start, or Add filter for its first filter. An EQ file: click '
                                    'Import an EQ file… and select the file. Pasted filters: paste the lines in the '
                                    'Filters box of the card, then click Start. Other items: click Start.',
                                    'The app reads the files as Equalizer APO uses them. If a file has an item that an '
                                    'EQ here cannot have (other filter types, a graphic EQ…), the app tells you.',
                                    'A measurement and a target are optional: with them, the graph shows your IEM with '
                                    'the EQ, and the error. If the EQ started from a profile, Use on device › Update '
                                    'saves it into that profile. Close, on its result card, shows the result before '
                                    'it.']},
                          {'key': '#hand-start',
                           'title': 'Start and Import an EQ file… (Manually)',
                           'body': ['Below Start from on the Manually tab. It starts a manual EQ from the item in '
                                    'Start from, and the result card shows it. For an EQ file, the button is Import '
                                    'an EQ file…: you select the file, and the EQ starts.',
                                    'An empty EQ: add filters on the EQ graph (double-click) or with Add filter. A '
                                    'copy of the selected EQ: the EQ on the result card, to change it and keep the '
                                    'initial EQ. Pasted filters: paste the lines in the Filters box first. A '
                                    "device's profile: Use on device › Update saves your changes into it."]},
                          {'key': '#hand-add',
                           'title': 'Add filter (Manually)',
                           'body': ['Beside Start on the Manually tab, with An empty EQ in Start from. It adds a '
                                    'filter (1 kHz, 0 dB, Q 1) to the manual EQ on the result card. With no manual EQ '
                                    'there, it starts an empty one first; a calculated EQ shown stays in EQs that you '
                                    'made.',
                                    "If the calculated EQ shown has edits, it starts nothing, so the edits aren't "
                                    'lost: use Add filter on the result card, or Undo all first. Add filter on the '
                                    'result card adds a filter to the EQ shown.']},
                          {'key': '#hand-paste',
                           'title': 'Name and Filters (Pasted filters)',
                           'body': ['Under Start from on the Manually tab, with Pasted filters. Paste the lines in '
                                    'Filters: Equalizer APO lines, Room EQ Wizard filters, or one filter on each line '
                                    'as frequency, gain and Q. Name is the name of the EQ (empty: “Pasted EQ”). Then '
                                    'click Start.',
                                    'With an empty Filters box, Start says to paste first. If the text has no '
                                    'filters, a message tells the formats, and the text stays in the box. When the '
                                    'EQ starts, the two boxes are emptied.']},
                          {'key': '#hand-close',
                           'title': 'Close (a manual EQ)',
                           'body': ['On the result card of a manual EQ, on the right side of its title. It shows the '
                                    'page as it was before the manual EQ: the result that you had, or no result.',
                                    'A manual EQ that you changed stays in EQs that you made, with your changes '
                                    '(Remove there removes it). The app removes an empty manual EQ, because it has no '
                                    'filters to keep. It also removes a manual EQ with no changes (pasted, from a '
                                    'file, a profile or a copy). Then the window shows Undo at the bottom. Save '
                                    'filters keeps it in a file.']},
                          {'key': 'x_name',
                           'title': 'File name',
                           'body': ['The name of the saved files. Each file adds its end (“ - filters.txt”, “ - '
                                    'Poweramp.json”…). At the start, the name has the measurement, the target, the '
                                    'method and the filter count. To change it, type a different name (clear the box '
                                    'for the automatic name). The report also gets this name. The app replaces a file '
                                    'with this name in your Saved EQs folder only if you agree.']}]},
               {'title': 'Saved files',
                'items': [{'key': 'export.apo',
                           'title': 'Equalizer APO / squiglink filters (.txt)',
                           'body': ['A text EQ file, which most apps can read. For Equalizer APO and Peace (Windows), '
                                    'EasyEffects (Linux: Equalizer › Import Preset › APO, up to 32 filters) and Import '
                                    'on squiglink (up to 20).']},
                          {'key': 'export.graphic',
                           'title': 'GraphicEQ (.txt)',
                           'body': ['A GraphicEQ line (the EQ as one full curve): Wavelet and RootlessJamesDSP '
                                    '(Android), and other apps that use a response curve.']},
                          {'key': 'export.poweramp',
                           'title': 'Poweramp preset (.json)',
                           'body': ['For Poweramp or Poweramp Equalizer (Android). Copy it to the phone. Then use '
                                    'Presets › Import in the equalizer. A maximum of ±15 dB and Q 12, with the '
                                    'pre-amp.']},
                          {'key': 'export.uapp',
                           'title': 'USB Audio Player PRO preset (.xml)',
                           'body': ['For the parametric EQ of USB Audio Player PRO (Android). Copy it into the '
                                    'TBEQPresets folder in the folder of UAPP. A maximum of 10 peaking filters and no '
                                    'shelves: for a larger EQ, the app does not make this file.']},
                          {'key': 'export.soundsource',
                           'title': 'SoundSource (.txt)',
                           'body': ['For SoundSource (macOS). Add it with Headphone EQ › Add Other Profile… (up to 32 '
                                    'filters, with the pre-amp).']},
                          {'key': 'export.voicemeeter',
                           'title': 'Voicemeeter (.xml)',
                           'body': ['For a Voicemeeter bus (Windows). Open the EQ of the bus. Right-click its top bar. '
                                    'Select Load EQ Settings. 6 filters, with gains up to +18 dB. The file has no '
                                    'pre-amp: decrease the gain of the bus by the pre-amp.']},
                          {'key': 'export.rockbox',
                           'title': 'Rockbox preset (.cfg)',
                           'body': ['For music players with Rockbox. Copy it to the player. Then use Sound Settings › '
                                    'Equalizer › Browse EQ Presets. A low shelf, 8 peaking filters and a high shelf, '
                                    'with Q up to 6.4 and ±24 dB.']},
                          {'key': 'export.convolution',
                           'title': 'Convolution impulse response (.wav)',
                           'body': ['The EQ as an impulse response (.wav, 32-bit float, stereo) for all convolution '
                                    'EQs: Viper4Android, JamesDSP, the Convolver of EasyEffects, Roon, foobar2000, '
                                    'HQPlayer, Equalizer APO. The accurate sound of the filters, with no limit on '
                                    'their number, and the pre-amp.']},
                          {'key': 'export.convolution_rate',
                           'title': 'Impulse response sample rate',
                           'body': ['It must be the same as the sample rate of your player or device (usually 48000 or '
                                    '44100). If not, the frequencies of the EQ are not fully correct.']},
                          {'key': 'export.report',
                           'title': 'An HTML report',
                           'body': ['An HTML page with the graph and the filters. It helps when you type the filters '
                                    'into an app manually. You can also keep it to record the EQ.']},
                          {'key': 'export.preamp_rounding',
                           'title': 'Pre-amp rounding',
                           'body': ['The rounding of the pre-amp to 0.1 dB in saved files. Safe (lower value): always '
                                    'the lower value, to prevent clipping. Same as squiglink: the rounding of the '
                                    'website (up to 0.05 dB too small).']},
                          {'key': 'export.extra_headroom',
                           'title': 'More headroom (dB)',
                           'body': ['The app adds this value in dB to the pre-amp, and the volume decreases more. '
                                    'It helps if your player or a different effect also increases the gain. 0 = '
                                    'none.']},
                          {'key': 'export.q_decimals',
                           'title': 'Q decimals in saved files',
                           'body': ['How many decimals Q has in saved files. 3 is sufficient: a 4th decimal changes an '
                                    'EQ by a maximum of 0.003 dB.']}]},
               {'title': 'The graph and Listen',
                'items': [{'key': '#opt-view',
                           'title': 'View',
                           'body': ['Frequency response: the curves as they are. Difference from target: the '
                                    'difference of each curve from the target. Thus, 0 dB is the target, and you can '
                                    'easily see all differences.']},
                          {'key': '#opt-y',
                           'title': 'Y range',
                           'body': ['The height of the dB scale: a smaller range shows smaller differences. Automatic '
                                    'adjusts it to the curves.']},
                          {'key': '#opt-ch',
                           'title': 'Channels',
                           'body': ['Also shows each file of the measurement (channels, seatings) behind their '
                                    'average, to show their differences.']},
                          {'key': '#snd-src',
                           'title': 'Sound',
                           'body': ['The sound to play: short music, pink or white noise, a 20 Hz-20 kHz sweep, a tone '
                                    'or Your audio file… (mp3, flac, wav, ogg …). The graph shows the frequency of the '
                                    'tone.']},
                          {'key': '#tone-from',
                           'title': 'Tone: from … to',
                           'body': ['The frequency range of the tone: the slider adjacent to these boxes moves the tone '
                                    'between these frequencies (Hz).']},
                          {'key': '#snd-vol',
                           'title': 'Volume',
                           'body': ['Start with a low volume: the gains of an EQ can make the volume much higher.']},
                          {'key': '#snd-lm',
                           'title': 'Same level (Listen)',
                           'body': ['Plays all versions at the same loudness. Thus, you compare the tone, not the '
                                    'volume (usually, a higher volume gives a better sound to the ear).']},
                          {'key': '#snd-blind',
                           'title': 'Hide the names',
                           'body': ['Hides the names of the versions until you click Show the names. Thus, the names '
                                    'do not have an effect on the sound that you hear.']},
                          {'key': '#snd-abx',
                           'title': 'ABX test',
                           'body': ['A test: can you hear a difference between two versions? Select A and B (EQ off, '
                                    'the selected EQ, an EQ to compare) and the number of trials. Then click Start '
                                    'ABX. In each trial, X is a random selection of A or B. Listen to A, B and X as many '
                                    'times as necessary. Then click X is A or X is B.',
                                    'Until the end, the app does not show if a selection is correct. At the end, the '
                                    'app shows how many of your selections were correct. It also shows '
                                    'how frequently random selections get that number or more. If this is less than 5 '
                                    '%, you can hear the difference. If not, your result can be from random selections '
                                    '(a longer test can show a small difference).',
                                    'During the test, Listen uses the same level and the same version in each ear. The '
                                    'app hides the version buttons and disables the keys 1–9 (they can show which version '
                                    'is X). Stop the test shows your results. A change to A or B (the filters, a '
                                    'different result) also stops the test and shows your results. The app keeps the results until you close AutoEQ Studio.']},
                          {'key': '#snd-ears',
                           'title': 'Ears',
                           'body': ['The same version in each ear (change it with the buttons or the keys 1–9), or a '
                                    'different version in each ear. For example, no EQ in the left ear and the EQ in '
                                    'the right ear. Also interchange the sides: your two ears are different.']},
                          {'key': '#snd-left', 'title': 'Left', 'body': ['The version that your left ear hears.']},
                          {'key': '#snd-right',
                           'title': 'Right',
                           'body': ['The version that your right ear hears. Interchange interchanges the sides.']},
                          {'key': 'snd_list',
                           'title': 'Your EQs to compare',
                           'body': ['EQs to compare on this IEM or headphone. Each EQ is a version above the list '
                                    '(keys 1–9) and, if Graph is on, a curve on the graph.',
                                    'You can add the EQ on the result card (Keep to compare, or “The selected EQ” '
                                    'below the list) or an EQ from History (Keep to compare). You can also add an EQ '
                                    'file (as the Manually tab reads it: Equalizer APO, Room EQ Wizard, Peace) or '
                                    'pasted filters. To rename an EQ, edit its name. Each measurement has its list (up '
                                    'to 12 EQs), also after you close the app.']}]},
               {'title': 'Find curves, and History',
                'items': [{'key': '#pk-src',
                           'title': 'All, In the app, This PC, Online databases (tabs)',
                           'body': ['All shows the items of each source. Each of the other tabs shows the items of '
                                    'one source. The number after the name is the number of items that the tab shows '
                                    'for the words in the search box and the selections.',
                                    '“…” after the number of This PC: the app continues to search this PC, and the '
                                    'number can change. “…” as the number of All or Online databases: the app '
                                    'continues to load the online lists.']},
                          {'key': '#pk-anykind',
                           'title': 'Targets and measurements',
                           'body': ['Also shows files that can be of the other type (a measurement when you select a '
                                    'target, or a target when you select a measurement). This helps if the app found '
                                    'an incorrect type for a file.']},
                          {'key': 'pk_filters',
                           'title': 'Rig, Type and Source lists',
                           'body': ['They make a long list shorter. Rig: one rig (for a measurement, first “Same rig '
                                    'as your target”). Type: IEM, headphone or earbud. Source: one database (the tabs '
                                    'show the app or this PC). Each item shows how many results it gives. The app keeps your '
                                    'selections.',
                                    'The items are from A to Z, and each list opens with a search box. Type a part of '
                                    'a name (each word must be in the name). Then click the item or press Enter.']},
                          {'key': '#pk-f-sure',
                           'title': 'Known rig',
                           'body': ['Hides the items with an unknown rig, a guessed rig (their tag has “?” at the end) '
                                    'or mixed rigs.']},
                          {'key': '#pk-f-dl',
                           'title': 'Available to download',
                           'body': ['Hides the entries that the app cannot download. The app traces those entries from '
                                    'a picture of their website.']},
                          {'key': '#pw-paste',
                           'title': 'Paste the image (an image from the website)',
                           'body': ['Some websites do not let other programs download their files, and the app obeys '
                                    'that limit. The app has no browser in it and does not get the data of the '
                                    'website. Your browser shows the graph, and the app reads only a picture of it.',
                                    'The app opens the website of the entry (a measurement or a target). If this '
                                    "entry isn't shown, select it from the site's list. For some websites, the app "
                                    "opens only the page of the database: select this entry from the site's list.",
                                    'Site target adjustments (like tilt or bass) are captured in the screenshot.',
                                    'If a website does not let the app download an entry, the app also uses '
                                    'pictures for the other entries of that database. After 7 days, the app '
                                    'tries to download again.',
                                    'Maximize your browser for better accuracy, and close any popups over the graph. '
                                    'Press Win+Shift+S and drag over the graph, or click Screenshot on the site to '
                                    'save it to Downloads.',
                                    'While the app waits, it looks at the clipboard and at the names of the picture '
                                    'files in your Downloads folder. It uses only a picture that is new after it '
                                    'started to wait. It does not change or delete a file. Paste the image uses the '
                                    'picture that is on the clipboard at this time. The app waits for a maximum of 10 '
                                    'minutes, or until you click Cancel.',
                                    'The tracer finds the axes and the curve automatically and opens on 3 Save. For a '
                                    'measurement, the result is one measurement: the average of the left and right '
                                    'curves. If a curve '
                                    'goes above or below the grid near an end of the frequency axis, the measurement '
                                    'does not include that part. The text on 3 Save gives the frequencies. Verify '
                                    'the traced curve against the picture before you add it.',
                                    'For an entry of a target, show only the target on the graph of the website. The '
                                    'tracer then traces the target line. If the line stops before an end of the '
                                    'frequency axis, 3 Save shows its first and last frequency.',
                                    'For an entry of a target or from Find a target, the tracer selects “A target '
                                    'line”. Thus, the add button is Add as target. The text on 3 Save tells you to '
                                    'click it. If the app '
                                    'cannot trace only the target line, remove the measurement curve from the graph '
                                    'of the website, then capture the graph again.',
                                    'A small picture, or a second curve in almost the same color, can cause errors. '
                                    'If the app cannot trace the '
                                    'picture automatically, the tracer opens on the tab where your input is '
                                    'necessary. A message gives the cause.',
                                    'The curve gets the name of the entry and the rig of its database. If '
                                    'the picture is not a graph, copy a new picture of the graph. Then '
                                    'paste it in the tracer. The tracer keeps the name and the rig of the entry. If '
                                    'you paste the same picture again before you add a curve from it, the tracer keeps '
                                    'the result and your changes.']},
                          {'key': '#cmp-q',
                           'title': 'Model (which measurement to use)',
                           'body': ['The model to find. Each word must be in a name. Thus, with a smaller number of '
                                    'words, you find more results (for example, “Blessing 2” and not the full name).']},
                          {'key': '#cmp-rig',
                           'title': 'Rig of your target',
                           'body': ['The rig that your target was made for. The app finds it from the name or the '
                                    'source of the target. If it is incorrect, change it. The app sorts the '
                                    'measurements by how accurately it can change their rig to this rig.']},
                          {'key': '#hist-this',
                           'title': 'This IEM only',
                           'body': ['Only the EQs that you made for the selected measurement.']},
                          {'key': 'history.keep',
                           'title': 'History keeps',
                           'body': ['The EQs that History (adjacent to the title of the graph) keeps after you close the '
                                    'app. The two selections are “EQs that you save or copy” and “All results, and the '
                                    'EQs that you save”.']},
                          {'key': 'history.eqd_before',
                           'title': 'Show a message below Measurement if History has an EQ for it',
                           'body': ['Below Measurement, a line tells how many EQs History has for that IEM or '
                                    'headphone, with a link to them.']}]},
               {'title': 'More settings › Website',
                'items': [{'key': 'site.profile',
                           'title': 'Which website to copy',
                           'body': ['The graph website whose values the Website methods copy: its smoothing, '
                                    'normalization, loudness tables and AutoEQ treble value. With other values, the '
                                    'Website methods give other filters than the website.',
                                    ['“The database of the measurement” (at first): the values of the website that '
                                     'your measurement is from. The app has the values of about 155 websites, read on '
                                     '2026-11-24. Online, it reads a website again when you use one of its entries and '
                                     'its values are more than 30 days old.',
                                     'A website by name: the values of that website, also for a measurement from a '
                                     'file or from your own image. Select the website where you type the results.',
                                     '“Other”: the app changes none of the values below.'],
                                    'The gray line below the list says where the values come from. A measurement from '
                                    'a file gets the usual values of squig.link websites. Best fit uses the app\'s own '
                                    'values (those of listener800), whatever the list says.',
                                    'A value that you type shows “custom ↺” and stays until you click it.',
                                    'On most websites, the AutoEQ panel has no boxes for the gain or the Q: the '
                                    'website always uses its own ranges (usually -12 to 12 dB and Q 0.5 to 2). For '
                                    'such a website, the Website methods use them too, and their gain and Q boxes are '
                                    'off and show those values.']},
                          {'key': 'site.normalization',
                           'title': 'Normalization',
                           'body': ['How the app gives the curves the same level before it compares them. Hz~: the '
                                    'average across 4 octaves around a frequency (listener800). Hz: one frequency. dB: '
                                    'the same loudness in phon (squig.link).']},
                          {'key': 'site.norm_hz',
                           'title': 'Around (Hz)',
                           'body': ['The frequency at which the curves have the same level (Hz and Hz~ modes), usually '
                                    '500 Hz.']},
                          {'key': 'site.norm_db',
                           'title': 'Loudness (phon)',
                           'body': ['The loudness of all the curves in dB mode, in phon. squig.link uses 60, a usual '
                                    'volume for music.']},
                          {'key': 'site.treble_start_from',
                           'title': 'AutoEQ TrebleStartFrom (Hz)',
                           'body': ['A setting of the AutoEQ of the website that the website does not show. Its first '
                                    'step uses no filters above this frequency (most websites 7000, listener800 '
                                    '15000). The app sets it from the website (Which website to copy).']},
                          {'key': 'site.sample_rate',
                           'title': 'Sample rate',
                           'body': ['The sample rate that the app uses to calculate the filters. The website uses '
                                    '48000. This setting changes only the highest treble, by a small value.']},
                          {'key': 'site.smooth_level',
                           'title': 'Smoothing level',
                           'body': ['How much the website makes the curves smooth before the normalization. 0 = none. '
                                    'The app sets it from the website (Which website to copy).']},
                          {'key': 'site.scale_smoothing',
                           'title': 'Smoothing scale',
                           'body': ['The smoothing scale of the website (most websites 0.1, listener800 0.2). The app '
                                    'sets it from the website (Which website to copy).']},
                          {'key': 'site.phon_table',
                           'title': 'Loudness tables',
                           'body': ['The equal-loudness tables for dB mode: ISO 226:2003 (most websites) or ISO '
                                    '226:2023 (listener800 and others).']}]},
               {'title': 'More settings › This PC',
                'items': [{'key': 'performance.cores',
                           'title': 'CPU cores',
                           'body': ['How many CPU threads the app uses when it calculates. 0 = all the cores minus 1, '
                                    'and not more than the free memory can hold. If the PC becomes slow while the app '
                                    'calculates, use a lower value.']}]},
               {'title': 'Find… › Sources',
                'items': [{'key': 'library.folders',
                           'title': 'Folders to search',
                           'body': ['The folders in which the app searches for curve files, with the folders in them. '
                                    'Add a folder… opens Windows\' folder dialog; a folder\'s ✕ removes it (with Undo). '
                                    'With no folders added: your Downloads, Documents, Desktop and Music folders. '
                                    'Search again searches the folders again for new files. The '
                                    'app does not search its downloads folder: its curves are the copies of the online '
                                    'databases on this PC (also offline).']},
                          {'key': 'databases',
                           'title': 'Online databases',
                           'body': ['All the online databases that Find… uses. To remove one from Find…, disable it. '
                                    'The app updates the lists automatically at intervals of some days. Add a '
                                    'database: one from the list of squig.link, or a page of the same type. A database '
                                    'that you added stays in the list when disabled; its ✕ removes it (with Undo).']}]},
               {'title': 'Queue',
                'items': [{'key': '#queue',
                           'title': 'Queue… (calculate EQs one after the other)',
                           'body': ['Select IEMs and targets. The app makes an EQ for each IEM with each target, one '
                                    'after the other, with your settings and method. It calculates the automatic '
                                    'settings for each EQ. When a file type is set in More settings › Saved files, it '
                                    'saves each selected result in your Saved EQs folder with its automatic name (it '
                                    'does not replace a file). It also keeps it in History and in EQs that you made.',
                                    'Cancel stops the EQ in progress and the EQs after it. Your selection of files '
                                    'does not change.']}]},
               {'title': 'Your result: compare',
                'items': [{'key': '#compare-results',
                           'title': 'Compare… (two EQs at the same time)',
                           'body': ['Each of the two EQs can be the EQ on the result card (with your changes) or an EQ '
                                    'in the History of this IEM. It can also be an EQ that you made (the best result '
                                    'for each filter count).',
                                    'The app shows the two EQs on your measurement and target. It shows their error in '
                                    'the error range, filters, pre-amp, maximum gain and Q, and the maximum difference '
                                    'between them. It also shows their filters at the same time. Show A and Show B '
                                    'show an EQ that you made on the result card again.']}]},
               {'title': 'Target › Adjust: your target',
                'items': [{'key': '#target-adjust',
                           'title': 'Adjust… (on the Target row)',
                           'body': ['Opens a window with the target adjustments: tilt, bass, half-tilt, ear gain, '
                                    'treble and air (the Custom DF of listener800), each on one row, and a graph of the '
                                    'target. Value: how much '
                                    '(+ increases, − decreases, and for the tilt, − gives more bass and + gives more '
                                    'treble). − and + (or ↑ ↓ and the mouse wheel in the box) change it one step at a '
                                    'time, and the graph changes with it. Hz: where a shelf starts, or the center of '
                                    'the ear gain. Q: the slope of a shelf, or the width of the ear gain.',
                                    'Hz and Q are gray while the value is 0, because they have no effect then. Below the '
                                    'Target row, the app shows the adjustments that you made. Clear the adjustments sets '
                                    'them to 0. Undo, adjacent to the message at the bottom of the window, sets them to '
                                    'their previous values.'],
                           'see': ['target-adjustments']},
                          {'key': '#target-save',
                           'title': 'Save as a target…',
                           'body': ['The app shows this button when you adjust the target (tilt, bass, ear gain, '
                                    'treble …). It saves the adjusted target as your target (in the targets of the '
                                    'app, with the name that you give). Then the app uses it and sets the adjustments '
                                    'to 0, because the new target contains them. The new target has the rig of the '
                                    'initial target, and the app changes it for a measurement, as for all targets. '
                                    'Undo, adjacent to the message at the bottom of the window, undoes these changes.']}]},
               {'title': 'Presets',
                'items': [{'key': '#presets',
                           'title': 'Presets (top bar, on Make an EQ)',
                           'body': ['A preset keeps all the settings of Make an EQ with a name. These are your EQ app, '
                                    'the method, the automatic settings and your values, the target adjustments, Error '
                                    'and selection and More settings. It does not keep your files: the target and the '
                                    'measurement do not change. For example, make one preset for the website and one '
                                    'for Equalizer APO.',
                                    'Save as a preset… opens a box for a name (the new preset replaces a preset with '
                                    'the same name). Click a preset to load all its settings. Undo, adjacent to the '
                                    'message at the bottom, loads the previous settings again.',
                                    'Delete a preset removes a preset. Reset all settings… sets all settings to '
                                    'their initial values (the app keeps your files and presets). Presets are files in '
                                    'your Presets folder (Settings › Your files).']}]}]
