from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QFrame, QLabel, QVBoxLayout


class FileDialog(QDialog):
    def __init__(self, parent, title, content, *, action=None, destructive=False, validator=None):
        super().__init__(parent, Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setWindowTitle(title)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        panel = QFrame()
        panel.setObjectName("fileDialogPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        heading = QLabel(title)
        heading.setObjectName("fileDialogTitle")
        layout.addWidget(heading)
        if isinstance(content, str):
            message = QLabel(content)
            message.setTextFormat(Qt.TextFormat.PlainText)
            message.setWordWrap(True)
            content = message
        layout.addWidget(content)

        ok = QDialogButtonBox.StandardButton.Ok
        cancel = QDialogButtonBox.StandardButton.Cancel
        buttons = QDialogButtonBox(ok | cancel if action else ok)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        confirm = buttons.button(ok)
        confirm.setText(action or "OK")
        confirm.setObjectName("deleteFileButton" if destructive else "confirmFileButton")
        default = buttons.button(cancel) if destructive else confirm
        layout.addWidget(buttons)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(panel)
        self.setFixedWidth(340)
        if destructive and isinstance(content, QLabel):
            content.ensurePolished()
            margins = layout.contentsMargins()
            width = self.width() - 2 * panel.frameWidth() - margins.left() - margins.right()
            full_text = content.text()
            short_text = content.fontMetrics().elidedText(full_text, Qt.TextElideMode.ElideMiddle, width)
            if short_text != full_text:
                content.setText(short_text)
                content.setToolTip(full_text)
                content.setAccessibleName(full_text)
        default.setDefault(True)
        default.setFocus()
        if validator is not None:
            def validate(text):
                try:
                    validator(text)
                except ValueError:
                    invalid = True
                else:
                    invalid = False
                confirm.setEnabled(not invalid)
                if content.property("invalid") != invalid:
                    content.setProperty("invalid", invalid)
                    content.style().unpolish(content)
                    content.style().polish(content)
                    content.update()

            content.textChanged.connect(validate)
            validate(content.text())
