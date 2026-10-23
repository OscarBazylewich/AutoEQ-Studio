"""Make an EQ's shared names and small helpers: ui/eq_page.py and its parts use them, and FORMAT_NAMES, MODE_SHORT,
MODE_HINT, TICKS and file_base_name still import from ui/eq_page.py too.
- FORMAT_NAMES: the files Save filters can write, by key; MODE_SHORT: each method's short name; MODE_HINT: the line
  beside Method; TICKS: the graph's frequencies
- label(text, role, wrap): a label, in one of the theme's text roles; hz(v): a frequency in Hz or kHz
- file_base_name(...): a saved EQ's name, "<IEM> to <target> - <layout or method> <n>f"
- Notices: a message from a worker thread, said on the window's thread; modal(dlg): a window over the page until it's
  closed
"""
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QLabel

from ui import theme


FORMAT_NAMES = {"apo": "Equalizer APO / squiglink (.txt)", "graphic": "GraphicEQ for Wavelet (.txt)",
                "poweramp": "Poweramp (.json)", "uapp": "USB Audio Player PRO (.xml)", "soundsource": "SoundSource (.txt)",
                "voicemeeter": "Voicemeeter (.xml)", "rockbox": "Rockbox (.cfg)", "convolution": "impulse response (.wav)",
                "report": "a report (.html)"}  # (AutoEQ Local's export.js)
MODE_SHORT = {"site_single": "Website AutoEQ", "site_sweep": "Website sweep", "best_fit": "Best fit"}
MODE_HINT = {"best_fit": "For EQ apps and devices: the closest match", "site_sweep": "For the squiglink / listener800 website",
             "site_single": "Checks one set of website values"}
TICKS = [20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000]


def label(text="", role=None, wrap=True):
    lab = QLabel(text)
    lab.setWordWrap(wrap)
    if role:
        theme.mark(lab, role=role)
    return lab


def hz(v):
    return f"{v / 1000:g} kHz" if v >= 1000 else f"{v:g} Hz"


def file_base_name(device, target, layout_name, mode, n):
    """"<IEM> to <target> - <layout or method> <n>f" (AutoEQ Local's export.js fileBaseName)."""
    what = layout_name.replace(" / ", ", ") if layout_name else {"site_single": "site AutoEQ", "site_sweep": "site AutoEQ",
                                                                 "best_fit": "best fit"}.get(mode, "EQ")
    return f"{device} to {target} - {what} {n}f"


class Notices(QObject):
    """A message from a worker thread, said on the window's thread (a queued signal)."""
    said = Signal(str)


def modal(dlg):
    """A window over the page until it's closed, then let go (each kept all its rows for the rest of the session)."""
    dlg.exec()
    dlg.deleteLater()
