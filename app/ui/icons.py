"""The app's icons, drawn here (no image files): three EQ sliders on a rounded square, blue when an EQ is on for the
device playing, grey when it's off. Also the small dots in the device list (playing, connected, not connected)."""
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap

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
