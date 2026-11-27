import threading
import numpy as np
import os
from .microphone_utils import ffmpeg_microphone
from pathlib import Path

# Add ffmpeg to environment (remove this part if it is already set in your environment)
ROOT = Path(__file__).resolve().parent
os.environ["PATH"] += os.pathsep + f"{ROOT}/ffmpeg"

class AudioStreamer:
    def __init__(self, sampling_rate=16000,  chunk_length_s = 1, ffmpeg_input_device=None):
        self._is_recording = True
        self._sampling_rate = sampling_rate
        self._ffmpeg_input_device = ffmpeg_input_device
        self._chunk_length_s = chunk_length_s
        self._audio = np.empty(0, dtype=np.float32)
        self._lock = threading.RLock()
        self._thread = threading.Thread(target=self._record_loop, daemon=True)
        self._thread.start()

    @property
    def is_recording(self):
        return self._is_recording

    @property
    def samples(self) -> int:
        with self._lock:
            return self._audio.size

    def _record_loop(self):
        microphone = ffmpeg_microphone(self._sampling_rate, self._chunk_length_s, ffmpeg_input_device=self._ffmpeg_input_device)
        try:
            for chunk in microphone:
                with self._lock:
                    if not self._is_recording:
                        break
                    chunk = np.frombuffer(chunk, dtype=np.float32)
                    if self._audio.size == 0:
                        self._audio = chunk
                    else:
                        self._audio = np.concatenate((self._audio, chunk))
        finally:
            with self._lock:
                self._is_recording = False
                microphone.close()


    def get_audio(self, samples: int):
        with (self._lock):
            return self._audio[:samples]

    def trim(self, samples: int):
        with self._lock:
            if samples <= 0:
                return
            self._audio = self._audio[samples:]

    def stop(self, clear_samples: bool=True):
        with self._lock:
            if not self._is_recording:
                return
            self._is_recording = False
            if clear_samples:
                self._audio = np.empty(0, dtype=np.float32)
