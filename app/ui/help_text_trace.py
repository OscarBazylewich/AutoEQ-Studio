"""The help words for Trace image (the tracer): HELP_TRACE, each control's line by its key (the #tr-* keys: its
tooltip, with the ids of its "See also" entries in Help), and SETTINGS_TRACE, the "Trace image" group in Help's
"Every setting". help_texts.py joins them with the other screens'. Words only: nothing is imported here.
"""
# flake8: noqa

HELP_TRACE = {'#tr-auto-on': ["Fits the tracer's settings to the image.", 'automatic-settings'],
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

SETTINGS_TRACE = [{'title': 'Trace a graph image',
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
                                       "target: it's added back when saving. The target must be in the app."]}]}]
