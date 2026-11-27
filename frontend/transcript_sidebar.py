from PyQt6.QtCore import QSignalBlocker, QSize, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMenu, QSizePolicy,
    QVBoxLayout, QWidget,
)

from .utils import button, icon


class TranscriptSidebar(QWidget):
    new_requested = pyqtSignal()
    open_requested = pyqtSignal(object)
    rename_requested = pyqtSignal(object)
    delete_requested = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("transcriptSidebar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        self.setFixedWidth(152)
        self._items = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(1, 3, 1, 1)
        layout.setSpacing(4)

        toolbar = QHBoxLayout()
        toolbar.addStretch()
        new_file = button("plus", size=24, glyph=16, flat=True)
        new_file.setToolTip("New File")
        new_file.setAccessibleName("New File")
        new_file.clicked.connect(self.new_requested.emit)
        toolbar.addWidget(new_file)
        layout.addLayout(toolbar)

        self._list = QListWidget()
        self._list.setObjectName("transcriptFiles")
        self._list.setAccessibleName("Files")
        self._list.currentItemChanged.connect(self._open_current)
        self._list.itemClicked.connect(self._open_current)
        self._list.itemActivated.connect(self._open_current)
        layout.addWidget(self._list, 1)

    def add_file(self, path):
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, path)
        item.setData(Qt.ItemDataRole.AccessibleTextRole, path.name)
        item.setSizeHint(QSize(0, 28))

        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(6, 0, 2, 0)
        name = QLabel(path.name)
        name.setTextFormat(Qt.TextFormat.PlainText)
        name.setToolTip(path.name)
        name.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        layout.addWidget(name, 1)
        options = button("ellipsis-vertical", size=24, glyph=16, flat=True)
        options.setToolTip("File Options")
        options.setAccessibleName(f"Options for {path.name}")
        options.clicked.connect(lambda: self._show_options(path, options))
        layout.addWidget(options)

        with QSignalBlocker(self._list):
            self._list.addItem(item)
            self._list.setItemWidget(item, row)
        self._items[path] = item

    def remove_file(self, path):
        item = self._items.pop(path)
        with QSignalBlocker(self._list):
            self._list.takeItem(self._list.row(item))

    def select_file(self, path):
        with QSignalBlocker(self._list):
            self._list.setCurrentItem(self._items.get(path))

    def _open_current(self, item, previous=None):
        if item is not None and item is self._list.currentItem():
            self.open_requested.emit(item.data(Qt.ItemDataRole.UserRole))

    def _show_options(self, path, control):
        menu = QMenu(self)
        menu.setObjectName("transcriptFileMenu")
        # Use the editor context menu's native vertical action layout.
        menu.addAction(icon("pencil", Qt.GlobalColor.black), "Rename", lambda: self.rename_requested.emit(path))
        menu.addAction(icon("trash", Qt.GlobalColor.black), "Delete", lambda: self.delete_requested.emit(path))
        menu.exec(control.mapToGlobal(control.rect().bottomLeft()))
        menu.deleteLater()
