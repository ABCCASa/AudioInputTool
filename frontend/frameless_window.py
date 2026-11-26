from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter
from PyQt6.QtWidgets import QStyle, QStyleOption, QWidget

class FramelessWindow(QWidget):
    def __init__(self, parent=None, flags=Qt.WindowType.Window):
        super().__init__(parent, flags | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self._drag_area = None

    def set_drag_area(self, widget: QWidget):
        self._drag_area = widget

    def paintEvent(self, event):
        option = QStyleOption()
        option.initFrom(self)
        painter = QPainter(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, option, painter, self)

    def resize_edges(self, pos):
        edge = Qt.Edge
        edges = edge(0)
        if pos.x() < 7:
            edges |= edge.LeftEdge
        elif pos.x() >= self.width() - 7:
            edges |= edge.RightEdge
        if pos.y() < 7:
            edges |= edge.TopEdge
        elif pos.y() >= self.height() - 7:
            edges |= edge.BottomEdge
        return edges

    def mouseMoveEvent(self, event):
        edges = self.resize_edges(event.position())
        edge = Qt.Edge
        cursor = Qt.CursorShape
        if edges in (edge.TopEdge | edge.LeftEdge, edge.BottomEdge | edge.RightEdge):
            self.setCursor(cursor.SizeFDiagCursor)
        elif edges in (edge.TopEdge | edge.RightEdge, edge.BottomEdge | edge.LeftEdge):
            self.setCursor(cursor.SizeBDiagCursor)
        elif edges & (edge.LeftEdge | edge.RightEdge):
            self.setCursor(cursor.SizeHorCursor)
        elif edges:
            self.setCursor(cursor.SizeVerCursor)
        else:
            self.unsetCursor()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            edges = self.resize_edges(event.position())
            if edges:
                self.windowHandle().startSystemResize(edges)
                return
            area = self._drag_area
            if area is not None and area.rect().contains(area.mapFrom(self, event.position().toPoint())):
                self.windowHandle().startSystemMove()
                return
        super().mousePressEvent(event)
