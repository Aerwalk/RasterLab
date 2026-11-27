"""Вкладки главного окна."""
from .base import Tab
from .image import ImageTab
from .color import ColorTab
from .compare import CompareTab
from .video import VideoTab

__all__ = ["Tab", "ImageTab", "ColorTab", "CompareTab", "VideoTab"]
