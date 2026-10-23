"""The app's icons, drawn here (no image files): three EQ sliders on a rounded square, blue when an EQ is on for the
device playing, grey when it's off. Also the small dots in the device list (playing, connected, not connected), and
Windows 11's own symbols beside a button's words (put(button, name): from Windows' icon font, Segoe Fluent Icons, or
Segoe MDL2 Assets on Windows 10; in the theme's text colour, the accent's text colour on the accent, drawn again when
the theme changes). GLYPHS names them."""
from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap

# Windows 11's symbols by name (their places in Segoe Fluent Icons; most are in Segoe MDL2 Assets too)
GLYPHS = {"eq": "E9E9", "devices": "E7F6", "profiles": "E8FD", "settings": "E713", "guide": "E82F", "help": "E9CE",
          "online": "E774", "run": "E768", "play": "E768", "pause": "E769", "stop": "E71A", "find": "E721",
          "add": "E710", "save": "E74E", "rename": "E8AC", "folder": "E838", "change_folder": "E8B7",
          "new_folder": "E8F4", "backup": "EDE1", "restore": "E8B5", "remove": "E74D", "delete": "E74D",
          "close": "E711", "cancel": "E711", "ok": "E8FB", "check": "E73E", "refresh": "E72C", "sync": "E895",
          "history": "E81C", "list": "E8FD", "listen": "E767", "volume": "E767", "mute": "E74F", "mic": "E720",
          "presets": "E8F1", "compare": "E8C8", "copy": "E8C8", "speaker": "E7F5", "headphones": "E7F6",
          "info": "E946", "warning": "E7BA", "error": "E783", "edit": "E70F", "pen": "EDC6", "erase": "E75C",
          "trace": "E70F", "file": "E7C3", "open": "E8E5", "open_new": "E8A7", "import": "E8B5", "export": "EDE1",
          "download": "E896", "upload": "E898", "share": "E72D", "print": "E749", "web": "E774", "link": "E71B",
          "undo": "E7A7", "redo": "E7A6", "back": "E72B", "forward": "E72A", "up": "E74A", "down": "E74B",
          "chevron_down": "E70D", "chevron_up": "E70E", "chevron_left": "E76B", "chevron_right": "E76C",
          "zoom_in": "E8A3", "zoom_out": "E71F", "fit": "E9A6", "filter": "E71C", "sort": "E8CB", "more": "E712",
          "lock": "E72E", "unlock": "E785", "pin": "E718", "unpin": "E77A", "favourite": "E734", "view": "E890",
          "hide": "ED1A", "image": "EB9F", "colour": "E790", "ruler": "ECC6", "move": "E7C2", "crop": "E7A8",
          "chart": "E9D9", "report": "E9F9", "select": "E8B3", "clock": "E823", "calendar": "E787", "tag": "E8EC",
          "tools": "E90F"}
_shown = []  # ((button, name)): the symbols shown, one per button, drawn again when the theme changes
_told = []  # (not empty once the theme tells put()'s symbols of a change: asked once)


def glyph(name, colour, size=16, on_colour=None, off_colour=None):
    """Windows 11's symbol `name` (GLYPHS) as an icon in a colour (on_colour: when its button is checked; off_colour:
    when it's unavailable), with room after it so the words beside it don't touch it."""
    from PySide6.QtGui import QFont, QFontDatabase
    family = "Segoe Fluent Icons" if "Segoe Fluent Icons" in QFontDatabase.families() else "Segoe MDL2 Assets"
    icon = QIcon()

    def pixmap(c):
        pm = QPixmap((size + 6) * 2, size * 2)  # (drawn at twice the size: sharp at 125 % and 150 %)
        pm.setDevicePixelRatio(2)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        f = QFont(family)
        f.setPixelSize(size)
        p.setFont(f)
        p.setPen(QColor(c))
        p.drawText(QRectF(0, 0, size, size), Qt.AlignCenter, chr(int(GLYPHS[name], 16)))
        p.end()
        return pm
    icon.addPixmap(pixmap(colour), QIcon.Normal, QIcon.Off)
    icon.addPixmap(pixmap(on_colour or colour), QIcon.Normal, QIcon.On)
    icon.addPixmap(pixmap(off_colour or colour), QIcon.Disabled, QIcon.Off)
    return icon


def put(button, name):
    """Windows 11's symbol `name` beside the button's words (they stay as they are), in the theme's colours: the
    text's, or the accent's text colour on a main action or a checked button; kept so when the theme changes. A
    button given another symbol keeps only the new one (Listen's Play and Stop), and buttons that are gone are let
    go of here as well (the device panel makes its buttons again on each change), not only when the theme changes."""
    import weakref
    from ui import theme
    if not _told:
        _told.append(True)
        theme.on_change(_redraw)
    _shown[:] = [(ref, n) for ref, n in _shown if _alive(ref) and ref() is not button]
    _shown.append((weakref.ref(button), name))  # (held weakly: a symbol never keeps its button)
    _draw(button, name)


def _alive(ref):
    import shiboken6
    b = ref()
    return b is not None and shiboken6.isValid(b)


def _draw(button, name):
    from ui import theme
    t = theme.tokens()
    primary = button.property("primary") in (True, "true")
    plain = button.property("nav") in (True, "true")  # (the top bar's: never filled when checked)
    button.setIcon(glyph(name, t["on_accent"] if primary else t["ink"], on_colour=t["ink"] if plain else t["on_accent"],
                         off_colour=t["on_accent_disabled"] if primary else t["disabled"]))
    button.setIconSize(QSize(22, 16))


def _redraw():
    for ref, name in list(_shown):
        if _alive(ref):
            _draw(ref(), name)
        else:
            _shown.remove((ref, name))

ON, OFF = QColor("#2f6fde"), QColor("#7a7f87")
DOTS = {"playing": QColor("#1f9d55"), "connected": QColor("#2f6fde"), "away": QColor("#9aa0a6")}


def _sliders(size, colour):
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(colour)
    p.drawRoundedRect(QRectF(0, 0, size, size), size * 0.22, size * 0.22)
    line = QPen(QColor("white"), max(1.0, size * 0.08), Qt.SolidLine, Qt.RoundCap)
    knob = size * 0.13
    for i, level in enumerate((0.62, 0.32, 0.52)):  # (three sliders at different heights)
        x = size * (0.28 + 0.22 * i)
        p.setPen(line)
        p.drawLine(QPointF(x, size * 0.2), QPointF(x, size * 0.8))
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("white"))
        p.drawEllipse(QRectF(x - knob, size * (0.2 + 0.6 * level) - knob, knob * 2, knob * 2))
        p.setBrush(colour)
    p.end()
    return pm


def app_icon(on=True):
    icon = QIcon()
    for s in (16, 20, 24, 32, 40, 48, 64, 128, 256):
        icon.addPixmap(_sliders(s, ON if on else OFF))
    return icon


def dot(kind, size=12):
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(DOTS[kind])
    p.drawEllipse(QRectF(2, 2, size - 4, size - 4))
    p.end()
    return QIcon(pm)
