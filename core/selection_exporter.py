"""Render a crop against its export background."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter

class SelectionExporter:
    @staticmethod
    def render(crop, outside_mode):
        if outside_mode == 'transparent':
            return crop
        image = QImage(crop.size(), QImage.Format.Format_ARGB32_Premultiplied)
        image.setDotsPerMeterX(crop.dotsPerMeterX())
        image.setDotsPerMeterY(crop.dotsPerMeterY())
        image.fill(Qt.GlobalColor.white)
        painter = QPainter(image)
        painter.drawImage(0, 0, crop)
        painter.end()
        return image
