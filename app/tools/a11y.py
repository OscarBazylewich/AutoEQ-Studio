"""Accessibility checks for the self-tests: what a screen reader would read for each control (Qt's accessible name)
and whether the keyboard can reach it.

unnamed(root): the controls shown under root that a screen reader would read as nothing, or only a symbol ("✕",
"↺"), as [(class, text, tooltip, where)]. unreachable(root): the controls shown that Tab can't reach (no keyboard
focus), but for the parts that aren't meant to be (a graph, the tour's own buttons).
"""
import re

from PySide6.QtGui import QAccessible
from PySide6.QtWidgets import (QAbstractButton, QAbstractItemView, QAbstractSlider, QAbstractSpinBox, QComboBox,
                               QKeySequenceEdit, QLineEdit, QPlainTextEdit, QTextEdit, QWidget)

CONTROLS = (QAbstractButton, QComboBox, QLineEdit, QAbstractSpinBox, QAbstractSlider, QPlainTextEdit, QTextEdit,
            QAbstractItemView, QKeySequenceEdit)


def _shown(w):
    return w.isVisible() and w.width() > 0


def _where(w):
    parts, p = [], w.parentWidget()
    while p is not None and len(parts) < 3:
        t = getattr(p, "title", None)
        name = t() if callable(t) and isinstance(t(), str) and t() else type(p).__name__
        parts.append(name)
        p = p.parentWidget()
    return " < ".join(parts)


def name_of(w):
    iface = QAccessible.queryAccessibleInterface(w)
    return (iface.text(QAccessible.Name) if iface is not None else "") or ""


def unnamed(root):
    out = []
    for w in root.findChildren(QWidget):
        if not isinstance(w, CONTROLS) or not _shown(w) or w.property("a11y_skip"):
            continue
        if isinstance(w, QLineEdit) and w.parentWidget() is not None and isinstance(w.parentWidget(), (QComboBox,
                                                                                                    QAbstractSpinBox)):
            continue  # (a combo box's or spin box's own text field: the box has the name)
        if type(w).__name__ in ("QScrollBar", "QHeaderView") or w.objectName().startswith("qt_"):
            continue  # (a table's header is read as part of its table)
        n = re.sub(r"[^\w]", "", name_of(w))
        if len(n) < 2:
            out.append((type(w).__name__, getattr(w, "text", lambda: "")() if hasattr(w, "text") else "",
                        w.toolTip()[:40], _where(w)))
    return out


def unreachable(root):
    from PySide6.QtCore import Qt
    out = []
    for w in root.findChildren(QWidget):
        if not isinstance(w, CONTROLS) or not _shown(w) or w.property("a11y_skip") or not w.isEnabled():
            continue
        if type(w).__name__ in ("QScrollBar", "QHeaderView") or w.objectName().startswith("qt_"):
            continue
        if isinstance(w, QLineEdit) and isinstance(w.parentWidget(), (QComboBox, QAbstractSpinBox)):
            continue
        if isinstance(w, QAbstractButton) and w.group() is not None and w.group().exclusive():
            continue  # (one of a group, like radio buttons: the checked one is in the Tab order, arrows move on)
        if not (w.focusPolicy() & Qt.TabFocus):
            out.append((type(w).__name__, getattr(w, "text", lambda: "")() if hasattr(w, "text") else "", _where(w)))
    return out
