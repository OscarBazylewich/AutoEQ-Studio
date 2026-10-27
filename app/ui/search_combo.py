"""Long lists made easy to find things in: natural_key() sorts names A to Z with numbers in number order ("IEM 2"
before "IEM 10", capitals and small letters together), and SearchCombo is a drop-down whose list opens with a search
box at its top when it holds more than SEARCH_FROM choices (type part of a name: only the rows with every word stay;
↑ ↓ and Enter choose, Esc closes); a shorter list opens as any drop-down.

SearchCombo is a QComboBox (addItem, findData, setCurrentIndex, currentData and activated work as usual): only its
long list is its own. Every drop-down in the app is one (the user's ask, 2026-10-13: a list over some number of
choices gets the search box, as Find…'s filters had; Advanced's Layout was the one asked for), and each is A to Z
(sort_items, where it's filled; the user's ask too).

Both lists, short and long, look alike (the theme's inputs part, ui\\theme_sheet.py): the short one is Qt's own
list, which draws that look itself (the frame Qt keeps it in has its own frame turned off), the long one is
#searchPopup, and their rows are drawn as the theme's list rows (the chosen one filled, the accent's bar beside it;
Qt's own drawing for a drop-down's rows only outlined it). (Qt never lets the app's stylesheet style a frame whose
parent is a drop-down: #searchPopup is a plain widget for that; as a frame it needed a stylesheet of its own.)
"""
import re

from PySide6.QtCore import QEvent, QPoint, Qt
from PySide6.QtWidgets import (QComboBox, QFrame, QLineEdit, QListWidget, QListWidgetItem, QStyledItemDelegate,
                               QVBoxLayout, QWidget)


SEARCH_FROM = 15  # a list with more choices than this opens with the search box (one screen of rows, about)


def natural_key(s):
    """A sort key: case-insensitive, the numbers in a name compared as numbers (decimals too: 0.42 before 0.5, 0.707
    before 0.8), runs of spaces as one."""
    parts = re.split(r"(\d+(?:\.\d+)?)", " ".join(str(s).casefold().split()))
    return [float(t) if i % 2 else t for i, t in enumerate(parts)]


class _Popup(QWidget):
    def __init__(self, combo):
        super().__init__(combo, Qt.Popup)
        self.combo = combo
        self.setObjectName("searchPopup")  # (its look: the theme's, as the short list's)
        self.setAttribute(Qt.WA_StyledBackground, True)  # (its background and border drawn from the theme's rule)
        v = QVBoxLayout(self)
        v.setContentsMargins(6, 6, 6, 6)
        v.setSpacing(4)
        self.q = QLineEdit()
        self.q.setPlaceholderText("Search…")
        self.q.setAccessibleName(f"Search {combo.accessibleName() or 'the list'}")
        self.q.setClearButtonEnabled(True)
        self.q.textChanged.connect(self.filter)
        self.q.installEventFilter(self)
        v.addWidget(self.q)
        self.list = QListWidget()
        self.list.setAccessibleName(combo.accessibleName() or "Choices")
        self.list.itemClicked.connect(self.choose)
        self.list.itemActivated.connect(self.choose)
        v.addWidget(self.list)
        self.none = QListWidgetItem("Nothing matches")
        self.none.setFlags(Qt.NoItemFlags)

    def fill(self):
        self.list.clear()
        self.none = QListWidgetItem("Nothing matches")
        self.none.setFlags(Qt.NoItemFlags)
        c = self.combo
        for i in range(c.count()):
            it = QListWidgetItem(c.itemText(i))
            it.setData(Qt.UserRole, i)
            self.list.addItem(it)
            if i == c.currentIndex():
                self.list.setCurrentItem(it)
        self.list.addItem(self.none)
        self.q.clear()
        self.filter("")

    def rows(self):
        return [self.list.item(k) for k in range(self.list.count()) if self.list.item(k) is not self.none]

    def filter(self, text):
        words = text.casefold().split()
        first = None
        for it in self.rows():
            ok = all(w in it.text().casefold() for w in words)
            it.setHidden(not ok)
            if ok and first is None:
                first = it
        self.none.setHidden(first is not None)
        cur = self.list.currentItem()
        if cur is None or cur.isHidden() or cur is self.none:
            self.list.setCurrentItem(first)
        if self.list.currentItem() is not None:
            self.list.scrollToItem(self.list.currentItem())

    def choose(self, it):
        i = it.data(Qt.UserRole) if it is not None else None
        if i is None:
            return
        self.hide()
        c = self.combo
        c.setCurrentIndex(i)
        c.activated.emit(i)

    def eventFilter(self, obj, e):
        """In the search box: ↑ ↓ move through what's shown, Enter chooses, Esc closes."""
        if obj is self.q and e.type() == QEvent.KeyPress:
            k = e.key()
            if k in (Qt.Key_Down, Qt.Key_Up, Qt.Key_PageDown, Qt.Key_PageUp):
                shown = [it for it in self.rows() if not it.isHidden()]
                if shown:
                    cur = self.list.currentItem()
                    n = shown.index(cur) if cur in shown else -1
                    step = {Qt.Key_Down: 1, Qt.Key_Up: -1, Qt.Key_PageDown: 10, Qt.Key_PageUp: -10}[k]
                    nxt = shown[max(0, min(len(shown) - 1, n + step))]
                    self.list.setCurrentItem(nxt)
                    self.list.scrollToItem(nxt)
                return True
            if k in (Qt.Key_Return, Qt.Key_Enter):
                self.choose(self.list.currentItem())
                return True
            if k == Qt.Key_Escape:
                self.hide()
                return True
        return False


class SearchCombo(QComboBox):
    """A drop-down whose list has a search box (see the module's words)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._popup = None
        self.pinned = 0  # (how many choices stay on top of the A to Z: sort_items' pinned)
        self.setItemDelegate(QStyledItemDelegate(self))  # (the short list's rows drawn as the theme's list rows)
        self.setMaxVisibleItems(SEARCH_FROM)  # (a short list shows every choice: a longer one opens with the search box)

    def sort_items(self, pinned=0):
        """The choices A to Z, numbers as numbers (natural_key); the first `pinned` (a "Choose…" or "Automatic…" that
        belongs on top) stay where they are, and the list remembers how many (self.pinned). The chosen one stays chosen,
        and nothing is said about it (no signals)."""
        self.pinned = pinned
        cur = self.currentIndex()
        keep, keep_text = (self.itemData(cur), self.itemText(cur)) if cur >= 0 else (None, None)
        # (each choice's words, value and tooltip read and added back in order: moving Qt's own rows across from Python
        # (takeRow) crashed the checks now and then)
        rows = [(self.itemText(i), self.itemData(i), self.itemData(i, Qt.ToolTipRole)) for i in range(pinned, self.count())]
        rows.sort(key=lambda r: natural_key(r[0]))
        blocked = self.blockSignals(True)
        try:
            for i in range(self.count() - 1, pinned - 1, -1):
                self.removeItem(i)
            for text, data, tip in rows:
                self.addItem(text, data)
                if tip:
                    self.setItemData(self.count() - 1, tip, Qt.ToolTipRole)
            i = self.findData(keep) if keep is not None else self.findText(keep_text or "")
            self.setCurrentIndex(i if i >= 0 else (0 if self.count() else -1))
        finally:
            self.blockSignals(blocked)

    def searches(self):
        """Does the list open with the search box (more than SEARCH_FROM choices)?"""
        return self.count() > SEARCH_FROM

    def showPopup(self):
        if not self.searches():
            pop = self.view().window()
            # (the list draws its look itself, the theme's: the frame Qt keeps it in has its own frame turned off,
            # each time, as Qt puts it back when the theme changes)
            pop.setFrameShape(QFrame.NoFrame)
            super().showPopup()
            self._wide_enough(pop)
            return
        if self._popup is None:
            self._popup = _Popup(self)
        p = self._popup
        p.fill()
        rows = max(1, min(self.count(), 14))
        h = self.list_height(p, rows)
        w = max(self.width(), min(520, p.list.sizeHintForColumn(0) + 40))  # (as wide as its longest row, within reason)
        below = self.mapToGlobal(QPoint(0, self.height() + 2))
        screen = self.screen().availableGeometry() if self.screen() else None
        if screen is not None and below.y() + h > screen.bottom():
            below = self.mapToGlobal(QPoint(0, -h - 2))
        p.setGeometry(below.x(), below.y(), w, h)
        p.show()
        p.q.setFocus()

    def _wide_enough(self, pop):
        """The short list as wide as its longest choice, so every name shows whole, and kept on the screen (Qt's own
        list is only as wide as the drop-down; Fusion's menu-like one, before 2026-10-23, widened itself)."""
        view = self.view()
        bar = view.verticalScrollBar()
        need = view.sizeHintForColumn(0) + 2 * view.frameWidth() + (bar.width() if bar.isVisible() else 0)
        if need <= pop.width():
            return
        g = pop.geometry()
        g.setWidth(need)
        screen = self.screen().availableGeometry() if self.screen() else None
        if screen is not None:
            g.setWidth(min(g.width(), screen.width()))
            if g.right() > screen.right():
                g.moveRight(screen.right())
        pop.setGeometry(g)

    @staticmethod
    def list_height(p, rows):
        row = p.list.sizeHintForRow(0) if p.list.count() else 24
        return 6 + p.q.sizeHint().height() + 4 + rows * max(row, 20) + 6 + 12

    def hidePopup(self):
        if self._popup is not None:
            self._popup.hide()
        super().hidePopup()
