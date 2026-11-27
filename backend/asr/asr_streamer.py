
from typing import Callable

from transformers import TextStreamer
from abc import ABC, abstractmethod

class AsrStreamer(TextStreamer, ABC):
    @abstractmethod
    def release(self):...


    @abstractmethod
    def model_sleep(self):...

    @abstractmethod
    def model_awake(self):...

    @property
    @abstractmethod
    def is_active(self) -> bool:...

    @abstractmethod
    def on_finalized_text(self, text: str, stream_end: bool = False):...

    @abstractmethod
    def stop(self):...

    @abstractmethod
    def start(self, callback: Callable[[str], None]):...


