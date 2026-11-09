"""A fixed-size composition view of a committed crop."""
import math
from PySide6.QtWidgets import QGraphicsObject, QGraphicsEllipseItem, QGraphicsLineItem
from PySide6.QtGui import QPainter, QPen, QColor
from PySide6.QtCore import Qt, QRectF, QLineF

class _RotationHandle(QGraphicsEllipseItem):
    def __init__(self, owner):
        super().__init__(-7, -7, 14, 14, owner)
        self.owner = owner
        self.setBrush(QColor('white'))
        self.setPen(QPen(QColor('#0084BE'), 2))
        self.setFlag(QGraphicsEllipseItem.GraphicsItemFlag.ItemIgnoresTransformations)
        self.setCursor(Qt.CursorShape.SizeAllCursor)
        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        self.setZValue(1)

    def _angle(self, pos):
        center = self.owner.mapToScene(self.owner.boundingRect().center())
        return math.degrees(math.atan2(pos.y() - center.y(), pos.x() - center.x()))

    def mousePressEvent(self, event):
        self.start_angle = self._angle(event.scenePos())
        self.start_rotation = self.owner.rotation()
        event.accept()

    def mouseMoveEvent(self, event):
        self.owner.setRotation(self.start_rotation + self._angle(event.scenePos()) - self.start_angle)
        self.owner.window._rotation_changed(self.owner)
        event.accept()

    def mouseReleaseEvent(self, event):
        self.owner.window._end_rotate(self.owner)
        event.accept()

class CompositionItem(QGraphicsObject):
    def __init__(self, entry, window):
        super().__init__()
        self.entry_id = entry.id
        self.selection = entry.selection
        self.window = window
        self._syncing = False
        self.setFlags(self.GraphicsItemFlag.ItemIsMovable |
                      self.GraphicsItemFlag.ItemIsSelectable |
                      self.GraphicsItemFlag.ItemIsFocusable |
                      self.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setTransformOriginPoint(self.boundingRect().center())
        self._handle_line = QGraphicsLineItem(self)
        pen = QPen(QColor('#0084BE'), 1)
        pen.setCosmetic(True)
        self._handle_line.setPen(pen)
        self._handle = _RotationHandle(self)
        self.update_from_entry(entry)
        self.set_view_zoom(1.0)
        self.set_edit_handles_visible(False)

    def boundingRect(self):
        return QRectF(0, 0, self.selection.image.width(), self.selection.image.height())

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.drawImage(self.boundingRect(), self.selection.image)
        if self.isSelected():
            pen = QPen(QColor('#0099CC'), 2, Qt.PenStyle.DashLine)
            pen.setCosmetic(True)
            painter.setPen(pen)
            painter.drawRect(self.boundingRect())

    def update_from_entry(self, entry):
        self._syncing = True
        self.setPos(entry.x, entry.y)
        self.setRotation(entry.rotation)
        self.setZValue(entry.z)
        self._syncing = False

    def set_view_zoom(self, zoom):
        center_x = self.boundingRect().center().x()
        self._handle.setPos(center_x, -30 / zoom)
        self._handle_line.setLine(QLineF(center_x, 0, center_x, -23 / zoom))

    def get_full_pos(self):
        return self.pos().x(), self.pos().y()

    def set_full_pos(self, x, y):
        self._syncing = True
        self.setPos(x, y)
        self._syncing = False

    def get_full_rect(self):
        rect = self.mapRectToScene(self.boundingRect())
        return rect.x(), rect.y(), rect.width(), rect.height()

    def get_rotation(self):
        return self.rotation()

    def set_edit_handles_visible(self, visible):
        self._handle.setVisible(visible)
        self._handle_line.setVisible(visible)
        self.update()

    def itemChange(self, change, value):
        if change == self.GraphicsItemChange.ItemPositionHasChanged and not self._syncing:
            self.window._item_moved_live(self)
        return super().itemChange(change, value)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.window._begin_move()

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self.window._end_move()

    def sample_color_at_scene(self, scene_pos):
        point = self.mapFromScene(scene_pos)
        image = self.selection.image
        if not (0 <= point.x() < image.width() and 0 <= point.y() < image.height()):
            return None
        color = image.pixelColor(int(point.x()), int(point.y()))
        if color.alpha() == 0:
            return None
        return color.red(), color.green(), color.blue()
