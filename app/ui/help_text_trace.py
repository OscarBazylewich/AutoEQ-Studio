"""The help words for Trace image (the tracer): HELP_TRACE, each control's line by its key (the #tr-* keys: its
tooltip, with the ids of its "See also" entries in Help), and SETTINGS_TRACE, the "Trace image" group in Help's
"Every setting". help_texts.py joins them with the other screens'. Words only: nothing is imported here.
"""
# flake8: noqa

HELP_TRACE = {'#tr-auto-on': ['', 'automatic-settings'],
 '#tr-d1': '',
 '#tr-d2': '',
 '#tr-f1': '',
 '#tr-f2': '',
 '#tr-snap': 'Snaps lines to the nearest grid line while dragging',
 '#tr-every': 'Uses all grid lines for irregular axes',
 '#tr-tol': 'Max color difference for a pixel to match the curve',
 '#tr-ppo': '',
 '#tr-fmin': '',
 '#tr-name': '',
 '#tr-dashed': 'Follows dashed or dotted curves across gaps',
 '#tr-shows': ['Graph type: measurement, target, or either relative to a target', 'compensated'],
 '#tr-comp': ['Reference target for a relative graph; added back to the traced curve', 'compensated'],
 '#tr-target-line': ["Save the graph's target line as a new target", 'tracer',
                     'databases']}

SETTINGS_TRACE = [{'title': 'Trace a graph image',
                   'items': [{'key': '#tr-auto-on',
                              'title': 'Automatic settings (tracer)',
                              'body': ["The app adjusts the tracer's settings for the image: color tolerance, points in "
                                       'each octave, the range to save and dashed lines. If you change a setting, it '
                                       'shows “your value”. The app keeps your value until you click ↺ or open a new '
                                       'picture.',
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
                             {'key': '#tr-shows',
                              'title': 'The graph shows',
                              'body': ['The type of the graph in the picture. The name of the add button and the gray '
                                       'text below it change with your selection.',
                                       ['A measurement: the picture shows the frequency response of an IEM or '
                                        'headphone. Add as measurement saves the curve and does not change it.',
                                        'A measurement as the difference from a target: the picture shows the '
                                        'difference of an IEM or headphone from a target (a compensated graph). '
                                        'Select that target in “Target of the graph”. Add as measurement adds the '
                                        'target to the curve and saves the result.',
                                        'A target line: the picture shows a target. Add as target saves the selected '
                                        'curve as a target and does not change it.',
                                        'A target line as the difference from a target: the picture shows the '
                                        'difference of a target from a different target (a compensated graph). Select '
                                        'the different target in “Target of the graph”. Add as target adds it to the '
                                        'selected curve and saves the result as a target.'],
                                       'For a picture from a website, the app makes the selection. For an entry of a '
                                       'target or from Find a target, it selects “A target line”. For a picture with '
                                       'only a target line, it also selects “A target line”. For other entries, it '
                                       'selects “A measurement”. You can change the selection.']},
                             {'key': '#tr-comp',
                              'title': 'Target of the graph',
                              'body': ['This list shows only for “A measurement as the difference from a target” and “A '
                                       'target line as the difference from a target”. Select the target that the '
                                       'graph shows the difference from. The app adds the target to the curve when '
                                       'you save it. The target must be in the app.']},
                             {'key': '#tr-target-line',
                              'title': 'Add the target line as target…',
                              'body': ["Save the graph's target line as a new target. You give its name first. It "
                                       'shows only when the app found a target line next to a measurement in a '
                                       'picture from a website.',
                                       'If the picture has only a target line, the app traces that line as the curve '
                                       'and selects “A target line” in “The graph shows”. Thus, the add button is Add '
                                       'as target. If you select “A measurement”, Add as measurement also adds the '
                                       'line. If the picture has more than one target line, show only one target on '
                                       'the graph of the website. Then copy a new picture.',
                                       'Add as measurement does not add the target line. If you change the target line '
                                       '(for example, you erase a part of it or rename it), it becomes a measurement '
                                       'curve. To add it as a target, select it. Select “A target line” in “The graph '
                                       'shows”. Then click Add as target. To remove it from the measurement, click its '
                                       '✕ (Remove curve) on 2 Trace.']}]}]
