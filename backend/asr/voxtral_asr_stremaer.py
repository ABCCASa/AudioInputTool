from typing import Callable
import torch
import time
from threading import RLock, Thread
from .audio_streamer import AudioStreamer
from .asr_streamer import AsrStreamer
from transformers import VoxtralRealtimeForConditionalGeneration, VoxtralRealtimeProcessor
import gc

class VoxtralAsrStreamer(AsrStreamer):
    def __init__(self,model_id: str = "mistralai/Voxtral-Mini-4B-Realtime-2602", device: str|torch.device|None = None, local_files_only=False):
        self.device = device
        self._processor = VoxtralRealtimeProcessor.from_pretrained(model_id,local_files_only=local_files_only)
        self._model = VoxtralRealtimeForConditionalGeneration.from_pretrained(model_id, local_files_only=local_files_only, dtype=torch.bfloat16).to(self.device)
        super().__init__(self._processor.tokenizer, skip_special_tokens=True, clean_up_tokenization_spaces=True)

        self._is_sleep = False
        self._is_active = False
        self._lock = RLock()

        self._callback: Callable[[str], None] | None = None
        self._asr_thread = None
        self._audio_streamer: AudioStreamer|None = None

    def model_sleep(self):
        with self._lock:
            if self._is_active:
                return
        if self._is_sleep:
            return
        self._model.to("cpu")
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        self._is_sleep = True

    def model_awake(self):
        if not self._is_sleep:
            return
        self._model.to(self.device)
        self._is_sleep = False

    def release(self):
        if self._asr_thread is not None:
            self._asr_thread.join()
        del self._model, self._processor, self.tokenizer
        self._callback = None
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    @property
    def is_active(self) -> bool:
        with self._lock:
            return self._is_active

    def on_finalized_text(self, text: str, stream_end: bool = False):
        if self._callback:
            self._callback(text)

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
        self._callback = callback
        self._audio_streamer = audio_streamer

        def asr_loop():
            try:
                while audio_streamer.samples < processor.num_samples_first_audio_chunk:
                    if not audio_streamer.is_recording:
                        return
                    time.sleep(0.1)

                first_chunk_inputs = processor(audio_streamer.get_audio(processor.num_samples_first_audio_chunk),
                          is_streaming=True, is_first_audio_chunk=True,
                          return_tensors="pt").to(model.device, dtype=model.dtype)

                def input_features_generator():


                    mel_frame_idx = processor.num_mel_frames_first_audio_chunk
                    hop_length = processor.feature_extractor.hop_length
                    win_length = processor.feature_extractor.win_length

                    yield first_chunk_inputs.input_features
                    audio_streamer.trim(mel_frame_idx * hop_length - win_length // 2)

                    while True:
                        if audio_streamer.samples < processor.num_samples_per_audio_chunk:
                            if audio_streamer.is_recording:
                                time.sleep(0.1)
                                continue
                            else:
                                return
                        inputs = processor(
                            audio_streamer.get_audio(processor.num_samples_per_audio_chunk),
                            is_streaming=True,
                            is_first_audio_chunk=False, return_tensors="pt").to(model.device, dtype=model.dtype)
                        yield inputs.input_features
                        audio_streamer.trim(processor.audio_length_per_tok * hop_length)
                generate_kwargs = {
                    "input_ids": first_chunk_inputs.input_ids,
                    "input_features": input_features_generator(),
                    "num_delay_tokens": first_chunk_inputs.num_delay_tokens,
                    "streamer": self,
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


