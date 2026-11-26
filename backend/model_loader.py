def load_local_model():
    try:
        import torch
        from .asr import AsrStreamer
        device = "cuda:0" if torch.cuda.is_available() else "cpu"
        return AsrStreamer(device=device, local_files_only=True)
    except Exception as exc:
        print(f"加载语音识别模型失败：{exc}")
        return None
