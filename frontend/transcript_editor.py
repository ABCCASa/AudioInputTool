from PyQt6.QtGui import QTextCursor
from PyQt6.QtWidgets import QApplication, QPlainTextEdit


class TranscriptEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        #self.setPlaceholderText("输入文本...")

    def insert_transcript(self, text: str):
        if not text:
            return
        if self.hasFocus():
            self.insertPlainText(text)
            self.ensureCursorVisible()
            return

        cursor = QTextCursor(self.document())
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(text)
        scrollbar = self.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def copy_all(self):
        QApplication.clipboard().setText(self.toPlainText())
