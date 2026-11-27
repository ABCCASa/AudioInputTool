import logging
from concurrent.futures import ThreadPoolExecutor
from threading import Event

from PyQt6.QtCore import QObject, pyqtSignal
from backend.model_loader import load_model

class RecordingController(QObject):
    model_initialized = pyqtSignal(bool)
    text_received = pyqtSignal(str)
    recording_started = pyqtSignal()
    recording_finished = pyqtSignal()

    def __init__(self, parent):
        super().__init__(parent)
        self.model = None
        self._executor = ThreadPoolExecutor(max_workers=1)
        self.stop_requested = Event()

    def initialize_model(self):
        self._executor.submit(self._load_model)

    def _load_model(self):
        try:
            self.model = load_model()
        except Exception:
            logging.exception("语音识别模型加载失败")
        finally:
            self.model_initialized.emit(self.model is not None)

    def start(self):
        self.stop_requested.clear()
        self._executor.submit(self._record)

    def request_sleep(self):
        self.stop_requested.set()
        self._executor.submit(self._sleep)

    def _sleep(self):
        if self.model is not None:
            self.model.model_sleep()

    def shutdown(self):
        self.stop_requested.set()
        self._executor.shutdown(wait=True)

    def _record(self):
        try:
            if self.model is None or self.stop_requested.is_set():
                return
            self.model.start(self.text_received.emit)
            if not self.model.is_active:
                return
            self.recording_started.emit()
            while self.model.is_active:
                if self.stop_requested.wait(0.02):
                    self.model.stop()
                    break
        except Exception as exc:
            print(exc)
        finally:
            self.recording_finished.emit()

