"""The help words for the window's own screens (Devices, Settings, and Presets in the top bar): HELP_DEVICES,
each control's line by its key (its tooltip, with the ids of its "See also" entries in Help), and
SETTINGS_DEVICES, the "Devices" group in Help's "Every setting". help_texts.py joins them with the other
screens'. Words only: nothing is imported here.
"""
# flake8: noqa

HELP_DEVICES = {'#dev-check': ["Whether this device's EQ really plays: Equalizer APO asked by itself.", 'q-applies'],
 '#presets': 'Every setting of Make an EQ saved under a name and loaded again in one go (not your files).',
 '#backup': 'Everything of yours in one .zip (Back up everything…), or put back from one (Restore…).',
 '#files-folder': ['Where your targets, measurements, saved EQs and presets are: Documents\\AutoEQ Studio unless you '
                   'chose another folder (Change…).', 'q-files'],
 '#dev-rename': 'Your own name for this device, shown everywhere instead of Windows\' name.',
 '#prof-edit': ["The chosen profile's filters, changed by hand in Make an EQ; Update puts them back.", 'by-hand']}

SETTINGS_DEVICES = [{'title': 'Devices',
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
                               {'key': '#prof-edit',
                                'title': 'Edit in Make an EQ (Profiles)',
                                'body': ['Opens the chosen profile in Make an EQ as an EQ by hand: change its filters '
                                         'in the table, as sliders or on the graph, listen to it, then Use on device › '
                                         'Update “its name” puts it back. The profile keeps its name and its devices, '
                                         'and those that have it switched on hear the change at once. A profile with '
                                         "parts an EQ here can't have (a graphic EQ, other filter types) can't be "
                                         'updated that way: use the EQ as a new profile instead.']},
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
                                         'comes back.']}]}]
