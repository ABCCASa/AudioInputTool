from pathlib import Path

from PyQt6.QtCore import QElapsedTimer, QEvent, QSize, Qt, QTimer
from PyQt6.QtGui import QIcon, QPainter, QPixmap, QTextCursor
from .recording import RecordingController
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
        self.mic = button("mic", "开始识别")
        self.mic.clicked.connect(self.toggle_recording)
        footer.addWidget(self.mic)
        self.timer_label = QLabel()
        self.timer_label.setObjectName("timer")
        self.loader = icon("loader").pixmap(18, 18)
        self.loader_timer = QTimer(self)
        self.loader_timer.timeout.connect(self.draw_loader)
        footer.addWidget(self.timer_label)
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

        self.recording = RecordingController(self)
        self.recording.text_received.connect(self.append_transcript)
        self.recording.recording_started.connect(self.start_timer)
        self.recording.finished.connect(self.recording_finished)
        self.session_open = False
        self.elapsed = QElapsedTimer()
        self.clock = QTimer(self)
        self.clock.timeout.connect(self.update_timer)
        QApplication.instance().aboutToQuit.connect(self.shutdown_recording)

        self.tray = QSystemTrayIcon(icon("audio-lines", Qt.GlobalColor.black), self)
        self.tray_menu = QMenu()
        self.tray_menu.addAction("显示窗口", self.restore_window)
        self.tray_menu.addAction("退出", self.quit_app)
        self.tray.setContextMenu(self.tray_menu)
        self.tray.activated.connect(self.tray_activated)
        if self.tray.isSystemTrayAvailable():
            self.tray.show()

    def toggle_recording(self):
        model = self.recording.model
        if (model is not None and model.is_active) or self.loader_timer.isActive():
            self.stop_recording()
            return
        if self.session_open:
            return  # Previous session is still delivering its final UI events.
        self.session_open = True
        self.timer_label.clear()
        self.loader_angle = 0
        self.draw_loader()
        self.loader_timer.start(80)
        self.mic.setAccessibleName("取消加载")
        self.recording.start()

    def draw_loader(self):
        frame = QPixmap(24, 24)
        frame.fill(Qt.GlobalColor.transparent)
        painter = QPainter(frame)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.translate(12, 12)
        painter.rotate(self.loader_angle)
        painter.drawPixmap(-9, -9, self.loader)
        painter.end()
        self.mic.setIcon(QIcon(frame))
        self.loader_angle = (self.loader_angle + 30) % 360

    def start_timer(self):
        self.loader_timer.stop()
        if self.recording.model.is_active and not self.recording.stop_requested.is_set():
            self.mic.setIcon(icon("square"))
            self.mic.setAccessibleName("停止识别")
            self.elapsed.start()
            self.update_timer()
            self.clock.start(250)

    def update_timer(self):
        seconds = self.elapsed.elapsed() // 1000
        self.timer_label.setText(f"{seconds // 60:02}:{seconds % 60:02}")

    def append_transcript(self, text):
        if text and not self.recording.stop_requested.is_set():
            if self.editor.hasFocus():
                self.editor.insertPlainText(text)
                self.editor.ensureCursorVisible()
                return
            cursor = QTextCursor(self.editor.document())
            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.insertText(text)
            self.editor.verticalScrollBar().setValue(self.editor.verticalScrollBar().maximum())

    def stop_recording(self):
        if self.session_open:
            self.recording.stop_requested.set()
            self.clock.stop()
            self.mic.setEnabled(False)

    def recording_finished(self):
        self.loader_timer.stop()
        self.clock.stop()
        self.session_open = False
        self.mic.setEnabled(True)
        self.mic.setAccessibleName("开始识别")
        self.mic.setIcon(icon("mic"))

    def shutdown_recording(self):
        self.stop_recording()
        self.recording.shutdown()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange and self.isMinimized():
            self.stop_recording()

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
        self.stop_recording()
        if self.tray.isSystemTrayAvailable():
            self.tray.show()
            self.hide()
            self.recording.request_sleep()
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
