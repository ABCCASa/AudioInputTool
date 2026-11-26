import torch
import time
from threading import Thread
from transformers import AutoModelForRNNT, AutoProcessor, TextIteratorStreamer
from transformers.models.nemotron3_5_asr.modeling_nemotron3_5_asr import Nemotron3_5AsrForRNNT
from transformers.models.nemotron3_5_asr.processing_nemotron3_5_asr import Nemotron3_5AsrProcessor
from .audio_streamer import AudioStreamer


class AsrStreamer:
    def __init__(self,
                 model_id:str = "nvidia/nemotron-3.5-asr-streaming-0.6b",
                 device: str|torch.device|None = None,
                 local_files_only=False):
        self._processor: Nemotron3_5AsrProcessor = AutoProcessor.from_pretrained(model_id,
                                                                                 local_files_only=local_files_only)
        self._model: Nemotron3_5AsrForRNNT = AutoModelForRNNT.from_pretrained(model_id,
                                                                              local_files_only=local_files_only
                                                                              ).to(device)
        self._processor.set_num_lookahead_tokens(13)

    @property
    def sampling_rate(self):
        return self._processor.feature_extractor.sampling_rate

    def generate(self, audio_streamer: AudioStreamer, language: str | list[str] = "auto"):
        processor = self._processor
        model = self._model
        sampling_rate = processor.feature_extractor.sampling_rate

        while audio_streamer.samples < processor.num_samples_first_audio_chunk:
            if not audio_streamer.is_recording:
                return
            time.sleep(0.01)

        first_chunk_inputs = processor(
            audio_streamer.get_audio(processor.num_samples_first_audio_chunk),
            sampling_rate=sampling_rate,
            is_streaming=True,
            is_first_audio_chunk=True,
            language=language,
        ).to(model.device, dtype=model.dtype)

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
                        time.sleep(0.01)
                        continue
                    else:
                        return
                inputs = processor(
                    audio_streamer.get_audio(processor.num_samples_per_audio_chunk),
                    sampling_rate=sampling_rate,
                    is_streaming=True,
                    is_first_audio_chunk=False,
                    language=language
                ).to(model.device, dtype=model.dtype)
                yield inputs.input_features
                audio_streamer.trim(chunk_frames * hop_length)


        streamer = TextIteratorStreamer(processor.tokenizer, skip_special_tokens=True)

        generate_kwargs = {
            **first_chunk_inputs,
            "input_features": input_features_generator(),
            "streamer": streamer,
            "max_length": int(1e9),
        }
        thread = Thread(target=model.generate, kwargs=generate_kwargs)
        thread.start()

        for text_chunk in streamer:
            yield text_chunk
        thread.join()

