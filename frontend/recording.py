import logging
from concurrent.futures import ThreadPoolExecutor
from threading import Event

from PyQt6.QtCore import QObject, pyqtSignal
from backend.model_loader import DEFAULT_MODEL, load_model

class RecordingController(QObject):
    model_load_failed = pyqtSignal()
    text_received = pyqtSignal(str)
    recording_started = pyqtSignal()
    recording_finished = pyqtSignal()

    def __init__(self, parent):
        super().__init__(parent)
        self._model = None
        self._model_id = DEFAULT_MODEL
        self._executor = ThreadPoolExecutor(max_workers=1)
        self.stop_requested = Event()

    def select_model(self, model_id):
        if model_id != self._model_id:
            self._model_id = model_id
            self._executor.submit(self._release_model)

    def _release_model(self):
        if self._model is not None:
            self._model.release()
            self._model = None

    def start(self):
        self.stop_requested.clear()
        self._executor.submit(self._record, self._model_id)

    def request_sleep(self):
        self.stop_requested.set()
        self._executor.submit(self._sleep)

    def _sleep(self):
        if self._model is not None:
            self._model.model_sleep()

    def shutdown(self):
        self.stop_requested.set()
        self._executor.submit(self._release_model)
        self._executor.shutdown(wait=True)

    def _record(self, model_id):
        try:
            if self.stop_requested.is_set():
                return
            if self._model is None:
                try:
                    self._model = load_model(model_id)
                    if self._model is None:
                        raise ValueError(f"不支持的模型 {model_id}")
                except Exception:
                    logging.exception("语音识别模型加载失败 %s", model_id)
                    self.model_load_failed.emit()
                    return
            if self.stop_requested.is_set():
                return
            self._model.start(self.text_received.emit)
            if not self._model.is_active:
                return
            self.recording_started.emit()
            while self._model.is_active:
                if self.stop_requested.wait(0.02):
                    break
        except Exception:
            logging.exception("语音录制失败 %s", model_id)
        finally:
            try:
                if self._model is not None and self._model.is_active:
                    self._model.stop()
            finally:
                self.recording_finished.emit()

