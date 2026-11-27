"""Чистые алгоритмы обработки: цвет, изображение, признаки, видео."""
from . import colors, image, features, video
from .colors import MODELS, convert, from_rgb, to_rgb
from .features import closest_pair
from .image import (OPERATIONS, adjust, gray, histogram, process, rgb)
from .video import FrameProcessor

__all__ = [
    "MODELS", "OPERATIONS", "FrameProcessor", "adjust", "closest_pair",
    "convert", "from_rgb", "gray", "histogram", "process", "rgb", "to_rgb",
    "colors", "features", "image", "video",
]
