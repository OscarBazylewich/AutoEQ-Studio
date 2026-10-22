"""What every setting does, in a line (HELP: the tooltips), and the Help page's words (WIKI: questions, terms and
every setting in full). Brought from AutoEQ Local's gui\\help.js and gui\\wiki.js (2026-10-05), then told in
AutoEQ Studio's controls (2026-10-06: where things are, what they're called; no browser or presets here):
HELP[key] is the text, or [text, ...ids of WIKI entries]; a key is a setting's path ("best_fit.filter_counts"; a
"to" field shares its "from" field's: ".1" -> ".0"), or a name for a part of the window ("slot:target", "sa").
"""
# flake8: noqa

HELP = {'slot:target': ['The curve you want your earphone to sound like.', 'target', 'rig'],
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
 '#dev-check': ["Whether this device's EQ really plays: Equalizer APO asked by itself.", 'q-applies'],
 '#presets': 'Every setting of Make an EQ saved under a name and loaded again in one go (not your files).',
 '#target-adjust': ['Shapes the target to taste: tilt, bass, half-tilt, ear gain, treble and air, each with − and +.',
                    'target-adjustments'],
 '#target-save': 'Keeps the target as adjusted as a target of your own, in use; the adjustments go back to 0.',
 '#compare-results': 'Two EQs side by side: on the graph, their numbers and their filters.',
 '#queue': 'EQs for several IEMs or targets in one go, each saved and kept in History.',
 '#backup': 'Everything of yours in one .zip (Back up everything…), or put back from one (Restore…).',
 '#files-folder': ['Where your targets, measurements, saved EQs and presets are: Documents\\AutoEQ Studio unless you '
                   'chose another folder (Change…).', 'q-files'],
 '#dev-rename': 'Your own name for this device, shown everywhere instead of Windows\' name.',
 '#use-try': ['Plays the EQ on a device for 5 minutes in every app, then Keep it or let its own EQ come back.',
              'q-try'],
 '#tr-auto-on': ["Fits the tracer's settings to the image.", 'automatic-settings'],
 '#tr-d1': 'The dB value at the top red line.',
 '#tr-d2': 'The dB value at the bottom red line.',
 '#tr-f1': 'The frequency at the left blue line.',
 '#tr-f2': 'The frequency at the right blue line.',
 '#tr-snap': 'Dragged lines jump onto the nearest gridline.',
 '#tr-every': 'Uses every gridline, for unevenly drawn axes.',
 '#tr-tol': 'How close a colour must be to count as the curve.',
 '#tr-ppo': 'How many points per octave are saved.',
 '#tr-fmin': 'The frequency range to save.',
 '#tr-name': "The saved file's name.",
 '#tr-dashed': 'Follows dashed or dotted curves across their gaps.',
 '#tr-comp': ['Adds a target back, for graphs drawn relative to one.', 'compensated']}

WIKI = {'intro': 'Every term the app uses, and answers to the questions that come up most. Point at a setting to see what '
          'it does in a line; here it is in full.',
 'steps': ['Choose a Target: the sound you want (e.g. a Harman or diffuse-field curve).',
           'Choose a Measurement: your IEM or headphone, from the app, this PC or the online databases.',
           'Choose Your EQ app: the app or device that will play the EQ. Its limits are kept and its file is saved.',
           'Press Run. The automatic settings are fitted to your files: the line above Run says what it tries.',
           'Check the result on the graph, edit the filters if you like, listen, and Save filters.'],
 'groups': [{'title': 'Curves and sound',
             'terms': [{'id': 'frequency-response',
                        'title': 'Frequency response (FR)',
                        'body': ['How loud an IEM or headphone plays each pitch, from deep bass (20 Hz) to the '
                                 'highest treble (20 kHz), drawn as a curve: left to right is low to high pitch, up '
                                 'is louder.',
                                 'Two earphones that measure alike sound alike in tone. EQ changes the frequency '
                                 'response, so EQing one towards a target makes it sound more like that target.'],
                        'see': ['target', 'measurement', 'db', 'hz']},
                       {'id': 'target',
                        'title': 'Target',
                        'body': ['The frequency response you want your earphone to have: a curve someone designed to '
                                 "sound neutral or pleasant (Harman, a diffuse-field curve, a reviewer's own). The "
                                 'EQ is fitted so your measurement matches it.',
                                 'A target is made for one measuring rig, because rigs measure the same earphone '
                                 'differently. The app tells you when your measurement comes from another rig, and '
                                 'can convert the target for it.'],
                        'see': ['measurement', 'rig', 'rig-conversion', 'target-adjustments']},
                       {'id': 'measurement',
                        'title': 'Measurement',
                        'body': ['A frequency response of your IEM or headphone, measured by you or by a reviewer '
                                 "(the online databases have about 54,500). It's usually a file per channel (L, R) "
                                 'and sometimes per seating; the ticked files are averaged.',
                                 'Units of one model differ, and so do fit and tips, so a measurement is a close '
                                 'guide to your own earphone, not an exact copy.'],
                        'see': ['seatings', 'unit-variation', 'rig', 'databases']},
                       {'id': 'db',
                        'title': 'dB (decibel)',
                        'body': ['The unit of loudness differences. +6 dB is clearly louder, +1 dB is about the '
                                 'smallest change most people notice in a broad region, and +10 dB sounds roughly '
                                 'twice as loud.',
                                 "On the graph, dB is the height of a curve. A filter's gain is in dB, and so is the "
                                 'error.'],
                        'see': ['error', 'preamp']},
                       {'id': 'hz',
                        'title': 'Hz, kHz and octaves',
                        'body': ['Hz (hertz) is the pitch: how many vibrations per second. 20 Hz is the deepest '
                                 'bass, 1000 Hz (1 kHz) the middle, 20 kHz the highest anyone hears.',
                                 'An octave is a doubling of pitch (100 to 200 Hz, 1 to 2 kHz). Hearing works in '
                                 "octaves, so the graph's frequency axis is drawn in octaves: each doubling takes "
                                 'the same width.'],
                        'see': ['frequency-response', 'q']},
                       {'id': 'level-matching',
                        'title': 'Level matching (normalization)',
                        'body': ["Curves are measured at different volumes, so before comparing they're moved up or "
                                 'down to line up. Only their overall height changes, never their shape.',
                                 ['Hz~: lined up on the average of the four octaves around a frequency '
                                  "(listener800's default, around 500 Hz).",
                                  'Hz: lined up at one frequency.',
                                  "dB: every curve set to the same loudness in phon (squig.link's default)."],
                                 'Advanced › Website › Level matching chooses it. It matters for the website '
                                 'methods, which copy the site exactly.'],
                        'see': ['phon', 'website-autoeq']},
                       {'id': 'phon',
                        'title': 'Phon and equal loudness',
                        'body': ["We don't hear every pitch as equally loud: bass and the highest treble need more "
                                 'energy to sound as loud as the middle, more so at low volumes. Equal-loudness '
                                 'tables (ISO 226) describe this.',
                                 'The phon is a loudness scale built on them. Level matching in dB mode sets every '
                                 'curve to the same loudness, e.g. 60 phon, a normal listening level.'],
                        'see': ['level-matching']},
                       {'id': 'smoothing',
                        'title': 'Smoothing',
                        'body': ["Evens out a curve's small ripples, as a reviewer's graph site does before showing "
                                 'it. The website methods smooth as the site does, so the results match it exactly; '
                                 '0 = no smoothing.'],
                        'see': ['website-autoeq']},
                       {'id': 'target-adjustments',
                        'title': 'Target adjustments (Custom DF)',
                        'body': ["listener800's controls for shaping a target to taste (Adjust, on the Target "
                                 'card): a tilt for the whole curve (dB per octave: negative = darker), and '
                                 'shelves or bumps for the bass, a half-tilt, the ear-gain region (2-5 kHz), the '
                                 'treble and the air above 10 kHz.',
                                 'Each has a gain (how much), a frequency (where) and for most a Q (how sharp the '
                                 'change is). They change the target before the EQ is fitted, with the same maths as '
                                 'the website.'],
                        'see': ['target', 'shelf', 'q']}]},
            {'title': 'EQ and filters',
             'terms': [{'id': 'eq',
                        'title': 'EQ: parametric and graphic',
                        'body': ['An equalizer changes how loud each part of the sound is. A parametric EQ has '
                                 'filters you place anywhere: each has a frequency, a gain and a Q. A graphic EQ has '
                                 'sliders at set frequencies (e.g. 10 bands from 31 Hz to 16 kHz): only their gains '
                                 'can change.',
                                 'Best fit makes either kind, within what your EQ app can take.'],
                        'see': ['peaking-filter', 'fixed-bands', 'eq-app']},
                       {'id': 'peaking-filter',
                        'title': 'Peaking filter (Peak, PK)',
                        'body': ['A boost or cut shaped like a hill or a dip, centred on a frequency. Three numbers '
                                 'set it: the frequency (where), the gain in dB (how much: + boosts, − cuts) and the '
                                 'Q (how wide).',
                                 'Most EQ apps call it Peak, PK, Bell or Parametric.'],
                        'see': ['q', 'shelf', 'db']},
                       {'id': 'q',
                        'title': 'Q (filter width)',
                        'body': ['How wide a filter is. A low Q (0.5-1) is a broad, gentle change over several '
                                 'octaves; a high Q (5-10) a narrow notch or spike. Q 1.41 is about an octave wide, '
                                 'Q 4.3 about a third of an octave.',
                                 'Broad filters change the overall tone and are forgiving of how the earphone sits '
                                 "in your ear. Narrow ones fix a sharp peak, but a peak's exact place moves with fit "
                                 "and tips, so very narrow filters can miss it on your ears. That's why the Q limits "
                                 'stop where tests found they stop helping.'],
                        'see': ['peaking-filter', 'shelf', 'unit-variation']},
                       {'id': 'shelf',
                        'title': 'Shelf filter (low shelf, high shelf)',
                        'body': ['Lifts or lowers everything below (low shelf) or above (high shelf) a corner '
                                 'frequency, like a step. A low shelf is the usual way to add or remove bass as a '
                                 'whole; a high shelf does the same for the treble.',
                                 'Its Q sets how steep the step is: 0.707 is the standard shelf. In Equalizer APO '
                                 "files they're LSC and HSC."],
                        'see': ['peaking-filter', 'q']},
                       {'id': 'preamp',
                        'title': 'Pre-amp and clipping',
                        'body': ["A digital signal can't go above full scale: a boost on top of loud music would "
                                 'clip (distort). So an EQ with boosts needs the volume turned down first by its '
                                 'highest boost: the pre-amp, e.g. −6.3 dB.',
                                 "The app sets it from the EQ's highest point. Most saved files include it; in other "
                                 'apps, set it yourself. The music is a little quieter: turn your player up instead. '
                                 '“Safe” rounding rounds it down so it can never clip.'],
                        'see': ['db', 'eq-app']},
                       {'id': 'fixed-bands',
                        'title': 'Fixed bands (graphic EQ layout)',
                        'body': ['For an EQ whose sliders sit at set frequencies: only their gains are fitted, '
                                 "within the sliders' range and in their steps (1 dB, 0.5 dB…), so what you set on "
                                 'the sliders is exactly what was scored.',
                                 'Your EQ app sets this for graphic EQ apps; Advanced › Best fit › Layout has the '
                                 "plain 10, 15 and 31-band layouts, Spotify's, and your own band frequencies."],
                        'see': ['eq', 'layout', 'eq-app']},
                       {'id': 'impulse-response',
                        'title': 'Impulse response and convolution',
                        'body': ['Another way to save an EQ: a short sound file (.wav) that is the EQ itself. '
                                 "Convolution EQs (Viper4Android, JamesDSP, EasyEffects' Convolver, Roon, "
                                 'foobar2000, HQPlayer, Equalizer APO) play music through it.',
                                 'It holds any number of filters exactly. Its sample rate must match what your '
                                 'device plays at.'],
                        'see': ['sample-rate', 'file-formats']},
                       {'id': 'sample-rate',
                        'title': 'Sample rate',
                        'body': ['How many times per second digital audio is sampled: 44100 (CD) or 48000 are usual. '
                                 'Digital filters depend on it slightly at the very top of the treble, so the app '
                                 "uses the same rate as the place the EQ will play (the website's 48000, your "
                                 "impulse response's)."],
                        'see': ['impulse-response']}]},
            {'title': 'Rigs and measurements',
             'terms': [{'id': 'rig',
                        'title': 'Rig (ear simulator): 711, 5128, 43AG, HMS',
                        'body': ['The device an earphone is measured on: an artificial ear (and sometimes head) with '
                                 'a microphone where the eardrum would be. Each kind measures the same earphone '
                                 'differently, mostly above 2 kHz.',
                                 ['711: a 711-type IEC 60318-4 coupler (or a copy of one), the most common for IEMs.',
                                  "5128: Brüel & Kjær's 5128 head and torso, with a more lifelike ear canal; used "
                                  'for IEMs and headphones.',
                                  '43AG: the GRAS 43AG, for headphones (with a 711-type ear inside).',
                                  "HMS: Head Acoustics' HMS, a head used for older headphone and IEM data "
                                  '(Innerfidelity).'],
                                 'A target is made for one rig; compare and EQ on the same rig when you can, or let '
                                 'the app convert.'],
                        'see': ['rig-tags', 'rig-conversion', 'target']},
                       {'id': 'rig-tags',
                        'title': 'Rig tags: 5128, 711?, rig ?, ⇄',
                        'body': ['The tag after each entry in the search list says which rig it was measured on (for '
                                 "a target, the rig it's made for).",
                                 ['“5128”: stated by the source, or worked out from its measurements with high '
                                  'confidence.',
                                  '“711?” with a dashed outline: probably that rig (worked out with medium '
                                  'confidence, or the usual rig for that database).',
                                  '“rig ?”: not known.',
                                  '⇄ after a tag: that database has a conversion of its own (blue when one is for '
                                  "your target's rig)."],
                                 "Most reviewers don't say which rig they use, so the app compares each database's "
                                 'curves with sources whose rig is certain. Hover a tag to see how its rig was '
                                 'found.'],
                        'see': ['rig', 'unit-conversion']},
                       {'id': 'rig-conversion',
                        'title': 'Rig conversion',
                        'body': ['When your measurement and target come from different rigs, the target is converted '
                                 "to the measurement's rig: the average difference between the two rigs, from models "
                                 'measured on both in the online databases, is added to it. Without this the EQ '
                                 'would also try to “correct” the difference between the rigs.',
                                 "It narrows the gap but can't close it. Tested on models left out of the average, "
                                 'IEMs between a 711 and a 5128 (265 models): 1-3 kHz 2.4 → 1.0 dB, 3-6 kHz 3.2 → '
                                 '1.5 dB, 6-10 kHz 3.5 → 2.6 dB. Above 10 kHz much is left, so fine-tune the treble '
                                 'by ear.',
                                 "Pairs without enough data (e.g. IEMs between a 5128 and an HMS) aren't converted: "
                                 'the note says so. Settings › Target › Rig conversion switches it off.'],
                        'see': ['rig', 'unit-conversion', 'treble-limit']},
                       {'id': 'unit-conversion',
                        'title': "A database's own conversion",
                        'body': ["A reviewer's setup can differ from the rig it's filed under (a copy of a 711 "
                                 'coupler, how deep it seats IEMs, its calibration), or be none of the four. So a '
                                 'database that shares enough models with sources on a rig gets a conversion of its '
                                 "own: its curves compared with theirs. It's kept only when it does better than the "
                                 "rigs' average, consistently, on models left out (92 kept, for 64 databases).",
                                 'When your measurement comes from one, the note under the graph names it, and the '
                                 'search list shows ⇄.'],
                        'see': ['rig-conversion', 'rig-tags']},
                       {'id': 'seatings',
                        'title': 'Channels, seatings and averaging',
                        'body': ['Many measurements come as several files: the left and right earpieces (L, R), and '
                                 'sometimes several seatings, the earphone taken out and put in again. The ticked '
                                 'files are averaged, as squiglink does, which gives a steadier curve than any one '
                                 'of them.',
                                 'Where seatings disagree (often above 10 kHz) is where a measurement is least '
                                 'reliable: the automatic settings stop scoring there.'],
                        'see': ['measurement', 'scored-range', 'treble-limit']},
                       {'id': 'unit-variation',
                        'title': 'Unit-to-unit variation',
                        'body': ['Two units of one model, measured by different people, differ: by about 1 dB after '
                                 "EQ in the app's tests, and more in the treble. Your own unit, ears and tips differ "
                                 'again.',
                                 "So fitting one measurement closer than you can hear only fits that measurement's "
                                 'details. The app picks the simplest result that sounds the same as the target, and '
                                 'its limits stop where closer fits stopped helping other units.'],
                        'see': ['simplest', 'error', 'measurement']},
                       {'id': 'seal',
                        'title': 'Seal and leaky bass',
                        'body': ["An IEM that doesn't seal in the ear (or on the rig) loses bass. A measurement with "
                                 'much less bass than others of the same model was probably not sealed; an EQ fitted '
                                 'to it would boost bass you already have.',
                                 '“Which measurement to use” scores this (Bass), and Listen lets you check with your '
                                 'own ears.'],
                        'see': ['compare-measurements', 'measurement']},
                       {'id': 'treble-limit',
                        'title': 'The treble above about 10 kHz',
                        'body': ["Above about 10 kHz, an IEM's measured response changes a lot with how deep it "
                                 'sits, the tips and the ear canal, so a measurement there says little about what '
                                 'you hear. Matching it exactly can make things worse.',
                                 "So the automatic settings score the match only up to where the measurement's "
                                 'seatings still agree (often about 10 kHz). Filters may still go higher; they just '
                                 "aren't judged there. Fine-tune the treble by ear."],
                        'see': ['scored-range', 'seatings', 'rig-conversion']},
                       {'id': 'compensated',
                        'title': 'Compensated graph (relative to a target)',
                        'body': ["Some graphs show an earphone's difference from a target (a flat line = matches it) "
                                 'instead of its own response. When tracing one, choose that target under “The graph '
                                 "shows”, and it's added back when saving, so the file is the earphone's own "
                                 'response again.'],
                        'see': ['tracer']},
                       {'id': 'tracer',
                        'title': 'Trace image',
                        'body': ['Turns a picture of a frequency response graph into curve files: it reads the axes, '
                                 'follows a curve by its colour, and saves it as a measurement or target. ✎ Trace '
                                 "image (by the graph's title) opens it: drop, paste or open a picture there. It has "
                                 'its own Guide.'],
                        'see': ['compensated', 'measurement']}]},
            {'title': 'Fitting and scoring',
             'terms': [{'id': 'error',
                        'title': 'Error (dB)',
                        'body': ["How far the EQ'd measurement is from the target, on average over the scored range: "
                                 'the root mean square of the difference, in dB. 0 would be a perfect match.',
                                 "Under about 0.5 dB is a very close match; a few hundredths of a dB aren't audible. "
                                 'Compare errors only between results with the same scored range.'],
                        'see': ['scored-range', 'simplest', 'unit-variation']},
                       {'id': 'scored-range',
                        'title': 'Scored range',
                        'body': ['The frequencies the error is measured over (Score from … to). Outside it the EQ is '
                                 "free: filters may go there, they just aren't judged. Automatic settings set it "
                                 'from where your measurement stays reliable.'],
                        'see': ['error', 'treble-limit']},
                       {'id': 'best-fit',
                        'title': 'Best fit',
                        'body': ["The app's own method: it fits filters directly to the target within your EQ app's "
                                 'limits, adding them one at a time (each new filter where the EQ is furthest from the '
                                 'target, then all of them fitted again), and picks the simplest result that sounds '
                                 "the same as the target. Usually closer or simpler than the website's AutoEQ.",
                                 'Use it for any EQ app; save or copy its filters.'],
                        'see': ['website-autoeq', 'simplest', 'layout']},
                       {'id': 'website-autoeq',
                        'title': 'Website AutoEQ (squiglink)',
                        'body': ['The AutoEQ button on squiglink graph sites (squig.link, listener800). The app runs '
                                 "the site's own code, so “Website AutoEQ: one run” gives exactly the filters the "
                                 'site would for the same settings.',
                                 '“Find best settings” runs it for many combinations and tells you which values to '
                                 'type into the site.'],
                        'see': ['sweep', 'best-fit', 'level-matching']},
                       {'id': 'sweep',
                        'title': 'Find best settings (website sweep)',
                        'body': ["Runs the website's AutoEQ for every combination of the lists you give (filter "
                                 'rows, frequency, gain and Q ranges) and picks by the Scoring rule. Use it when the '
                                 'EQ goes into the website: you then type the winning values into its AutoEQ panel.'],
                        'see': ['website-autoeq', 'simplest']},
                       {'id': 'simplest',
                        'title': 'The simplest that sounds the same',
                        'body': ["Of all a run's results, the one with the fewest filters (then the lowest max Q, "
                                 'then the smallest boost) that sounds the same as the target: within 0.25 dB '
                                 "everywhere, judged as the ear hears it (the difference smoothed to the ear's "
                                 'frequency resolution, the overall level left out). 0.25 dB is about the smallest '
                                 'broad change listeners noticed in pink noise, the most revealing sound. Fewer, '
                                 'broader filters are easier to enter and less sensitive to fit.',
                                 "When your EQ app's limits (or a measurement filters can't follow) keep every "
                                 'result further off, the simplest that sounds the same as the closest one; the '
                                 'result says how far off it is and where.',
                                 'The other choice (Settings › Scoring › Pick): the lowest error, however many '
                                 'filters it takes. (Until 1.0.9 also the simplest within 0.1 dB of the best average '
                                 'error: an average can hide a broad difference you can hear.)'],
                        'see': ['error', 'unit-variation']},
                       {'id': 'penalties',
                        'title': 'Penalties and the treble guard',
                        'body': [['Fighting-filter penalties (Advanced): discourage filters that cancel each other (a '
                                  'boost on top of a cut), which add nothing but sensitivity. Each value listed is '
                                  'tried.',
                                  'Gain penalty: discourages needlessly large boosts and cuts.',
                                  "Treble guard: keeps the EQ's average effect above the scored range near 0 dB, so "
                                  "filters don't wander there."],
                                 'Each makes the error count a little worse when the fit does that thing. The gain '
                                 'penalty and treble guard are set for you (the tests never found better values).'],
                        'see': ['best-fit']},
                       {'id': 'automatic-settings',
                        'title': 'Automatic settings, “yours” and ↺',
                        'body': ["With a target and a measurement chosen, the method's settings are fitted to them: "
                                 'how far up the match is scored, how many filters, how much boost and cut, how '
                                 'narrow, whether to use a low shelf. “Why these values” lists the reason for each.',
                                 "Change a setting and it's marked “yours”: it keeps your value from then on. “yours "
                                 '↺” hands it back. Untick Automatic settings to use every setting exactly as it '
                                 'is.'],
                        'see': ['speed-accuracy']},
                       {'id': 'speed-accuracy',
                        'title': 'The search',
                        'body': ['What a run tries: Best fit adds filters one at a time under every boost and Q limit '
                                 'that suits your curves, each with two fighting-filter penalties, until the EQ sounds '
                                 'the same as the target. The line above Run says what will be tried and roughly how '
                                 'long it takes on this PC.',
                                 'There were three searches (Quick, Standard, Thorough) until 1.0.8. Once Best fit '
                                 'grew its EQs all three took seconds, and one search trying everything they tried '
                                 'found the fewest filters for every IEM and headphone tested: a few seconds for most, '
                                 'up to about a minute and a half for a headphone the EQ can\'t bring all the way.'],
                        'see': ['automatic-settings', 'best-fit']},
                       {'id': 'layout',
                        'title': 'Layout',
                        'body': ['What the EQ is for, so Best fit keeps to it: any filters (an app that takes any), '
                                 "fixed bands (a graphic EQ's sliders), or an EQ app's own (its number of filters, "
                                 'shelves, and gain, Q and frequency ranges). Your EQ app sets it; Advanced › Best '
                                 'fit › Layout shows it.'],
                        'see': ['eq-app', 'fixed-bands']},
                       {'id': 'limits',
                        'title': 'Limits (allowed range)',
                        'body': ['Every number has a floor and a ceiling, shown when you point at a box. A value '
                                 'outside turns red, and leaving the box moves it to the nearest limit.',
                                 "Each limit is a hard limit of what uses it (e.g. the website's Q 5) or measured: "
                                 "e.g. Best fit's boost up to +35 dB and Q up to 27 cover what 99.9% of 3,000 real "
                                 'measurements need.'],
                        'see': []},
                       {'id': 'own-filters',
                        'title': 'Start from your own filters',
                        'body': ['Best fit can start from an EQ you already have: typed as filter lines, as a table '
                                 'or sliders (Edit as a table…), or from an EQ file (Load an EQ file…). “Keep them '
                                 'exactly as they are”: Best fit adds filters on top of yours. Off: yours are a '
                                 'starting point the fit may move too. One more result shows yours alone, to '
                                 'compare.',
                                 'While you edit them, the graph shows the measurement with them as “With your '
                                 'filters”.'],
                        'see': ['retry', 'best-fit']},
                       {'id': 'retry',
                        'title': 'Retry from these filters',
                        'body': ['On the result card, after editing filters: runs Best fit again from the ones '
                                 'shown, for this run only. “Fine-tune them” moves each a little to match closer; '
                                 '“Keep them, add filters” keeps yours exactly and adds filters.'],
                        'see': ['own-filters']}]},
            {'title': 'Apps, files and listening',
             'terms': [{'id': 'eq-app',
                        'title': 'Your EQ app',
                        'body': ['The app or device that will play the EQ (Equalizer APO, Poweramp, Wavelet, a '
                                 'Qudelix…). Choosing it keeps its own limits (how many bands, the gain, Q and '
                                 "frequency ranges, a graphic EQ's sliders) and ticks exactly the file it imports "
                                 'for Save filters. The line under it says how to load the EQ, with a link to where '
                                 'its limits come from.',
                                 'Apps without a file of their own (Qudelix, FiiO, Moondrop…) are entered by hand '
                                 'from the filter table or the report. “Not listed, or not sure”: any filters, saved '
                                 'as an Equalizer APO file, which many apps read.'],
                        'see': ['file-formats', 'layout', 'preamp']},
                       {'id': 'file-formats',
                        'title': 'Saved file formats',
                        'body': [["Equalizer APO / squiglink (.txt): Equalizer APO, Peace, EasyEffects, squiglink's "
                                  'Import.',
                                  'GraphicEQ (.txt): Wavelet, RootlessJamesDSP.',
                                  'Poweramp (.json), USB Audio Player PRO (.xml): Android.',
                                  'SoundSource (.txt): macOS. Voicemeeter (.xml): Windows. Rockbox (.cfg): music '
                                  'players.',
                                  'Impulse response (.wav): convolution EQs.'],
                                 "Each file keeps to its app's limits; when that would change the EQ by 0.1 dB or "
                                 'more, saving says by how much. Advanced › Saved files ticks others. Files go to '
                                 'your Saved EQs folder (Settings › Your files).'],
                        'see': ['eq-app', 'impulse-response', 'preamp']},
                       {'id': 'databases',
                        'title': 'Online databases and This PC',
                        'body': ['The search list finds curves in three places: files already in the app, curve '
                                 'files on this PC (in Downloads, Documents, Desktop and Music), and about 150 '
                                 "online databases (squig.link's list, the AutoEq repository, listener800). Online "
                                 'ones download when you use or preview them.',
                                 'Find… › Sources… turns databases on or off, adds another squig.link-style page, '
                                 'and sets the folders searched on this PC. Offline, the lists saved before and the '
                                 'curves downloaded before are used.'],
                        'see': ['rig-tags', 'measurement']},
                       {'id': 'compare-measurements',
                        'title': 'Which measurement to use',
                        'body': ['“Other measurements of this model” under Measurement finds every measurement of '
                                 'your model, levels them together and ranks them for your target: the rig (and how '
                                 'well it converts), agreement with the others, the bass (a leaky seal), how many '
                                 'seatings were averaged, and the data. It can also average several from one rig.',
                                 "Each source's rig is as it states, or the usual one for that kind of database. "
                                 "It's a recommendation: units, fit and tips vary."],
                        'see': ['rig-conversion', 'seal', 'seatings']},
                       {'id': 'history',
                        'title': 'History',
                        'body': ["Your past EQs, kept between sessions (History, by the graph's title): the ones you "
                                 'save or copy, or every run (Advanced › History). Show brings one back with its '
                                 'files and settings; Listen adds it to your EQs to compare.'],
                        'see': ['eqs-to-compare']},
                       {'id': 'eqs-to-compare',
                        'title': 'EQs to compare',
                        'body': ['A list per IEM or headphone (up to 12) of EQs you want to hear side by side: from '
                                 'a result (📌 Keep to compare), History, an EQ file or pasted filters. Each is a '
                                 'version in Listen (keys 1-9) and, while Graph is ticked, a curve on the graph. '
                                 'Kept between sessions.'],
                        'see': ['match-loudness', 'history']},
                       {'id': 'match-loudness',
                        'title': 'Level-matched (Listen)',
                        'body': ['Plays every version in Listen equally loud. Louder tends to sound better, so '
                                 'without it the version with more boost often wins for the wrong reason.'],
                        'see': ['blind-test', 'eqs-to-compare']},
                       {'id': 'blind-test',
                        'title': 'Blind test',
                        'body': ['Hides which version is which (A, B…) until you press Reveal, so what you expect '
                                 "doesn't decide what you hear. Switch between them with the buttons or keys 1-9."],
                        'see': ['match-loudness']}]}],
 'settings': [{'title': 'Choosing and running',
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
                          'title': '↻ Retry from these filters',
                          'body': ['Runs Best fit again from the filters shown, for this run only. Fine-tune them: '
                                   'each moves a little to match closer. Keep them, add filters: yours stay exactly '
                                   'and more are added.']},
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
                                   'card (📌 Keep to compare, or + The selected EQ), one from History (Listen), an EQ '
                                   'file or pasted filters. Edit a name to rename it. Each measurement has its own '
                                   'list, kept between sessions (up to 12).']}]},
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
                                   'puts them all back to 0 (Undo, in the notice, brings them back).'],
                          'see': ['target-adjustments']},
                         {'key': '#target-save',
                          'title': 'Save as a target…',
                          'body': ['Shown once the target is adjusted (tilt, bass, ear gain, treble …). It saves the '
                                   'target as adjusted as a target of your own (in the app\'s targets, under the name '
                                   'you give), puts it in use and sets the adjustments back to 0, since they are in it '
                                   'now. It is made for the original target\'s rig and converted for a measurement '
                                   'the same way. Undo, in the notice, puts everything back.']}]},
              {'title': 'Presets',
               'items': [{'key': '#presets',
                          'title': 'Presets ▾ (top bar, on Make an EQ)',
                          'body': ['A preset keeps every setting of Make an EQ under a name: your EQ app, the method, '
                                   'the automatic settings and your own values, the target adjustments, '
                                   'scoring, Advanced. Not your files: the target and measurement stay as they are. '
                                   'Keep one per use, e.g. one for the website and one for Equalizer APO.',
                                   'Save current settings as… asks for a name (the same name again replaces that '
                                   'preset); click a preset to load all its settings, and Undo in the notice puts the '
                                   'ones before back. Delete a preset removes one; Reset all settings… puts every '
                                   'setting back to its default (your files and presets are kept). Presets are files '
                                   'in your Presets folder (Settings › Your files).']}]},
              {'title': 'Devices',
               'items': [{'key': '#dev-check',
                          'title': 'Is the EQ playing? (Check again)',
                          'body': ["The line under a device's EQ says whether it really plays (✓) or not (✕). "
                                   "AutoEQ Studio asks Equalizer APO's own Benchmark tool (read only: nothing is "
                                   'changed) by itself, and again whenever the EQ, config.txt or the device changes. '
                                   'Check again asks now and says all it found: whether APO reads AutoEQ Studio\'s '
                                   "file, finds this device's section and loads the EQ chosen for it, and what "
                                   'config.txt loads for every device on top.']},
                         {'key': '#files-folder',
                          'title': 'Your files (Settings)',
                          'body': ['Your targets and measurements (what Make an EQ uses), saved EQs and reports, and '
                                   'presets are in one folder, each kind in a folder of its own: Targets, '
                                   'Measurements, Saved EQs, Presets. It\'s Documents\\AutoEQ Studio, where Windows '
                                   'apps keep the files you make, unless you choose another. You can put curve files '
                                   'in Targets and Measurements yourself (Explorer, or Open the folder): Make an EQ '
                                   'lists them.',
                                   'Change… picks another folder (not inside AutoEQ Studio\'s own: an update would '
                                   'lose them), offers to move your files there (a file with the same name is never '
                                   'replaced: a different one is kept beside it, with (2) after its name), and starts '
                                   'AutoEQ Studio again to use it. An older AutoEQ Studio kept them in its own '
                                   'folder (inputs, output, presets): the first time Make an EQ opens, it offers to '
                                   'move them.']},
                         {'key': '#backup',
                          'title': 'Backup (Settings)',
                          'body': ['Back up everything… writes one .zip with all that is yours: the devices, their '
                                   'profiles and their EQ files, Make an EQ\'s settings, History, your EQs to compare, '
                                   'your targets and measurements, presets and saved EQs (not the curves downloaded '
                                   'from the online databases: they download again when used). Restore from a '
                                   'backup… puts them back, on this PC or another, after keeping how things are now '
                                   '(data\\backups); files with the same name are replaced, nothing else is deleted. '
                                   'AutoEQ Studio starts again after it.']},
                         {'key': '#dev-rename',
                          'title': 'Rename… (a device)',
                          'body': ['Your own name for a device (e.g. “Dongle – KZ”), shown in the list, the tray '
                                   'and the notices. Windows\' name stays under it. Empty: Windows\' name again.']},
                         {'key': '#use-try',
                          'title': 'Try for 5 minutes on (Use on device)',
                          'body': ['Plays the EQ on a device in every app (your music player, games…) for 5 '
                                   'minutes, without making it a profile. A bar at the top (and the tray icon\'s '
                                   'menu) says the time left, with Keep it (it becomes a profile, switched on) and '
                                   'Stop now. When the time is up, or AutoEQ Studio quits, the device\'s own EQ '
                                   'comes back.']}]},
              {'title': 'Trace image',
               'items': [{'key': '#tr-auto-on',
                          'title': 'Automatic settings (tracer)',
                          'body': ["Fits the tracer's settings to the image: colour tolerance, points per octave, "
                                   'the range to save, dashed lines. A setting you change is marked “yours” and kept '
                                   'for the next trace too, until you hand it back with ↺.',
                                   'It always works carefully: the labels read large with a second try, the trace '
                                   'placed between pixels, a trace that stops early tried again as a dashed line and '
                                   'with more colour tolerance. (A speed-accuracy slider chose until 1.0.13: every '
                                   'way took about a second, and the quick one missed dashed lines.)']},
                         {'key': '#tr-d1',
                          'title': 'Top red line (dB)',
                          'body': ['The dB label of the gridline under the top red line. Any two labelled lines far '
                                   'apart work.']},
                         {'key': '#tr-d2',
                          'title': 'Bottom red line (dB)',
                          'body': ['The dB label of the gridline under the bottom red line.']},
                         {'key': '#tr-f1',
                          'title': 'Left blue line (Hz)',
                          'body': ["The frequency of the gridline under the left blue line. Filled in when it's read "
                                   'from the image: check it.']},
                         {'key': '#tr-f2',
                          'title': 'Right blue line (Hz)',
                          'body': ['The frequency of the gridline under the right blue line.']},
                         {'key': '#tr-snap',
                          'title': 'Snap to gridlines',
                          'body': ['Dragged lines jump onto the nearest gridline, so they sit exactly on it.']},
                         {'key': '#tr-every',
                          'title': 'Follow every gridline',
                          'body': ['Uses every gridline in between, for graphs whose axes are drawn unevenly. '
                                   'Harmless otherwise.']},
                         {'key': '#tr-tol',
                          'title': 'Colour tolerance',
                          'body': ["How far a pixel's colour may be from the curve's and still count. Raise it for "
                                   'faded or blurry curves; lower it if the trace jumps to another line.']},
                         {'key': '#tr-ppo',
                          'title': 'Points per octave',
                          'body': ['How many points per octave are saved. 48 matches squiglink; more only makes the '
                                   'file bigger.']},
                         {'key': '#tr-fmin',
                          'title': 'Save from … to (Hz)',
                          'body': ['The frequency range to save (from … to), within what you traced. Auto: what the '
                                   "graph's axis covers."]},
                         {'key': '#tr-name',
                          'title': 'Name',
                          'body': ["The saved file's name. With several curves, each gets its label added (e.g. L "
                                   'and R).']},
                         {'key': '#tr-dashed',
                          'title': 'Dashed or dotted line',
                          'body': ['For dashed or dotted curves: the trace carries on across the gaps.']},
                         {'key': '#tr-comp',
                          'title': 'The graph shows (compensated)',
                          'body': ['If the graph shows the difference from a target (compensated), choose that '
                                   "target: it's added back when saving. The target must be in the app."]}]}],
 'questions': [{'id': 'q-which-method',
                'q': 'Which EQ method should I use?',
                'body': ['Choose Your EQ app first: it picks the method. For the website (squig.link, listener800), '
                         'the Website methods reproduce its AutoEQ exactly, so you only type its settings. For '
                         'anything else, use Best fit, which is usually closer or simpler, and save or copy its '
                         'file.'],
                'see': ['best-fit', 'website-autoeq', 'eq-app']},
               {'id': 'q-error',
                'q': 'What does the error number mean? Is mine good?',
                'body': ["It's the average difference between the EQ'd curve and the target over the scored range. "
                         "Under about 0.5 dB is a very close match; differences of a few hundredths of a dB aren't "
                         'audible. Two units of one model differ by about 1 dB, so chasing the last tenth only fits '
                         'the measurement, not your earphone.'],
                'see': ['error', 'unit-variation']},
               {'id': 'q-treble',
                'q': "Why isn't the treble matched exactly? Why stop scoring at 10 kHz?",
                'body': ["Above about 10 kHz an IEM's response changes with insertion depth, tips and your ear, so a "
                         'measurement there is unreliable and an exact match can sound worse. The automatic settings '
                         "score only as far as the measurement's seatings agree. Fine-tune the treble by ear in "
                         'Listen.'],
                'see': ['treble-limit', 'scored-range']},
               {'id': 'q-preamp',
                'q': 'Why is the pre-amp negative? Will it be quieter?',
                'body': ["Boosts need headroom, or loud music clips. The pre-amp turns the volume down by the EQ's "
                         "highest boost, so it's quieter: turn your player up to make up for it. Set it in your EQ "
                         'app with the filters; most saved files include it.'],
                'see': ['preamp']},
               {'id': 'q-filters',
                'q': 'How many filters should I use?',
                'body': ['Let the app decide: it adds filters one at a time and keeps the fewest that make the EQ '
                         'sound the same as the target (usually 8 to 19 in tests). If your EQ app has fewer bands, '
                         'choose it as Your EQ app and its limit is kept. “Fewer or more filters” on the result card shows the best result '
                         'for each count, one click away.'],
                'see': ['simplest', 'eq-app']},
               {'id': 'q-rigs',
                'q': 'My measurement and target come from different rigs. What happens?',
                'body': ["A note under the graph says so, and the target is converted to the measurement's rig "
                         '(Settings › Target › Rig conversion turns it off). That removes most of the '
                         "rigs' difference below 6 kHz, less above. A target made for your measurement's rig, or a "
                         "measurement from the target's rig, is still best."],
                'see': ['rig-conversion', 'rig']},
               {'id': 'q-many',
                'q': 'There are many measurements of my IEM. Which one?',
                'body': ['Use “Other measurements of this model…” under Measurement: it ranks them for your target '
                         'with the reasons (rig, agreement with the others, bass seal, averaging, data), and can '
                         'average several from one rig.'],
                'see': ['compare-measurements', 'seal']},
               {'id': 'q-website',
                'q': "Why does my result differ from squig.link's AutoEQ?",
                'body': ['Best fit is a different method: it usually finds a closer or simpler EQ than the site. The '
                         'Website methods give exactly what the site gives, if Advanced › Website matches the site '
                         'you use (which site to copy, level matching, smoothing) and the same target adjustments '
                         'are set.'],
                'see': ['website-autoeq', 'level-matching']},
               {'id': 'q-sounds-wrong',
                'q': 'The EQ looks right but sounds wrong. Why?',
                'body': ['You hear your own unit, ears and tips plus the EQ; the measurement was another unit, on a '
                         'rig. Check the seal and tips first (lost bass is the usual sign). Try another measurement '
                         'of the model, compare versions in Listen with Level-matched on, and fine-tune the filters '
                         'by ear: the table and sliders are editable.'],
                'see': ['unit-variation', 'seal', 'match-loudness']},
               {'id': 'q-yours',
                'q': 'What does “yours” next to a setting mean?',
                'body': ['You changed it, so the automatic settings leave it alone from then on. “yours ↺” hands it '
                         'back to automatic.'],
                'see': ['automatic-settings']},
               {'id': 'q-auto-why',
                'q': 'Why do the automatic settings choose these values?',
                'body': ['Each value under “Why these values” comes from your measurement and target, and from tests '
                         'on real measurements:',
                         ["Scored range: up to where your measurement's files (seatings, channels) still agree, "
                          'often about 10 kHz. Above that a measurement changes with fit and insertion depth, so '
                          "matching it there doesn't help.",
                          'Filter counts: up to where fits stop improving (32 filters for Best fit, 20 rows for the '
                          'website). The simplest result that sounds the same as the target is kept (within 0.25 dB '
                          'everywhere, as the ear hears it): on 15 IEMs and headphones the old rule, the simplest '
                          'within 0.1 dB of the best average error, differed from the closest by up to 0.87 dB '
                          'somewhere.',
                          'Boost and cut: enough for what the target needs, with a little room.',
                          'Q: from the narrowest peak or dip, and Q 3 to 5 too: with many filters they matched '
                          'closer in tests, also on other units, while Q 8-16 did worse.',
                          'Low shelf: on when the bass is 3 dB or more off as a whole. (No high shelf: in tests it '
                          'helped about as often as it made the fit worse.)',
                          'Fighting-filter penalties: 0.003 and 0.01, every limit with each. The lighter one '
                          'found the fewest filters for most IEMs and headphones in tests, the stronger one for a few '
                          '(the HD600: 15 filters against 19).']],
                'see': ['automatic-settings', 'speed-accuracy', 'simplest', 'treble-limit']},
               {'id': 'q-have-eq',
                'q': 'I already have an EQ. Can I improve it?',
                'body': ["Yes: Best fit's “Start from your own filters” (typed, or Load an EQ file…), or edit a "
                         "result's filters and use Retry from these filters. Best fit fine-tunes yours or adds "
                         'filters to them.'],
                'see': ['own-filters', 'retry']},
               {'id': 'q-load',
                'q': 'How do I get the EQ into my app?',
                'body': ['Choose it as Your EQ app: the line under it says how to load the EQ, and Save filters '
                         'writes its file to your Saved EQs folder (“Open the Saved EQs folder” on the result card). For '
                         'apps without a file, type the filters from the table (or the report) into the app.'],
                'see': ['eq-app', 'file-formats']},
               {'id': 'q-graph',
                'q': 'I only have a picture of a graph. Can I use it?',
                'body': ["Yes: ✎ Trace image (by the graph's title), then drop, paste or open the picture there. It "
                         'reads the axes, follows the curve and saves it as a measurement or target.'],
                'see': ['tracer']},
               {'id': 'q-listen',
                'q': 'How should I listen to compare EQs?',
                'body': ['With the IEM or headphone that was measured, the same tips, at a low volume first. Keep '
                         "Level-matched on, switch between versions with keys 1-9, and try Blind test so you don't "
                         'know which is which.'],
                'see': ['match-loudness', 'blind-test', 'eqs-to-compare']},
               {'id': 'q-applies',
                'q': "I switched an EQ on but can't hear it. Is it applied?",
                'body': ["Devices › the device: the line under its EQ says whether APO plays it (Check again asks "
                         "now). The usual causes: APO isn't installed on that device (APO's Configurator, then "
                         'restart), config.txt has no line for AutoEQ Studio (Set up… at the top of Devices), or '
                         'another app\'s EQ in config.txt applies on top.'],
                'see': []},
               {'id': 'q-try',
                'q': 'Can I hear an EQ in my own music player before keeping it?',
                'body': ['Yes: Use on device › Try for 5 minutes on, and the device. It plays in every app for 5 '
                         "minutes; Keep it makes it the device's profile, otherwise its own EQ comes back. Listen, "
                         'under the result, compares versions inside AutoEQ Studio.'],
                'see': []},
               {'id': 'q-files',
                'q': 'Where are my files? Is anything uploaded?',
                'body': ["Everything stays on this PC. Your targets, measurements, saved EQs and presets are in "
                         'Documents\\AutoEQ Studio (Targets, Measurements, Saved EQs, Presets), or the folder you '
                         'chose: Settings › Your files shows it and changes it. The app\'s own settings, History and '
                         'log are in AppData\\Roaming\\AutoEQ Studio when it\'s installed (in its data folder when '
                         'run from its own folder), the downloaded curves in AppData\\Local\\AutoEQ Studio (its '
                         "downloads folder). The only things fetched from the internet are the databases' lists "
                         'and the curves you use or preview, and nothing at all while AutoEQ Studio is Offline (top '
                         'right).'],
                'see': ['databases']}]}
