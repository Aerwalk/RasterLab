"""Публичный facade: см. src.rasterlab.ui."""
from src.rasterlab.ui import App, ImageView, main
from src.rasterlab.ui.histogram import draw as draw_histograms

__all__ = ["App", "ImageView", "draw_histograms", "main"]
