from pathlib import Path

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import QPushButton


ASSETS = Path(__file__).resolve().parent / "asset"


def icon(name, color=Qt.GlobalColor.white):
    pixmap = QPixmap(str(ASSETS / f"{name}.png"))
    painter = QPainter(pixmap)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    painter.fillRect(pixmap.rect(), color)
    painter.end()
    return QIcon(pixmap)


def button(name, size=34, glyph=18, *, flat=False):
    control = QPushButton()
    control.setFlat(flat)
    control.setIcon(icon(name))
    control.setIconSize(QSize(glyph, glyph))
    control.setFixedSize(size, size)
    control.setCursor(Qt.CursorShape.PointingHandCursor)
    return control
