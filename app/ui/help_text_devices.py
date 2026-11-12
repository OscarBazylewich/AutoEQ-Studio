"""The help words for the window's own screens (Devices, Settings, and Presets in the top bar): HELP_DEVICES,
each control's line by its key (its tooltip, with the ids of its "See also" entries in Help), and
SETTINGS_DEVICES, the "Devices" group in Help's "Every setting". help_texts.py joins them with the other
screens'. Words only: nothing is imported here.
"""
# flake8: noqa

HELP_DEVICES = {'#dev-check': ['Does Equalizer APO use the EQ of this device? AutoEQ Studio examines this automatically, '
                               'with APO.', 'q-applies'],
 '#presets': 'A preset keeps all the settings of Make an EQ (not your files), with a name. You can load all these '
             'settings again in one step.',
 '#backup': 'Save a backup… saves all your data in one .zip file. Load a backup… loads your data from this .zip file.',
 '#files-folder': ['The folder for your targets, measurements, saved EQs and presets: Documents\\AutoEQ Studio, unless '
                   'you selected a different folder (Change…).', 'q-files'],
 '#dev-rename': 'Your name for this device. AutoEQ Studio shows this name, not the Windows name.',
 '#prof-edit': ['Make an EQ opens the filters of the selected profile, and you change them manually. Update saves them '
                'in the profile.', 'by-hand', 'set-use-update'],
 '#hotkey': 'This hotkey changes the EQ of the active device: each EQ in sequence, then Off. It operates in all apps.',
 '#onoff-hotkey': ['This hotkey disables the EQ of the active device and enables it again, to compare. It operates in '
                   'all apps.', 'match-loudness'],
 '#onoff-matched': ['“Off” has the same loudness as the EQ. Thus, you compare the sound, not the volume.',
                    'match-loudness']}

SETTINGS_DEVICES = [{'title': 'Devices',
                     'items': [{'key': '#dev-check',
                                'title': 'Does Equalizer APO use the EQ? (Examine again)',
                                'body': ['The line below the EQ of a device shows if Equalizer APO uses the EQ (✓) or '
                                         'not (✕). AutoEQ Studio gets this information automatically from the Benchmark '
                                         'tool of Equalizer APO. This tool only reads, and it does not change a file. '
                                         'AutoEQ Studio gets the information again each time the EQ, config.txt or the '
                                         'device changes.',
                                         'Examine again gets the information and shows all of it. It shows if APO reads '
                                         'the file of AutoEQ Studio and finds the part for this device. It shows if APO '
                                         'loads the EQ that you selected for this device, and the lines that config.txt '
                                         'also loads for all devices.']},
                               {'key': '#files-folder',
                                'title': 'Your files (Settings)',
                                'body': ['Your targets and measurements (Make an EQ uses them), saved EQs and reports, '
                                         'and presets are in one folder. Each type has a folder in it: Targets, '
                                         'Measurements, Saved EQs, Presets. The usual folder is Documents\\AutoEQ '
                                         'Studio, where Windows apps keep the files that you make. You can select a '
                                         'different folder. You can put curve files in Targets and Measurements (with '
                                         'Explorer, or with Open the folder). Make an EQ shows them in its lists.',
                                         'Change… selects a different folder. This folder must not be in the folder of '
                                         'AutoEQ Studio, because an update can delete it. With Move and start '
                                         'again, AutoEQ Studio moves your files into the new folder. If a file with the same name is in it, '
                                         'AutoEQ Studio does not replace that file. It keeps the new file in the same folder, '
                                         'with (2) after its name. Then AutoEQ Studio starts again and uses the new '
                                         'folder.',
                                         'A previous version of AutoEQ Studio kept the files in its folder (inputs, '
                                         'output, presets). When Make an EQ opens for the first time, you can move '
                                         'them (Move them).']},
                               {'key': '#backup',
                                'title': 'Backup (Settings)',
                                'body': ['Save a backup… writes all your data in one .zip file: devices, profiles, EQ '
                                         'files, settings, History, EQs to compare, targets, measurements, presets and '
                                         'saved EQs. It does not save the curves from the online databases: AutoEQ '
                                         'Studio downloads them again when it uses them. Load a backup… loads the data '
                                         'on this PC or on a different PC. First, it saves a backup of the data that you '
                                         'have at this time (data\\backups). It replaces the files that have the same '
                                         'names, and it does not delete other files. Then AutoEQ Studio starts again.']},
                               {'key': '#hotkey',
                                'title': 'Hotkey (Settings)',
                                'body': ['This hotkey operates in all apps. It changes the EQ of the active device to '
                                         'each of its profiles in sequence, then to Off. The initial hotkey is '
                                         'Ctrl+Alt+E. You can click the box and press different keys. The ✕ in the box '
                                         'removes the hotkey. Windows does not accept keys that a different app '
                                         'uses.']},
                               {'key': '#onoff-hotkey',
                                'title': 'Hotkey to disable the EQ and enable it again (Settings)',
                                'body': ['This hotkey operates in all apps (the initial hotkey is Ctrl+Alt+Space). It '
                                         'disables the EQ of the active device, to compare the sound with no EQ. Then it '
                                         'enables the EQ again. AutoEQ Studio does not save this condition. If you '
                                         'select an EQ for the device, or start AutoEQ Studio again, the EQ is on '
                                         'again. If the device has no EQ on, the hotkey enables the last EQ of the '
                                         'device.',
                                         'The tray icon menu also has this item (EQ off, to compare). When the EQ of a '
                                         'device is off, a bar at the top of the window shows it, with Enable it again. '
                                         'This bar is the same as the bar of Use for 5 minutes on.']},
                               {'key': '#onoff-matched',
                                'title': 'Same level (the on/off hotkey)',
                                'body': ['On (the initial setting): “off” is no EQ, at a lower volume. It has the same '
                                         'loudness as the EQ (pink noise as the ear hears it, as in Listen). Thus, you '
                                         'compare the sound, not the volume: a sound with more loudness is almost '
                                         'always better to the ear. The notification shows the difference. If an EQ with '
                                         'no pre-amp has more loudness than no EQ, the same level is not possible '
                                         'without clipping, and the notification shows this. Off: “off” is no '
                                         'EQ, with no other change.']},
                               {'key': '#prof-edit',
                                'title': 'Edit in Make an EQ (Profiles)',
                                'body': ['Edit in Make an EQ opens the selected profile in Make an EQ as a manual EQ. You '
                                         'can change its filters in the table, in the sliders or on the graph, and '
                                         'listen to it. Then Use on device › Update “its name” saves it in the profile. '
                                         'The profile keeps its name and its devices. A device that has this profile on '
                                         'uses the change immediately, but some conditions can prevent this (refer to '
                                         '“Update a profile (Use on device)”). The message has Undo.',
                                         'Make an EQ cannot edit some profiles (a graphic EQ, or other filter types): '
                                         'for these, you can use the EQ as a new profile. Use on device can also put a '
                                         'result into a profile that you have (Update a profile): the profile keeps '
                                         'its name and its devices.']},
                               {'key': '#dev-rename',
                                'title': 'Rename… (a device)',
                                'body': ['Your name for a device (for example, “Dongle – KZ”). AutoEQ Studio shows it '
                                         'in the list, the tray and the notifications. The Windows name stays below it. '
                                         'If the name is empty, the device has the Windows name again.']},
                               {'key': '#use-try',
                                'title': 'Use for 5 minutes on (Use on device)',
                                'body': ['With this menu item, the device uses the EQ in all apps for 5 minutes, and '
                                         'AutoEQ Studio does not make a profile of it. A bar at the top (and the tray '
                                         'icon menu) shows the remaining time. The bar has Keep it (the EQ becomes a '
                                         'profile, and it is on) and Do not keep it. After the 5 minutes, or if AutoEQ '
                                         'Studio stops, the device has its EQ again.']},
                               {'key': '#use-update',
                                'title': 'Update a profile (Use on device)',
                                'body': ['In the menu of Use on device, each row Update “name” puts the EQ of the '
                                         'result into a profile that you have. The row shows the first device that has '
                                         'the profile on, and the number of other devices. Its tooltip shows all of '
                                         'them. Update a profile shows all your profiles.',
                                         'The profile keeps its name, its file name, and its devices. A device that has '
                                         'the profile on uses the new EQ immediately. A device that has the profile '
                                         'only in its list does not change. A device that is not connected uses the new '
                                         'EQ when you connect it. A device on which Equalizer APO is not installed does '
                                         'not use the EQ (refer to Devices). After you update a profile from a '
                                         'different result, the From column of Profiles shows the file name of that '
                                         'result.',
                                         'When you click the row, the app updates the profile immediately. The message '
                                         'has Undo for 20 seconds (Ctrl+Z does the same). After Undo, the profile has '
                                         'its previous EQ again. Undo is not possible after you delete the profile, or '
                                         'after its file changes again.',
                                         'If the result came from a profile (Edit in Make an EQ), Update “its name” is '
                                         'the first row of the menu. If the file of that profile has items that Make an '
                                         'EQ cannot show (a graphic EQ, or other filter types), the row is off. For '
                                         'that profile, you can use the EQ as a new profile.',
                                         'While a device uses an EQ for 5 minutes, or has its EQ off to compare, it does '
                                         'not change. It uses the new EQ after that, if you do not click Keep it.']}]}]
