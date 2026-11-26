from typing import Callable
import torch
import time
from threading import RLock, Thread
from transformers import AutoModelForRNNT, AutoProcessor, TextStreamer
from transformers.models.nemotron3_5_asr.modeling_nemotron3_5_asr import Nemotron3_5AsrForRNNT
from transformers.models.nemotron3_5_asr.processing_nemotron3_5_asr import Nemotron3_5AsrProcessor
from .audio_streamer import AudioStreamer

class AsrStreamer(TextStreamer):
    def __init__(self,
                 model_id:str = "nvidia/nemotron-speech-streaming-en-0.6b",
                 device: str|torch.device|None = None,
                 local_files_only=False):
        self._processor = AutoProcessor.from_pretrained(model_id,local_files_only=local_files_only)
        self._model = AutoModelForRNNT.from_pretrained(model_id, local_files_only=local_files_only ).to(device)
        self._processor.set_num_lookahead_tokens(6)
        self._is_active = False
        self._lock = RLock()
        super().__init__(self._processor.tokenizer, skip_special_tokens=True)
        self.callback: Callable[[str], None] | None = None
        self._asr_thread = None
        self._audio_streamer: AudioStreamer|None = None
        self._is_sleep = False
        self.device = device

    def model_sleep(self):
        with self._lock:
            if self._is_active:
                return
        if self._is_sleep:
            return
        self._model.to("cpu")
        torch.cuda.empty_cache()
        self._is_sleep = True

    def model_awake(self):
        if not self._is_sleep:
            return
        self._model.to(self.device)
        self._is_sleep = False

    @property
    def is_active(self) -> bool:
        with self._lock:
            return self._is_active

    def on_finalized_text(self, text: str, stream_end: bool = False):
        if self.callback:
            self.callback(text)

    def stop(self):
        with self._lock:
            if not self._is_active:
                return
            self._is_active = False
        if self._audio_streamer:
            self._audio_streamer.stop(True)
            self._audio_streamer = None
        if self._asr_thread:
            self._asr_thread.join()
            self._asr_thread = None

    def start(self, callback: Callable[[str], None]):
        with self._lock:
            if self._is_active:
                return
            self._is_active = True

        self.model_awake()
        processor = self._processor
        model = self._model
        sampling_rate = processor.feature_extractor.sampling_rate
        audio_streamer = AudioStreamer(sampling_rate, 0.2)
        self.callback = callback
        self._audio_streamer = audio_streamer

        def asr_loop():
            try:
                while audio_streamer.samples < processor.num_samples_first_audio_chunk:
                    if not audio_streamer.is_recording:
                        return
                    time.sleep(0.1)

                first_chunk_inputs = processor(
                    audio_streamer.get_audio(processor.num_samples_first_audio_chunk),
                    sampling_rate=sampling_rate,
                    is_streaming=True,
                    is_first_audio_chunk=True, ).to(model.device, dtype=model.dtype)

                def input_features_generator():
                    first_frame = processor.num_mel_frames_first_audio_chunk
                    chunk_frames = processor.num_mel_frames_per_audio_chunk
                    hop_length = processor.feature_extractor.hop_length
                    n_fft = processor.feature_extractor.n_fft

                    yield first_chunk_inputs.input_features[:, : first_frame, :]
                    audio_streamer.trim(first_frame * hop_length - n_fft // 2)

                    while True:
                        if audio_streamer.samples < processor.num_samples_per_audio_chunk:
                            if audio_streamer.is_recording:
                                time.sleep(0.1)
                                continue
                            else:
                                return
                        inputs = processor(
                            audio_streamer.get_audio(processor.num_samples_per_audio_chunk),
                            sampling_rate=sampling_rate,
                            is_streaming=True,
                            is_first_audio_chunk=False, ).to(model.device, dtype=model.dtype)
                        yield inputs.input_features
                        audio_streamer.trim(chunk_frames * hop_length)
                generate_kwargs = {
                    **first_chunk_inputs,
                    "input_features": input_features_generator(),
                    "streamer": self,
                    "max_new_tokens": int(1e9),
                }
                model.generate(**generate_kwargs)
            finally:
                with self._lock:
                    if self._is_active:
                        self._is_active = False

                if self._audio_streamer:
                    self._audio_streamer.stop(True)
                    self._audio_streamer = None


        thread = Thread(target=asr_loop, daemon=True)
        self._asr_thread = thread
        thread.start()


