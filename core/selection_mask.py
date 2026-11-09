"""Antialiased polygon masks in crop-local pixel coordinates."""
from PIL import Image, ImageDraw, ImageChops
from PySide6.QtGui import QImage

def qimage_from_pil(image):
    rgba = image.convert('RGBA')
    return QImage(rgba.tobytes(), rgba.width, rgba.height, rgba.width * 4,
                   QImage.Format.Format_RGBA8888).copy()

def apply_mask_to_crop(crop, points):
    image = crop.convert('RGBA')
    if not points:
        return image
    pixels = image.width * image.height
    scale = 4 if pixels <= 4_000_000 else 2 if pixels <= 10_000_000 else 1
    mask = Image.new('L', (image.width * scale, image.height * scale), 0)
    ImageDraw.Draw(mask).polygon([(x * scale, y * scale) for x, y in points], fill=255)
    if scale != 1:
        mask = mask.resize(image.size, Image.Resampling.LANCZOS)
    image.putalpha(ImageChops.multiply(image.getchannel('A'), mask))
    return image
