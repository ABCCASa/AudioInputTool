from backend.asr import AsrStreamer
import torch
import sys
from PyQt6.QtWidgets import QApplication
from frontend.window import VoiceInputWindow

def main():
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    model = AsrStreamer(device=device, local_files_only=True)
    app = QApplication(sys.argv)
    app.setApplicationName("语音输入")
    window = VoiceInputWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
