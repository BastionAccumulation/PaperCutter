"""Committed crops owned by one document session."""
from dataclasses import dataclass
from uuid import uuid4
from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtGui import QImage
from core.selection_geometry import SelectionGeometry

@dataclass(frozen=True, eq=False)
class SelectionItem:
    id: str
    geometry: SelectionGeometry
    image: QImage
    preview: QImage

    @classmethod
    def create(cls, geometry, image):
        preview = image.scaled(200, 80, Qt.AspectRatioMode.KeepAspectRatio,
                               Qt.TransformationMode.SmoothTransformation)
        return cls(uuid4().hex, geometry, image, preview)

class SelectionManager(QObject):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items = []

    @property
    def items(self):
        return tuple(self._items)

    def add(self, selection):
        self._items.append(selection)
        self.changed.emit()

    def remove(self, index):
        del self._items[index]
        self.changed.emit()

    def clear(self):
        self._items.clear()
        self.changed.emit()
