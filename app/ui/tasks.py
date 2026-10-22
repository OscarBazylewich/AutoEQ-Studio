"""Slow work off the window's thread: background(fn, done) runs fn() in a worker thread and calls done(result, error)
back on the window's thread, so the window never freezes (loading curves, the maths' first import, saving).
A run itself has its own thread in eq.service (/api/run); the window only asks how it's going."""
import traceback

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

_alive = set()  # (each task's messenger, until it has answered: Qt would drop it otherwise)


class _Messenger(QObject):
    finished = Signal(object, object)


class _Job(QRunnable):
    def __init__(self, fn, messenger):
        super().__init__()
        self.fn, self.messenger = fn, messenger

    def run(self):
        try:
            res, err = self.fn(), None
        except Exception as e:  # noqa: BLE001 - handed to done()
            traceback.print_exc()
            res, err = None, e
        try:
            self.messenger.finished.emit(res, err)
        except RuntimeError:  # (the app has quit meanwhile: nobody to answer)
            pass


def alive(obj):
    """Is a Qt object still there (a window closed with deleteLater is gone)?"""
    import shiboken6
    return shiboken6.isValid(obj)


def background(fn, done, owner=None):
    """owner: a window the answer is for; once it's gone (closed and deleted) done isn't called."""
    m = _Messenger()
    _alive.add(m)

    def finish(res, err):
        _alive.discard(m)
        if owner is not None and not alive(owner):
            return
        done(res, err)
    m.finished.connect(finish)
    QThreadPool.globalInstance().start(_Job(fn, m))
