import logging
from pathlib import Path
from asr import DEFAULT_MODEL, supported_models

from PyQt6.QtCore import QEvent, Qt, QTimer
from .file_dialog import FileDialog
from .recording_button import RecordingButton
from .captioned_window import CaptionedWindow
from .utils import button, icon
from backend.recording_controller import RecordingController
from backend.transcript_controller import TranscriptController
from .transcript_editor import TranscriptEditor
from .transcript_sidebar import TranscriptSidebar
from PyQt6.QtWidgets import (
    QApplication, QComboBox, QDialog, QHBoxLayout, QLabel, QLineEdit,
    QMenu, QSystemTrayIcon,
)


class VoiceInputWindow(CaptionedWindow):
    MINIMUM_WIDTH = 280

    def __init__(self):
        super().__init__(
            flags=(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint
                   | Qt.WindowType.WindowMinimizeButtonHint),
        )
        self.setWindowTitle("语音输入")
        self.setObjectName("voiceInputWindow")
        self.resize(560, 400)
        self.setMinimumSize(self.MINIMUM_WIDTH, 164)
        self.setStyleSheet(Path(__file__).with_name("style.qss").read_text(encoding="utf-8"))
        self.tray_requested.connect(self.hide_to_tray)
        self.close_requested.connect(self.quit_app)

        self.transcripts = TranscriptController()
        self.files_toggle = button("panel-left-open", size=28, glyph=16, flat=True)
        self.files_toggle.setCheckable(True)
        self.files_toggle.toggled.connect(self.toggle_files)
        self.caption_layout.insertWidget(0, self.files_toggle)

        body = QHBoxLayout()
        body.setSpacing(self.window_layout.spacing())
        self.sidebar = TranscriptSidebar()
        self.sidebar.new_requested.connect(self.new_file)
        self.sidebar.open_requested.connect(self.open_file)
        self.sidebar.rename_requested.connect(self.rename_file)
        self.sidebar.delete_requested.connect(self.delete_file)
        body.addWidget(self.sidebar)
        self.editor = TranscriptEditor()
        self.editor.modificationChanged.connect(self.create_file_on_edit)
        body.addWidget(self.editor, 1)
        self.window_layout.addLayout(body, 1)
        try:
            for path in self.transcripts.files():
                self.sidebar.add_file(path)
        except OSError as error:
            QTimer.singleShot(0, lambda error=error: self.show_file_error("Load Files", error))

        footer = QHBoxLayout()
        footer.setSpacing(6)
        self.model_selector = QComboBox()
        self.model_selector.setAccessibleName("识别模型")
        self.model_selector.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.model_selector.addItems(supported_models())
        default_index = self.model_selector.findText(DEFAULT_MODEL)
        if default_index >= 0:
            self.model_selector.setCurrentIndex(default_index)
        self.model_selector.setToolTip(self.model_selector.currentText())
        self.model_selector.currentTextChanged.connect(self.model_selector.setToolTip)
        footer.addWidget(self.model_selector, 1)
        self.model_load_error = QLabel("Load Failed")
        self.model_load_error.setObjectName("modelLoadError")
        self.model_load_error.hide()
        footer.addWidget(self.model_load_error)
        self.mic = RecordingButton()
        self.model_selector.setFixedHeight(self.mic.height())
        self.mic.clicked.connect(self.toggle_recording)
        footer.addWidget(self.mic)
        self.window_layout.addLayout(footer)
        self.files_toggle.setChecked(True)

        self.recording = RecordingController(self, model_id=self.model_selector.currentText())
        self.model_selector.currentTextChanged.connect(self.select_model)
        self.recording.model_load_failed.connect(self.on_model_load_failed)
        self.recording.text_received.connect(self.append_transcript)
        self.recording.recording_started.connect(self.recording_started)
        self.recording.recording_finished.connect(self.recording_finished)
        self.session_open = False
        QApplication.instance().aboutToQuit.connect(self.shutdown_recording)

        self.tray = QSystemTrayIcon(icon("audio-lines", Qt.GlobalColor.black), self)
        self.tray_menu = QMenu()
        self.tray_menu.addAction("显示窗口", self.restore_window)
        self.tray_menu.addAction("退出", self.quit_app)
        self.tray.setContextMenu(self.tray_menu)
        self.tray.activated.connect(self.tray_activated)
        if self.tray.isSystemTrayAvailable():
            self.tray.show()

    def toggle_files(self, visible):
        self.sidebar.setVisible(visible)
        width = self.MINIMUM_WIDTH
        if visible:
            width += self.sidebar.minimumWidth() + self.window_layout.spacing()
        self.setMinimumWidth(width)
        self.files_toggle.setIcon(icon("panel-left-close" if visible else "panel-left-open"))
        label = "Hide Files" if visible else "Show Files"
        self.files_toggle.setToolTip(label)
        self.files_toggle.setAccessibleName(label)

    def show_file_error(self, title, error):
        logging.warning("%s failed: %s", title, error)
        if isinstance(error, FileExistsError):
            message = "A file with that name already exists."
        elif isinstance(error, UnicodeError):
            message = "Unable to read or write UTF-8 text."
        elif isinstance(error, ValueError):
            message = str(error)
        else:
            message = f"Unable to {title.lower()}."
        dialog = FileDialog(self, title, message)
        dialog.exec()
        dialog.deleteLater()

    def save_file(self):
        current = self.transcripts.current_path
        if current is not None and not self.editor.document().isModified():
            return
        text = self.editor.toPlainText()
        if current is None and not text:
            return
        path = self.transcripts.save(text)
        if current is None:
            self.sidebar.add_file(path)
            self.sidebar.select_file(path)
        self.editor.document().setModified(False)

    def create_file_on_edit(self, modified):
        if not modified or self.transcripts.current_path is not None or self.editor.document().isEmpty():
            return
        try:
            path = self.transcripts.create()
        except OSError as error:
            QTimer.singleShot(0, lambda error=error: self.show_file_error("Save File", error))
            return
        self.sidebar.add_file(path)
        self.sidebar.select_file(path)

    def show_file(self, text):
        self.editor.setPlainText(text)
        self.editor.document().setModified(False)
        self.sidebar.select_file(self.transcripts.current_path)

    def new_file(self):
        try:
            self.save_file()
            path = self.transcripts.create()
        except (OSError, UnicodeError) as error:
            self.show_file_error("New File", error)
            return
        self.sidebar.add_file(path)
        self.show_file("")
        self.editor.setFocus()

    def open_file(self, path):
        try:
            if path == self.transcripts.current_path:
                if not path.exists() and self.transcripts.recreate_missing_file(path, self.editor.toPlainText()):
                    self.editor.document().setModified(False)
                return
            self.save_file()
            text = self.transcripts.open(path)
        except (OSError, UnicodeError) as error:
            self.sidebar.select_file(self.transcripts.current_path)
            self.show_file_error("Open File", error)
            return
        self.show_file(text)

    def rename_file(self, path):
        name_field = QLineEdit(path.stem)
        name_field.setAccessibleName("File Name")
        dialog = FileDialog(
            self, "Rename", name_field, action="Rename", validator=self.transcripts.normalize_filename,
        )
        name_field.setFocus()
        name_field.selectAll()
        result = dialog.exec()
        name = name_field.text()
        dialog.deleteLater()
        if result != QDialog.DialogCode.Accepted:
            return
        try:
            target = self.transcripts.rename(path, name)
        except (OSError, ValueError) as error:
            self.show_file_error("Rename", error)
            return
        if target.name != path.name:
            self.sidebar.remove_file(path)
            self.sidebar.add_file(target)
            self.sidebar.select_file(self.transcripts.current_path)

    def delete_file(self, path):
        dialog = FileDialog(self, "Delete", f"Delete {path.name}?", action="Delete", destructive=True)
        result = dialog.exec()
        dialog.deleteLater()
        if result != QDialog.DialogCode.Accepted:
            return
        deleting_current = path == self.transcripts.current_path
        try:
            self.transcripts.delete(path)
        except OSError as error:
            self.show_file_error("Delete", error)
            return
        self.sidebar.remove_file(path)
        if deleting_current:
            self.show_file("")
        else:
            self.sidebar.select_file(self.transcripts.current_path)

    def select_model(self, model_id):
        self.recording.select_model(model_id)
        self.model_load_error.hide()
        self.mic.setToolTip("")

    def on_model_load_failed(self):
        self.model_load_error.show()
        self.mic.setToolTip("模型加载失败，点击重试或选择其他模型")

    def toggle_recording(self):
        if self.session_open:
            self.stop_recording()
            return
        self.session_open = True
        self.model_selector.setEnabled(False)
        self.model_load_error.hide()
        self.mic.setToolTip("")
        self.mic.show_processing()
        self.recording.start()

    def recording_started(self):
        if not self.recording.stop_requested.is_set():
            self.mic.show_recording()

    def append_transcript(self, text):
        if not self.recording.stop_requested.is_set():
            self.editor.insert_transcript(text)

    def stop_recording(self):
        if self.session_open:
            self.recording.stop_requested.set()
            self.mic.show_processing()

    def recording_finished(self):
        self.session_open = False
        self.model_selector.setEnabled(True)
        self.mic.show_idle()

    def shutdown_recording(self):
        self.recording.shutdown()

    def changeEvent(self, event):
        super().changeEvent(event)
        if (event.type() == QEvent.Type.WindowStateChange and self.isMinimized()
                and not event.oldState() & Qt.WindowState.WindowMinimized):
            self.stop_recording()
            try:
                self.save_file()
            except (OSError, UnicodeError) as error:
                self.showNormal()
                self.show_file_error("Save File", error)

    def closeEvent(self, event):
        self.stop_recording()
        try:
            self.save_file()
        except (OSError, UnicodeError) as error:
            event.ignore()
            self.restore_window()
            self.show_file_error("Save File", error)
            return
        self.tray.hide()
        super().closeEvent(event)

    def quit_app(self):
        if self.close():
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
            self.stop_recording()
            try:
                self.save_file()
            except (OSError, UnicodeError) as error:
                self.show_file_error("Save File", error)
                return
            self.tray.show()
            self.hide()
            self.recording.request_sleep()
        else:
            self.showMinimized()
