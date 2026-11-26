from PyQt6.QtCore import QSize, Qt, QTimer
from PyQt6.QtGui import QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import QPushButton

from .utils import icon


class RecordingButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(34, 34)
        self.setIconSize(QSize(18, 18))
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._loader = icon("loader").pixmap(18, 18)
        self._loader_angle = 0
        self._animation = QTimer(self)
        self._animation.timeout.connect(self._draw_loader)
        self.show_idle()

    def show_processing(self):
        self.setEnabled(False)
        if self._animation.isActive():
            return
        self._draw_loader()
        self._animation.start(80)

    def show_recording(self):
        self._animation.stop()
        self.setEnabled(True)
        self.setIcon(icon("square"))

    def show_idle(self):
        self._animation.stop()
        self.setEnabled(True)
        self.setIcon(icon("mic"))

    def _draw_loader(self):
        frame = QPixmap(24, 24)
        frame.fill(Qt.GlobalColor.transparent)
        painter = QPainter(frame)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.translate(12, 12)
        painter.rotate(self._loader_angle)
        painter.drawPixmap(-9, -9, self._loader)
        painter.end()
        self.setIcon(QIcon(frame))
        self._loader_angle = (self._loader_angle + 30) % 360
