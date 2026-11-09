"""PDF document and page render cache."""
from collections import OrderedDict
import fitz
from PySide6.QtGui import QImage
from config.settings import Settings

class PDFRenderer:
    def __init__(self, file_path):
        self.doc = fitz.open(str(file_path))
        self.cache = OrderedDict()
        if self.doc.page_count == 0:
            self.doc.close()
            raise ValueError('PDF 中没有可显示的页面')

    def render_page(self, page_num, zoom):
        key = (page_num, zoom)
        if key in self.cache:
            self.cache.move_to_end(key)
            return self.cache[key]
        pix = self.doc[page_num].get_pixmap(matrix=fitz.Matrix(zoom, zoom),
                                          colorspace=fitz.csRGB, alpha=False)
        image = QImage(pix.samples, pix.width, pix.height, pix.stride,
                       QImage.Format.Format_RGB888).copy()
        self.cache[key] = image
        if len(self.cache) > Settings.MAX_CACHE_SIZE:
            self.cache.popitem(last=False)
        return image

    def page_size(self, page_num):
        rect = self.doc[page_num].rect
        return rect.width, rect.height

    @property
    def page_count(self):
        return len(self.doc)

    def close(self):
        self.cache.clear()
        self.doc.close()
