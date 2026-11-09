"""Document view with selections stored in document coordinates."""
from math import ceil
from PySide6.QtWidgets import QWidget, QScrollArea
from PySide6.QtGui import QPainter, QColor, QPen, QPainterPath, QImage
from PySide6.QtCore import Qt, QPointF, Signal, QRectF
from config.settings import Settings
from core.selection_geometry import SelectionGeometry, PageTransform

class DocumentCanvas(QWidget):
    selection_changed = Signal(bool)

    def __init__(self):
        super().__init__()
        self.session = None
        self.image = QImage()
        self.transform = None
        self.selection_mode = False
        self.selection_tool = 'rect'
        self._drawing = False
        self._points = []
        self._gesture = None
        self.setMinimumSize(400, 300)
        self.setStyleSheet(f"background-color: rgba(244,254,255,0.72); border: 1px solid {Settings.BORDER['normal']};")

    def bind_session(self, session):
        if self.session is not None:
            self.session.draft_changed.disconnect(self._draft_changed)
        self.session = session
        self.session.draft_changed.connect(self._draft_changed)
        self._drawing = False
        self._points = []
        self._gesture = None
        self.set_image(session.preview)
        self.update_transform()
        self._draft_changed(session.page_num)

    def set_image(self, image):
        self.image = image
        self.update()

    def update_transform(self):
        w, h = self.session.source.page_size(self.session.page_num)
        self.transform = PageTransform(w, h, self.session.source.display_base * self.session.zoom)
        self.setFixedSize(ceil(w * self.transform.scale), ceil(h * self.transform.scale))
        self.update()

    def page_changed(self):
        self._drawing = False
        self._points = []
        self._gesture = None
        self.set_image(self.session.preview)
        self.update_transform()
        self._draft_changed(self.session.page_num)

    def _draft_changed(self, page_num):
        if page_num != self.session.page_num:
            return
        self.selection_changed.emit(self.session.draft is not None and not self._drawing)
        self.update()

    def set_selection_mode(self, enabled):
        self.selection_mode = enabled
        self._drawing = False
        self._points = []
        self._gesture = None
        self.setCursor(Qt.CursorShape.CrossCursor if enabled else Qt.CursorShape.ArrowCursor)

    def set_selection_tool(self, tool):
        if self.selection_tool == tool:
            return
        self.selection_tool = tool
        self._drawing = False
        self._points = []
        self._gesture = None
        if self.session is not None:
            self.session.set_draft(None)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        if self.session is None:
            return
        target = self.transform.to_widget((0, 0, self.transform.width, self.transform.height))
        painter.drawImage(target, self.image)
        geometry = self._gesture if self._drawing else self.session.draft
        if geometry is None:
            return
        painter.setPen(QPen(QColor(255, 107, 107, 220), 2, Qt.PenStyle.DashLine))
        painter.setBrush(QColor(255, 107, 107, 30))
        if geometry.shape_type == 'rect':
            painter.drawRect(self.transform.to_widget(geometry.rect))
        else:
            scale = self.transform.scale
            path = QPainterPath(QPointF(geometry.points[0][0] * scale, geometry.points[0][1] * scale))
            for x, y in geometry.points[1:]:
                path.lineTo(x * scale, y * scale)
            if not self._drawing:
                path.closeSubpath()
            painter.drawPath(path)

    def mousePressEvent(self, event):
        if self.selection_mode and event.button() == Qt.MouseButton.LeftButton:
            self._drawing = True
            self._points = [self.transform.to_document(event.position())]
            self._gesture = None
            self.session.set_draft(None)

    def mouseMoveEvent(self, event):
        if self._drawing:
            point = self.transform.to_document(event.position())
            if self.selection_tool == 'free':
                self._points.append(point)
            else:
                self._points = [self._points[0], point]
            self._update_geometry()

    def mouseReleaseEvent(self, event):
        if self._drawing and event.button() == Qt.MouseButton.LeftButton:
            point = self.transform.to_document(event.position())
            if self.selection_tool == 'free':
                self._points.append(point)
            else:
                self._points = [self._points[0], point]
            self._update_geometry()
            geometry = self._gesture
            self._drawing = False
            _, _, w, h = geometry.rect
            complete = w * self.transform.scale > 5 and h * self.transform.scale > 5
            if geometry.shape_type == 'free':
                complete = complete and len(set(geometry.points)) >= 3
            self.session.set_draft(geometry if complete else None)
            self._points = []
            self._gesture = None

    def _update_geometry(self):
        xs, ys = zip(*self._points)
        x, y = min(xs), min(ys)
        rect = (x, y, max(xs) - x, max(ys) - y)
        points = tuple(self._points) if self.selection_tool == 'free' else ()
        self._gesture = SelectionGeometry(self.session.page_num, self.selection_tool, rect, points)
        self.update()

class ScrollableCanvas(QScrollArea):
    def __init__(self):
        super().__init__()
        self.canvas = DocumentCanvas()
        self.setWidget(self.canvas)
        self.setWidgetResizable(False)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        from ui.glass_effect import GlassEffect
        self.setStyleSheet(f"""
            QScrollArea {{ background-color: rgba(236,252,255,0.34); border: none; }}
            {GlassEffect._get_scrollbar_styles()}
        """)

    def get_canvas(self):
        return self.canvas
