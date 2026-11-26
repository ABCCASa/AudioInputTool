from typing import Callable
import torch
import time
from threading import RLock, Thread
from transformers import AutoModelForRNNT, AutoProcessor, TextStreamer, AutoConfig
from transformers.models.nemotron3_5_asr.modeling_nemotron3_5_asr import Nemotron3_5AsrForRNNT
from transformers.models.nemotron3_5_asr.processing_nemotron3_5_asr import Nemotron3_5AsrProcessor
from .audio_streamer import AudioStreamer
from abc import ABC, abstractmethod

class AsrStreamer(TextStreamer, ABC):


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


