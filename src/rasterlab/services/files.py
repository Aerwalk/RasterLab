"""Чтение и запись файлов, извлечение метаданных изображения."""
from pathlib import Path
import cv2
import numpy as np
from PIL import Image, ImageOps

IMAGE_TYPES = [
    ("Изображения", "*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp *.gif"),
    ("Все файлы", "*.*"),
]
VIDEO_TYPES = [
    ("Видео", "*.mp4 *.avi *.mov *.mkv *.webm"),
    ("Все файлы", "*.*"),
]

_DEPTH_BY_MODE = {"1": 1, "L": 8, "LA": 16, "P": 8, "RGB": 24, "RGBA": 32,
                  "CMYK": 32, "I": 32, "F": 32}
_PNG_CHANNELS = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}


def _source_depth(path, im):
    fmt, mode = im.format, im.mode
    depth = _DEPTH_BY_MODE.get(mode, 16 if mode.startswith("I;16") else None)
    if fmt == "PNG":
        with open(path, "rb") as stream:
            header = stream.read(26)
        depth = header[24] * _PNG_CHANNELS[header[25]]
    elif fmt == "BMP":
        with open(path, "rb") as stream:
            header = stream.read(30)
        dib_size = int.from_bytes(header[14:18], "little")
        offset = 24 if dib_size == 12 else 28
        depth = int.from_bytes(header[offset:offset + 2], "little")
    elif fmt == "TIFF":
        bits = im.tag_v2.get(258)
        if bits:
            depth = sum(bits) if isinstance(bits, tuple) else int(bits)
    return depth


def image_info(path, im):
    depth = _source_depth(path, im)
    return {
        "Файл": str(Path(path).resolve()),
        "Размер на диске": f"{Path(path).stat().st_size:,} байт",
        "Разрешение файла": f"{im.size[0]} × {im.size[1]} px",
        "Глубина файла": f"{depth} бит/пиксель" if depth else "не определена",
        "Формат": im.format,
        "Режим файла": im.mode,
        "DPI": str(im.info.get("dpi", "не задан")),
        "Кадров": str(getattr(im, "n_frames", 1)),
        "ICC-профиль": "есть" if im.info.get("icc_profile") else "нет",
        "Рабочее представление": "sRGB-подобное RGB, 8 бит/канал; альфа на белом фоне",
    }


def _normalize(im, mode, fmt):
    oriented = ImageOps.exif_transpose(im)
    if mode.startswith("I;16") or (mode == "I" and fmt == "PNG"):
        values = np.asarray(oriented, dtype=float)
        oriented = Image.fromarray(np.uint8(np.clip(values / 257, 0, 255)))
    if "A" in oriented.getbands() or "transparency" in im.info:
        rgba = oriented.convert("RGBA")
        background = Image.new("RGBA", rgba.size, "white")
        background.alpha_composite(rgba)
        oriented = background
    return np.array(oriented.convert("RGB"))


def load_image(path):
    """Возвращает (RGB uint8, словарь метаданных исходного файла)."""
    with Image.open(path) as im:
        info = image_info(path, im)
        return _normalize(im, im.mode, im.format), info


def save_image(image, path):
    Image.fromarray(image).save(path)


def resize_preview(frame, max_width=960):
    """Уменьшает кадр для отображения без искажения пропорций."""
    height, width = frame.shape[:2]
    if width <= max_width:
        return frame
    return cv2.resize(frame, (max_width, round(height * max_width / width)))
