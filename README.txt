AUTOEQ STUDIO
=============

AutoEQ Studio brings AutoEQ Local and EQ Switcher together in one program, in its own window (no browser).

What it does:
- Make an EQ (AutoEQ Local's part): an EQ that brings your headphones or IEMs to a target, saved as the file your EQ
  app needs, or put straight onto a device with "Use on device".
- Devices (EQ Switcher's part): each of your playback devices gets its own EQ, switched by itself. Plug in your
  earphones' dongle and their EQ is on; connect your Bluetooth earbuds and theirs is; your speakers can have none.
  Like Poweramp's per-device EQ, for Windows.

Everything AutoEQ Local and EQ Switcher do is here too.

The first time you open Make an EQ, AutoEQ Studio copies your AutoEQ Local files in (settings, History, EQs to
compare, your targets and measurements, saved EQs, downloads), from an "AutoEQ Local" folder beside its own or in
Downloads; AutoEQ Local keeps its own.

It works through Equalizer APO (https://sourceforge.net/projects/equalizerapo/), which does the actual sound
processing. AutoEQ Studio tells APO which EQ goes with which device; APO then switches by itself whenever the device
playing changes, even when AutoEQ Studio isn't running.


INSTALLING IT (the usual way)
-----------------------------
"AutoEQ Studio Setup <version>.exe" (made by "Make installer.bat", in releases\) installs it like any Windows app:
for you only, without asking for administrator permission (Equalizer APO lets every user change its settings, so
nothing needs more). It goes in AppData\Local\Programs\AutoEQ Studio, with its own Python inside (nothing else to
install or download), a Start menu shortcut (a desktop one if you tick it), and an entry in Settings > Apps >
Installed apps with its version and Uninstall. If Windows says "Windows protected your PC" (the installer isn't
signed): More info, Run anyway.
Installed, nothing of yours is in the program's folder (an update replaces it):
  Documents\AutoEQ Studio            your files (see YOUR FILES), as for every copy
  AppData\Roaming\AutoEQ Studio      settings, History, EQs to compare, backups kept by a restore, the log
  AppData\Local\AutoEQ Studio        downloaded curves and the database lists (fetched again if lost)
The first start puts the sample IEM and target in place. An installed copy starts fresh: to bring everything over
from a copy run from its folder, make a backup there (Settings > Backup) and restore it in the installed one.
Updating: run a newer Setup; it closes AutoEQ Studio first (or asks you to) and keeps your files and settings.
Uninstalling (Installed apps > AutoEQ Studio > Uninstall): it takes AutoEQ Studio out of Equalizer APO (every device
back to APO's own configuration) and out of Start with Windows, then asks whether to delete your settings, History
and downloaded curves too; Documents\AutoEQ Studio always stays.
Only one AutoEQ Studio runs at a time: quit one run from its folder (tray icon > Quit, and untick its Start with
Windows) before starting the installed one.

YOUR FILES
----------
Your targets and measurements (what Make an EQ uses), saved EQs and presets are in Documents\AutoEQ Studio, where
Windows apps keep the files you make (as Room EQ Wizard, Audacity or REAPER do), each kind in a folder of its own:
  Targets         target curves                  Saved EQs     EQ files and reports (Save filters, Report)
  Measurements    your headphones' and IEMs'     Presets       saved settings presets
Put curve files in Targets or Measurements yourself (Explorer) and Make an EQ lists them; Add… and Use put them there
too. Settings > Your files shows the folder (Open the folder) and chooses another (Change…: your files can be moved
there; a file is never replaced, a different one of the same name is kept beside it with (2) after its name; the app
starts again). Not inside AutoEQ Studio's own folder: an update or a new copy would lose them.
An older AutoEQ Studio kept them in its own folder (inputs\target, inputs\measurement, output\, presets\): the first
time Make an EQ opens, it offers to move them (Move them, Choose another folder…, or Not now: asked again next time).
Backups made before and after this hold the same names, so either restores into either.

STARTING IT (from its folder)
-----------------------------
Double-click "AutoEQ Studio.bat". The first time it sets up its Python packages (Qt, numpy, scipy and the rest,
about 150 MB; it needs 64-bit Python 3.10 or newer). It then opens its window and puts an icon by the clock (the
tray: if you don't see it, click the ^ arrow there). Closing the window leaves it running in the tray; Quit is in the
icon's right-click menu. Starting it again while it runs just shows its window.

The top bar has the screens (Make an EQ, Devices, Profiles, Settings) and, on the right, Presets (on Make an EQ),
Guide, Help and Online / Offline. The window is light or dark as Windows is (Settings > Personalization > Colors), and changes with it;
with one of Windows' contrast themes on (Settings > Accessibility > Contrast themes) it uses that theme's colours.
It looks like Windows 11's own apps: the main buttons, ticks and what's chosen are in your Windows accent colour (on
the same Colors page), and on Windows 11 the window's background is Mica, tinted by your desktop picture (plain
while the window isn't the active one, or with Transparency effects off).
Every control can be reached with Tab (the top bar's screens with the arrow keys) and has a name a screen reader
says.

Guide: a tour of a whole EQ job on Make an EQ (30 steps: choose, the settings, run, review, save, listen, more), as
AutoEQ Local's was. Each step lights up a part of the screen, says what it does and shows it in a short demo: a
pointer opens Find… and types a search, picks a row and shows it on the graph, opens a list and chooses, types the
target adjustments while the target changes on the graph (kept in sight at the top while the page scrolls), shows a
run's progress and the EQ'd curve; before a run the result steps show an example result worked out from your files.
The card: "3 of 30" lists every step to go straight to one, Replay (R), Pause (P), Skip demo, the demo's speed,
"Play all steps" (the whole tour by itself), Back / Next (the arrow keys), End tour (Esc), Start again. Scrolling
while a demo plays pauses it; Resume scrolls back. What a demo shows is put back after it, and nothing is chosen, run,
saved or downloaded. With Windows' animation effects off a demo is numbered markers instead. The tracer has its own
Guide (on a sample graph).
Presets (top bar, on Make an EQ): every setting saved under a name and loaded again in one go (not your files: the
target and measurement stay); Delete a preset; Reset all settings… (Undo puts yours back). They're in Presets.
Help: every term (Q, shelf, rig, pre-amp…), the questions that come up most and every setting in full, with a search
box. Point at any setting and press F1: Help opens at it.


ONLINE AND OFFLINE
------------------
Click Online / Offline (top right; also in Settings). Offline, AutoEQ Studio never connects to the internet: it uses
only what's on this PC (your files, curves downloaded before, the database lists it already has), and links to
websites are turned off. Online, it can also use the internet (the online databases, as AutoEQ Local does). Switching
EQs on your devices never needs the internet either way.


MAKE AN EQ
----------
One column, top to bottom:
- The graph: your measurement (orange), the target (dashed) and, after a run, the measurement with the EQ (blue);
  under it the EQ itself (pink: above 0 boosts, below 0 cuts). "Error without EQ": how far the measurement is from
  the target before any EQ. Over it: View (Absolute, or Relative to target: what's left to correct, 0 dB = on
  target), Y range (Auto or 30-60 dB), Channels (each file's curve too); point at the graph and its values show
  there. The shaded ends aren't scored; a target converted to another rig has a band showing how far off it may be.
- Target and Measurement: the files in the app, A to Z (numbers as numbers: "IEM 2" before "IEM 10"; a
  measurement is a set: left and right, or several seatings). Add…
  takes files from this PC; Find… (or the / key) searches the app, this PC and the online databases (Show draws one
  on the graph, dotted: "Hide shown curves" takes them off; Use takes it, and Undo under the files puts back what you
  had; Sources… chooses where it looks: this PC's folders, each online database on or off, another squig.link-style
  database added from squig.link's list or by its address; its results are A to Z in each part, and the Rig, Type
  and Source filters' lists are A to Z with a search box at the top: type part of a name to find it); "Other measurements of this model…" ranks every measurement of your IEM for the target (Which measurement to
  use?). History (by the graph's title) has the EQs you saved or copied before.
- Make the EQ: Your EQ app (its limits are kept, and Save writes exactly its file), the method (Best fit for EQ apps;
  the Website ones for squig.link's own AutoEQ), the search (what a run tries and how long it takes on this PC), Run. Best fit adds filters one at a time and keeps the simplest EQ that sounds the same as the target
  (within 0.25 dB everywhere, as the ear hears it); the line under the result's numbers says so, or how far off it is
  and where when your EQ app's limits can't get there.
  "Run several…" makes EQs for several IEMs or targets in one go (tick them; each is saved and kept in History).
  "By hand" makes the EQ yourself: Start empty, From an EQ file… (Equalizer APO, AutoEq, squig.link, Room EQ
  Wizard's "Export filter settings as text", a Peace preset), Paste filters…, From a device's profile, or A copy of
  the EQ shown. It shows on the result card as a run of its own, so everything below works for it; a measurement
  and target are optional (chosen, the graph shows your IEM with it and its error). Files are read as Equalizer APO
  plays them (a shelf at its corner frequency moved to its centre, a slope as its Q); an EQ here has peaking and
  shelf filters, so other filter types, a graphic EQ or a convolution are left out, and said. Begun from a
  profile, Use on device › Update puts it back into that profile (Profiles: "Edit in Make an EQ" does the same).
- Settings and Advanced (folds): the automatic settings' values and why, or your own ("yours", ↺ hands one back).
  Every list is A to Z (numbers as numbers; a "Choose…" stays on top), and any list of more than 15 choices
  (Advanced › Layout, Find…'s Source, …) opens with a search box at its top.
  Best fit can start from your own filters (typed, "Edit as a table…" or "Load an EQ file…"): the graph shows them
  as "With your filters".
- Adjust (on the Target card, under the target): tilt, bass, half-tilt, ear gain, treble and air, one row each:
  Amount with − and + (or ↑ ↓ and the mouse wheel in the box; the graph follows), then Hz and Q (greyed while the
  amount is 0). "Reset adjustments" puts them back to 0; "Save as a
  target…" keeps the target as adjusted as a target of your own, in use (the adjustments go back to 0: they're in it
  now; Undo in the notice puts it all back).
- Your result: its error, pre-amp, biggest boost and Max Q, "Runs this session" (an earlier run back), "Fewer or more
  filters" (the best result for each count; "All results…" lists every result the run tried, with a grid of the
  error by filter count and max Q; "Compare…" puts two EQs side by side: this one, another filter count or run, or
  one from History), its filters (a table or sliders, to edit; Revert, Retry from these
  filters), the File name, then:
    Save filters       writes the file(s) your EQ app needs into the Saved EQs folder
    Copy               the filters as Equalizer APO text, on the clipboard
    Use on device      makes this EQ a profile of a device and switches it on there (see Devices); or "Try for 5
                       minutes on" a device: it plays in every app, then Keep it (the bar at the top, or the tray
                       icon's menu) or the device's own EQ comes back by itself
    Keep to compare    adds it to this IEM's EQs to compare (on the graph, dashed; and in Listen)
    Report             an HTML page with the graph and the filters (also written by Save when ticked in Advanced)
  A Website method's result also says what to type into squiglink's AutoEQ panel ("Use in single run" copies it).
  The EQ graph (under the graph) edits the filters too: each has a handle there, numbered as in the table, on its
  own curve at its frequency. Drag one (left and right: its frequency; up and down: its gain), turn the mouse wheel
  over it (its Q), right-click it (Peak, Low shelf, High shelf, Switched on, Delete); double-click where there's
  none for a new filter. The curves, numbers, table and Listen follow as you drag; the scale stays put until you let
  go. An EQ you're trying on a device (Try for 5 minutes on) plays each change there as you make it, in every app.
- Listen: hear the EQ through your own IEM or headphone. Start with the volume low. Play plays music (a short loop
  made by the app), pink or white noise, a sweep, a tone (its frequency shown on the graph) or your own file, through
  the version you pick: EQ off, the selected EQ (as edited) or one of your EQs to compare (keys 1-9 switch).
  Level-matched keeps them all equally loud, so you compare the EQ, not the volume. Blind test hides which is which
  until Reveal; "A different version in each ear" puts one in each (Swap them too: your ears differ). If the device
  playing has its own EQ on (Devices), it plays on top of what you hear here: Listen says so, with "Switch it off".


TRACING A GRAPH (Trace image, by the graph's title)
---------------------------------------------------
For an IEM or headphone whose measurement exists only as a picture (a maker's sheet, a review's screenshot): open,
drop or paste (Ctrl+V) the picture, and it becomes a measurement or a target. Pasting or dropping a picture on Make an
EQ opens the tracer with it too.
1. Axes: the gridlines are found, and the numbers on the axes read with Windows' own text reader; the two red lines
   (dB) and two blue lines (Hz) sit on gridlines with their values filled in. Check them against the picture; drag a
   line onto another gridline or type a value when one is wrong.
2. Trace: Auto trace finds a curve by itself (press again for the next one: left, right …), or click a curve to
   follow it. Draw (by hand), Erase (a box), Smooth, Undo and Redo fix spots. Dashed or dotted curves are bridged.
   Each curve has a name (L, R): together they're one device.
3. Save: Add as measurement (the curves become the measurement in use), Add as target, or Save .txt…. If the graph
   was drawn relative to a target ("compensated"), choose it under "The graph shows" and it's added back.
Automatic settings fit the colour tolerance, the points per octave and the range to save to the picture (it always
reads labels and follows curves as carefully as it can: about a second). A value you change is yours (↺ hands it
back). Keys: T D E H the tools, A Auto trace, S Smooth, F fit, + and - zoom, Delete clears the curve, Ctrl+Z undo;
the mouse wheel zooms, the right button (or Space) moves the picture. On a touch screen two fingers pinch to zoom and
drag the picture; with one, a tap traces and a finger that moves drags.
If Windows has no text reader for your language, the values are typed instead (Settings > Time & language >
Language adds English with its "optical character recognition").


COMING FROM EQ SWITCHER
-----------------------
On its first start, AutoEQ Studio brings over EQ Switcher's profiles, the profiles each device has and the one on,
the hotkey and the notices setting. Then:
1. Click "Set up…" (the bar at the top). EQ Switcher's line in APO's config.txt is turned off and AutoEQ Studio's is
   added, so only one of them applies an EQ. Set up also offers (ticked) to turn off EQ Switcher's Start with
   Windows and to quit it if it's running.
2. In AutoEQ Studio's Settings, turn Start with Windows on if you want it at sign-in.
An older EQ Switcher can't be asked to quit: Set up says so; quit it from its tray icon (> Quit). While it still runs
it keeps the hotkey; AutoEQ Studio takes it as soon as EQ Switcher quits.


SETTING IT UP (once)
--------------------
1. Equalizer APO must be installed, and installed on each device you want an EQ on: in APO's Configurator, tick
   the devices, then restart Windows. AutoEQ Studio says when a device doesn't have APO (and opens the
   Configurator). A device you plug in for the first time (a new USB DAC) needs this too.
2. Click "Set up…" (the bar at the top). It adds one line to APO's config.txt that brings in the EQ chosen for each
   device, after keeping a copy of config.txt (config.txt.autoeq-studio-backup).
   - Lines that are on in config.txt now (e.g. an "Include:" of an EQ file you switch by hand) would apply to every
     device on top of its own EQ, so it offers to turn them off (# in front; nothing is deleted).
   - The EQ files config.txt uses are offered as profiles (not ones you have already); the one on now becomes the
     EQ of the device playing now.
   Settings > "Take AutoEQ Studio out of APO…" undoes it: its line goes, the lines it turned off are on again.


PROFILES AND DEVICES
--------------------
A profile is a copy of an EQ file in Equalizer APO's format: an "Equalizer APO" file saved by Make an EQ (Import
starts in AutoEQ Studio's Saved EQs folder; or AutoEQ Local's), AutoEq's ParametricEQ.txt, squig.link's
export, or one saved from APO's Editor. (Use on device does it in one step, from Make an EQ's result.) Profiles are kept in APO's config folder ("AutoEQ Studio\profiles"), so changing the
original file later doesn't change the profile: import it again. Profiles › "Edit in Make an EQ" opens the chosen one
there as an EQ by hand: change its filters, then Use on device › Update puts it back (its devices keep it, and hear
the change at once).

Devices tab: your playback devices, as Windows names them ("Headset (EarPods)"), the one playing now first (green
dot; connected: your Windows accent colour, blue by default; grey: not connected). Choose one to give it profiles
("Add a profile") and choose the one on, or Off. Rename… gives it your own name ("Dongle – KZ"), shown everywhere.
The line under its EQ says whether the EQ really plays: AutoEQ Studio asks Equalizer APO itself (✓ or ✕; Check
again says all it found).
A device can have several profiles (e.g. a USB-C dongle used with different IEMs): switch between them from the
tray icon's menu or with the hotkey.

Devices are remembered once seen, so a device's EQ is ready before you plug it in. Bluetooth earbuds show up in
Windows twice (music, and "Hands-Free" for calls): AutoEQ Studio treats them as one device, and its EQ is on for both.


THE TRAY ICON
-------------
Blue: an EQ is on for the device playing; grey: none. Hover for which. Right-click: the device playing, its profiles
and Off (click one to switch), Open AutoEQ Studio, Quit. A notice says which EQ is on when another device starts
playing or you switch (Settings: turn notices off).

Hotkey (Settings; Ctrl+Alt+E to start with): goes through the playing device's profiles, then Off, in any program.
If Windows refuses a key (another program has it), Settings says so: choose another.

On/off hotkey (Settings; Ctrl+Alt+Space to start with): the playing device's EQ off for now, to compare it with no EQ
on whatever is playing, then back on (also the tray icon's menu: "EQ off for now, to compare"). Level-matched (on to
start with), "off" plays no EQ turned down to the EQ's loudness (Listen's measure: pink noise as the ear weighs it),
so the louder one doesn't seem better for being louder; the notice says by how much. It isn't saved: choosing an EQ
for the device, or starting AutoEQ Studio again, ends it; Devices says when it's on, with "Switch it back on". With
no EQ on, the hotkey switches on the one the device had last.

Start with Windows (Settings): starts in the tray when you sign in. Task Manager's Startup apps lists it as
"AutoEQ Studio" (a copy of Python's pythonw.exe by that name, in the .venv\Scripts folder; an entry called
"pythonw" there is EQ Switcher's, which Set up offers to turn off).

In the tray it stays light: Make an EQ isn't loaded there. Once you've used Make an EQ, opening the window gets it
ready in the background at the first quiet moment (no key or mouse input for a moment), so its tab opens at once;
the window uses a few hundred MB more then. Closed to the tray, the window gives that memory back to Windows after
30 s: Task Manager then shows a few MB.


BACKUP
------
Settings > Backup: "Back up everything…" writes one .zip with all that's yours (the devices, their profiles and
EQ files, Make an EQ's settings, History, EQs to compare, your targets, measurements, presets and saved EQs; not the
curves downloaded from the online databases, which download again when used). "Restore from a backup…" puts them
back, on this PC or a new one: it first keeps how things are now (in data\backups), replaces files with the same
name, deletes nothing else, and starts AutoEQ Studio again.


WHAT IT CAN'T DO
----------------
It knows the output device, not what's plugged into it: two IEMs on the same dongle or headphone jack look the same
to Windows. Give that device a profile for each and switch with the tray icon or the hotkey.


CHECKING WHAT APO DOES
----------------------
Devices › a device: the line under its EQ asks APO itself whether that device's EQ applies ("Check again" asks
anew), and says what it found: whether APO reads AutoEQ Studio's file, finds the device and loads its EQ, and what else config.txt loads for
every device on top. It changes nothing.
It uses Equalizer APO's Benchmark.exe (in its folder), which runs a test sound through your configuration as if it
played on a device and can print what it does, without changing anything. By hand, for a device whose id is
{d3bfcd09-…} (AutoEQ Studio's switcher.txt lists each device's id):
    "C:\Program Files\EqualizerAPO\Benchmark.exe" -l 2 --guid "{d3bfcd09-…}" -v --nopause
"Matching pattern" with that id, followed by the EQ's filters, means the device's EQ plays.


FILES
-----
AutoEQ Studio.bat   starts it
Make share zip.bat  for you: a zip of the program to send to testers (they set up Python themselves);
Make ready-to-run zip.bat  the same with its own Python inside (about 120 MB): testers unzip and double-click
Make zip for friends.bat   for you: "AutoEQ Studio <version>.zip" in releases\, to send: the installer and READ ME
                           FIRST.txt (how to install it). It makes the installer first, as Make installer.bat
Make installer.bat  for you: "AutoEQ Studio Setup <version>.exe" in releases\ (see INSTALLING IT; needs Inno
                    Setup 6: winget install JRSoftware.InnoSetup --scope user). The version is app\paths.py's VERSION
app\                the program (Python and Qt)
downloads\          curves downloaded from the online databases (app\tools\download_all.py fetches every one of
                    them, for offline use: a few hours, a few GB; run it again later for what's new). Find… shows
                    them under Online databases (Use takes the copy here), not again under This PC
samples\            example curves to try
data\               your settings (settings.json) and its log (app.log, each line dated): what went wrong, if anything did; data\eq\:
                    Make an EQ's settings, History (history.json), EQs to compare (listen.json), where each of your
                    files came from (sources.json: its rig) and the database lists
(Your targets, measurements, saved EQs and presets: Documents\AutoEQ Studio, see YOUR FILES.)
.venv\              the Python packages (setup makes it). When this folder is in OneDrive or its path is long, they go
                    in %LOCALAPPDATA%\AutoEQ Studio\venv instead (the black window says so): syncing thousands of
                    package files, or Windows' 260-character path limit, would break them
In APO's config folder (usually C:\Program Files\EqualizerAPO\config):
  AutoEQ Studio\switcher.txt   one "Device:" section per device with its EQ (written again on every change)
  AutoEQ Studio\profiles\      your profiles
  config.txt                   one line added: Include: AutoEQ Studio\switcher.txt
