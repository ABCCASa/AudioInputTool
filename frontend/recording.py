from concurrent.futures import ThreadPoolExecutor
from threading import Event

from PyQt6.QtCore import QObject, pyqtSignal
from backend.model_loader import load_local_model

class RecordingController(QObject):
    text_received = pyqtSignal(str)
    recording_started = pyqtSignal()
    finished = pyqtSignal()

    def __init__(self, parent):
        super().__init__(parent)
        self.model = None
        self._executor = ThreadPoolExecutor(max_workers=1)
        self.stop_requested = Event()

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
            if self.stop_requested.is_set():
                return
            if self.model is None:
                self.model = load_local_model()
            if self.model is None or self.stop_requested.is_set():
                return
            self.model.start(self.deliver_text)
            if not self.model.is_active:
                return
            self.recording_started.emit()
            while self.model.is_active:
                if self.stop_requested.wait(0.05):
                    self.model.stop()
                    break
        except Exception as exc:
            print(exc)
        finally:
            self.finished.emit()


    def deliver_text(self, text):
        try:
            self.text_received.emit(text)
        except RuntimeError as exc:
            print(f"发送界面文字更新失败：{exc}")
