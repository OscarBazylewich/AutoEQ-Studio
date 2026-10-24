"""Make an EQ's code loaded ahead, off the window's thread (2026-10-24: the click imported it on the window's thread
and froze the window for 0.5-2 s). The window's thread is the only one that calls these.

start(delay_ms)   begin (again: nothing more), after delay_ms
ready()           the screen's code is imported (or its import failed: error())
error()           the exception its import ended with (the window then imports on its own thread, as before, so
                  the error shows as it did)
when_ready(fn)    fn() on the window's thread once ready (at once when it is)
hold(), release() pause and resume the background import between modules while the window's thread builds the
                  screen (Python's lock shared with it made each build step about twice as long); release() for each
                  hold()

(Its first version: the API only, each call doing nothing, so Make an EQ's build can hold and release it.)
"""

_state = {"held": 0}


def start(delay_ms=0):
    return None


def ready():
    return False


def error():
    return None


def when_ready(fn):
    return None


def hold():
    _state["held"] += 1


def release():
    _state["held"] = max(0, _state["held"] - 1)
