"""Document sources and the lifetime of an editing session."""
from pathlib import Path
from PIL import Image, ImageOps
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QImage
from core.composition_model import CompositionModel
from core.pdf_renderer import PDFRenderer
from core.selection_manager import SelectionManager, SelectionItem
from core.selection_mask import apply_mask_to_crop, qimage_from_pil
from core.compat import qimage_to_pil

PDF_EXPORT_SCALE = 180 / 72

class ImageSource:
    display_base = 1.0
    page_count = 1

    def __init__(self, path):
        with Image.open(path) as image:
            self.original = ImageOps.exif_transpose(image).convert('RGBA')

    def page_size(self, page_num):
        return self.original.size

    def render(self, page_num, zoom):
        w, h = self.original.size
        factor = min(zoom, 1.0)
        return qimage_from_pil(self.original.resize(
            (max(1, round(w * factor)), max(1, round(h * factor))), Image.Resampling.LANCZOS))

    def crop(self, geometry):
        x, y, w, h = geometry.pixel_rect(1.0)
        image = self.original.crop((x, y, x + w, y + h))
        return qimage_from_pil(apply_mask_to_crop(image, geometry.pixel_mask(1.0)))

    def close(self):
        self.original.close()

class PDFSource:
    display_base = PDF_EXPORT_SCALE

    def __init__(self, path):
        self.renderer = PDFRenderer(path)

    @property
    def page_count(self):
        return self.renderer.page_count

    def page_size(self, page_num):
        return self.renderer.page_size(page_num)

    def render(self, page_num, zoom):
        return self.renderer.render_page(page_num, PDF_EXPORT_SCALE * zoom)

    def crop(self, geometry):
        page = self.renderer.render_page(geometry.page_num, PDF_EXPORT_SCALE)
        image = qimage_to_pil(page.copy(*geometry.pixel_rect(PDF_EXPORT_SCALE)))
        crop = qimage_from_pil(apply_mask_to_crop(image, geometry.pixel_mask(PDF_EXPORT_SCALE)))
        crop.setDotsPerMeterX(round(180 / 0.0254))
        crop.setDotsPerMeterY(round(180 / 0.0254))
        return crop

    def close(self):
        self.renderer.close()

class DocumentSession(QObject):
    draft_changed = Signal(int)

    def __init__(self, path, source):
        super().__init__()
        self.path = Path(path)
        self.source = source
        self.page_num = 0
        self.drafts = {}
        self.selections = SelectionManager(self)
        self.composition = CompositionModel(self)
        self.composition_window = None
        self.overwrite_decision = None
        self.zoom = 1.0
        if isinstance(source, ImageSource):
            w, h = source.page_size(0)
            self.zoom = max(0.1, min(1920 / w, 1440 / h, 1.0))
        self.preview = QImage()

    @classmethod
    def open(cls, path):
        source = PDFSource(path) if Path(path).suffix.lower() == '.pdf' else ImageSource(path)
        session = cls(path, source)
        try:
            session.preview = source.render(0, session.zoom)
        except (OSError, ValueError, RuntimeError):
            session.close()
            raise
        return session

    @property
    def draft(self):
        return self.drafts.get(self.page_num)

    def set_draft(self, geometry):
        if geometry is None:
            self.drafts.pop(self.page_num, None)
        else:
            self.drafts[self.page_num] = geometry
        self.draft_changed.emit(self.page_num)

    def commit_draft(self):
        geometry = self.draft
        crop = self.source.crop(geometry)
        self.selections.add(SelectionItem.create(geometry, crop))
        self.set_draft(None)

    @property
    def has_content(self):
        return bool(self.drafts or self.selections.items or self.composition.entries)

    def close(self):
        if self.composition_window is not None:
            self.composition_window.dispose()
            self.composition_window = None
        self.selections.clear()
        self.composition.clear_history_and_content()
        self.drafts.clear()
        self.preview = QImage()
        self.source.close()
