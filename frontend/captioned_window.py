from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QSystemTrayIcon, QVBoxLayout, QWidget
from .utils import button
from .frameless_window import FramelessWindow

class CaptionedWindow(FramelessWindow):
    tray_requested = pyqtSignal()
    close_requested = pyqtSignal()

    def __init__(self, parent=None, flags=Qt.WindowType.Window, *, logo_icon: QIcon):
        super().__init__(parent, flags)
        self.window_layout = QVBoxLayout(self)
        self.window_layout.setContentsMargins(9, 7, 9, 8)
        self.window_layout.setSpacing(6)
        title_bar = QWidget()
        header = QHBoxLayout(title_bar)
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(5)
        logo = QLabel()
        logo.setPixmap(logo_icon.pixmap(18, 18))
        logo.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        header.addWidget(logo)
        header.addStretch()
        actions = []
        if QSystemTrayIcon.isSystemTrayAvailable():
            actions.append(("panel-bottom-close", "隐藏到系统托盘", self.tray_requested.emit))
        actions.extend((("minus", "最小化", self.showMinimized), ("x", "关闭", self.close_requested.emit)))
        for name, label, action in actions:
            control = button(name, label, 28, 16)
            control.setObjectName("caption")
            control.clicked.connect(action)
            header.addWidget(control)
        self.window_layout.addWidget(title_bar)
        self.set_drag_area(title_bar)
