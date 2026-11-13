"""The Help page's words that every screen shares (help_window.py shows them; help_texts.py joins them into
WIKI with the screens' own): INTRO, the line at the top of the page; STEPS, an EQ job in five steps; TERMS, the
five groups of terms (Curves and sound, EQ and filters, Rigs and measurements, Fitting and scoring, Apps, files
and listening); QUESTIONS, the answers to the questions that come up most. Words only: nothing is imported here.
"""
# flake8: noqa

INTRO = ('This page gives all the names that the app uses, and help for frequent problems. Put the cursor on '
         'a setting to see a short text about it. The full text is on this page.')

STEPS = ['Select a Target: the sound that you want (for example, a Harman or diffuse-field curve).',
         'Select a Measurement: your IEM or headphone, from the app, this PC or the online databases.',
         'Select Your EQ app: the app or device that will play the EQ. The EQ stays in its limits, and the app '
         'saves its file.',
         'Click Calculate. The app adjusts the automatic settings for your files. The line Settings to try shows '
         'the number of EQs that it tries (its tooltip shows the settings).',
         'Examine the result on the graph. If necessary, edit the filters. Listen to the EQ. Click Save filters.']

TERMS = [{'title': 'Curves and sound',
          'terms': [{'id': 'frequency-response',
                     'title': 'Frequency response (FR)',
                     'body': ['The loudness of each frequency that an IEM or headphone plays, from the deep bass '
                              '(20 Hz) to the highest treble (20 kHz). The graph shows it as a curve: low '
                              'frequencies on the left, high frequencies on the right, more loudness at the top.',
                              'Two earphones with the same measurement have the same tone. An EQ changes the '
                              'frequency response. Thus, an EQ for a target makes the sound of the earphone '
                              'nearer to the sound of that target.'],
                     'see': ['target', 'measurement', 'db', 'hz']},
                    {'id': 'target',
                     'title': 'Target',
                     'body': ['The frequency response that you want for your earphone. It is a curve for a neutral '
                              'or good sound (Harman, a diffuse-field curve, or the curve of a person who measures '
                              'earphones). The app adjusts the EQ to make your measurement agree with the '
                              'target.',
                              'A target is for one rig, because different rigs give different measurements of the '
                              'same earphone. If your measurement comes from a different rig, the app tells you. '
                              'It can change the target for that rig.'],
                     'see': ['measurement', 'rig', 'rig-conversion', 'target-adjustments']},
                    {'id': 'measurement',
                     'title': 'Measurement',
                     'body': ['A frequency response of your IEM or headphone, that you or a different person '
                              'measured (the online databases have approximately 54,500). Usually, it has a file '
                              'for each channel (L, R). Some measurements also have a file for each seating. The '
                              'app uses the average of the selected files.',
                              'Units of one model are different, and the position in the ear and the tips are '
                              'also different. Thus, a measurement is a good guide to your earphone, but not an '
                              'accurate copy.'],
                     'see': ['seatings', 'unit-variation', 'rig', 'databases']},
                    {'id': 'db',
                     'title': 'dB (decibel)',
                     'body': ['The unit of differences in loudness. +6 dB gives a clearly higher loudness. +1 dB '
                              'is approximately the smallest change that most persons hear across a wide '
                              'frequency range. +10 dB is approximately two times the loudness.',
                              'On the graph, dB is the height of a curve. The gain of a filter and the error are '
                              'also in dB.'],
                     'see': ['error', 'preamp']},
                    {'id': 'hz',
                     'title': 'Hz, kHz and octaves',
                     'body': ['Hz (hertz) is the frequency: the number of vibrations in each second. 20 Hz is the '
                              'deepest bass, 1000 Hz (1 kHz) is the middle, and 20 kHz is the highest frequency '
                              'that persons hear.',
                              'An octave is two times the frequency (100 to 200 Hz, 1 to 2 kHz). The ear hears in '
                              'octaves. Thus, the frequency axis of the graph uses octaves: each octave has the '
                              'same width.'],
                     'see': ['frequency-response', 'q']},
                    {'id': 'level-matching',
                     'title': 'Normalization (same level)',
                     'body': ['Each curve has a different volume. Thus, before the app compares curves, it '
                              'changes their levels to make them the same. Only the height of a curve changes, '
                              'not its shape.',
                              ['Hz~: the same average across the 4 octaves around a frequency (listener800 uses '
                               'it, around 500 Hz).',
                               'Hz: the same level at one frequency.',
                               'dB: all curves have the same loudness in phon (squig.link uses it).'],
                              'More settings › Website › Normalization sets it. It is important for the website '
                              'methods, which copy the website accurately.'],
                     'see': ['phon', 'website-autoeq']},
                    {'id': 'phon',
                     'title': 'Phon and equal loudness',
                     'body': ['The ear does not hear all frequencies with equal loudness. The bass and the highest '
                              'treble must have a higher level for the same loudness as the middle frequencies, '
                              'and more at low volumes. Equal-loudness tables (ISO 226) give this data.',
                              'The phon is a scale of loudness from these tables. Normalization in dB sets all '
                              'curves to the same loudness, for example 60 phon, a usual volume for music.'],
                     'see': ['level-matching']},
                    {'id': 'smoothing',
                     'title': 'Smoothing',
                     'body': ['Smoothing removes the small peaks and notches of a curve, as a graph website does '
                              'before it shows the curve. The website methods use the same smoothing as the '
                              'website. Thus, the results are the same. 0 = no smoothing.'],
                     'see': ['website-autoeq']},
                    {'id': 'target-adjustments',
                     'title': 'Target adjustments (Custom DF)',
                     'body': ['Adjust (on the Target card) has the controls of listener800 that change a target as '
                              'you want. It has a tilt for the full curve (dB in each octave: a value below 0 = '
                              'less treble). It also has shelves or peaks for the bass, a half-tilt, the ear gain '
                              '(2-5 kHz), the treble and the air above 10 kHz.',
                              'Each has a gain (how much), a frequency (where) and, for most, a Q (how sharp the '
                              'change is). They change the target before the app adjusts the EQ. The app '
                              'calculates them as the website does.'],
                     'see': ['target', 'shelf', 'q']}]},
         {'title': 'EQ and filters',
          'terms': [{'id': 'eq',
                     'title': 'EQ: parametric and graphic',
                     'body': ['An equalizer changes the loudness of each part of the sound. A parametric EQ has '
                              'filters that you can put at all frequencies: each filter has a frequency, a gain and '
                              'a Q. A graphic EQ has sliders at specified frequencies (for example, 10 bands from '
                              '31 Hz to 16 kHz): you can change only their gains.',
                              'Best fit makes the two types, in the limits of your EQ app.'],
                     'see': ['peaking-filter', 'fixed-bands', 'eq-app']},
                    {'id': 'peaking-filter',
                     'title': 'Peaking filter (Peak, PK)',
                     'body': ['A filter that increases or decreases the level around a frequency. 3 values set it: '
                              'the frequency (where), the gain in dB (how much: + increases the level, − decreases it) and '
                              'the Q (the width).',
                              'Most EQ apps use the name “Peak”, “PK”, “Bell” or “Parametric”.'],
                     'see': ['q', 'shelf', 'db']},
                    {'id': 'q',
                     'title': 'Q (filter width)',
                     'body': ['The width of a filter. A low Q (0.5-1) gives a wide, smooth change across more than '
                              'one octave. A high Q (5-10) gives a thin notch or peak. Q 1.41 is approximately one '
                              'octave wide, and Q 4.3 is approximately 1/3 of an octave.',
                              'Wide filters change the general tone, and small changes in the position of the '
                              'earphone in your ear have almost no effect on them. Thin filters correct a sharp '
                              'peak. But the position of the peak changes with the earphone position and the tips. '
                              'Thus, a very thin filter can be at an incorrect frequency for your ears. The Q '
                              'limits stop where a higher Q did not help in tests.'],
                     'see': ['peaking-filter', 'shelf', 'unit-variation']},
                    {'id': 'shelf',
                     'title': 'Shelf filter (low shelf, high shelf)',
                     'body': ['A filter that increases or decreases all frequencies below (low shelf) or above '
                              '(high shelf) a corner frequency, with the shape of a step. A low shelf is the usual '
                              'method to add or remove bass. A high shelf does the same for the treble.',
                              'Its Q sets the slope of the step: 0.707 is the standard shelf. In Equalizer APO '
                              'files, they are LSC and HSC.'],
                     'see': ['peaking-filter', 'q']},
                    {'id': 'preamp',
                     'title': 'Pre-amp and clipping',
                     'body': ['Digital audio cannot go above full scale. If an EQ increases the level of music that '
                              'has a high volume, it causes clipping (distortion). Thus, an EQ with gains above 0 dB must '
                              'first decrease the volume by its highest gain: this is the pre-amp, for example '
                              '−6.3 dB.',
                              'The app sets it from the highest point of the EQ. Most saved files include it. In '
                              'other apps, you must set it. The music has a lower volume: increase the volume of '
                              'your player. “Safe” rounding uses the lower value, to prevent clipping.'],
                     'see': ['db', 'eq-app']},
                    {'id': 'fixed-bands',
                     'title': 'Graphic EQ (layout)',
                     'body': ['For an EQ with sliders at specified frequencies. Best fit adjusts only their gains, in '
                              'the range of the sliders and in their steps (1 dB, 0.5 dB…). Thus, the app '
                              'calculates the error with the values that you set on the sliders.',
                              'Your EQ app sets this for graphic EQ apps. More settings › Best fit › Layout has '
                              'the usual 10, 15 and 31-band layouts, the Spotify layout, and Your bands.'],
                     'see': ['eq', 'layout', 'eq-app']},
                    {'id': 'impulse-response',
                     'title': 'Impulse response and convolution',
                     'body': ['A different method to save an EQ: a short sound file (.wav) that is the EQ. '
                              'Convolution EQs (Viper4Android, JamesDSP, the Convolver of EasyEffects, Roon, '
                              'foobar2000, HQPlayer, Equalizer APO) play music through it.',
                              'It keeps all the filters of an EQ accurately, with no limit on their number. Its '
                              'sample rate must be the same as the sample rate of your device.'],
                     'see': ['sample-rate', 'file-formats']},
                    {'id': 'sample-rate',
                     'title': 'Sample rate',
                     'body': ['The number of samples in each second of digital audio: 44100 (CD) or 48000 are '
                              'usual. At the top of the treble, digital filters change a small quantity with it. '
                              'Thus, the app uses the rate of the app or device that plays the EQ (48000 for the '
                              'website, the rate of your impulse response).'],
                     'see': ['impulse-response']}]},
         {'title': 'Rigs and measurements',
          'terms': [{'id': 'rig',
                     'title': 'Rig (ear simulator): 711, 5128, 43AG, HMS',
                     'body': ['The device that measures an earphone. It has the shape of an ear (or of a head with '
                              'ears), with a microphone at the position of the eardrum. Each type gives a '
                              'different measurement of the same earphone. The differences are largest above '
                              '2 kHz.',
                              ['711: a 711-type IEC 60318-4 coupler (or a copy of one), the most usual rig for '
                               'IEMs.',
                               '5128: the 5128 head and torso of Brüel & Kjær, with an ear canal that is nearer to '
                               'the ear of a person. For IEMs and headphones.',
                               '43AG: the GRAS 43AG, for headphones (with a 711-type ear in it).',
                               'HMS: the HMS of Head Acoustics, a head for previous headphone and IEM data '
                               '(Innerfidelity).'],
                              'A target is for one rig. If possible, compare and make the EQ on the same rig. If '
                              'not, let the app change the target.'],
                     'see': ['rig-tags', 'rig-conversion', 'target']},
                    {'id': 'rig-tags',
                     'title': 'Rig tags: 5128, 711?, rig ?, ⇄',
                     'body': ['The tag after each item in the search list shows the rig of the measurement (for a '
                              'target, the rig that it is for). Its text shows how sure the app is:',
                              ['“5128”: the source gives it, or the app found it from the measurements and it is '
                               'almost sure.',
                               '“711?”: it is very possible that it is that rig (the app found it, but it is less sure, or '
                               'it is the usual rig for that database).',
                               '“rig ?”: not known.',
                               '“mixed”: its files come from different rigs.',
                               '“5128 ⇄”: that database has its rig change (put the cursor on the tag to see the '
                               'rig of its targets, and how much it helps).'],
                              'Most persons who measure do not tell which rig they use. Thus, the app compares the '
                              'curves of each database with sources that have a known rig. Put the cursor on a tag '
                              'to see how the app found its rig.'],
                     'see': ['rig', 'unit-conversion']},
                    {'id': 'rig-conversion',
                     'title': 'Rig change',
                     'body': ['If your measurement and target come from different rigs, the app changes the target '
                              'for the rig of the measurement. It adds the average difference between the two rigs '
                              'to the target. This average comes from models in the online databases with '
                              'measurements on the two rigs. If the app does not do this, the EQ also tries to '
                              '“correct” the difference between the rigs.',
                              'It makes the difference smaller, but it does not remove it. A test on 265 models that '
                              'were not in the average (IEMs, between a 711 and a 5128) gave these differences:',
                              ['1-3 kHz: 2.4 → 1.0 dB.',
                               '3-6 kHz: 3.2 → 1.5 dB.',
                               '6-10 kHz: 3.5 → 2.6 dB.'],
                              'Above 10 kHz, much of the difference stays. Thus, you must adjust the treble while '
                              'you listen.',
                              'The app does not change the target for pairs of rigs without sufficient data (for '
                              'example, IEMs between a 5128 and an HMS). The message tells you this. Settings › '
                              'Target › Rig change disables it.'],
                     'see': ['rig', 'unit-conversion', 'treble-limit']},
                    {'id': 'unit-conversion',
                     'title': 'Rig change by a database',
                     'body': ['The equipment of a person can be different from the rig in the database (a copy of a '
                              '711 coupler, the IEM depth, the calibration). It can '
                              'also be none of the 4 rigs. Thus, if a database and the sources on a rig have '
                              'sufficient models that are the same, the app compares their curves. Then it '
                              'calculates a rig change for that database. The app keeps it only if it is always '
                              'better than the rig average on models that it did not use (92 kept, for 64 databases).',
                              'If your measurement comes from such a database, the message below the graph gives '
                              'its name, and the search list shows ⇄.'],
                     'see': ['rig-conversion', 'rig-tags']},
                    {'id': 'seatings',
                     'title': 'Channels, seatings and averages',
                     'body': ['Many measurements have more than one file: the left and right channels (L, R). Some '
                              'measurements also have more than one seating (the person removed the earphone and '
                              'put it in the ear again). The app uses the average of the selected files, as '
                              'squiglink does. The average is a more stable curve than each file.',
                              'Where the seatings do not agree (frequently above 10 kHz), the measurement is not '
                              'accurate. The automatic settings do not calculate the error there.'],
                     'see': ['measurement', 'scored-range', 'treble-limit']},
                    {'id': 'unit-variation',
                     'title': 'Differences between units',
                     'body': ['In the tests of the app, two units of one model from different persons are different '
                              'by approximately 1 dB after the EQ. In the treble, the difference is larger. '
                              'Your unit, ears and tips are different again.',
                              'Thus, if an EQ goes nearer to one measurement than you can hear, it only follows that '
                              'one measurement. The app selects the result with the minimum number of filters for the '
                              'same sound as the target. Its limits stop where nearer EQs did not help other '
                              'units.'],
                     'see': ['simplest', 'error', 'measurement']},
                    {'id': 'seal',
                     'title': 'Seal and bass leak',
                     'body': ['An IEM without a seal in the ear (or on the rig) has less bass. If a measurement has '
                              'much less bass than other measurements of the same model, it is very possible that it had no '
                              'seal. An EQ for that measurement gives too much bass.',
                              '“Other measurements of this model…” gives a value for this (Bass). In Listen, you '
                              'can examine it with your ears.'],
                     'see': ['compare-measurements', 'measurement']},
                    {'id': 'treble-limit',
                     'title': 'The treble above approximately 10 kHz',
                     'body': ['Above approximately 10 kHz, the measured response of an IEM changes much with its '
                              'depth in the ear, the tips and the ear canal. Thus, a measurement there does not '
                              'tell much about the sound that you hear. An EQ that agrees accurately with it can '
                              'make the sound worse.',
                              'Thus, the automatic settings calculate the error only to the frequency where the '
                              'seatings of the measurement agree (frequently approximately 10 kHz). Filters can go '
                              'higher, but the app does not calculate the error there. Adjust the treble while '
                              'you listen.'],
                     'see': ['scored-range', 'seatings', 'rig-conversion']},
                    {'id': 'compensated',
                     'title': 'Compensated graph (difference from a target)',
                     'body': ['Some graphs show the difference of an earphone from a target (a flat line = the same '
                              'as the target), not its frequency response. When you trace such a graph, select '
                              'that target in “The graph shows”. When you save the curve, the app adds the target '
                              'again. Thus, the file has the frequency response of the earphone.'],
                     'see': ['tracer']},
                    {'id': 'tracer',
                     'title': 'Trace a graph image',
                     'body': ['It changes a picture of a frequency response graph into curve files. It reads the '
                              'axes, follows a curve by its color, and saves it as a measurement or a target. '
                              'Trace a graph image… (near the title of the graph) opens it. Drag, paste or open a '
                              'picture there. Its window also has a Guide. Find… also opens it for an entry that the '
                              'app cannot download.'],
                     'see': ['compensated', 'measurement']}]},
         {'title': 'Best fit and the error',
          'terms': [{'id': 'error',
                     'title': 'Error (dB)',
                     'body': ['The average distance between the measurement with the EQ and the target, across the '
                              'error range: the root mean square of the difference, in dB. 0 dB = the same curve as '
                              'the target.',
                              'Below approximately 0.5 dB, the EQ is very near to the target. You cannot hear a '
                              'difference of 0.05 dB or less. Compare errors only between results with the same '
                              'error range.'],
                     'see': ['scored-range', 'simplest', 'unit-variation']},
                    {'id': 'scored-range',
                     'title': 'Error range',
                     'body': ['The frequencies where the app calculates the error (Error from … to). Above and below '
                              'this range, the EQ has no limits: filters can go there, but the app does not '
                              'calculate the error there. The automatic settings set it from the range where your '
                              'measurement is accurate.'],
                     'see': ['error', 'treble-limit']},
                    {'id': 'best-fit',
                     'title': 'Best fit',
                     'body': ['The method of the app: it adjusts filters directly to the target, in the limits of '
                              'your EQ app. It adds the filters one at a time. Each new filter goes where the EQ is '
                              'farthest from the target. Then the app adjusts all the filters again. It selects the '
                              'result with the minimum number of filters for the same sound as the target. Usually, '
                              'the result is nearer to the target, or has a smaller number of filters, than the '
                              'AutoEQ of the website.',
                              'Use it for all EQ apps. Save or copy its filters.'],
                     'see': ['website-autoeq', 'simplest', 'layout']},
                    {'id': 'website-autoeq',
                     'title': 'Website AutoEQ (squiglink)',
                     'body': ['The AutoEQ button on squiglink graph websites (squig.link, listener800). The app uses '
                              'the code of the website. Thus, “Website AutoEQ: one set” gives the same filters as '
                              'the website for the same settings.',
                              '“Website AutoEQ: find the best settings” uses it with many sets of values, and tells '
                              'you the values to type in the website.'],
                     'see': ['sweep', 'best-fit', 'level-matching']},
                    {'id': 'sweep',
                     'title': 'Website best settings',
                     'body': ['It uses the AutoEQ of the website for all sets of values from the lists that you give '
                              '(filter rows, frequency, gain and Q ranges). It selects with the Best result setting '
                              '(Error and selection). Use it if the EQ goes into the website: then type the best '
                              'values into its AutoEQ panel.'],
                     'see': ['website-autoeq', 'simplest']},
                    {'id': 'simplest',
                     'title': 'The minimum number of filters for the same sound',
                     'body': ['Of all the results, the app selects the result with the minimum number of filters '
                              'for the same sound as the target. If 2 results have the same number of filters, it '
                              'selects the lower maximum Q, then the lower maximum gain. The same sound is a '
                              'difference of 0.25 dB or less at all frequencies, as the ear hears it. The app makes the difference smooth as the ear does, and it ignores the general '
                              'level. 0.25 dB is approximately the smallest wide change that persons heard in pink '
                              'noise, the sound that shows differences best. A small number of wide filters is '
                              'easier to enter, and the position of the earphone has less effect on it.',
                              'The limits of your EQ app, or a measurement that filters cannot follow, can keep all '
                              'results farther from the target. Then the app selects the minimum number of filters '
                              'for the same sound as the nearest result. The result shows how far from the '
                              'target it is, and where.',
                              'The other selection (Settings › Error and selection › Best result): the lowest '
                              'error, with no limit on the number of filters. (Until 1.0.9, there was also the '
                              'minimum number of filters in 0.1 dB of the best average error. An average does not '
                              'always show a wide difference that you can hear.)'],
                     'see': ['error', 'unit-variation']},
                    {'id': 'penalties',
                     'title': 'Penalties and the treble limit',
                     'body': [['Penalties for opposite filters (More settings): they help to prevent filters that cancel '
                               'the effect of each other (+ gain on − gain). These filters only make the '
                               'EQ more sensitive. The app tries each value in the list.',
                               'Gain penalty: it helps to prevent large gains that are not necessary.',
                               'Treble limit: it keeps the average effect of the EQ above the error range near 0 '
                               'dB. Thus, filters do not go there without control.'],
                              'Each one makes the error a small quantity larger when Best fit makes such filters. '
                              'The app sets the gain penalty and the treble limit for you (the tests did not find better '
                              'values).'],
                     'see': ['best-fit']},
                    {'id': 'automatic-settings',
                     'title': 'Automatic settings, “your value” and ↺',
                     'body': ['When you select a target and a measurement, the app adjusts these settings of the '
                              'method for them:',
                              ['The error range.',
                               'The number of filters.',
                               'The maximum and minimum gain.',
                               'The maximum Q.',
                               'If it uses a low shelf.'],
                              '“About these settings” gives the cause of each value.',
                              'If you change a setting, it shows “your value”, and the app keeps your value. “your '
                              'value ↺” makes it automatic again. To use all settings as they are, clear Automatic '
                              'settings.'],
                     'see': ['speed-accuracy']},
                    {'id': 'speed-accuracy',
                     'title': 'The settings that the app tries',
                     'body': ['Best fit adds filters one at a time. It uses each maximum gain and maximum Q that is '
                              'applicable to your curves, each with 2 penalties for opposite filters. It stops '
                              'when the EQ has the same sound as the target. The line Settings to try shows the '
                              'number of EQs that it will try and the approximate time on this PC (its tooltip shows '
                              'the settings).',
                              'Until 1.0.8, there were 3 sets of settings (“Quick”, “Standard”, “Thorough”). After '
                              'Best fit started to add filters one at a time, the 3 sets used only seconds. One set '
                              'with all their settings found the minimum number of filters for all IEMs and '
                              'headphones in the tests. For most, it uses some seconds. For a headphone that the EQ '
                              'cannot make the same as the target, it uses a maximum of approximately 1.5 minutes.'],
                     'see': ['automatic-settings', 'best-fit']},
                    {'id': 'layout',
                     'title': 'Layout',
                     'body': ['The type of EQ, to keep Best fit in its limits:',
                              ['Parametric filters (an app with no limits).',
                               'A graphic EQ (its sliders).',
                               'The limits of an EQ app (its number of filters, shelves, and gain, Q and frequency '
                               'ranges).'],
                              'Your EQ app sets it. More settings › Best fit › Layout shows it.'],
                     'see': ['eq-app', 'fixed-bands']},
                    {'id': 'limits',
                     'title': 'Limits (permitted range)',
                     'body': ['Each value has a minimum and a maximum. You see them when you put the cursor on a '
                              'box. A value that is not in the range becomes red. When you go to a different box, the app moves '
                              'the value to the nearest limit.',
                              'Each limit comes from the app or website that uses the value (for example, Q 5 on the '
                              'website), or from measurements. For example, the maximum gain of Best fit (+35 dB) '
                              'and its maximum Q (27) are sufficient for 99.9% of 3,000 measurements.'],
                     'see': []},
                    {'id': 'own-filters',
                     'title': 'Start from your filters',
                     'body': ['Best fit can start from an EQ that you have (More settings › Best fit). You can type '
                              'filter lines, use a table '
                              'or sliders (Edit as a table…), or load an EQ file (Load an EQ file…). With “Keep them '
                              'as they are”, Best fit adds filters to your filters. Without it, Best fit can also change '
                              'your filters. One more result shows only your filters, to compare.',
                              'While you edit them, the graph shows the measurement with your filters as “With your '
                              'filters”.'],
                     'see': ['retry', 'best-fit']},
                    {'id': 'retry',
                     'title': 'Calculate from these filters',
                     'body': ['On the result card, after you edit the filters: Best fit starts again from the '
                              'filters that you see, for this time only. “Adjust them” moves each filter a small '
                              'distance, to be nearer to the target. “Keep them and add filters” keeps your '
                              'filters as they are and adds filters.'],
                     'see': ['own-filters']},
                    {'id': 'by-hand',
                     'title': 'A manual EQ',
                     'body': ['An EQ that you make (Make the EQ › Manually). You add the filters and set the '
                              'frequency, gain and Q of each filter, in the table or with the sliders. If you start '
                              'from an EQ file, pasted lines or a profile, the app reads them as Equalizer APO '
                              'plays them. It moves a shelf at its corner frequency (“LS … Q”, “LS 6dB” of Room EQ '
                              'Wizard) to its center frequency. It changes a slope or a width in octaves to the Q with the '
                              'same sound.',
                              'It keeps peaking filters and shelves (all EQ apps can use them). It does not use other '
                              'filter types (high-pass and low-pass, notch…), a graphic EQ or a convolution, and it '
                              'tells you. The app calculates the pre-amp for you. Thus, the EQ does not cause '
                              'clipping.'],
                     'see': ['peaking-filter', 'shelf', 'preamp']}]},
         {'title': 'Apps, files and Listen',
          'terms': [{'id': 'eq-app',
                     'title': 'Your EQ app',
                     'body': ['The app or device that will play the EQ (Equalizer APO, Poweramp, Wavelet, a '
                              'Qudelix…). When you select it, the EQ stays in its limits (bands, gain, Q and '
                              'frequency ranges, graphic EQ sliders). It also selects the file that the app imports, '
                              'for Save filters. The ⓘ after the label Your EQ app tells you how to load the EQ, with '
                              'a link to the source of its limits.',
                              'For apps without a file (Qudelix, FiiO, Moondrop…), enter the filters manually from '
                              'the filter table or the report. “Not in the list, or not sure”: no limits, saved as '
                              'an Equalizer APO file, which many apps read.'],
                     'see': ['file-formats', 'layout', 'preamp']},
                    {'id': 'file-formats',
                     'title': 'Saved file formats',
                     'body': [['Equalizer APO / squiglink (.txt): Equalizer APO, Peace, EasyEffects, the Import of '
                               'squiglink.',
                               'GraphicEQ (.txt): Wavelet, RootlessJamesDSP.',
                               'Poweramp (.json), USB Audio Player PRO (.xml): Android.',
                               'SoundSource (.txt): macOS. Voicemeeter (.xml): Windows. Rockbox (.cfg): music '
                               'players.',
                               'Impulse response (.wav): convolution EQs.'],
                              'Each file stays in the limits of its app. If this changes the EQ by 0.1 dB or more, '
                              'the app tells you by how much when you save. In More settings › Saved files, you can '
                              'select other formats. The files go to your Saved EQs folder (Settings › Your files).'],
                     'see': ['eq-app', 'impulse-response', 'preamp']},
                    {'id': 'databases',
                     'title': 'Online databases and This PC',
                     'body': ['The search list finds curves in 3 sources:',
                              ['The files in the app.',
                               'Curve files on this PC (in Downloads, Documents, Desktop and Music).',
                               'Approximately 150 online databases (the list of squig.link, the AutoEq repository, '
                               'listener800).'],
                              'The app downloads an online curve when you use it or show a preview of it. Some '
                              'databases do not let the app download their files. For their entries (measurements '
                              'and targets), the app opens the website and waits for a picture of the graph (a '
                              'screenshot). The tracer then makes the curve from the picture. If a website does not '
                              'let the app download an entry, the app also uses pictures for the other entries of '
                              'that database. After 7 days, the app tries to download again.',
                              'In Find… › Sources…, you can enable or disable databases, add a page of the '
                              'squig.link type, and set the folders to search on this PC. Offline, the app uses '
                              'only the lists and the curves that are on this PC.'],
                     'see': ['rig-tags', 'measurement']},
                    {'id': 'compare-measurements',
                     'title': 'Which measurement to use',
                     'body': ['“Other measurements of this model…” below Measurement finds all measurements of '
                              'your model. It sets them to the same level and sorts them for your target, with '
                              'these values:',
                              ['The rig (and how good the rig change is).',
                               'How much a measurement agrees with the others.',
                               'The bass (a seal leak).',
                               'The number of seatings in the average.',
                               'The data.'],
                              'It can also calculate the average of more than one measurement from one rig.',
                              'The rig of each source is the rig that it gives, or the usual rig for that type of '
                              'database. The sorted list is not always correct for your earphone: units, the '
                              'position in the ear and the tips are different.'],
                     'see': ['rig-conversion', 'seal', 'seatings']},
                    {'id': 'history',
                     'title': 'History',
                     'body': ['Your previous EQs, which the app keeps when you close it (History…, near the title of '
                              'the graph). It keeps the EQs that you save or copy, or all results (More settings › '
                              'History). Show opens an EQ again with its files and settings. Keep to compare adds '
                              'it to your EQs to compare.'],
                     'see': ['eqs-to-compare']},
                    {'id': 'eqs-to-compare',
                     'title': 'EQs to compare',
                     'body': ['A list for each IEM or headphone of the EQs that you want to compare (a maximum of '
                              '12). They come from a result (Keep to compare), History, an EQ file or pasted '
                              'filters. Each EQ is a version in Listen (keys 1-9). While Graph is selected, it is also a curve on the graph. The '
                              'app keeps the list when you close it.'],
                     'see': ['match-loudness', 'history']},
                    {'id': 'match-loudness',
                     'title': 'Same level (Listen)',
                     'body': ['Listen plays all versions with the same loudness. Usually, persons think that a '
                              'version with more loudness is better. Thus, without the same level, persons '
                              'frequently select the version with more gain, for an incorrect cause.'],
                     'see': ['blind-test', 'eqs-to-compare']},
                    {'id': 'blind-test',
                     'title': 'Hide the names',
                     'body': ['It hides the names of the versions (A, B…) until you click Show the names. Thus, the '
                              'name of a version does not change the sound that you hear. Select a version with the buttons '
                              'or keys 1-9.'],
                     'see': ['match-loudness', 'abx']},
                    {'id': 'abx',
                     'title': 'ABX test',
                     'body': ['A test that shows if you can hear a difference. In each trial of two versions, A and B, '
                              'X is one of them, selected at random, and you tell which one it is. If you '
                              'select at random, you are correct approximately 50% of the time. Thus, the number of '
                              'correct selections does not tell much: it is important to know how frequently random selections '
                              'give the same result. 12 of 16 occurs at '
                              'random approximately 4 % of the time, and 9 of 16 approximately 40 %. Less than 5 % '
                              'is the usual limit for “you hear a difference”.',
                              'The same level is most important here: it is easy to identify a version with a small '
                              'quantity more loudness, only for that cause. Thus, Listen keeps the same loudness '
                              'while a test is in progress.'],
                     'see': ['blind-test', 'match-loudness']}]}]

QUESTIONS = [{'id': 'q-which-method',
              'q': 'Which EQ method is best for you?',
              'body': ['First, select Your EQ app: it selects the method. For the website (squig.link, listener800), '
                       'the Website methods give the same result as its AutoEQ. Thus, you only type its settings. '
                       'For all other apps, use Best fit. Usually, it is nearer to the target or has a smaller '
                       'number of filters. Save or copy its file.'],
              'see': ['best-fit', 'website-autoeq', 'eq-app']},
             {'id': 'q-error',
              'q': 'The error value: is it good?',
              'body': ['It is the average difference between the curve with the EQ and the target, across the error '
                       'range. Below approximately 0.5 dB, the EQ is very near to the target. You cannot hear '
                       'differences of 0.05 dB or less. Two units of one model are different by approximately '
                       '1 dB. Thus, an error that is 0.1 dB smaller only follows the measurement, not your '
                       'earphone.'],
              'see': ['error', 'unit-variation']},
             {'id': 'q-treble',
              'q': 'The treble does not agree with the target, and the error stops at 10 kHz.',
              'body': ['Above approximately 10 kHz, the response of an IEM changes with its depth in the ear, the '
                       'tips and your ear. Thus, a measurement there is not accurate, and an EQ that follows it '
                       'accurately can give a worse sound. The automatic settings calculate the error only to the '
                       'frequency where the seatings of the measurement agree. Adjust the treble with Listen.'],
              'see': ['treble-limit', 'scored-range']},
             {'id': 'q-preamp',
              'q': 'The pre-amp is less than 0 dB. Does the volume decrease?',
              'body': ['Gains above 0 dB must have headroom, or music with a high volume causes clipping. The '
                       'pre-amp decreases the volume by the highest gain of the EQ. Thus, the volume is lower. '
                       'Increase the volume of your player to correct it. Set the pre-amp in your EQ app with the '
                       'filters. Most saved files include it.'],
              'see': ['preamp']},
             {'id': 'q-filters',
              'q': 'How many filters are best?',
              'body': ['Let the app select. It adds filters one at a time. It keeps the minimum number of '
                       'filters for the same sound as the target (usually 8 to 19 in tests). If your EQ app has a '
                       'smaller number of bands, select it as Your EQ app: the EQ stays in its limit. “Number of '
                       'filters” on the result card shows the best result for each number, with one click.'],
              'see': ['simplest', 'eq-app']},
             {'id': 'q-rigs',
              'q': 'Your measurement and target come from different rigs.',
              'body': ['A message below the graph tells you this. The app changes the target for the rig of the '
                       'measurement (Settings › Target › Rig change disables it). This removes most of the '
                       'difference between the rigs below 6 kHz, and less above 6 kHz. But a target for the rig of '
                       'your measurement, or a measurement from the rig of the target, is best.'],
              'see': ['rig-conversion', 'rig']},
             {'id': 'q-many',
              'q': 'There are many measurements of your IEM. Which one is best?',
              'body': ['Use “Other measurements of this model…” below Measurement. It sorts them for your target '
                       'and gives the causes (rig, agrees with others, bass seal, average, data). It can also calculate '
                       'the average of more than one measurement from one rig.'],
              'see': ['compare-measurements', 'seal']},
             {'id': 'q-website',
              'q': 'Your result is different from the AutoEQ of squig.link.',
              'body': ['Best fit is a different method: usually, it finds an EQ that is nearer to the target or has '
                       'a smaller number of filters. The Website methods give the same result as the website in '
                       'these conditions:',
                       ['More settings › Website agrees with the website that you use (Which website to copy, '
                        'Normalization, smoothing).',
                        'The target adjustments are the same.']],
              'see': ['website-autoeq', 'level-matching']},
             {'id': 'q-sounds-wrong',
              'q': 'The EQ on the graph is correct, but the sound is not correct.',
              'body': ['You hear your unit, ears and tips, with the EQ. The measurement was of a different unit, on '
                       'a rig. To correct the sound:',
                       ['Examine the seal and the tips first (less bass is the usual sign).',
                        'Use a different measurement of the model.',
                        'Compare the versions in Listen, with Same level on.',
                        'Adjust the filters while you listen. You can edit the table and the sliders.']],
              'see': ['unit-variation', 'seal', 'match-loudness']},
             {'id': 'q-yours',
              'q': 'A setting shows “your value”.',
              'body': ['You changed it. Thus, the automatic settings do not change it. “your value ↺” makes it '
                       'automatic again.'],
              'see': ['automatic-settings']},
             {'id': 'q-auto-why',
              'q': 'How the automatic settings get their values',
              'body': ['Each value in “About these settings” comes from your measurement and target, and from tests '
                       'on measurements of IEMs and headphones:',
                       ['Error range: to the frequency where the files of your measurement (seatings, channels) '
                        'agree, frequently approximately 10 kHz. Above it, a measurement changes with the position '
                        'and the depth of the earphone in the ear. Thus, an EQ that follows it there does not help.',
                        'Filter counts: to the number where the result does not become better (32 filters for '
                        'Best fit, 20 rows for the website). It keeps the minimum number of filters for the '
                        'same sound as the target (0.25 dB or less, as the ear hears it). The previous method was '
                        'the minimum number of filters in 0.1 dB of the best average error. On 15 IEMs and '
                        'headphones, it was different from the nearest result by a maximum of 0.87 dB at some '
                        'frequencies.',
                        'Maximum and minimum gain: sufficient for the target, with a small quantity more.',
                        'Maximum Q: from the thinnest peak or notch, and also Q 3 to 5. With many filters, these '
                        'were nearer to the target in tests, also on other units. Q 8-16 was worse.',
                        'Low shelf: on if all the bass is 3 dB or more from the target. (No high shelf: in tests, it '
                        'made the result better and worse approximately the same number of times.)',
                        'Penalties for opposite filters: 0.003 and 0.01, each limit with each penalty. In tests, the '
                        'lower penalty found the minimum number of filters for most IEMs and headphones. The higher '
                        'penalty found it for some (the HD600: 15 filters, not 19).']],
              'see': ['automatic-settings', 'speed-accuracy', 'simplest', 'treble-limit']},
             {'id': 'q-have-eq',
              'q': 'You have an EQ. Can the app make it better?',
              'body': ['Yes. Use “Start from your filters” (More settings › Best fit: type them, or use Load an EQ '
                       'file…). Or '
                       'edit the filters of a result and use Calculate from these filters. Best fit adjusts your filters '
                       'or adds filters to them.'],
              'see': ['own-filters', 'retry']},
             {'id': 'q-load',
              'q': 'How do you put the EQ into your app?',
              'body': ['Select it as Your EQ app. The ⓘ after the label Your EQ app tells you how to load the EQ. '
                       'Save filters '
                       'writes its file to your Saved EQs folder (“Open the Saved EQs folder” on the result card). '
                       'For apps without a file, type the filters from the table (or the report) into the app.'],
              'see': ['eq-app', 'file-formats']},
             {'id': 'q-graph',
              'q': 'You have only a picture of a graph. Can you use it?',
              'body': ['Yes. Click Trace a graph image… (near the title of the graph). Drag, paste or open the '
                       'picture there. It reads the axes, follows the curve and saves it as a measurement or a '
                       'target.'],
              'see': ['tracer']},
             {'id': 'q-listen',
              'q': 'How do you compare EQs in Listen?',
              'body': ['Use the IEM or headphone of the measurement, with the same tips. Start at a low volume. Keep '
                       'Same level on. Select the versions with keys 1-9. Use Hide the names. Then you do not know '
                       'which version is which.'],
              'see': ['match-loudness', 'blind-test', 'eqs-to-compare']},
             {'id': 'q-applies',
              'q': 'You enabled an EQ, but you cannot hear it. Does Equalizer APO use it?',
              'body': ['Go to Devices › the device. The line below its EQ tells you if APO uses it (Examine again '
                       'examines it at this time). The usual causes are:',
                       ["APO is not installed on that device (use APO's Configurator, then restart).",
                        'config.txt has no line for AutoEQ Studio (Add AutoEQ Studio to APO… at the top of '
                        'Devices).',
                        'In config.txt, the EQ of a different app is also active.']],
              'see': []},
             {'id': 'q-try',
              'q': 'Can you hear an EQ in your music player before you keep it?',
              'body': ['Yes. Click Use on device › Use for 5 minutes on. Then click the device. The EQ plays in all '
                       'apps for 5 minutes. Keep it makes it the profile of the device. If you do not click it, the '
                       'device uses its previous EQ again.',
                       'Listen, below the result, compares versions in AutoEQ Studio.'],
              'see': []},
             {'id': 'q-files',
              'q': 'Where are your files? Does the app upload data?',
              'body': ['All your data stays on this PC. Your targets, measurements, saved EQs and presets are in '
                       'Documents\\AutoEQ Studio (Targets, Measurements, Saved EQs, Presets), or in the folder that '
                       'you selected. Settings › Your files shows it and changes it.',
                       'The settings, History and log of the app are in AppData\\Roaming\\AutoEQ Studio if you '
                       'installed it. If you started it from its folder, they are in its data folder. The downloaded '
                       'curves are in AppData\\Local\\AutoEQ Studio (its downloads folder).',
                       'The app downloads only the lists of the databases and the curves that you use or show as a '
                       'preview. When AutoEQ Studio is Offline (top right), it does not download data.'],
              'see': ['databases']}]
