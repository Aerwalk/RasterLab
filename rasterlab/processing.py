"""Публичный facade: см. src.rasterlab.core и src.rasterlab.services.files."""
from src.rasterlab.core import (OPERATIONS, adjust, closest_pair, gray,
                                histogram, process, rgb)
from src.rasterlab.core.video import FrameProcessor
from src.rasterlab.services.files import load_image

# Backward-compatible alias used by tests, tools and the original report.
VideoProcessor = FrameProcessor

__all__ = ["OPERATIONS", "FrameProcessor", "VideoProcessor", "adjust",
           "closest_pair", "gray", "histogram", "load_image", "process", "rgb"]
