from pathlib import Path
from backend.model_loader import supported_models

from PyQt6.QtCore import QElapsedTimer, QEvent, Qt, QTimer
from .recording_button import RecordingButton
from .captioned_window import CaptionedWindow
from .utils import button, icon
from .recording import RecordingController
from .transcript_editor import TranscriptEditor
from PyQt6.QtWidgets import (
    QApplication, QComboBox, QHBoxLayout, QLabel, QMenu,
    QSystemTrayIcon,
)


class VoiceInputWindow(CaptionedWindow):
    def __init__(self):
        super().__init__(
            flags=Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint,
            logo_icon=icon("audio-lines"),
        )
        self.setWindowTitle("语音输入")
        self.setObjectName("voiceInputWindow")
        self.resize(460, 244)
        self.setMinimumSize(280, 164)
        self.setStyleSheet(Path(__file__).with_name("style.qss").read_text(encoding="utf-8"))
        self.tray_requested.connect(self.hide_to_tray)
        self.close_requested.connect(self.quit_app)

        self.editor = TranscriptEditor()
        self.window_layout.addWidget(self.editor, 1)

        footer = QHBoxLayout()
        footer.setSpacing(6)
        self.mic = RecordingButton()
        self.mic.clicked.connect(self.toggle_recording)
        footer.addWidget(self.mic)
        self.timer_label = QLabel(self)
        self.timer_label.setObjectName("timer")
        self.timer_label.ensurePolished()
        metrics = self.timer_label.fontMetrics()
        self.timer_label.setMinimumWidth(max(metrics.horizontalAdvance(text) for text in ("888:88", "加载失败")))
        footer.addWidget(self.timer_label)
        self.model_selector = QComboBox()
        self.model_selector.setAccessibleName("识别模型")
        self.model_selector.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.model_selector.addItems(supported_models())
        self.model_selector.setToolTip(self.model_selector.currentText())
        self.model_selector.currentTextChanged.connect(self.model_selector.setToolTip)
        footer.addWidget(self.model_selector, 1)
        copy = button("copy", flat=True)
        copy.clicked.connect(self.editor.copy_all)
        clear = button("trash", flat=True)
        clear.clicked.connect(self.editor.clear)
        footer.addWidget(copy)
        footer.addWidget(clear)
        self.window_layout.addLayout(footer)

        self.recording = RecordingController(self)
        self.model_selector.currentTextChanged.connect(self.select_model)
        self.recording.model_load_failed.connect(self.on_model_load_failed)
        self.recording.text_received.connect(self.append_transcript)
        self.recording.recording_started.connect(self.start_timer)
        self.recording.recording_finished.connect(self.recording_finished)
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

    def select_model(self, model_id):
        self.recording.select_model(model_id)
        self.timer_label.clear()
        self.mic.setToolTip("")

    def on_model_load_failed(self):
        self.timer_label.setText("加载失败")
        self.mic.setToolTip("模型加载失败，点击重试或选择其他模型")

    def toggle_recording(self):
        if self.session_open:
            self.stop_recording()
            return
        self.session_open = True
        self.model_selector.setEnabled(False)
        self.timer_label.clear()
        self.mic.setToolTip("")
        self.mic.show_processing()
        self.recording.start()

    def start_timer(self):
        if not self.recording.stop_requested.is_set():
            self.mic.show_recording()
            self.elapsed.start()
            self.update_timer()
            self.clock.start(250)

    def update_timer(self):
        seconds = self.elapsed.elapsed() // 1000
        self.timer_label.setText(f"{seconds // 60:02}:{seconds % 60:02}")

    def append_transcript(self, text):
        if not self.recording.stop_requested.is_set():
            self.editor.insert_transcript(text)

    def stop_recording(self):
        if self.session_open:
            self.recording.stop_requested.set()
            self.clock.stop()
            self.mic.show_processing()

    def recording_finished(self):
        self.clock.stop()
        self.session_open = False
        self.model_selector.setEnabled(True)
        self.mic.show_idle()

    def shutdown_recording(self):
        self.recording.shutdown()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange and self.isMinimized():
            self.stop_recording()

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
