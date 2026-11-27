import torch
from .asr import NemotronAsrStreamer

def load_model(local_files_only=False):
    try:
        device = "cuda:0" if torch.cuda.is_available() else "cpu"
        #return NemotronAsrStreamer(device=device, local_files_only=local_files_only)
        return NemotronAsrStreamer(device=device, local_files_only=local_files_only)
    except Exception as exc:
        print(f"加载语音识别模型失败：{exc}")
        return None
