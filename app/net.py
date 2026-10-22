"""Online or offline: one switch for the whole app (the top bar's Online / Offline, saved in data\\settings.json).

Offline, AutoEQ Studio never connects to the internet: no database lists, no downloads, no looking things up. It uses
only what's on this PC (your files, curves downloaded before, the lists it has). Online, it does both. Every connection
the app makes goes through check() first (eq\\databases.py's _get is the one place it downloads), so nothing can slip
past the switch; a link you click to a website (e.g. Equalizer APO's) is turned off too while offline.
"""
_state = {"offline": False}
_listeners = []


class Offline(OSError):
    """Something needed the internet while the app is offline (the message says what to do)."""


def offline():
    return _state["offline"]


def set_offline(on):
    on = bool(on)
    if on != _state["offline"]:
        _state["offline"] = on
        for fn in list(_listeners):
            try:
                fn(on)
            except RuntimeError as e:  # (a window that's gone: Qt says "already deleted"; it's let go)
                if "already deleted" not in str(e):
                    raise
                _listeners.remove(fn)


def on_change(fn):
    """fn(offline) is called whenever the switch changes."""
    _listeners.append(fn)


def check(what="That"):
    """Raise Offline when the app is offline: call before any connection."""
    if _state["offline"]:
        raise Offline(f"{what} needs the internet, and AutoEQ Studio is offline. Switch to Online (top right) to do it.")
