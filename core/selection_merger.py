"""Stack committed crops without changing their source pixels."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter

class SelectionMerger:
    @staticmethod
    def render(selections, spacing=10):
        width = max(s.image.width() for s in selections)
        height = sum(s.image.height() for s in selections) + spacing * (len(selections) - 1)
        image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
        image.setDotsPerMeterX(selections[0].image.dotsPerMeterX())
        image.setDotsPerMeterY(selections[0].image.dotsPerMeterY())
        image.fill(Qt.GlobalColor.white)
        painter = QPainter(image)
        y = 0
        for selection in selections:
            painter.drawImage(0, y, selection.image)
            y += selection.image.height() + spacing
        painter.end()
        return image
