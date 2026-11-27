"""Публичный facade графического интерфейса."""
from src.rasterlab.ui import App, ImageView, main
from src.rasterlab.ui.histogram import draw as draw_histograms
from src.rasterlab.ui.model import ImageModel

__all__ = ["App", "ImageModel", "ImageView", "draw_histograms", "main"]
