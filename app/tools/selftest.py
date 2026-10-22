"""AutoEQ Studio's self-test: every part on a fake Equalizer APO folder in a temporary folder (the real one is never
touched), the window drawn off-screen. Run it after any change:
    ".venv\\Scripts\\python.exe" "app\\tools\\selftest.py" [--quick]
Each line says ok or FAIL; the last says whether all passed (exit code 1 when not). The EQ part's checks
(eq_checks.py, on a copy of the app) run last, as one line here with their count; --quick leaves them out.
"""
import os
import shutil
import sys
import tempfile
import time

TOOLS = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(TOOLS)
ROOT = os.path.dirname(APP)
sys.path.insert(0, APP)
os.environ["QT_QPA_PLATFORM"] = "offscreen"

FAILS = []


def check(name, ok, detail=""):
    print(("ok   " if ok else "FAIL ") + name + ("" if ok else f"  ({detail})"))
    if not ok:
        FAILS.append(name)


EARPODS = b"Preamp: -26.7 dB\r\nFilter 1: ON LSC Fc 105 Hz Gain 9.0 dB Q 0.70\r\nFilter 2: ON PK Fc 2000 Hz Gain -2 dB Q 1\r\n" \
          b"Filter 3: OFF PK Fc 5000 Hz Gain 1 dB Q 2\r\n"
SAMSON = "Preamp: -3,3 dB\nFilter: ON PK Fc 60 Hz Gain 3 dB Q 0.7\n".encode("utf-16")  # (Notepad's "Unicode", a comma)
CONFIG = "# Include: Samson.txt\r\nInclude: EarPods.txt\r\n".encode("utf-8-sig")


def fake_apo(top):
    conf = os.path.join(top, "apo", "config")
    os.makedirs(conf)
    for name, raw in (("config.txt", CONFIG), ("EarPods.txt", EARPODS), ("Samson.txt", SAMSON)):
        with open(os.path.join(conf, name), "wb") as fh:
            fh.write(raw)
    return conf


def eqfile_checks():
    from switcher import eqfile
    s = eqfile.summary(EARPODS.decode())
    check("eq files: filters switched on and the pre-amp counted", s == {"filters": 2, "preamp": -26.7, "graphic": False}, s)
    s = eqfile.summary("Preamp: -3,3 dB\nGraphicEQ: 20 -1; 1000 0; 20000 2\n")
    check("eq files: a GraphicEQ, and a decimal comma", s == {"filters": 0, "preamp": -3.3, "graphic": True}, s)
    refused = []
    for text in ("Device: Speakers\nPreamp: 1 dB", "Include: other.txt\n", "Convolution: room.wav\n", "hello\n", ""):
        try:
            eqfile.summary(text)
        except eqfile.NotAnEqFile as e:
            refused.append(str(e)[:12])
    check("eq files: a Device or Include line, a convolution by a short path, and no EQ at all are refused",
          len(refused) == 5, refused)
    eqfile.summary("Convolution: C:\\IRs\\room.wav\n")  # (a full path works anywhere: kept)
    names = [eqfile.name_from_file(n) for n in ("Truthear GATe to Harman - Best fit - filters.txt",
                                                "Samson SR950 ParametricEQ.txt", "Moondrop Aria EqualizerAPO.txt",
                                                "EQ.txt")]
    check("eq files: a profile's name leaves out where the file came from", names ==
          ["Truthear GATe to Harman", "Samson SR950", "Moondrop Aria", "EQ"], names)


def device_checks():
    from switcher import devices as D
    E = D.Endpoint
    eps = [E("{1}", "Headphones", "Buds", D.NOT_PRESENT, True), E("{2}", "Headset", "Buds Hands-Free", D.NOT_PRESENT, False),
           E("{3}", "Speakers", "Realtek", D.NOT_PRESENT, False), E("{4}", "Speakers", "Realtek", D.ACTIVE, True),
           E("{5}", "Headset", "EarPods", D.ACTIVE, False)]
    devs = D.group(eps)
    got = [(d.label, d.guids, d.connected, d.apo) for d in devs]
    check("devices: Bluetooth's Hands-Free and an old copy of a device join it; connected ones first; APO is judged "
          "on the endpoints in use, not Hands-Free", got == [
              ("Headset (EarPods)", ["{5}"], True, False), ("Speakers (Realtek)", ["{3}", "{4}"], True, True),
              ("Headphones (Buds)", ["{1}", "{2}"], False, True)], got)
    eps = D.endpoints()  # (this PC's: read only)
    import winreg
    try:  # (Windows' list of playback devices: when it has any, endpoints() must find them)
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\MMDevices\Audio\Render") as k:
            listed = winreg.QueryInfoKey(k)[0]
    except OSError:
        listed = 0
    check("devices: this PC's playback devices are read", isinstance(eps, list) and all(e.guid.startswith("{") for e in eps)
          and (eps or not listed), (len(eps), listed))
    playing = D.playing()  # (Windows' default playback device, through comtypes: read only)
    check("devices: the device playing is Windows' default one, one of this PC's (or none)",
          playing is None or (playing.startswith("{") and any(e.guid == playing for e in eps)), playing)


def apo_checks(top):
    from switcher.apo import Apo, INCLUDE_LINE, OFF_MARK
    import textfile
    conf = fake_apo(top)
    a = Apo(conf)
    check("apo: the config folder is found and writable", a.found and a.writable())
    refs = [os.path.basename(p) for p in a.referenced_files()]
    check("apo: the EQ files config.txt uses, on or off, are offered", refs == ["Samson.txt", "EarPods.txt"], refs)
    check("apo: the lines on now are found", a.others_on(a.read_config()) == ["Include: EarPods.txt"])
    off = a.install_line()
    a.install_line()  # (twice: still one line, and the first copy of config.txt kept)
    with open(a.config_txt, "rb") as fh:
        raw = fh.read()
    with open(os.path.join(conf, "config.txt.autoeq-studio-backup"), "rb") as fh:
        backup = fh.read()
    check("apo: setting up turns the other lines off, adds its line once, keeps the BOM, CRLF and the first copy",
          off == ["Include: EarPods.txt"] and raw.startswith(b"\xef\xbb\xbf") and raw.count(INCLUDE_LINE.encode()) == 1
          and (OFF_MARK + "Include: EarPods.txt\r\n").encode() in raw and backup == CONFIG, raw)
    check("apo: set up", a.set_up())
    a.remove_line()
    with open(a.config_txt, "rb") as fh:
        back = fh.read()
    check("apo: taking AutoEQ Studio out puts config.txt back as it was", back == CONFIG and not a.set_up(), back)
    text = a.switcher_text([("Headset (EarPods)", ["{5}"], "EarPods.txt"), ("Buds", ["{1}", "{2}"], None),
                            ("Never seen", [], "x.txt")])
    lines = [x for x in text.split("\r\n") if x and not x.startswith("#")]
    check("apo: one Device section per device (its endpoints, its profile), none without endpoints, then all devices",
          lines == ["Device: {5}", "Include: profiles\\EarPods.txt", "Device: {1}; {2}", "Device: all"], lines)
    lines = [x for x in a.switcher_text([("A", ["{d3bfcd09-14ce-41c7-b4f5-e83278716021}"], None)]).split("\r\n")
             if x.startswith("Device: {")]
    check("apo: each id written as Windows names it, with its { } (APO compares whole words: a bare id never matched)",
          lines == ["Device: {d3bfcd09-14ce-41c7-b4f5-e83278716021}"], lines)
    first = a.write_switcher([("A", ["{5}"], None)])
    second = a.write_switcher([("A", ["{5}"], None)])
    check("apo: the file is written only when it changes (APO reloads on every write)", first and not second)
    check("apo: no temporary files left", not [f for f in os.listdir(a.own) if f.endswith(".tmp")])
    textfile.write_atomic(a.config_txt, b"")
    a.install_line()
    check("apo: an empty config.txt gets just the line", textfile.read(a.config_txt).strip() == INCLUDE_LINE)


def core_checks(top):
    from switcher import core
    from switcher import devices as D
    from switcher.apo import Apo
    conf = fake_apo(top)
    data = os.path.join(top, "data", "settings.json")
    os.makedirs(os.path.dirname(data))
    with open(data, "w") as fh:  # (a hand-edited file with junk: what can't be used is dropped)
        fh.write('{"profiles": {"x": 5}, "devices": {"k": {"profiles": "no", "active": "x"}}, "notify": "yes"}')
    eps = [D.Endpoint("{5}", "Headset", "EarPods", D.ACTIVE, True), D.Endpoint("{1}", "Headphones", "Buds", D.NOT_PRESENT, True)]
    now = {"playing": "{5}"}
    sw = core.Switcher(data, Apo(conf), endpoints=lambda: list(eps), playing=lambda: now["playing"])
    check("core: settings with junk in them load (what can't be used dropped)",
          sw.s["profiles"] == {} and sw.s["notify"] is True and sw.s["devices"]["k"]["profiles"] == [])
    # (review #29: other parts' choices, e.g. Listen's, kept from one start to the next)
    sw.s["listen"] = {"vol": -40}
    sw.save()
    again = core.Switcher(data, Apo(conf), endpoints=lambda: list(eps), playing=lambda: now["playing"])
    check("core: other parts' settings (Listen's, the tracer's) are kept from one start to the next",
          again.s.get("listen") == {"vol": -40}, again.s.get("listen"))
    # (review #5: a settings file that can't be read is never written over)
    import textfile
    bad = os.path.join(top, "bad", "settings.json")
    os.makedirs(os.path.dirname(bad))
    with open(bad, "w") as fh:
        fh.write('{"profiles": {"a": {"name": "Mine", "file": "x.txt"}}, "dev')  # (cut off)
    own = os.path.join(conf, "AutoEQ Studio", "switcher.txt")
    with open(own, "w", encoding="utf-8") as fh:
        fh.write("Device: x\nInclude: profiles\\x.txt\n")  # (an EQ on: still on after the damaged start)
    apo_before = open(own, encoding="utf-8").read()
    broken = core.Switcher(bad, Apo(conf), endpoints=lambda: list(eps), playing=lambda: now["playing"])
    apo_after = open(own, encoding="utf-8").read() if os.path.isfile(own) else None
    check("core: a damaged settings file is kept as .bad and said; the app starts fresh; APO's file isn't written "
          "(every EQ would go off: review 2)", os.path.exists(bad + ".bad") and "couldn't be read" in broken.problem
          and not broken.read_only and broken.s["profiles"] == {} and apo_after == apo_before,
          (broken.problem, apo_before, apo_after))
    with open(os.path.join(conf, "AutoEQ Studio", "switcher.txt"), "w") as fh:
        fh.write("kept")
    real = textfile.read_json_kept
    textfile.read_json_kept = lambda path, kind: (_ for _ in ()).throw(PermissionError(13, "in use"))
    try:
        locked = core.Switcher(data, Apo(conf), endpoints=lambda: list(eps), playing=lambda: now["playing"])
    finally:
        textfile.read_json_kept = real
    before = open(data, encoding="utf-8").read()
    locked.set("notify", False)
    locked.apply()
    with open(os.path.join(conf, "AutoEQ Studio", "switcher.txt")) as fh:
        apo_now = fh.read()
    check("core: a settings file another program holds makes nothing change: neither it nor APO's file is written",
          locked.read_only and "in use" in locked.problem and open(data, encoding="utf-8").read() == before
          and apo_now == "kept", (locked.read_only, locked.problem))
    refused = []
    for act in (locked.set_up_apo, locked.remove_from_apo):
        try:
            act()
        except OSError:
            refused.append(act.__name__)
    check("core: read-only, setting APO up or taking it out is refused too (review 2)",
          refused == ["set_up_apo", "remove_from_apo"], refused)
    told = []
    sw.listeners.append(lambda what, info: told.append((what, info.get("playing_changed"))))
    ear = sw.import_profile(os.path.join(conf, "EarPods.txt"))
    sam = sw.import_profile(os.path.join(conf, "Samson.txt"))
    again = sw.import_profile(os.path.join(conf, "EarPods.txt"))
    names = [sw.profile_name(i) for i in (ear, sam, again)]
    check("core: profiles imported (the same file twice: its own name and file)",
          names == ["EarPods", "Samson", "EarPods (2)"] and len(set(p["file"] for p in sw.profiles().values())) == 3, names)
    with open(os.path.join(sw.apo.profiles, sw.profiles()[sam]["file"]), "rb") as fh:
        check("core: a profile is the file's bytes as they were (UTF-16 kept)", fh.read() == SAMSON)
    ep, buds = "Headset|EarPods", "Headphones|Buds"
    sw.add_to_device(ep, ear)
    sw.add_to_device(ep, sam, switch_on=False)
    sw.add_to_device(buds, sam)
    with open(os.path.join(sw.apo.own, "switcher.txt")) as fh:
        text = fh.read()
    check("core: APO's file has each device's profile",
          "Device: {5}\nInclude: profiles\\EarPods.txt" in text and "Device: {1}\nInclude: profiles\\Samson.txt" in text, text)
    order = [sw.cycle()[1] for _ in range(3)]
    check("core: the hotkey goes through the playing device's profiles, then Off", order == [sam, None, ear], order)
    check("core: switching to a profile the device doesn't have is refused", not sw.set_active(ep, again))
    told.clear()
    eps.append(D.Endpoint("{2}", "Headset", "Buds Hands-Free", D.NOT_PRESENT, True))
    now["playing"] = "{1}"
    eps[1].state = D.ACTIVE
    changed = sw.refresh()
    check("core: a device starting to play is told (with playing_changed), its new endpoint remembered",
          changed and ("devices", True) in told and sw.record(buds)["guids"] == ["{1}", "{2}"]
          and sw.playing_key == buds, (told, sw.record(buds)))
    check("core: nothing changed, nothing told", not sw.refresh())
    file = os.path.join(sw.apo.profiles, sw.profiles()[sam]["file"])
    sw.remove_profile(sam)
    check("core: removing a profile takes it off every device (those it was on are off) and deletes its copy",
          sw.record(buds)["active"] is None and sam not in sw.record(ep)["profiles"] and not os.path.exists(file))
    sw.rename_profile(again, "EarPods")
    check("core: a rename to a name in use gets its own", sw.profile_name(again) == "EarPods (2)")
    sw2 = core.Switcher(data, Apo(conf), endpoints=lambda: list(eps), playing=lambda: "{1}")
    check("core: settings saved and read back", sw2.record(ep)["active"] == ear and sw2.record(buds)["guids"] == ["{1}", "{2}"])
    off = sw.set_up_apo()
    check("core: setting up APO", off == ["Include: EarPods.txt"] and sw.apo.set_up())
    gone = core.Switcher(os.path.join(top, "d2.json"), Apo(os.path.join(top, "nowhere")), endpoints=lambda: [],
                         playing=lambda: None)
    try:
        gone.import_profile(os.path.join(conf, "EarPods.txt"))
        said = ""
    except OSError as e:
        said = str(e)
    check("core: without APO, importing says so and nothing is written", "isn't installed" in said and not gone.apply(), said)


def takeover_checks(top):
    """From EQ Switcher: its line turned off on setting up, its file not offered as an EQ, its profiles and choices
    brought over on the first start."""
    from switcher import core
    from switcher import devices as D
    from switcher.apo import Apo
    import json
    conf = fake_apo(top)
    old_dir = os.path.join(conf, "EQ Switcher", "profiles")
    os.makedirs(old_dir)
    with open(os.path.join(old_dir, "EarPods.txt"), "wb") as fh:
        fh.write(EARPODS)
    with open(os.path.join(conf, "EQ Switcher", "switcher.txt"), "w") as fh:
        fh.write("Device: {5}\nInclude: profiles\\EarPods.txt\nDevice: all\n")
    with open(os.path.join(conf, "config.txt"), "w") as fh:
        fh.write("# Include: Samson.txt\n# (EQ Switcher) Include: EarPods.txt\nInclude: EQ Switcher\\switcher.txt\n")
    old = os.path.join(top, "old.json")
    with open(old, "w") as fh:
        json.dump({"profiles": {"p1": {"name": "EarPods", "file": "EarPods.txt", "filters": 2, "preamp": -26.7},
                                "gone": {"name": "Lost", "file": "lost.txt"}},
                   "devices": {"Headset|EarPods": {"label": "Headset (EarPods)", "guids": ["{5}"], "profiles": ["p1", "gone"],
                                                   "active": "p1"}}, "hotkey": "Ctrl+Alt+Q", "notify": False}, fh)
    eps = [D.Endpoint("{5}", "Headset", "EarPods", D.ACTIVE, True)]
    sw = core.Switcher(os.path.join(top, "new.json"), Apo(conf), endpoints=lambda: eps, playing=lambda: "{5}")
    refs = [os.path.basename(p) for p in sw.apo.referenced_files()]
    check("takeover: EQ Switcher's per-device file isn't offered as an EQ; a line another app turned off still is",
          refs == ["Samson.txt", "EarPods.txt"], refs)
    n = sw.bring_over(old, old_dir)
    rec = sw.record("Headset|EarPods")
    check("takeover: EQ Switcher's profiles (their files copied) and choices come over; one whose file is gone doesn't",
          n == 1 and rec["profiles"] == ["p1"] and rec["active"] == "p1" and sw.s["hotkey"] == "Ctrl+Alt+Q"
          and not sw.s["notify"] and os.path.isfile(os.path.join(sw.apo.profiles, "EarPods.txt")), (n, rec))
    check("takeover: brought over once (a second time does nothing)", sw.bring_over(old, old_dir) == 0)
    check("takeover: an EQ file with a profile's contents counts as that profile (not offered again)",
          sw.has_profile_like(os.path.join(conf, "EarPods.txt")) and not sw.has_profile_like(os.path.join(conf, "Samson.txt")))
    off = sw.set_up_apo()
    check("takeover: setting up turns EQ Switcher's line off, so the two never both apply an EQ",
          off == ["Include: EQ Switcher\\switcher.txt"] and sw.apo.set_up(), off)


def qt_checks(top):
    from PySide6.QtWidgets import QApplication
    qapp = QApplication.instance() or QApplication([])
    from switcher import core
    from switcher import devices as D
    from ui import winsys
    from switcher.apo import Apo
    k = winsys.to_windows("Ctrl+Alt+E")
    check("hotkey: Ctrl+Alt+E as Windows takes it", k == (winsys.MOD_NOREPEAT | winsys.MOD_CONTROL | winsys.MOD_ALT, 0x45), k)
    check("hotkey: F13, Shift+Win+9, none", winsys.to_windows("F13") == (winsys.MOD_NOREPEAT, 0x7C)
          and winsys.to_windows("Shift+Meta+9") == (winsys.MOD_NOREPEAT | winsys.MOD_SHIFT | winsys.MOD_WIN, 0x39)
          and winsys.to_windows("") is None)
    check("hotkey: a typing key without Ctrl, Alt or Win refused (it would be taken from every program); F-keys and "
          "media keys alone are fine", [winsys.to_windows(t) for t in ("E", "Shift+E", "Space", "Down")] == [None] * 4
          and winsys.to_windows("Ctrl+Space") and winsys.to_windows("Media Play"))
    # (Windows registers a hotkey for a real window; the off-screen test window has none, so the key itself is tried:
    # a key nobody uses, registered for this thread, then let go)
    import ctypes
    k = winsys.to_windows("Ctrl+Alt+Shift+F24")
    ok = bool(ctypes.windll.user32.RegisterHotKey(None, 0xBEE, *k))
    check("hotkey: Windows takes the key as written", ok and ctypes.windll.user32.UnregisterHotKey(None, 0xBEE))
    from ui import forms
    check("settings boxes: lists read as AutoEQ Local reads them (\"4-10\", \"4, 6, 8\", ranges), and shown back",
          forms.parse_list("4-7", True) == [4, 5, 6, 7] and forms.parse_list("6, 4 4", True) == [4, 6]
          and forms.parse_list("1-99", True) is None and forms.parse_list("2.5, x", False) is None
          and forms.parse_ranges("-12..6, -10 to 20") == [[-12, 6], [-10, 20]] and forms.parse_ranges("6..-12") is None
          and forms.fmt_list([4, 5, 6, 7]) == "4-7" and forms.fmt_list([2, 3.5]) == "2, 3.5" and forms._num(5e-05) == "0.00005")
    L = forms.Limits({"a.0": {"min": 20, "max": 20000, "unit": "Hz"}, "a.1": {"min": 20, "max": 20000, "unit": "Hz"},
                      "n": {"min": 1, "max": 32, "int": True, "list": True}}, [("a.0", "a.1", True)])
    get = {"a.0": 100, "a.1": 1000}.get
    check("settings boxes: limits as AutoEQ Local's limits.js (range, whole numbers, a pair's order, clamping)",
          L.check("a.0", 10, get)[0] == "range" and L.check("n", [1.5], get)[0] == "range"
          and L.check("a.0", 1000, get)[0] == "pair" and L.check("a.1", 100, get)[0] == "pair" and L.check("a.0", 500, get) is None
          and L.clamp("n", [0, 40, 5]) == [1, 5, 32] and L.clamp("a.0", 5) == 20)
    check("start with Windows: the command runs the app's own Python without a console, in the tray",
          winsys.start_command().endswith('start.py" --tray')
          and any(n in winsys.start_command() for n in ("pythonw.exe", winsys.LAUNCHER)))
    # (Task Manager names a startup entry by its program's file: a copy of pythonw.exe called "AutoEQ Studio.exe";
    # made here in a temporary folder, not the app's environment)
    import filecmp
    pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    lt = tempfile.mkdtemp(prefix="autoeqstudio-launcher-")
    shutil.copy(pyw, lt)
    made = winsys.make_launcher(lt)
    cmd = f'"{made}" "{winsys.START}" --tray'
    check("start with Windows: listed as AutoEQ Studio (\"AutoEQ Studio.exe\", the same file as pythonw.exe); an "
          "older entry (by pythonw.exe) still counts as on, another program's or copy's doesn't",
          made == os.path.join(lt, "AutoEQ Studio.exe") and filecmp.cmp(pyw, made, shallow=False)
          and winsys.make_launcher(lt) == made and winsys.autostart_on(cmd)
          and winsys.autostart_on(f'"{pyw}" "{winsys.START}" --tray')
          and not winsys.autostart_on('"C:\\x\\pythonw.exe" "C:\\x\\start.py" --tray') and not winsys.autostart_on(""),
          made)
    shutil.rmtree(lt, ignore_errors=True)

    conf = fake_apo(top)
    eps = [D.Endpoint("{5}", "Headset", "EarPods", D.ACTIVE, False), D.Endpoint("{1}", "Headphones", "Buds", D.NOT_PRESENT, True)]
    sw = core.Switcher(os.path.join(top, "s.json"), Apo(conf), endpoints=lambda: eps, playing=lambda: "{5}")

    class Stub:  # (what the window asks of the app)
        hotkey_problem = ""
        said = []

        def tray_message(self, title, text):
            self.said.append(title)

        @staticmethod
        def autostart_on():
            return False

        def set_autostart(self, on):
            pass

        @staticmethod
        def set_offline(on):
            import net
            net.set_offline(on)

    from ui.window import SetUpDialog, Window
    sw.s["page"] = "devices"  # (the EQ screen has its own checks: eq_checks.py, on a copy)
    win = Window(sw, Stub())
    win.show()
    qapp.processEvents()
    check("window: the screens; the EQ screen isn't made (nor the EQ part loaded) until it's opened",
          [b.text() for b in win.nav.values()] == ["Make an EQ", "Devices", "Profiles", "Settings"]
          and win.page() == "devices" and win.eq_page is None and "eq" not in sys.modules and "pyqtgraph" not in sys.modules)
    import net
    win.online_btn.click()
    off = (net.offline(), win.online_btn.text(), win.chk_offline.isChecked())
    win.online_btn.click()
    check("window: Online / Offline at the top switches the whole app, and Settings shows it",
          off == (True, "○ Offline", True) and not net.offline() and win.online_btn.text() == "● Online", off)
    check("window: the banner asks to set APO up", win.banner.isVisible() and "isn't using" in win.banner_text.text())
    check("window: the device playing is chosen, and APO missing on it is said",
          win.selected == "Headset|EarPods" and any("isn't installed on this device" in w.text()
                                                     for w in win.dev_panel.findChildren(type(win.banner_text))))
    # (Set up takes over from EQ Switcher: stand-ins here, never this PC's Run key or a running EQ Switcher)
    names = ("eq_switcher_autostart", "eq_switcher_running", "eq_switcher_autostart_off", "eq_switcher_quit")
    real = {n: getattr(winsys, n) for n in names}
    done_es = []
    winsys.eq_switcher_autostart = winsys.eq_switcher_running = lambda: True
    winsys.eq_switcher_autostart_off = lambda: done_es.append("Start with Windows off")
    winsys.eq_switcher_quit = lambda wait=2.0: done_es.append("quit") or True
    try:
        dlg = SetUpDialog(sw, win)
        offered = (dlg.chk_es_auto is not None and dlg.chk_es_auto.isChecked(),
                   dlg.chk_es_quit is not None and dlg.chk_es_quit.isChecked())
        dlg._go()
    finally:
        for n in names:
            setattr(winsys, n, real[n])
    qapp.processEvents()
    rec = sw.record("Headset|EarPods")
    check("window: setting up adds config.txt's EQ files, the one on now becoming the playing device's",
          len(sw.profiles()) == 2 and [sw.profile_name(i) for i in rec["profiles"]] == ["EarPods"]
          and rec["active"] == rec["profiles"][0] and sw.apo.set_up() and not win.banner.isVisible(),
          (sw.profiles(), rec))
    check("window: Set up offers to turn off EQ Switcher's Start with Windows and to quit it (both ticked), and does "
          "both", offered == (True, True) and done_es == ["Start with Windows off", "quit"], (offered, done_es))
    # Is the EQ playing? Benchmark's answer (a stand-in for it here) on the device's line and, with Check again, said
    # in full
    from PySide6.QtWidgets import QMessageBox, QPushButton
    from switcher import check as apo_check
    win._checks.clear()
    chk = [b for b in win.dev_panel.findChildren(QPushButton) if b.text() == "Check again"]
    pfile = os.path.join(sw.apo.profiles, sw.profiles()[rec["active"]]["file"])
    real_run, real_info, real_warn = apo_check.run, QMessageBox.information, QMessageBox.warning
    told = []
    apo_check.run = lambda apo, guid, timeout=60: (told.append(guid), {
        "loaded": [apo.config_txt, os.path.join(apo.config, "AutoEQ Studio", "switcher.txt"), pfile],
        "matched": ["{5}"]})[1]
    QMessageBox.information = staticmethod(lambda *a, **k: told.append(("ok", a[2])))
    QMessageBox.warning = staticmethod(lambda *a, **k: told.append(("not", a[2])))
    try:
        if chk:
            chk[0].click()
            t0 = time.time()
            while len(told) < 2 and time.time() - t0 < 10:
                qapp.processEvents()
                time.sleep(0.02)
    finally:
        apo_check.run, QMessageBox.information, QMessageBox.warning = real_run, real_info, real_warn
    line = win.check_label.text() if win.check_label is not None else ""
    check("window: Check again asks APO for the device's endpoint and says all it found (its EQ applies, but APO "
          "isn't on the device); the device's line says it too",
          len(chk) == 1 and "{5}" in told and any(isinstance(x, tuple) and x[0] == "not" and "applies on this device"
                                                   in x[1] and "isn't installed on this device" in x[1] for x in told)
          and line.startswith("✕ Equalizer APO isn't installed on this device"), (told, line))
    # (APO's Configurator: DeviceSelector.exe in APO 1.3 and later, Configurator.exe before; only the old name was
    # looked for, so "Open APO's Configurator" never showed with a current APO)
    found = []
    for names in (["DeviceSelector.exe"], ["Configurator.exe"], ["DeviceSelector.exe", "Configurator.exe"], []):
        inst = tempfile.mkdtemp(prefix="autoeqstudio-apo-install-")
        for n in names:
            open(os.path.join(inst, n), "w").close()
        found.append(os.path.basename(Apo(conf, inst).configurator or ""))
        shutil.rmtree(inst, ignore_errors=True)
    check("APO's Configurator is found by its current name (DeviceSelector.exe) and its old one",
          found == ["DeviceSelector.exe", "Configurator.exe", "DeviceSelector.exe", ""], found)
    # (started as from its Start menu shortcut: in its own folder, without this app's Qt on PATH; it found our Qt
    # first and stopped with "no Qt platform plugin could be initialized")
    from ui import winsys
    real_path = os.environ.get("PATH", "")
    ours = os.path.join(sys.prefix, "Lib", "site-packages", "PySide6")
    other = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "System32")
    os.environ["PATH"] = os.pathsep.join([ours, other, real_path])
    given = os.environ["PATH"]
    exe = os.path.join(top, "EqualizerAPO", "DeviceSelector.exe")
    calls = []
    try:
        winsys.start_program(exe, opener=lambda path, cwd: calls.append((path, cwd, os.environ["PATH"])))
        after = os.environ["PATH"]
    finally:
        os.environ["PATH"] = real_path
    passed = calls[0][2].split(os.pathsep) if calls else []
    check("APO's Configurator starts in its own folder without this app's Qt on PATH (its own Qt is found); the app's "
          "PATH is as before after",
          calls and calls[0][:2] == (exe, os.path.dirname(exe)) and other in passed
          and not any(os.path.normcase(p).startswith(os.path.normcase(sys.prefix)) for p in passed) and after == given,
          calls)
    # the line asks by itself, once per change (the answer kept while nothing it depends on changes)
    asked = []
    apo_check.run = lambda apo, guid, timeout=60: (asked.append(guid), {"loaded": [], "matched": []})[1]
    try:
        win.render_device_panel()
        win.render_device_panel()
        qapp.processEvents()
        again = list(asked)
        win._checks.clear()
        win.render_device_panel()
        t0 = time.time()
        while not asked and time.time() - t0 < 10 or win._checking and time.time() - t0 < 10:
            qapp.processEvents()
            time.sleep(0.02)
    finally:
        apo_check.run = real_run
    check("window: the device's line isn't asked again while nothing changed; asked by itself after a change "
          "(✕: APO doesn't read AutoEQ Studio's file)", again == [] and asked == ["{5}"]
          and "✕" in win.check_label.text() and "doesn't read" in win.check_label.text(), (again, asked,
                                                                                         win.check_label.text()))
    # (the one-line answer kept a profile's name whole: "Truthear GATe (Diffuse field)" was cut at its bracket)
    from ui.window import check_line
    lines = [check_line(True, "“Truthear GATe (Diffuse field)” applies on this device: APO finds its section and "
                              "loads its file. config.txt also loads, on top: x.txt."),
             check_line(False, "AutoEQ Studio chose “A. B (C)”, but APO doesn't load its file for this device (the "
                               "file is missing from APO's folder)."),
             check_line(True, "AutoEQ Studio's EQ is off for this device (APO finds its section, with no EQ in it)."),
             check_line(None, "Couldn't ask Equalizer APO: Benchmark isn't there.")]
    check("window: the device's line keeps a profile's name whole (brackets, a full stop) and drops the rest",
          lines == ["“Truthear GATe (Diffuse field)” applies on this device.",
                    "AutoEQ Studio chose “A. B (C)”, but APO doesn't load its file for this device.",
                    "AutoEQ Studio's EQ is off for this device.", "Couldn't ask Equalizer APO"], lines)
    # (the EQ switched while APO is still being asked: the line is about the new one, not the one asked about)
    key = "Headset|EarPods"
    first = sw.record(key)["active"]
    other = next(p for p in sw.profiles() if p != first)
    sw.add_to_device(key, other, switch_on=False)
    asked = []

    def slow(apo, guid, timeout=60):
        pid = sw.record(key)["active"]
        asked.append(sw.profile_name(pid))
        time.sleep(0.4)
        return {"loaded": [apo.config_txt, os.path.join(apo.config, "AutoEQ Studio", "switcher.txt"),
                           os.path.join(apo.profiles, sw.profiles()[pid]["file"])], "matched": [guid]}
    apo_check.run = slow
    try:
        win._checks.clear()
        win.render_device_panel()
        t0 = time.time()
        while not asked and time.time() - t0 < 5:
            qapp.processEvents()
            time.sleep(0.02)
        sw.set_active(key, other)
        t0 = time.time()
        while (win._checking or key not in win._checks) and time.time() - t0 < 10:
            qapp.processEvents()
            time.sleep(0.02)
    finally:
        apo_check.run = real_run
    told = win.check_label.toolTip() if win.check_label is not None else ""  # (all of the answer; this test device
    # has no APO, so its short line says that)
    check("window: the EQ switched while APO is asked: it's asked again, and the answer is about the EQ on now",
          asked == [sw.profile_name(first), sw.profile_name(other)] and sw.profile_name(other) in told
          and sw.profile_name(first) not in told, (asked, told))
    sw.set_active(key, first)
    sw.remove_from_device(key, other)
    qapp.processEvents()
    # your name for a device: shown in the list, the panel and the tray; Windows' name kept; empty gives it back
    sw.set_nickname("Headset|EarPods", "  Dongle – KZ  ")
    win.render_all()
    item = win.dev_list.currentItem().text()
    kept = core.Switcher(os.path.join(top, "s.json"), Apo(conf), endpoints=lambda: eps, playing=lambda: "{5}")
    from switcher.core import shown
    named = (item.startswith("Dongle – KZ"), shown(sw.record("Headset|EarPods")),
             kept.record("Headset|EarPods").get("nickname"), sw.record("Headset|EarPods")["label"])
    sw.set_nickname("Headset|EarPods", "")
    check("window: a device's own name (Rename…) shown in the list, kept, Windows' name under it; empty: Windows' "
          "name again", named == (True, "Dongle – KZ", "Dongle – KZ", "Headset (EarPods)")
          and shown(sw.record("Headset|EarPods")) == "Headset (EarPods)", named)
    # trying an EQ: in APO's file for that device only, the bar says it, Keep it makes it a profile; a hand switch or
    # the time up ends it; a trial left by a crash is gone at the next start
    swt = os.path.join(conf, "AutoEQ Studio", "switcher.txt")
    before = sw.record("Headset|EarPods")["active"]
    sw.try_eq("Headset|EarPods", "Preamp: -3 dB\r\nFilter 1: ON PK Fc 1000 Hz Gain -3 dB Q 1\r\n", "Trial EQ", 5)
    win.render_trial()
    trying = (open(swt).read().count("_trying.txt"), win.trial_holder.isVisible() or not win.isVisible(),
              "Trial EQ" in win.trial_text.text(), win._status("Headset|EarPods")[1])
    leftover = core.Switcher(os.path.join(top, "s.json"), Apo(conf), endpoints=lambda: eps, playing=lambda: "{5}")
    after_crash = (os.path.exists(sw.trial_path()), "_trying" in open(swt).read())
    sw.try_eq("Headset|EarPods", "Preamp: -3 dB\r\nFilter 1: ON PK Fc 1000 Hz Gain -3 dB Q 1\r\n", "Trial EQ", 5)
    pid = sw.end_trial(keep=True)
    rec2 = sw.record("Headset|EarPods")
    kept_it = (sw.profile_name(pid), rec2["active"] == pid, sw.trial, os.path.exists(sw.trial_path()))
    sw.try_eq("Headset|EarPods", "Preamp: -1 dB\r\n", "Second", 5)
    sw.set_active("Headset|EarPods", before)
    by_hand = (sw.trial, "_trying" in open(swt).read(), rec2["active"] == before)
    sw.try_eq("Headset|EarPods", "Preamp: -1 dB\r\n", "Third", 5)
    sw.trial["until"] = 0
    from ui import app as app_mod
    app_mod.App.poll(type("A", (), {"sw": sw, "hotkey_problem": "", "end_trial": staticmethod(lambda keep=False: sw.end_trial(keep))})())
    check("devices: Try for 5 minutes plays the EQ on that device only (APO's file, the bar, the status), Keep it makes "
          "it a profile switched on; a hand switch or the time up ends it; one left by a crash is gone at the next start",
          trying == (1, True, True, "Trying: Trial EQ") and after_crash == (False, False) and leftover.trial is None
          and kept_it == ("Trial EQ", True, None, False) and by_hand == (None, False, True) and sw.trial is None
          and "_trying" not in open(swt).read(), (trying, after_crash, kept_it, by_hand, sw.trial))
    sw.remove_profile(pid)
    qapp.processEvents()
    from PySide6.QtWidgets import QRadioButton
    radios = [r for r in win.dev_panel.findChildren(QRadioButton) if r.isVisible()]
    check("window: the device's choices are Off and its profile, the profile on",
          [r.text() for r in radios] == ["Off", "EarPods"] and radios[1].isChecked(), [r.text() for r in radios])
    radios[0].setChecked(True)
    qapp.processEvents()
    check("window: choosing Off switches the EQ off", sw.record("Headset|EarPods")["active"] is None)
    check("window: one device panel at a time (the old one's parts are gone at once)",
          len([r for r in win.dev_panel.findChildren(QRadioButton) if r.parent() is not None and r.isVisible()]) == 2)
    sys.path.insert(0, os.path.join(APP, "tools"))
    import a11y
    gaps = {}
    for page_key in ("devices", "profiles", "settings"):
        win.show_page(page_key, remember=False)
        qapp.processEvents()
        u, r = a11y.unnamed(win), a11y.unreachable(win)
        if u or r:
            gaps[page_key] = ([f"{x[0]}:{x[1] or x[2][:16]}" for x in u], [f"{x[0]}:{x[1]}" for x in r])
    win.show_page("devices", remember=False)
    check("access: on Devices, Profiles and Settings every control has a name a screen reader reads, and Tab "
          "reaches it", not gaps, gaps)
    win.close()
    check("window: closing it leaves the app in the tray (said once)", not win.isVisible() and Stub.said and sw.s["told_tray"])
    win.render_all()
    check("window: the profiles list", win.prof_table.rowCount() == 2)
    # (review #28: starting hidden in the tray with Make an EQ as the saved screen doesn't make it, nor load numpy)
    sw.s["page"] = "eq"
    hidden = Window(sw, Stub())
    qapp.processEvents()
    check("window: starting hidden on Make an EQ makes the screen only when the window is shown (the tray stays light)",
          hidden.eq_page is None and getattr(hidden, "_eq_pending", False) and "eq" not in sys.modules
          and "numpy" not in sys.modules, (hidden.eq_page, "numpy" in sys.modules))
    sw.listeners.remove(hidden._changed)
    hidden.deleteLater()
    sw.s["page"] = "devices"
    # (review 2) Restore: nothing is saved between putting the backup back and the restart (Listen's and the tracer's
    # save on quit wrote the old settings over it); the devices' poll stops. Dialogs and the files are stand-ins.
    import backup
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QFileDialog, QMessageBox
    real = (QFileDialog.getOpenFileName, QMessageBox.question, QMessageBox.information, backup.read, backup.restore)
    seen, stub = [], win.app
    stub.timer = QTimer()
    stub.timer.start(60000)
    stub.restart = lambda: seen.append((sw.read_only, stub.timer.isActive()))
    QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: ("backup.zip", ""))
    QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.Yes)
    QMessageBox.information = staticmethod(lambda *a, **k: None)
    backup.read = lambda src: {"made": "today", "files": 1, "profiles": 0}
    backup.restore = lambda src, prof: {"files": 1, "kept": "kept.zip", "skipped": []}
    try:
        win.restore_backup()
    finally:
        QFileDialog.getOpenFileName, QMessageBox.question, QMessageBox.information, backup.read, backup.restore = real
        sw.read_only = False
        stub.timer.stop()
    check("window: after a restore nothing is saved over it before the restart (settings read-only, the poll stopped)",
          seen == [(True, False)], seen)
    help_checks()
    contrast_checks()


def benchmark_checks(top):
    """switcher\\check.py: Equalizer APO's Benchmark output read (the files it loads, the sections that match the
    device) and said in plain words, for each case."""
    from switcher import check as c
    from switcher.apo import Apo
    conf = os.path.join(top, "bench", "config")
    os.makedirs(os.path.join(conf, "AutoEQ Studio", "profiles"))
    apo = Apo(conf)
    ours = os.path.join(conf, "AutoEQ Studio", "switcher.txt")
    eq = os.path.join(conf, "AutoEQ Studio", "profiles", "My IEM.txt")
    other = os.path.join(conf, "Loudness.txt")
    out = "\n".join([f"12:00:00.001 (TRACE) Loading configuration from {apo.config_txt}",
                      '12:00:00.002 (TRACE) Matching pattern "all" with device ...',
                      f"12:00:00.003 (TRACE) Loading configuration from {other}",
                      f"12:00:00.004 (TRACE) Loading configuration from {ours}  ",
                      '12:00:00.005 (TRACE) Matching pattern "{5}; {6}" with device Headset',
                      f"12:00:00.006 (TRACE) Loading configuration from {eq}"])
    found = c.parse(out)
    check("check: Benchmark's lines read (the files loaded, the sections matched but \"all\")",
          found == {"loaded": [apo.config_txt, other, ours, eq], "matched": ["{5}; {6}"]}, found)
    applies = c.explain(apo, found, "My IEM", eq)
    off = c.explain(apo, dict(found, loaded=found["loaded"][:3]), None)
    not_ours = c.explain(apo, {"loaded": [apo.config_txt], "matched": []}, "My IEM", eq)
    no_section = c.explain(apo, {"loaded": [apo.config_txt, ours], "matched": []}, "My IEM", eq)
    missing = c.explain(apo, dict(found, loaded=found["loaded"][:3]), "My IEM", eq)
    no_apo = c.explain(apo, found, "My IEM", eq, apo_on_device=False)
    check("check: said plainly: the EQ applies (and what config.txt adds on top), off, config.txt without AutoEQ "
          "Studio's line, no section for the device, the EQ's file missing, APO not on the device",
          applies[0] and "“My IEM” applies" in applies[1] and "Loudness.txt" in applies[1]
          and off[0] and "off for this device" in off[1]
          and not not_ours[0] and "doesn't read AutoEQ Studio's file" in not_ours[1]
          and not no_section[0] and "no section" in no_section[1]
          and not missing[0] and "missing" in missing[1]
          and not no_apo[0] and "isn't installed" in no_apo[1], (applies, off, not_ours, no_section, missing, no_apo))
    raised = ""
    try:
        c.run(apo, "{5}")
    except OSError as e:
        raised = str(e)
    check("check: without APO's Benchmark tool, said (nothing run)", "Benchmark tool isn't there" in raised, raised)


def backup_checks(top):
    """backup.py: everything of yours in one .zip and back, in this test's own folders (never the real ones)."""
    import json
    import zipfile
    import backup
    import paths
    real_env = {k: os.environ.get(k) for k in ("AUTOEQSTUDIO_ROOT", "AUTOEQSTUDIO_DATA")}
    os.environ.update(AUTOEQSTUDIO_ROOT=top, AUTOEQSTUDIO_DATA=os.path.join(top, "data"))
    paths.locate()
    prof = os.path.join(top, "apo", "AutoEQ Studio", "profiles")
    files = {os.path.join(top, "data", "settings.json"): '{"profiles": {"a": 1}, "files_folder": "Z:/gone"}',
             os.path.join(top, "data", "eq", "history.json"): "[1]",
             os.path.join(top, "data", "app.log"): "log",
             os.path.join(top, "Targets", "T.csv"): "20 0",
             os.path.join(top, "Saved EQs", "My EQ.txt"): "Preamp: -3 dB",
             os.path.join(top, "downloads", "site", "M.txt"): "20 0",
             os.path.join(prof, "P.txt"): "Preamp: -1 dB", os.path.join(prof, "_trying.txt"): "Preamp: 0 dB",
             os.path.join(prof, "_Aux.txt"): "Preamp: -2 dB"}  # (a profile named Aux: Windows' reserved name, "_")
    try:
        for p, text in files.items():
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w") as fh:
                fh.write(text)
        z = os.path.join(top, "b.zip")
        info = backup.make(z, prof)
        names = sorted(zipfile.ZipFile(z).namelist())
        check("backup: one .zip of what's yours (settings, History, targets, saved EQs, the profiles' files; by the "
              "names backups have always had), not the log, downloads or a trial's file", names == ["apo-profiles/P.txt", "apo-profiles/_Aux.txt", "backup.json", "data/eq/history.json",
                                                             "data/settings.json", "inputs/target/T.csv",
                                                             "output/My EQ.txt"]
              and (info["files"], info["profiles"]) == (6, 2), names)
        with open(os.path.join(top, "data", "settings.json"), "w") as fh:
            fh.write('{"profiles": {}}')
        os.remove(os.path.join(top, "Targets", "T.csv"))
        os.remove(os.path.join(prof, "P.txt"))
        with open(os.path.join(top, "Targets", "New.csv"), "w") as fh:
            fh.write("20 1")
        got = backup.restore(z, prof, keep_dir=os.path.join(top, "kept"))
        back = (json.load(open(os.path.join(top, "data", "settings.json"))),
                os.path.isfile(os.path.join(top, "Targets", "T.csv")),
                os.path.isfile(os.path.join(top, "Targets", "New.csv")), os.path.isfile(os.path.join(prof, "P.txt")))
        kept = zipfile.ZipFile(got["kept"]).namelist()
        check("backup: restoring puts the files back (settings, a deleted target, a profile), keeps the others, and "
              "keeps how things were first; your files' folder stays this PC's (review 2)", back == ({"profiles": {"a": 1}}, True, True, True)
              and got["files"] == 6 and "inputs/target/New.csv" in kept, (back, got))
        # odd backups: not one, a newer one, names reaching outside its parts
        odd = os.path.join(top, "odd.zip")
        with zipfile.ZipFile(odd, "w") as zz:
            zz.writestr("backup.json", json.dumps({"app": "AutoEQ Studio", "format": 1, "made": "x", "files": 3,
                                                   "profiles": 0}))
            zz.writestr("../evil.txt", "x")
            zz.writestr("data/../../evil2.txt", "x")
            zz.writestr("data/other.json", "x")
            zz.writestr("inputs/target/Ok.csv", "20 0")
        r = backup.restore(odd, prof, keep_dir=os.path.join(top, "kept"))
        newer = os.path.join(top, "newer.zip")
        with zipfile.ZipFile(newer, "w") as zz:
            zz.writestr("backup.json", json.dumps({"app": "AutoEQ Studio", "format": 99}))
        said = []
        for bad in (os.path.join(top, "Targets", "Ok.csv"), newer):
            try:
                backup.read(bad)
            except ValueError as e:
                said.append(str(e))
        check("backup: a backup's odd names are never written outside its parts; a file that isn't a backup, or one "
              "from a newer AutoEQ Studio, is said", r["files"] == 1 and not os.path.exists(os.path.join(top, "..", "evil.txt"))
              and not os.path.exists(os.path.join(os.path.dirname(top), "evil2.txt"))
              and not os.path.exists(os.path.join(top, "data", "other.json")) and len(said) == 2
              and "isn't one of" in said[0] and "newer" in said[1], (r, said))
    finally:
        for k, v in real_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        paths.locate()


def userfiles_checks(top):
    """Your files' folder: Documents\\AutoEQ Studio by default (Targets, Measurements, Saved EQs, Presets), the folder
    chosen in Settings when there is one; moving them from an older copy's places and to a new folder never replaces
    a file; folders that can't hold them are said. A copy of the program with stand-in Documents (never the real one)."""
    import json
    import subprocess
    import paths
    import userfiles
    prog = os.path.dirname(_app_copy(os.path.join(top, "prog", "app")))
    env = {k: v for k, v in os.environ.items() if not k.startswith("AUTOEQSTUDIO_")}
    env.update(AUTOEQSTUDIO_DOCUMENTS=os.path.join(top, "docs"), QT_QPA_PLATFORM="offscreen")
    code = ("import sys, json; sys.path.insert(0, sys.argv[1]); import paths\n"
            "print(json.dumps([paths.ROOT, paths.TARGETS, paths.SAVED_EQS, paths.DATA]))")

    def where():
        out = subprocess.run([sys.executable, "-c", code, os.path.join(prog, "app")], capture_output=True, text=True,
                             env=env, timeout=60)
        try:
            return json.loads(out.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError):
            return out.stderr[-300:]
    first = where()
    os.makedirs(os.path.join(prog, "data"), exist_ok=True)
    with open(os.path.join(prog, "data", "settings.json"), "w", encoding="utf-8") as fh:
        json.dump({"profiles": {}, paths.FILES_KEY: os.path.join(top, "mine")}, fh)
    chosen = where()
    docs = os.path.join(top, "docs", "AutoEQ Studio")
    check("your files: Documents\\AutoEQ Studio by default (Targets, Saved EQs …; the app's data stays its own), the "
          "folder chosen in Settings when there is one",
          first == [docs, os.path.join(docs, "Targets"), os.path.join(docs, "Saved EQs"), os.path.join(prog, "data")]
          and chosen[:2] == [os.path.join(top, "mine"), os.path.join(top, "mine", "Targets")], (first, chosen))
    # moving: an older copy's inputs\target, output\ … into the folder; a different file of the same name kept as (2)
    real_env = {k: os.environ.get(k) for k in ("AUTOEQSTUDIO_ROOT", "AUTOEQSTUDIO_DATA")}
    os.environ.update(AUTOEQSTUDIO_ROOT=os.path.join(top, "files"), AUTOEQSTUDIO_DATA=os.path.join(top, "fdata"))
    paths.locate()
    try:
        old = os.path.join(top, "old")
        for rel, text in ((r"inputs\target\T.csv", "20 0"), (r"inputs\measurement\M L.txt", "20 1"),
                          (r"output\My EQ.txt", "Preamp: -3 dB"), (r"presets\P.json", "{}"),
                          (r"inputs\sources.json", '{"M L.txt": {"site": "Old"}, "T.csv": {"site": "Old"}}')):
            os.makedirs(os.path.dirname(os.path.join(old, rel)), exist_ok=True)
            with open(os.path.join(old, rel), "w", encoding="utf-8") as fh:
                fh.write(text)
        os.makedirs(paths.MEASUREMENTS)
        with open(os.path.join(paths.MEASUREMENTS, "M L.txt"), "w", encoding="utf-8") as fh:
            fh.write("20 9")  # (a different file of the same name: both kept)
        os.makedirs(paths.TARGETS)
        with open(os.path.join(paths.TARGETS, "T.csv"), "w", encoding="utf-8") as fh:
            fh.write("20 0")  # (the same file: not kept twice)
        os.makedirs(os.path.dirname(paths.SOURCES))
        with open(paths.SOURCES, "w", encoding="utf-8") as fh:
            json.dump({"T.csv": {"site": "Ours"}}, fh)
        pairs, sources = userfiles.old_places([old])
        n = userfiles.count(pairs)
        moved, renamed = userfiles.move_all(pairs, sources)
        have = sorted(os.path.relpath(os.path.join(d, f), paths.ROOT) for d, _s, fs in os.walk(paths.ROOT) for f in fs)
        recs = json.load(open(paths.SOURCES, encoding="utf-8"))
        check("your files: an older copy's targets, measurements, saved EQs and presets moved into their folders; a "
              "different file of the same name kept as (2), the same one not twice; the old records merged, ours first; "
              "the old folders gone", (n, moved, renamed) == (4, 3, 1) and have == [
                  os.path.join("Measurements", "M L (2).txt"), os.path.join("Measurements", "M L.txt"),
                  os.path.join("Presets", "P.json"), os.path.join("Saved EQs", "My EQ.txt"), os.path.join("Targets", "T.csv")]
              and recs == {"T.csv": {"site": "Ours"}, "M L.txt": {"site": "Old"}}
              and (not os.path.exists(old) or not os.listdir(old)), (n, moved, renamed, have, recs, os.listdir(old) if os.path.exists(old) else None))
        # (review 2: one folder reached by two paths, e.g. a mapped drive; here the same path: nothing removed)
        same = userfiles.move_tree(paths.TARGETS, paths.TARGETS)
        import _winapi
        link = os.path.join(top, "targets-link")
        _winapi.CreateJunction(paths.TARGETS, link)  # (the same folder by another path, as a mapped drive is)
        try:
            linked = userfiles.same_folder(link, paths.TARGETS)
            by_link = userfiles.move_tree(link, paths.TARGETS)
        finally:
            if os.path.lexists(link):  # (the junction only, if the move's tidy-up left it: its folder stays)
                os.rmdir(link)
        check("your files: moving a folder onto itself, or onto itself by another path (a junction), removes nothing",
              same == (0, 0) and by_link == (0, 0) and linked and os.path.isfile(os.path.join(paths.TARGETS, "T.csv")),
              (same, by_link, linked))
        # to a new folder; folders that can't hold them
        new = os.path.join(top, "elsewhere")
        pairs = userfiles.change_pairs(new)
        moved, renamed = userfiles.move_all(pairs)
        there = sorted(os.path.relpath(os.path.join(d, f), new) for d, _s, fs in os.walk(new) for f in fs)
        why = [userfiles.problem_with(p) for p in (os.path.join(paths.PROGRAM, "mine"), os.path.join(paths.TARGETS, "x"),
                                                    os.path.join(top, "fine"))]
        check("your files: Change… moves them all into the new folder's same folders; not into the program's folder "
              "or one of your files' own", (moved, renamed) == (5, 0) and len(there) == 5
              and "Targets" in {os.path.dirname(t) for t in there} and why[0] and "own folder" in why[0]
              and why[1] and "Targets" in why[1] and why[2] is None, (moved, renamed, there, why))
    finally:
        for k, v in real_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        paths.locate()


def contrast_checks():
    """Windows' contrast themes: the app's colours become Windows' own for it (here a stand-in set), white text on a
    button only where the theme says so; and back."""
    from PySide6.QtWidgets import QApplication
    from ui import theme
    qapp = QApplication.instance()
    hc = dict(theme.LIGHT, bg="#000000", card="#000000", ink="#ffffff", muted="#ffffff", field="#000000",
              btn="#1aebff", on_btn="#000000", on_sel="#000000", c1="#1aebff", sel="#1aebff")
    theme.apply(qapp, dark=False, contrast=hc)
    css, pal = qapp.styleSheet(), qapp.palette()
    on = (theme.tokens()["bg"], "color: #000000" in css and "#1aebff" in css,
          pal.color(pal.ColorRole.HighlightedText).name(), pal.color(pal.ColorRole.Window).name())
    theme.apply(qapp, dark=False, contrast=False)
    back = theme.tokens() is theme.LIGHT and "#1aebff" not in qapp.styleSheet()
    real = theme.system_tokens()
    check("contrast: with a Windows contrast theme on, the app takes its colours (window, text, highlight, the text "
          "on a highlighted button), and goes back after; this PC's theme colours are read",
          on == ("#000000", True, "#000000", "#000000") and back and all(v.startswith("#") and len(v) == 7
                                                                        for v in real.values()), (on, back))


def help_checks():
    """Help (ui\\help_window.py): its words told in AutoEQ Studio's controls, every link and F1 key found, the search."""
    import json
    import re
    from PySide6.QtWidgets import QCheckBox
    from ui import help_window as hw
    from ui.help_texts import WIKI
    words = json.dumps(WIKI, ensure_ascii=False)
    gone = [w for w in ("ⓘ", "(top bar)", "Match loudness", "AutoEQ Local", "Settings › Sources", "Settings › App",
                        "Adjust next to", '"id": "presets"') if w in words]
    check("help: its words name AutoEQ Studio's controls (no ⓘ, top bar, presets or browser of AutoEQ Local's page)",
          not gone, gone)
    by = hw._by_id()
    missing = [(e["id"], s) for e in by.values() for s in e.get("see") or [] if s not in by]
    keys = set()
    for name in os.listdir(os.path.join(APP, "ui")):
        if name.endswith(".py"):
            with open(os.path.join(APP, "ui", name), encoding="utf-8") as fh:
                keys |= set(re.findall(r'help_window\.tag\([^,]+, "([^"]+)"\)', fh.read()))
    unknown = sorted(k for k in keys if not hw.help_key(k))
    check("help: every “See also” opens an entry, and every control tagged for F1 has a help text",
          not missing and not unknown and len(keys) >= 10, (missing, unknown, len(keys)))
    w = hw.open_at()
    w.q.setText("rig conversion")
    found = w.toc.count()
    w.q.setText("zzzz qqqq")
    none = "Nothing matches" in w.view.toPlainText()
    w.q.setText("rig")
    w.go("set-best-fit-filter-counts")
    check("help: the search keeps the entries with every word; going to an entry clears a search that hid it and "
          "lights it", 0 < found < 15 and none and w.q.text() == "" and w.lit == "set-best-fit-filter-counts", (found, none))
    box = QCheckBox("x")
    hw.tag(box, "best_fit.filter_counts.1")
    check("help: F1 on a control opens its setting's entry (a “to” box: its “from” box's)",
          hw.entry_of_widget(box) == "set-best-fit-filter-counts" and "F1" in box.toolTip(), box.toolTip())
    w.close()


def file_checks():
    bad = []
    # (the program's files only: the main folder's own and app\\; not the user's inputs, output, downloads, releases)
    files = [os.path.join(ROOT, n) for n in os.listdir(ROOT) if os.path.isfile(os.path.join(ROOT, n))]
    for d, subs, names in os.walk(APP):
        subs[:] = [s for s in subs if s != "__pycache__"]
        files += [os.path.join(d, n) for n in names]
    for p in files:
        n = os.path.basename(p)
        if n.endswith((".py", ".md", ".txt", ".bat")):
            with open(p, "rb") as fh:
                raw = fh.read()
            if any(b < 32 and b not in (9, 10, 13) for b in raw):
                bad.append(n + ": a control character (a \\b or \\f written as one?)")
            if n.endswith(".bat") and raw.count(b"\n") != raw.count(b"\r\n"):
                bad.append(n + ": not CRLF")
    check("files: no control characters; the .bat files have CRLF line endings", not bad, bad)
    # (Claude Code reads .claude\CLAUDE.md and .claude\notes\WORKLOG.md with every request: they stay short, older
    # entries go to WORKLOG-archive.md; the user, 2026-10-14. Only on the developer's PC: git leaves .claude out)
    notes = {}
    for n, where in (("CLAUDE.md", (".claude",)), ("WORKLOG.md", (".claude", "notes"))):
        p = os.path.join(ROOT, *where, n)
        if os.path.isfile(p):
            with open(p, encoding="utf-8") as fh:
                notes[n] = fh.read()
    long = [f"{n}: {len(t.split())} words" for n, t in notes.items() if len(t.split()) > 1500]
    entries = notes.get("WORKLOG.md", "").count("\n## 20")
    if entries > 5:
        long.append(f"WORKLOG.md: {entries} entries (move the oldest to WORKLOG-archive.md)")
    check("files: CLAUDE.md and WORKLOG.md short (read with every request: 1,500 words at most, 5 entries)", not long,
          long)
    # (review #1: setup.bat moves the environment out of a main folder longer than 80 characters; the deepest file
    # in it must fit under Windows' 260-character limit below such a folder)
    venv = os.path.join(ROOT, ".venv")
    if os.path.isdir(venv):
        deepest = max((len(os.path.relpath(os.path.join(d, n), ROOT)) for d, _s, ns in os.walk(venv) for n in ns), default=0)
        check(f"setup: the deepest package file ({deepest} characters below the main folder) fits below an 80-character "
              "main folder", 81 + deepest <= 259, deepest)


def app_checks(top):
    """The App (ui\\app.py) in its own process, on a fake APO folder and data folder: EQ Switcher's profiles brought
    over on the first start, Offline kept for the next start."""
    import json
    import subprocess
    conf = fake_apo(top)
    old_dir = os.path.join(conf, "EQ Switcher", "profiles")
    os.makedirs(old_dir)
    with open(os.path.join(old_dir, "EarPods.txt"), "wb") as fh:
        fh.write(EARPODS)
    old = os.path.join(top, "eqswitcher.json")
    with open(old, "w") as fh:
        json.dump({"profiles": {"p1": {"name": "EarPods", "file": "EarPods.txt"}}, "devices": {}, "hotkey": ""}, fh)
    code = ("import sys; sys.path.insert(0, sys.argv[1])\n"
            "from PySide6.QtWidgets import QApplication\n"
            "qapp = QApplication([])\n"
            "import net\n"
            "from ui.app import App\n"
            "a = App(qapp, show=False)\n"
            "print('brought', a.brought, sorted(p['name'] for p in a.sw.s['profiles'].values()))\n"
            "a.set_offline(True)\n"
            "a.tray.hide(); a.win.close(); net.set_offline(False)\n"
            "b = App(qapp, show=False)\n"
            "print('offline', net.offline(), b.sw.s.get('offline'), b.brought)\n"
            "b.tray.hide()\n")
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", AUTOEQSTUDIO_APO_CONFIG=conf, AUTOEQSTUDIO_OLD_SETTINGS=old,
               AUTOEQSTUDIO_DATA=os.path.join(top, "data"), AUTOEQSTUDIO_ROOT=os.path.join(top, "root"))
    out = subprocess.run([sys.executable, "-c", code, APP], capture_output=True, text=True, env=env, timeout=120)
    lines = [l for l in out.stdout.strip().splitlines() if l.startswith(("brought ", "offline "))]
    check("app: the first start brings EQ Switcher's profiles over; Offline is kept for the next start",
          lines == ["brought 1 ['EarPods']", "offline True True 0"], lines or out.stderr[-400:])


def zip_checks(top):
    """The share zip (make_share_zip.py), made in a temporary folder: none of the user's files, every module the app
    loads, and the program starts from the unpacked copy (ui.app and eq.service import)."""
    import datetime
    import subprocess
    import zipfile
    sys.path.insert(0, TOOLS)
    import make_share_zip as mz
    entries = mz.plan(datetime.datetime(2026, 1, 1))
    names = [a for a, _ in entries]
    user = [a for a in names if os.path.basename(a) in mz.NEVER or a.split("/")[1] in ("output", "downloads", "presets")
            or "/.venv/" in a or "/tools/" in a]
    code_files = {os.path.relpath(os.path.join(d, n), ROOT).replace(os.sep, "/") for d, subs, ns in os.walk(APP)
                  for n in ns if n.endswith(".py") and "__pycache__" not in d and os.path.join(APP, "tools") not in d}
    missing = sorted(f for f in code_files if f"{mz.TOP}/{f}" not in names)
    out = os.path.join(top, "share.zip")
    mz.write(out, entries)
    zipfile.ZipFile(out).extractall(os.path.join(top, "unzipped"))
    app = os.path.join(top, "unzipped", mz.TOP, "app")
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", AUTOEQSTUDIO_DATA="", AUTOEQSTUDIO_ROOT="")
    env.pop("AUTOEQSTUDIO_DATA")
    env.pop("AUTOEQSTUDIO_ROOT")
    env["AUTOEQSTUDIO_DOCUMENTS"] = os.path.join(top, "docs")  # (stands in for Documents: never the real one)
    run = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, sys.argv[1]); import ui.app, eq.service, "
                          "eq.paths as p; print(p.ROOT); print(p.STUDIO_DATA)", app], capture_output=True, text=True,
                         env=env, timeout=120)
    where = [os.path.normcase(l) for l in run.stdout.strip().splitlines()[-2:]]
    check("share zip: none of the user's files, every module of the app; it loads from the unpacked copy, its data "
          "beside it and your files in Documents\\AutoEQ Studio", not user and not missing and run.returncode == 0
          and where == [os.path.normcase(os.path.join(top, "docs", "AutoEQ Studio")),
                        os.path.normcase(os.path.join(os.path.dirname(app), "data"))],
          (user[:3], missing[:3], where, run.stderr[-300:]))
    # the ready-to-run zip's own Python: what it holds (not made here: 120 MB; --check-runtime tests one unpacked)
    rt = [a for a, _ in mz.runtime_entries()]
    has = lambda end: any(a.endswith(end) for a in rt)
    bat = mz.READY_BAT
    check("ready-to-run zip: its Python (python, pythonw, the named launcher, Qt's widgets, numpy, SciPy, the sound "
          "card's library) without pip or Qt's QML; its launcher CRLF and guarding against too long a folder",
          all(has(e) for e in ("/runtime/python.exe", "/runtime/pythonw.exe", "/runtime/AutoEQ Studio.exe",
                               "/PySide6/QtWidgets.pyd", "/numpy/__init__.py", "/scipy/__init__.py",
                               "libportaudio64bit.dll"))
          and not any("/site-packages/pip/" in a or "/PySide6/qml/" in a for a in rt)
          and bat.count(b"\n") == bat.count(b"\r\n") and b"goto :toolong" in bat
          and "Nothing needs installing" in mz.ready_testing(open(os.path.join(TOOLS, "TESTING.txt"), encoding="utf-8").read()),
          len(rt))


def light_checks():
    """The tray stays light: the switching part and the window load neither the EQ part nor its maths (numpy, scipy)."""
    import subprocess
    code = ("import sys; sys.path.insert(0, sys.argv[1]); from switcher import core, apo, devices; from ui import window, "
            "icons, winsys; print(sorted(m for m in ('eq', 'numpy', 'scipy', 'py_mini_racer') if m in sys.modules))")
    out = subprocess.run([sys.executable, "-c", code, APP], capture_output=True, text=True,
                         env=dict(os.environ, QT_QPA_PLATFORM="offscreen"))
    check("light: the tray and window load neither the EQ part nor its maths", out.stdout.strip() == "[]",
          out.stdout.strip() or out.stderr[-300:])


def eq_checks():
    """The EQ part's checks (eq_checks.py: AutoEQ Local's, on a copy of this app), in their own process."""
    import subprocess
    out = subprocess.run([sys.executable, os.path.join(TOOLS, "eq_checks.py")], capture_output=True, text=True,
                         encoding="utf-8", errors="replace")
    lines = out.stdout.splitlines()
    for line in lines:
        if line.startswith("FAIL"):
            print(line)
    passed = sum(line.startswith("ok") for line in lines)
    check(f"eq part: {passed} checks of the EQ part: its maths, files and screens (eq_checks.py)", out.returncode == 0 and passed > 150,
          "; ".join(line for line in lines if line.startswith("FAIL"))[:500] or out.stderr[-500:])


def launcher_checks(top):
    """The installer's and ready-to-run zip's launcher (brand_exe.py): named AutoEQ Studio with the app's version
    (Task Manager's Startup apps said "Python"), Python's signature taken off (not left broken), and it still runs
    Python (beside Python's DLLs, its library found through PYTHONHOME)."""
    import subprocess
    sys.path.insert(0, TOOLS)
    import brand_exe
    import make_share_zip as mz
    import paths
    folder = os.path.join(top, "launcher")
    os.makedirs(folder)
    exe = os.path.join(folder, "AutoEQ Studio.exe")
    with open(exe, "wb") as fh:
        fh.write(mz.launcher())
    for n in os.listdir(sys.base_prefix):
        if n.lower().endswith(".dll"):
            shutil.copy2(os.path.join(sys.base_prefix, n), folder)
    said = os.path.join(folder, "ran.txt")
    run = subprocess.run([exe, "-c", f"open(r'{said}', 'w').write('ran')"], env=dict(os.environ, PYTHONHOME=sys.base_prefix),
                         timeout=60)
    info = brand_exe.describe(exe)
    signed = subprocess.run(["powershell", "-NoProfile", "-Command", f"(Get-AuthenticodeSignature '{exe}').Status"],
                            capture_output=True, text=True, timeout=60).stdout.strip()
    check("launcher: named AutoEQ Studio with the app's version, no broken signature, and it runs Python",
          info.get("FileDescription") == "AutoEQ Studio" and info.get("ProductName") == "AutoEQ Studio"
          and info.get("FileVersion") == paths.VERSION and signed == "NotSigned" and run.returncode == 0
          and os.path.isfile(said), (info, signed, run.returncode))


def lint_checks():
    """Ruff (the linter, ruff.toml beside app\\): unused and undefined names, likely bugs. Only in the development
    environment (it isn't part of the app): skipped, and said, without it."""
    import subprocess
    ruff = os.path.join(os.path.dirname(sys.executable), "ruff.exe")
    if not os.path.isfile(ruff):
        print("skip code: Ruff isn't installed here (\".venv\\Scripts\\python.exe -m pip install ruff\")")
        return
    out = subprocess.run([ruff, "check", "--quiet", APP], capture_output=True, text=True, cwd=ROOT, timeout=120)
    check("code: Ruff finds nothing (unused or undefined names, likely bugs)", out.returncode == 0,
          (out.stdout + out.stderr)[-600:])


def text_count(path, word):
    """How many times word is in a text file (0: no file)."""
    if not os.path.exists(path):
        return 0
    with open(path, encoding="utf-8") as fh:
        return fh.read().count(word)


def _app_copy(dest):
    """A copy of the program (not its tools): its own start.py, so nothing it does can match the user's copy (its Run
    entry is this copy's alone)."""
    shutil.copytree(APP, dest, ignore=shutil.ignore_patterns("__pycache__", "tools", "installed.txt"))
    return dest


def installed_checks(top):
    """Installed (app\\installed.txt): your files in Documents, settings and log in AppData\\Roaming, what can be
    fetched again in AppData\\Local, the samples in the program; nothing brought over from AutoEQ Local. Then the
    installer's --quit and --uninstall on a running copy (a fake APO folder: its line goes; the log's lines dated)."""
    import json
    import re
    import subprocess
    import time
    from switcher.apo import Apo
    inst = _app_copy(os.path.join(top, "inst", "app"))
    open(os.path.join(inst, "installed.txt"), "w").close()
    for rel in (r"first-start\Targets\T.txt", r"first-start\cache\databases.json"):  # (what the installer brings)
        os.makedirs(os.path.dirname(os.path.join(top, "inst", rel)), exist_ok=True)
        with open(os.path.join(top, "inst", rel), "w", encoding="utf-8") as fh:
            fh.write("seed")
    env = {k: v for k, v in os.environ.items() if not k.startswith("AUTOEQSTUDIO_")}
    env.update(APPDATA=os.path.join(top, "roam"), LOCALAPPDATA=os.path.join(top, "local"), QT_QPA_PLATFORM="offscreen",
               AUTOEQSTUDIO_DOCUMENTS=os.path.join(top, "docs"))
    code = ("import os, sys, json; sys.path.insert(0, sys.argv[1]); import paths, eq.paths as e, eq.bring_over as b\n"
            "paths.first_start()\n"
            "print(json.dumps({'installed': paths.INSTALLED, 'root': paths.ROOT, 'data': paths.DATA, 'log': paths.LOG,"
            " 'cache': e.CACHE, 'downloads': e.DOWNLOAD_DIR, 'samples': e.SAMPLES_DIR, 'targets': e.TARGET_DIR,"
            " 'eqdata': e.DATA, 'docs': paths._documents(), 'bring': b.default_source(), 'old': paths.old_app('EQ Switcher'),"
            " 'seeded': sorted(os.path.relpath(os.path.join(d, n), paths.ROOT) for d, _s, ns in os.walk(paths.ROOT) for n in ns),"
            " 'lists': os.path.isfile(os.path.join(e.CACHE, 'databases.json'))}))")
    out = subprocess.run([sys.executable, "-c", code, inst], capture_output=True, text=True, env=env, timeout=60)
    try:
        p = json.loads(out.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        p = {"error": out.stderr[-400:]}
    roam, local, prog = (os.path.join(top, d) for d in ("roam", "local", "inst"))
    want = {"installed": True, "root": os.path.join(p.get("docs") or "?", "AutoEQ Studio"),
            "data": os.path.join(roam, "AutoEQ Studio"), "log": os.path.join(roam, "AutoEQ Studio", "app.log"),
            "cache": os.path.join(local, "AutoEQ Studio", "cache"), "downloads": os.path.join(local, "AutoEQ Studio", "downloads"),
            "samples": os.path.join(prog, "samples"), "targets": os.path.join(p.get("docs") or "?", "AutoEQ Studio", "Targets"),
            "eqdata": os.path.join(roam, "AutoEQ Studio", "eq"), "bring": None, "old": os.path.join(top, "EQ Switcher"),
            "docs": os.path.join(top, "docs"), "seeded": [os.path.join("Targets", "T.txt")], "lists": True}
    wrong = {k: (p.get(k), v) for k, v in want.items() if p.get(k) != v}
    check("installed: your files in Documents, settings and log in AppData\\Roaming, downloads and caches in "
          "AppData\\Local, samples in the program; nothing brought over from the retired apps; the first start puts the sample curves and "
          "the database lists in place", not wrong, wrong)
    # (review 2) a test build (make_installer.py --test-build) never reaches the user's app, folders or APO
    with open(os.path.join(inst, "test-build.txt"), "w") as fh:
        fh.write("test")
    code = ("import sys, json; sys.path.insert(0, sys.argv[1]); import paths, start\n"
            "print(json.dumps([paths.DATA, paths.ROOT, list(paths.apo_folders()), start.SERVER, start.MUTEX]))")
    out = subprocess.run([sys.executable, "-c", code, inst], capture_output=True, text=True, env=env, timeout=60)
    try:
        t = json.loads(out.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        t = [out.stderr[-400:]]
    check("installed: a test build has its own folders, running channel and mutex, and no Equalizer APO unless a test "
          "folder is given", len(t) == 5 and t[0] == os.path.join(roam, "AutoEQ Studio (test)")
          and t[1] == os.path.join(top, "docs", "AutoEQ Studio (test)") and t[2] == [None, None]
          and "-test" in t[3] and t[4] == "AutoEQStudioRunning-test", t)
    os.remove(os.path.join(inst, "test-build.txt"))
    # --quit and --uninstall, as the installer runs them (a copy of the program, not installed: test folders)
    run_app = _app_copy(os.path.join(top, "run", "app"))
    conf = fake_apo(os.path.join(top, "run"))
    Apo(conf).install_line()
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", AUTOEQSTUDIO_APO_CONFIG=conf,
               AUTOEQSTUDIO_OLD_SETTINGS=os.path.join(top, "none.json"),
               AUTOEQSTUDIO_DATA=os.path.join(top, "run", "data"), AUTOEQSTUDIO_ROOT=os.path.join(top, "run", "root"))
    start = os.path.join(run_app, "start.py")
    log = os.path.join(top, "run", "data", "app.log")
    running = subprocess.Popen([sys.executable, start, "--tray"], env=env, stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
    t = time.time()
    while time.time() - t < 60 and not (os.path.exists(log) and "started" in open(log, encoding="utf-8").read()):
        time.sleep(0.2)
    second = subprocess.run([sys.executable, start, "--tray"], env=env, capture_output=True, text=True, timeout=60)
    check("one copy: starting it again shows the running one and ends; the first keeps running (review 2)",
          second.returncode == 0 and running.poll() is None and text_count(log, "started") == 1,
          (second.returncode, running.poll(), second.stderr[-300:]))
    un = subprocess.run([sys.executable, start, "--uninstall"], env=env, capture_output=True, text=True, timeout=60)
    try:
        ended = running.wait(20) is not None
    except subprocess.TimeoutExpired:
        running.kill()
        ended = False
    text = open(log, encoding="utf-8").read() if os.path.exists(log) else ""
    lines = [l for l in text.splitlines() if l.strip()]
    dated = bool(lines) and all(re.match(r"\d{4}-\d\d-\d\d \d\d:\d\d:\d\d  ", l) for l in lines)
    check("installer: --uninstall makes the running copy quit and takes AutoEQ Studio out of APO's config.txt; the "
          "log's every line has its date and time", un.returncode == 0 and ended and not Apo(conf).set_up() and dated,
          (un.returncode, ended, Apo(conf).set_up(), lines[-4:], un.stderr[-300:]))
    none = subprocess.run([sys.executable, start, "--quit"], env=env, capture_output=True, text=True, timeout=60)
    check("installer: --quit with nothing running ends at once, without an error", none.returncode == 0,
          (none.returncode, none.stderr[-300:]))
    # (review 2) the restart after a restore: the new copy (--restarted) waits for the old one to quit, then starts
    def wait_started(n, secs=60):
        t0 = time.time()
        while time.time() - t0 < secs and text_count(log, "started") < n:
            time.sleep(0.2)
        return text_count(log, "started") >= n
    before = text_count(log, "started")
    old = subprocess.Popen([sys.executable, start, "--tray"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    first = wait_started(before + 1)
    new = subprocess.Popen([sys.executable, start, "--restarted", "--tray"], env=env, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)
    time.sleep(3)
    waited = new.poll() is None and text_count(log, "started") == before + 1  # (still waiting: not started yet)
    subprocess.run([sys.executable, start, "--quit"], env=env, capture_output=True, timeout=60)  # (the old one quits)
    then = wait_started(before + 2)
    old_gone = old.poll() is not None
    subprocess.run([sys.executable, start, "--quit"], env=env, capture_output=True, timeout=60)
    for p in (old, new):
        try:
            p.wait(20)
        except subprocess.TimeoutExpired:
            p.kill()
    check("restart: the copy started by a restore waits for the old one to quit, then starts (one copy at a time)",
          first and waited and then and old_gone, (first, waited, then, old_gone))
    # (review 2) --uninstall turns off this copy's Start with Windows (the Run key: a stand-in, never the real one)
    import start as start_mod
    from ui import winsys
    turned = []
    real = (winsys.autostart_on, winsys.set_autostart, start_mod.paths.apo_folders)
    winsys.autostart_on = lambda value=None: True
    winsys.set_autostart = lambda on: turned.append(on)
    start_mod.paths.apo_folders = lambda: (None, None)
    try:
        start_mod.uninstall()
    finally:
        winsys.autostart_on, winsys.set_autostart, start_mod.paths.apo_folders = real
    check("installer: --uninstall turns this copy's Start with Windows off", turned == [False], turned)
    # (review 2) installer.iss compiles, the real build and the test build (a tiny stand-in program: seconds)
    sys.path.insert(0, TOOLS)
    import brand_exe
    import make_installer
    iscc = next((p for p in make_installer.ISCC if os.path.isfile(p)), None)
    if not iscc:
        print("skip installer: Inno Setup 6 isn't installed here")
        return
    stage = os.path.join(top, "iss", "stage")
    os.makedirs(stage)
    brand_exe.icon_file(os.path.join(stage, "AutoEQ Studio.ico"))
    with open(os.path.join(stage, "readme.txt"), "w") as fh:
        fh.write("stand-in")
    bad = []
    for extra in ([], ["/DTestBuild"]):
        r = subprocess.run([iscc, "/Q", *extra, "/DAppVersion=0.0.0", f"/DStage={stage}",
                            f"/DOutDir={os.path.join(top, 'iss', 'out')}", os.path.join(TOOLS, "installer.iss")],
                           capture_output=True, text=True, timeout=300)
        if r.returncode:
            bad.append(((extra or ["real"])[0], (r.stdout + r.stderr)[-400:]))
    check("installer: installer.iss compiles (the real build and the test build)", not bad, bad)


def main():
    # (UTF-8 whatever the console: check names have characters like ⓘ and →, which Windows' console code page lacks)
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    top = tempfile.mkdtemp(prefix="autoeqstudio-selftest-")
    # (the EQ part, if anything here opens it, works in the test's folders: never the real ones)
    os.environ.update(AUTOEQSTUDIO_ROOT=os.path.join(top, "studio"), AUTOEQSTUDIO_DATA=os.path.join(top, "studio", "data"))
    try:
        eqfile_checks()
        device_checks()
        for i, part in enumerate((apo_checks, core_checks, takeover_checks, qt_checks, benchmark_checks, backup_checks)):
            sub = os.path.join(top, str(i))
            os.makedirs(sub)
            part(sub)
        file_checks()
        lint_checks()
        light_checks()
        for part, name in ((app_checks, "app"), (zip_checks, "zip"), (launcher_checks, "launcher"),
                           (installed_checks, "installed"),
                           (userfiles_checks, "userfiles")):
            sub = os.path.join(top, name)
            os.makedirs(sub)
            part(sub)
        if "--quick" not in sys.argv:  # (the EQ part's: about a minute)
            eq_checks()
    finally:
        shutil.rmtree(top, ignore_errors=True)
    print("\nAll checks passed." if not FAILS else f"\n{len(FAILS)} check(s) failed.")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
