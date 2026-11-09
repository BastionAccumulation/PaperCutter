"""Document-space selections and their pixel projection."""
from dataclasses import dataclass
from math import floor, ceil
from PySide6.QtCore import QRectF

@dataclass(frozen=True)
class SelectionGeometry:
    page_num: int
    shape_type: str
    rect: tuple[float, float, float, float]
    points: tuple[tuple[float, float], ...] = ()

    def pixel_rect(self, scale):
        x, y, w, h = self.rect
        left, top = floor(x * scale), floor(y * scale)
        return left, top, ceil((x + w) * scale) - left, ceil((y + h) * scale) - top

    def pixel_mask(self, scale):
        left, top, _, _ = self.pixel_rect(scale)
        return tuple((x * scale - left, y * scale - top) for x, y in self.points)

@dataclass(frozen=True)
class PageTransform:
    width: float
    height: float
    scale: float

    def to_document(self, point):
        return (min(max(point.x() / self.scale, 0.0), self.width),
                min(max(point.y() / self.scale, 0.0), self.height))

    def to_widget(self, rect):
        x, y, w, h = rect
        return QRectF(x * self.scale, y * self.scale, w * self.scale, h * self.scale)
