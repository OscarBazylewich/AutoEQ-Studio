"""The Help page's words that every screen shares (help_window.py shows them; help_texts.py joins them into
WIKI with the screens' own): INTRO, the line at the top of the page; STEPS, an EQ job in five steps; TERMS, the
five groups of terms (Curves and sound, EQ and filters, Rigs and measurements, Fitting and scoring, Apps, files
and listening); QUESTIONS, the answers to the questions that come up most. Words only: nothing is imported here.
"""
# flake8: noqa

INTRO = ('Every term the app uses, and answers to the questions that come up most. Point at a setting to see what '
         'it does in a line; here it is in full.')

STEPS = ['Choose a Target: the sound you want (e.g. a Harman or diffuse-field curve).',
         'Choose a Measurement: your IEM or headphone, from the app, this PC or the online databases.',
         'Choose Your EQ app: the app or device that will play the EQ. Its limits are kept and its file is saved.',
         'Press Run. The automatic settings are fitted to your files: the line above Run says what it tries.',
         'Check the result on the graph, edit the filters if you like, listen, and Save filters.']

TERMS = [{'title': 'Curves and sound',
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
                     'see': ['match-loudness']}]}]

QUESTIONS = [{'id': 'q-which-method',
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
              'see': ['databases']}]
