from backend.asr import AsrStreamer
from backend.asr import AudioStreamer
import torch

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
audio_streamer = AudioStreamer(chunk_length_s = 0.5)
import time
time.sleep(2)
model = AsrStreamer(device=device, local_files_only=True)
for x in model.generate(audio_streamer):
    print(x, end="", flush=True)
