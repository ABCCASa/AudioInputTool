from pathlib import Path

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QMenu, QPlainTextEdit,
    QPushButton, QStyle, QStyleOption, QSystemTrayIcon, QVBoxLayout, QWidget,
)


ASSETS = Path(__file__).resolve().parent / "asset"


def icon(name, color=Qt.GlobalColor.white):
    pixmap = QPixmap(str(ASSETS / f"{name}.png"))
    painter = QPainter(pixmap)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    painter.fillRect(pixmap.rect(), color)
    painter.end()
    return QIcon(pixmap)


def button(name, label, size=34, glyph=18):
    control = QPushButton()
    control.setIcon(icon(name))
    control.setIconSize(QSize(glyph, glyph))
    control.setFixedSize(size, size)
    control.setAccessibleName(label)
    control.setCursor(Qt.CursorShape.PointingHandCursor)
    return control


class VoiceInputWindow(QWidget):
    def __init__(self):
        super().__init__(
            None,
            Qt.WindowType.Window
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint,
        )
        self.setWindowTitle("语音输入")
        self.setObjectName("voiceInputWindow")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.resize(460, 244)
        self.setMinimumSize(280, 164)
        self.setStyleSheet(Path(__file__).with_name("style.qss").read_text(encoding="utf-8"))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(9, 7, 9, 8)
        layout.setSpacing(6)
        header = QHBoxLayout()
        header.setSpacing(5)
        logo = QLabel()
        logo.setPixmap(icon("audio-lines").pixmap(18, 18))
        logo.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        header.addWidget(logo)
        header.addStretch()
        for name, label, action in (
            ("panel-bottom-close", "隐藏到系统托盘", self.hide_to_tray),
            ("minus", "最小化", self.showMinimized),
            ("x", "关闭", self.quit_app),
        ):
            control = button(name, label, 28, 16)
            control.setObjectName("caption")
            control.clicked.connect(action)
            header.addWidget(control)
        layout.addLayout(header)

        self.editor = QPlainTextEdit()
        self.editor.setAccessibleName("输入文本")
        self.editor.setPlaceholderText("输入文本...")
        layout.addWidget(self.editor, 1)

        footer = QHBoxLayout()
        footer.setSpacing(6)
        mic = button("mic", "录音（暂未启用）")
        mic.setEnabled(False)
        # Keep the reference color even in the disabled state.
        mic_icon = mic.icon()
        mic_icon.addPixmap(mic_icon.pixmap(24, 24), QIcon.Mode.Disabled)
        mic.setIcon(mic_icon)
        footer.addWidget(mic)
        timer = QLabel("00:00")
        timer.setObjectName("timer")
        footer.addWidget(timer)
        footer.addStretch()
        copy = button("copy", "复制全部文本")
        copy.setFlat(True)
        copy.clicked.connect(self.copy_text)
        clear = button("trash", "清空文本")
        clear.setFlat(True)
        clear.clicked.connect(self.editor.clear)
        footer.addWidget(copy)
        footer.addWidget(clear)
        layout.addLayout(footer)

        self.tray = QSystemTrayIcon(icon("audio-lines", Qt.GlobalColor.black), self)
        self.tray_menu = QMenu()
        self.tray_menu.addAction("显示窗口", self.restore_window)
        self.tray_menu.addAction("退出", self.quit_app)
        self.tray.setContextMenu(self.tray_menu)
        self.tray.activated.connect(self.tray_activated)
        if self.tray.isSystemTrayAvailable():
            self.tray.show()

    def copy_text(self):
        QApplication.clipboard().setText(self.editor.toPlainText())

    def quit_app(self):
        self.tray.hide()
        QApplication.instance().quit()

    def restore_window(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger,
                      QSystemTrayIcon.ActivationReason.DoubleClick):
            self.restore_window()

    def hide_to_tray(self):
        if self.tray.isSystemTrayAvailable():
            self.tray.show()
            self.hide()
        else:
            self.showMinimized()

    def paintEvent(self, event):
        option = QStyleOption()
        option.initFrom(self)
        painter = QPainter(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, option, painter, self)

    def resize_edges(self, pos):
        edge = Qt.Edge
        edges = edge(0)
        if pos.x() < 7:
            edges |= edge.LeftEdge
        elif pos.x() >= self.width() - 7:
            edges |= edge.RightEdge
        if pos.y() < 7:
            edges |= edge.TopEdge
        elif pos.y() >= self.height() - 7:
            edges |= edge.BottomEdge
        return edges

    def mouseMoveEvent(self, event):
        edges = self.resize_edges(event.position())
        edge = Qt.Edge
        cursor = Qt.CursorShape
        if edges in (edge.TopEdge | edge.LeftEdge, edge.BottomEdge | edge.RightEdge):
            self.setCursor(cursor.SizeFDiagCursor)
        elif edges in (edge.TopEdge | edge.RightEdge, edge.BottomEdge | edge.LeftEdge):
            self.setCursor(cursor.SizeBDiagCursor)
        elif edges & (edge.LeftEdge | edge.RightEdge):
            self.setCursor(cursor.SizeHorCursor)
        elif edges:
            self.setCursor(cursor.SizeVerCursor)
        else:
            self.unsetCursor()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            edges = self.resize_edges(event.position())
            if edges:
                self.windowHandle().startSystemResize(edges)
                return
            if event.position().y() < self.editor.y():
                self.windowHandle().startSystemMove()
                return
        super().mousePressEvent(event)
