"""Owned pixel conversions between Qt and Pillow."""
from PIL import Image
from PySide6.QtGui import QImage

def qimage_to_pil(qimage):
    image = qimage.convertToFormat(QImage.Format.Format_RGBA8888)
    return Image.frombytes('RGBA', (image.width(), image.height()), bytes(image.constBits()),
                           'raw', 'RGBA', image.bytesPerLine())
