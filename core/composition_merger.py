"""Render the same transforms used by the composition scene."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage, QPainter

class CompositionMerger:
    @staticmethod
    def render(model):
        bounds = model.export_rect()
        image = QImage(int(bounds.width()), int(bounds.height()),
                       QImage.Format.Format_ARGB32_Premultiplied)
        source = model.entries[0].selection.image
        image.setDotsPerMeterX(source.dotsPerMeterX())
        image.setDotsPerMeterY(source.dotsPerMeterY())
        if model.background_mode == 'transparent':
            image.fill(Qt.GlobalColor.transparent)
        elif model.background_mode == 'white':
            image.fill(Qt.GlobalColor.white)
        else:
            image.fill(QColor(*model.background_color))
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        for entry in sorted(model.entries, key=lambda e: e.z):
            painter.resetTransform()
            painter.translate(-bounds.x(), -bounds.y())
            painter.setTransform(entry.transform(), True)
            painter.drawImage(entry.rect, entry.selection.image)
        painter.end()
        return image
