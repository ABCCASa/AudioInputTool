import torch
from .asr import NemotronAsrStreamer
from .asr import VoxtralAsrStreamer

device = "cuda:0" if torch.cuda.is_available() else "cpu"
DEFAULT_MODEL = "nvidia/nemotron-speech-streaming-en-0.6b"

def supported_models():
    return (
        "mistralai/Voxtral-Mini-4B-Realtime-2602",
        "nvidia/nemotron-speech-streaming-en-0.6b",
        "nvidia/nemotron-3.5-asr-streaming-0.6b",
    )

def _load_voxtral(model_id: str, local_files_only=False):
    return VoxtralAsrStreamer(model_id, device=device, local_files_only=local_files_only)

def _load_nemotron(model_id: str, local_files_only=False):
    return NemotronAsrStreamer(model_id, local_files_only=local_files_only)

def load_model(model_id: str = DEFAULT_MODEL, local_files_only=False):
    if model_id in ["nvidia/nemotron-speech-streaming-en-0.6b", "nvidia/nemotron-3.5-asr-streaming-0.6b", ]:
        return _load_nemotron(model_id, local_files_only=local_files_only)
    elif model_id in ["mistralai/Voxtral-Mini-4B-Realtime-2602"]:
        return _load_voxtral(model_id, local_files_only=local_files_only)
    return None
