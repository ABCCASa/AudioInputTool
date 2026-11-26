import sys
from PyQt6.QtWidgets import QApplication
from frontend.voice_input_window import VoiceInputWindow

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("语音输入")
    window = VoiceInputWindow()
    window.show()
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())
