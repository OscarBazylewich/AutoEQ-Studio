AUTOEQ STUDIO
=============

AutoEQ Studio is AutoEQ Local and EQ Switcher in one program, in its window (not in a browser).

The parts:
- Make an EQ (from AutoEQ Local): it makes an EQ that changes your headphones or IEMs to the sound of a target. It
  saves the EQ as the file that your EQ app uses, or "Use on device" puts the EQ directly on a device.
- Devices (from EQ Switcher): each of your playback devices has its EQ, and the EQ changes automatically. When you
  connect the dongle of your earphones or your Bluetooth earbuds, their EQ is on. Your speakers can have no EQ. It
  is the same as the EQ for each device in Poweramp, for Windows.

All the functions of AutoEQ Local and EQ Switcher are in AutoEQ Studio.

The first time that you open Make an EQ, AutoEQ Studio copies your AutoEQ Local files. These are the settings, History,
EQs to compare, your targets and measurements, saved EQs and downloads. It copies them from an "AutoEQ Local" folder
next to its folder, or in Downloads. AutoEQ Local keeps its files.

AutoEQ Studio operates through Equalizer APO (https://sourceforge.net/projects/equalizerapo/), which processes the
sound. AutoEQ Studio tells APO which EQ to use for each device. When the active device changes, APO changes the EQ
automatically, also when AutoEQ Studio does not operate.


INSTALL IT (the usual procedure)
--------------------------------
"AutoEQ Studio Setup <version>.exe" (in releases\, from "Make installer.bat") installs AutoEQ Studio, the same as
other Windows apps. It installs only for you, without an administrator password (Equalizer APO lets each person on
the PC change its settings). It goes in AppData\Local\Programs\AutoEQ Studio, with its Python: you do not install or
download other items. It adds a Start menu shortcut (and a desktop shortcut, if you select it), and an item in
Settings > Apps > Installed apps, with its version and Uninstall.
If Windows shows "Windows protected your PC" (the installer has no digital signature), click "More info". Then
click "Run anyway".
An installed copy keeps none of your files in the program folder (an update replaces that folder):
  Documents\AutoEQ Studio            your files (refer to YOUR FILES), the same for all copies
  AppData\Roaming\AutoEQ Studio      settings, History, EQs to compare, the backups that Load a backup keeps, the log
  AppData\Local\AutoEQ Studio        downloaded curves and the database lists (the app downloads them again if they
                                     are missing)
At the first start, the app puts the sample IEM and target in their folders. An installed copy starts with no data.
To move all your data from a copy that you started from its folder:
  1. In that copy, save a backup (Settings > Backup).
  2. In the installed copy, load that backup.
Update: start a newer Setup. It closes AutoEQ Studio first (or tells you to close it), and keeps your files and
settings.
Uninstall (Installed apps > AutoEQ Studio > Uninstall): it removes AutoEQ Studio from Equalizer APO (each device
gets the initial settings of APO) and from Start with Windows. Then you select if it also deletes your settings,
History and downloaded curves. Documents\AutoEQ Studio always stays.
Only one AutoEQ Studio can operate at a time. Before you start the installed copy, stop the copy from its folder:
  1. In the Settings of that copy, clear the Start with Windows tick box.
  2. Right-click its tray icon.
  3. Click Stop AutoEQ Studio.

YOUR FILES
----------
Your targets and measurements (the files that Make an EQ uses), saved EQs and presets are in Documents\AutoEQ
Studio. Windows apps keep the files that you make in this folder (for example, Room EQ Wizard, Audacity or REAPER).
Each type of file has its folder:
  Targets         target curves                  Saved EQs     EQ files and reports (Save filters, Report)
  Measurements    curves of your headphones      Presets       saved presets of the settings
                  and IEMs
You can put curve files in Targets or Measurements (in Explorer), and Make an EQ shows them in its lists. Add… and
Use also put files there.
Settings > Your files shows the folder (Open the folder) and selects a different folder (Change…). Change… can move
your files to that folder. It does not replace a file: if a different file has the same name, the moved file gets
(2) after its name. Then the app starts again. Do not use a folder in the program folder of AutoEQ Studio, because
an update or a new copy can delete your files.
A previous version of AutoEQ Studio kept them in its folder (inputs\target, inputs\measurement, output\, presets\).
The first time that Make an EQ opens, it can move them: Move them, Select a different folder…, or Not at this time
(it shows this message again the next time). Backups from before and after this change use the same names. Thus,
each version can load them.

START IT FROM ITS FOLDER
------------------------
Double-click "AutoEQ Studio.bat". The first time, it installs its Python packages (Qt, numpy, scipy and others,
approximately 150 MB). It must have 64-bit Python 3.10 or a newer version. Then it opens its window and puts an icon
near the clock (the tray). If you cannot see the icon, click the ^ arrow near the clock.
When you close the window, the app continues in the tray. Stop AutoEQ Studio is in the right-click menu of the icon.
If you start the app again while it operates, it only shows its window.

The top bar is also the title bar of the window. It has the screens (Make an EQ, Devices, Profiles, Settings). On the
right side, it has Presets and Guide (on Make an EQ), Help, Online / Offline, and the buttons Minimize, Maximize and
Close. If the window has a small width, the screens, Presets and Guide show only their symbols (their names are in
their tooltips). The window is light or dark, the same as Windows (Settings > Personalization > Colors), and it
changes when Windows changes. With a Windows contrast theme (Settings > Accessibility > Contrast
themes), the window uses the colors of that theme.
The window looks almost the same as the apps of Windows 11. The primary buttons, the tick boxes and the selected
items have your Windows accent color (on the same Colors page). On Windows 11, the background of the window is Mica,
with a color from your desktop picture. The background has no color when a different window is active, or when
Transparency effects are off.
You can go to each control with Tab (in the top bar, go to the screens with the arrow keys). Each control has a name
for a screen reader.

Guide: the 30 steps to make an EQ on Make an EQ (select, the settings, calculate, examine, save, listen and more),
the same as the Guide of AutoEQ Local. Each step highlights a part of the screen, tells you about it and shows it in
a short demo. In a demo, a pointer opens Find…, types a name, selects a row and shows it on the graph. It also opens
a list and selects an item. Or it types the target adjustments while the target changes on the graph (the graph
stays at the top while the page scrolls). A demo also shows how the app calculates, and the curve with the EQ.
Before you calculate, the steps of the result show an example result from your files.
The card of the Guide has:
  - "3 of 30": a list of all the steps (Go to a step).
  - Play again (R), Wait (P), Complete the demo, and the speed of the demo.
  - "Play all steps": all the Guide, automatically.
  - Back / Next (the arrow keys), Close the Guide (Esc) and Start again.
If you scroll while a demo plays, the demo waits. Continue scrolls to the step again. After a demo, the items that it
changed are as they were before it. A demo does not select, calculate, save or download. If the Animation effects
of Windows are off, a demo shows markers with numbers. The tracer has its Guide (on a sample graph).
Presets (top bar, on Make an EQ): a preset keeps all settings with a name, and you load them again in one step. It
does not keep your files: the target and the measurement do not change. The menu also has Delete a preset and Use
the initial settings… (Undo gives you your settings again). The presets are in the Presets folder.
Help: the names that the app uses (Q, shelf, rig, pre-amp…), the frequent problems and all settings, with a search
box. When the pointer is on a setting, press F1: Help opens at that setting.


ONLINE AND OFFLINE
------------------
Click Online / Offline (at the top, on the right side, and in Settings). When AutoEQ Studio is offline, it does not
connect to the internet. It uses only the data on this PC: your files, the curves that you downloaded and the
database lists that it has. The links to websites are disabled. When it is online, it can also use the internet (the
online databases, the same as AutoEQ Local). The EQs of your devices change without the internet, online and offline.


MAKE AN EQ
----------
One column, from the top to the bottom:
- Target and Measurement (one card, a row for each): the files in the app, from A to Z (numbers in their sequence:
  "IEM 2" before "IEM 10"). A measurement is a set: left and right, or more than one seating. Add… adds files from this
  PC. Find… (or the / key) searches the app, this PC and the online databases:
    - Preview shows a curve on the graph (dotted line). "Hide previews" removes the previews.
    - Use selects the curve. Undo, at the bottom of the window, gives you the previous curve again.
    - ⋯ (in the rows of the app) has the other commands: Show files, Move to Measurement and Delete….
    - The tabs above the results show the number of items in each source.
    - Sources… selects where Find… looks, with a tab for each part: the folders of this PC, the online databases (on
      or off) and more squig.link databases. You add a squig.link database from a list or with its URL.
    - The results are from A to Z in each part. The Rig, Type and Source lists are from A to Z. They have a search
      box at the top: type a part of a name to find it.
  "Other measurements of this model…" sorts all the measurements of your IEM for the target (Which measurement to
  use). Adjust… (on the Target row) opens a window: tilt, bass, half-tilt, ear gain, treble and air, one row for each.
  Value: − and + (or ↑ ↓ and the mouse wheel in the box), and the graph of the window shows each change. Then Hz and Q
  (gray while the value is 0). "Clear the adjustments" changes them to 0. "Save as a target…" saves the adjusted
  target as your target and uses it. The adjustments go to 0, because they are in the new target. Undo, at the bottom
  of the window, gives you all of this again. Below the Target row, the app shows the adjustments that you made.
- The graph: your measurement (orange), the target (dashed line) and, after you calculate, the measurement with the
  EQ (blue). Below it, the EQ graph shows the EQ (pink: above 0 it adds gain, below 0 it removes gain). "Error
  without EQ": the difference between the measurement and the target with no EQ. Above the graph:
    - View: Frequency response, or Difference from target (the part that the EQ must correct: 0 dB is on the
      target).
    - Y range: Automatic, or 30 to 60 dB.
    - Channels: also the curve of each file.
  When the pointer is on the graph, the graph shows its values at that position. The app does not calculate the
  error at the gray ends. If the app changed a target for a different rig, a band shows the possible error of that
  change.
  History… (near the title of the graph) has the EQs that you saved or copied: Show opens one, and its ⋯ has Copy,
  Keep to compare and Remove from the history.
- Make the EQ: first Your EQ app, for the two tabs (the EQ stays in its limits, and Save writes its file: the ⓘ after
  its label shows them). Then select how to make the EQ, on two tabs: Automatically or Manually (it opens on the tab
  that you selected last). Below the tabs: Settings and More settings (click to open or close them), then Calculate or
  Start.
  Automatically: the method, Settings to try and Calculate. The methods are Best fit for EQ apps, and the Website
  methods for the AutoEQ of squig.link. Settings to try shows the number of EQs that the app tries, and the time that
  is necessary on this PC (its tooltip shows the settings).
  Best fit adds filters one at a time. It keeps the minimum number of filters for the same sound as the target. The
  same sound is a difference of 0.25 dB or less at all frequencies, as the ear hears it. The line below the numbers
  of the result tells you this. If the limits of your EQ app stop this, the line shows the error and its frequencies.
  "Queue…" makes EQs for more than one IEM or target, one after the other (select them). It saves each EQ and keeps
  it in History.
  Manually: you make the EQ. Start from: an empty EQ, a copy of the selected EQ, an EQ file, pasted filters or a
  device's profile. An EQ file can be from Equalizer APO, AutoEq, squig.link, Room EQ Wizard ("Export filter settings
  as text") or Peace (a preset). Then click Start. The manual EQ is on the result card, the same as a calculated EQ.
  Thus, all the parts below operate for it. A measurement and a target are optional (if you select them, the graph
  shows your IEM with the EQ, and its error).
  The app reads files as Equalizer APO plays them (a shelf at its corner frequency moves to its center frequency, a
  slope becomes its Q). An EQ here has peaking filters and shelf filters. Thus, the app removes other filter types, a
  graphic EQ or a convolution, and it tells you.
  If the EQ started from a profile, Use on device › Update puts it into that profile again. "Edit in Make an EQ" in
  Profiles does the same.
  Close (on the right side of its title) shows the result that was there before the manual EQ, or no result. If you
  changed the EQ, it stays in "EQs that you made", and you can open it again. If it is empty, it closes. If it has no
  changes, it closes, and Undo in the message can open it again.
- Settings and More settings (in Make the EQ, click to open or close them): the values of the automatic settings, or
  your values. Each label is above its box. "About these settings" (click to open it) tells you how the app adjusts
  each value. A value that you change shows "your value", and ↺ makes it automatic again. More settings has a tab for
  each part (the tab of a method shows only with that method). All lists are from A to Z (numbers in their sequence,
  and a "Select…" item stays at the top). A list with more than 15 items (More settings › Layout, the Source list of
  Find…, …) opens with a search box at the top. Best fit can start from your filters (More settings › Best fit: type
  them, or use "Edit as a table…" or "Load an EQ file…"). The graph shows them as "With your filters".
- Your result:
    - The error, the pre-amp, the maximum gain and the maximum Q.
    - "EQs that you made": open a different EQ that you made.
    - "Number of filters": the best result for each number of filters. "All results…" shows each result that the
      app tried, with a grid of the error for each filter count and maximum Q. "Compare…" shows two EQs at the same
      time: this EQ and an EQ with a different number of filters, from a different # or from History.
    - The filters, to edit: a table, or Sliders (a graphic EQ: each slider shows the gain of its filter from 0 dB, on
      a dB scale). It also has Undo all and Calculate from these filters. When the graph is not on the screen, a
      copy of the graph is above the page while you edit. The copy is not on the control that you change. If you
      clear "Show the graph while you edit", the copy does not show.
    - File name, then:
    Save filters       writes the files that your EQ app uses into the Saved EQs folder
    Copy               copies the filters to the clipboard, as Equalizer APO text
    Use on device      makes this EQ a profile of a device and enables it on that device (refer to Devices). Or
                       "Use for 5 minutes on" a device: the EQ operates in all apps. Then click Keep it (the bar at
                       the top, or the menu of the tray icon). If you do not, the device gets its EQ again
                       automatically.
    Keep to compare    adds it to the EQs to compare of this IEM (on the graph as a dashed line, and in Listen)
    Report             an HTML page with the graph and the filters (Save filters also writes it, if you select it
                       in More settings)
  The result of a Website method also shows the values to type in the AutoEQ part of squiglink ("Use these
  settings" copies them).
  The EQ graph (below the graph) also edits the filters. Each filter has a handle there, with its number from the
  table, on its curve at its frequency:
    - Drag a handle left or right to change its frequency.
    - Drag it up or down to change its gain.
    - Turn the mouse wheel on it to change its Q.
    - Right-click it for Peak, Low shelf, High shelf and Remove (the On tick box of the table turns a filter off).
    - Double-click where there is no handle to add a filter.
  The curves, the numbers, the table and Listen change while you drag. The scale does not change until you release
  the handle. If you use an EQ on a device for 5 minutes (Use for 5 minutes on), each change goes to that device
  while you edit, in all apps.
- Listen: listen to the EQ through your IEM or headphone. Start with a low volume. Play plays music (short, the app
  makes it, and it starts again at the end). It can also play pink noise, white noise, a sweep, a tone (the graph
  shows its frequency) or your audio file. You hear it through the version that you select: EQ off, the selected EQ
  (edited) or one of your EQs to compare (keys 1-9 change it).
  Same level gives them all the same loudness. Thus, you compare the EQ, not the volume. Hide the names hides the
  name of each version until you click Show the names. "A different version in each ear" puts one version in each
  ear. Also click Interchange, because your left ear and your right ear are not the same.
  If the active device has its EQ on (Devices), you also hear that EQ: Listen tells you, with "Disable it".
  ABX test: can you hear the difference between two versions? Select A and B (two of the versions) and the number
  of trials. Then click Start ABX. In each trial, X is A or B, at random. Click "Listen to A", "Listen to B" and
  "Listen to X" as many times as necessary. Then click "X is A" or "X is B".
  The app does not show if you are correct until the end. Then it shows the number of correct trials. It also shows
  how frequently random selections get that number or more. Below 5 %, you can hear the difference. Above 5 %, it
  can be random.
  While the test operates, Listen uses Same level and the same version in each ear. It hides the version buttons and
  keys 1-9, because with them, you can know X. "Stop the test" shows your results until that time. If you change A
  or B during the test (you edit the EQ or show a different result), the test stops and shows them too. The results
  stay until you close AutoEQ Studio.


TRACE A GRAPH (Trace a graph image…, near the title of the graph)
-----------------------------------------------------------------
Use the tracer if the measurement of an IEM or headphone is only a picture (a data sheet, or a screenshot from a
website). Open, drag or paste (Ctrl+V) the picture, and it becomes a measurement or a target. If you paste or drag a
picture on Make an EQ, the tracer also opens with it.
1. Axes: the app finds the grid lines and reads the numbers on the axes with the text reader of Windows. The two red
   lines (dB) and the two blue lines (Hz) are on grid lines, with their values. Examine them on the picture. If a
   value is not correct, drag the line to a different grid line or type the value.
2. Trace: Trace automatically finds a curve (click it again for the next curve: left, right …), or click a curve to
   trace it. Make a line (manually), Erase (a box), Make smooth, Undo and Redo correct small areas. The tracer
   connects the spaces in dashed or dotted curves. Each curve has a name (L, R): together, the curves are one device.
3. Save: Add as measurement (the curves become the measurement that you use), Add as target, or Save .txt…. If the
   graph shows the difference from a target ("compensated"), select that target in "The graph shows". The tracer
   then adds the target to the curves.
The automatic settings adjust the color tolerance, the points in each octave and the range to save for the picture.
The tracer always reads the labels and follows the curves as accurately as possible (approximately 1 s). A value
that you change is your value (↺ makes it automatic again).
Keys: T D E H the tools, A Trace automatically, S Make smooth, F Show all, + and - zoom, Delete clears the curve,
Ctrl+Z undo. The mouse wheel zooms, and the right button (or Space) moves the picture. On a touch screen, two fingers
zoom and move the picture. With one finger, a tap traces and a finger that moves drags.
If Windows has no text reader for your language, you type the values (Settings > Time & language > Language: add
English with its "optical character recognition").


IF YOU USED EQ SWITCHER
-----------------------
At its first start, AutoEQ Studio copies these items from EQ Switcher:
  - The profiles.
  - The profiles of each device, and the profile that is on.
  - The hotkey and the notification setting.
Then:
1. Click "Add AutoEQ Studio to APO…" (the bar at the top). This disables the EQ Switcher line in APO's config.txt
   and adds the AutoEQ Studio line. Thus, only one app changes the EQs. Add to APO can also disable "Start with
   Windows" in EQ Switcher, and close EQ Switcher if it is open. The two tick boxes are selected at first.
2. If you want AutoEQ Studio to start when Windows starts, enable Start with Windows in its Settings.
Add to APO cannot close some previous versions of EQ Switcher, and it tells you this. Close EQ Switcher from its tray
icon ("Quit"). While EQ Switcher operates, it keeps the hotkey. AutoEQ Studio gets the hotkey when EQ Switcher
closes.


ADD AUTOEQ STUDIO TO APO (one time)
-----------------------------------
1. Install Equalizer APO on each device that must have an EQ:
   a. In APO's Configurator, select the devices.
   b. Restart Windows.
   AutoEQ Studio tells you when a device does not have APO (and opens the Configurator). Do this also for a device
   that you connect for the first time (for example, a new USB DAC).
2. Click "Add AutoEQ Studio to APO…" (the bar at the top). It makes a copy of config.txt
   (config.txt.autoeq-studio-backup). Then it adds one line to APO's config.txt, which gives each device the EQ that
   you selected for it.
   - The enabled lines in config.txt operate for all devices, together with the EQ of each device. An example is an
     "Include:" of an EQ file that you change manually. Thus, Add to APO can disable them (# at the start: it does
     not delete lines).
   - It can add the EQ files that config.txt uses as profiles (not the files that you have as profiles). The EQ file
     that is on becomes the EQ of the active device.
   Settings > "Remove AutoEQ Studio from APO…" removes its line, and enables the lines that it disabled.


PROFILES AND DEVICES
--------------------
A profile is a copy of an EQ file in the Equalizer APO format. The EQ file can be:
  - An "Equalizer APO" file from Make an EQ (Import starts in the Saved EQs folder of AutoEQ Studio, or of AutoEQ
    Local).
  - ParametricEQ.txt from AutoEq.
  - A file exported from squig.link.
  - A file that you saved in the Editor of APO.
Use on device does this in one step, from the result of Make an EQ. The profiles are in APO's config folder ("AutoEQ
Studio\profiles"). Thus, if you change the file that you imported, the profile does not change: import it again.
The buttons of Profiles are above its table: first Import EQ files… and Open the profiles folder, then a line and the
buttons for one profile (they are enabled when you select a profile). "Edit in Make an EQ" opens the selected profile
there as a manual EQ. When you change its filters, Use on device › Update puts it into the profile again (its devices
keep it, and you hear the change immediately). Rename… gives it a different name, and Delete… (the last button)
deletes its file, after a message.

Devices: your playback devices, with their Windows names ("Headset (EarPods)"), connected devices first, from A to Z.
A green dot: active. Your Windows accent color (blue at first): connected. Gray: not connected.
Select a device to give it profiles ("Add a profile": a profile, Import EQ files… or Make an EQ), and select the
profile that is on, or Off. The ✕ of a profile removes it from the device (Undo is in the message near the ✕).
Rename… (in the card with the name of the device) gives the device your name for it ("Dongle – KZ"), and all screens
show this name. During an EQ for 5 minutes, the card shows that EQ as selected.
The line below its EQ tells you if Equalizer APO uses the EQ (✓ in green). If APO does not use it, a warning bar
shows the cause: AutoEQ Studio gets this information from Equalizer APO. Examine again shows all that it found.
A device can have more than one profile (for example, a USB-C dongle that you use with different IEMs). Select one
from the menu of the tray icon or with the hotkey.

AutoEQ Studio keeps each device in its list after the first time. Thus, a device can have its EQ before you connect
it. Windows shows Bluetooth earbuds as two devices (music, and "Hands-Free" for the microphone). AutoEQ Studio uses
them as one device, and its EQ is on for the two.


THE TRAY ICON
-------------
Blue: an EQ is on for the active device. Gray: no EQ. Put the pointer on the icon to see which EQ. Right-click the
icon to open its menu:
  - Open AutoEQ Studio (in bold: a click on the icon does this).
  - The active device, its profiles and Off (click one to change to it).
  - Stop AutoEQ Studio.
A notification tells you which EQ is on when a different device becomes active or when you change the EQ. In
Settings, you can disable the notifications.

Hotkey (Settings, Ctrl+Alt+E at first): it goes to the next profile of the active device, then Off, in all programs.
If Windows does not accept a key (a different program uses it), Settings tells you: select a different key.

On/off hotkey (Settings, Ctrl+Alt+Space at first): it disables the EQ of the active device. Then you can compare
the EQ with no EQ, on all sound. When you press the hotkey again, it enables the EQ again (the menu of the tray icon
also has it: "EQ off, to compare"). With Same level (on at first), "off" has the same loudness as the EQ, with a
lower volume. The app measures the loudness as Listen does: pink noise, as the ear hears it. Thus, the EQ is not
better only because it has more loudness. The notification shows the difference in dB.
The app does not save this condition: if you select an EQ for the device, or start AutoEQ Studio again, the EQ is
on again. A bar at the top of the window shows when the EQ is off, with "Enable it again" (the same as the bar of
"EQ for 5 minutes"). If no EQ is on, the hotkey enables the last EQ of the device.

Start with Windows (Settings): the app starts in the tray when Windows starts. Startup apps in Task Manager shows it
as "AutoEQ Studio" (a copy of pythonw.exe of Python with that name, in the .venv\Scripts folder). An item with the
name "pythonw" there is from EQ Switcher, and Add to APO can disable it.

In the tray, the app uses a small quantity of memory: it does not load Make an EQ there. After you use Make an EQ one
time, the window prepares it when the window opens. It does this when you do not use the keyboard or the mouse for
a short time. Thus, its
tab opens quickly. The window then uses some hundreds of MB more. When you close the window to the tray, it releases
that memory to Windows after 30 s. Then Task Manager shows some MB.


BACKUP
------
Settings > Backup: "Save a backup…" writes one .zip with all your data. It has the devices, their profiles and EQ
files, the settings of Make an EQ, History and EQs to compare. It also has your targets, measurements, presets and
saved EQs. It does not keep the curves from the online databases: the app downloads them again when you use them.

"Load a backup…" puts the data on this PC or on a new PC. First, it saves the data that is there at that time (in
data\backups). Then it replaces the files that have the same names, it deletes no other files, and it starts AutoEQ
Studio again.


LIMITS
------
AutoEQ Studio knows the output device, not the item that is connected to it. For Windows, two IEMs on the same dongle
or headphone jack are one device. Give that device a profile for each IEM. Then change the profile with the tray icon or
the hotkey.


EXAMINE EQUALIZER APO
---------------------
Devices › a device: the line below its EQ shows if APO uses the EQ of that device ("Examine again" examines it
again). It shows if APO reads the AutoEQ Studio file, finds the device and loads its EQ. It also shows the other
items that config.txt loads for all devices. It does not change your settings.
It uses Benchmark.exe of Equalizer APO (in its folder). Benchmark.exe sends a test sound through your APO settings, as
if a device plays it, and it can show the result. It does not change your settings. The file switcher.txt of
AutoEQ Studio has the id of each device.
To do this manually for a device with the id {d3bfcd09-…}, use this command line:
    "C:\Program Files\EqualizerAPO\Benchmark.exe" -l 2 --guid "{d3bfcd09-…}" -v --nopause
"Matching pattern" with that id, then the filters of the EQ, shows that the device uses the EQ.


FILES
-----
AutoEQ Studio.bat   starts the app
Make share zip.bat  for you: a zip of the program to send to persons who test the app (they install Python)
Make ready-to-run zip.bat  the same, with its Python in it (approximately 120 MB): they unzip it and double-click
Make zip for friends.bat   for you: "AutoEQ Studio <version>.zip" in releases\, to send: the installer and READ ME
                           FIRST.txt (how to install it). It makes the installer first, as Make installer.bat does
Make installer.bat  for you: "AutoEQ Studio Setup <version>.exe" in releases\ (refer to INSTALL IT). It must have Inno
                    Setup 6: winget install JRSoftware.InnoSetup --scope user. The version is VERSION in app\paths.py
app\                the program (Python and Qt)
downloads\          curves from the online databases. app\tools\download_all.py downloads all of them, to use offline
                    (some hours, some GB). Start it again to get new curves. Find… shows them in Online databases
                    (Use uses the copy here), and not again in This PC
samples\            example curves
data\               your settings (settings.json) and their log (app.log, each line with its date): the errors, if
                    there are errors. data\eq\: the settings of Make an EQ, History (history.json), EQs to compare
                    (listen.json), the source of each of your files (sources.json: its rig) and the database lists
(Your targets, measurements, saved EQs and presets: Documents\AutoEQ Studio, refer to YOUR FILES.)
.venv\              the Python packages (AutoEQ Studio.bat makes it). If this folder is in OneDrive or its path is
                    long, they go in %LOCALAPPDATA%\AutoEQ Studio\venv (the black window tells you). If OneDrive
                    copies thousands of package files, or a path has more than 260 characters, the packages can become
                    damaged
In APO's config folder (usually C:\Program Files\EqualizerAPO\config):
  AutoEQ Studio\switcher.txt   one "Device:" part for each device, with its EQ (AutoEQ Studio writes it again after each
                               change)
  AutoEQ Studio\profiles\      your profiles
  config.txt                   AutoEQ Studio adds one line: Include: AutoEQ Studio\switcher.txt
