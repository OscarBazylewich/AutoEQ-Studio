"""The help words for Trace image (the tracer): HELP_TRACE, each control's line by its key (the #tr-* keys: its
tooltip, with the ids of its "See also" entries in Help), and SETTINGS_TRACE, the "Trace image" group in Help's
"Every setting". help_texts.py joins them with the other screens'. Words only: nothing is imported here.
"""
# flake8: noqa

HELP_TRACE = {'#tr-auto-on': ["The app adjusts the tracer's settings for the image.", 'automatic-settings'],
 '#tr-d1': 'The dB value at the top red line.',
 '#tr-d2': 'The dB value at the bottom red line.',
 '#tr-f1': 'The frequency at the left blue line.',
 '#tr-f2': 'The frequency at the right blue line.',
 '#tr-snap': 'The lines that you drag move to the nearest grid line.',
 '#tr-every': 'The app uses all grid lines, for irregular axes.',
 '#tr-tol': "How different a pixel's color can be from the curve's color.",
 '#tr-ppo': 'The number of points in each octave that the app saves.',
 '#tr-fmin': 'The frequency range to save.',
 '#tr-name': "The saved file's name.",
 '#tr-dashed': 'The app follows dashed or dotted curves across their spaces.',
 '#tr-comp': ['The app adds a target to the curve, for a graph that shows the difference from a target.',
              'compensated'],
 '#tr-target-line': 'Adds the target line of the picture as a target. You give its name first.'}

SETTINGS_TRACE = [{'title': 'Trace a graph image',
                   'items': [{'key': '#tr-auto-on',
                              'title': 'Automatic settings (tracer)',
                              'body': ["The app adjusts the tracer's settings for the image: color tolerance, points in "
                                       'each octave, the range to save and dashed lines. If you change a setting, it '
                                       'shows “your value”. The app also keeps your value for the next picture, until you '
                                       'click ↺.',
                                       'The app always works carefully. It makes the labels larger before it reads them, '
                                       'and tries again if necessary. It puts the traced line between pixels. If a traced '
                                       'line stops before the end of the curve, it tries again as a dashed line and with '
                                       'more color tolerance. (Before version 1.0.13, a slider set the speed and the '
                                       'precision. With each setting, the time was approximately 1 s, and the fast '
                                       'setting did not find dashed lines.)']},
                             {'key': '#tr-d1',
                              'title': 'Top red line (dB)',
                              'body': ['The dB label of the grid line at the top red line. You can use two grid lines '
                                       'with labels, if they are far from each other.']},
                             {'key': '#tr-d2',
                              'title': 'Bottom red line (dB)',
                              'body': ['The dB label of the grid line at the bottom red line.']},
                             {'key': '#tr-f1',
                              'title': 'Left blue line (Hz)',
                              'body': ['The frequency of the grid line at the left blue line. If the app reads it from '
                                       'the image, the app writes it here. Examine it.']},
                             {'key': '#tr-f2',
                              'title': 'Right blue line (Hz)',
                              'body': ['The frequency of the grid line at the right blue line.']},
                             {'key': '#tr-snap',
                              'title': 'Align with grid lines',
                              'body': ['The lines that you drag move to the nearest grid line, and stay on it.']},
                             {'key': '#tr-every',
                              'title': 'Follow all grid lines',
                              'body': ['The app uses all the grid lines between the blue lines, for graphs with '
                                       'irregular axes. For other graphs, it causes no problems.']},
                             {'key': '#tr-tol',
                              'title': 'Color tolerance',
                              'body': ["How different a pixel's color can be from the curve's color, and be part of the "
                                       'curve. For curves with a weak color or edges that are not sharp, increase it. If '
                                       'the traced line goes to a different line, decrease it.']},
                             {'key': '#tr-ppo',
                              'title': 'Points in each octave',
                              'body': ['The number of points in each octave that the app saves. squiglink uses 48. '
                                       'More points only make the file larger.']},
                             {'key': '#tr-fmin',
                              'title': 'Save from … to (Hz)',
                              'body': ['The frequency range to save (from … to), in the range that you traced. Automatic: '
                                       "the range of the graph's axis."]},
                             {'key': '#tr-name',
                              'title': 'Name',
                              'body': ["The saved file's name. If there is more than one curve, the app adds the label of "
                                       'each curve to its file name (for example, L and R).',
                                       'For a picture from a website, the file has the name of the entry. With more '
                                       'than one measurement curve, each file also has the name of its curve.']},
                             {'key': '#tr-dashed',
                              'title': 'Dashed or dotted line',
                              'body': ['For dashed or dotted curves: the traced line continues across the spaces.']},
                             {'key': '#tr-comp',
                              'title': 'The graph shows (compensated)',
                              'body': ['If the graph shows the difference from a target (compensated), select that '
                                       'target. The app adds the target to the curve when you save it. The target must '
                                       'be in the app.']},
                             {'key': '#tr-target-line',
                              'title': 'Add the target line as target…',
                              'body': ['Adds the target line of the picture as a target. You give its name first. It '
                                       'shows only when the app found a target line in a picture from a website.',
                                       'Add as measurement does not add the target line. If you change the target line '
                                       '(for example, you erase a part of it or rename it), it becomes a measurement '
                                       'curve. To add it as a target, select it, then click Add as target.']}]}]
