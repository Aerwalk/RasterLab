"""Состояние изображения и история одного шага, отделённое от виджетов."""
import numpy as np
from ..core.image import gray, histogram


class ImageModel:
    def __init__(self):
        self.original = None
        self.current = None
        self.before = None
        self.undo_image = None
        self.channel = "RGB"

    @property
    def loaded(self):
        return self.current is not None

    def require_loaded(self):
        if not self.loaded:
            raise ValueError("Сначала загрузите изображение.")

    def load(self, image):
        self.original = image.copy()
        self.current = image
        self.before = image.copy()
        self.undo_image = None

    def commit(self, image):
        self.require_loaded()
        self.undo_image = self.current.copy()
        self.before = self.current.copy()
        self.current = image

    def undo(self):
        self.require_loaded()
        if self.undo_image is None:
            return False
        self.before = self.current.copy()
        self.current = self.undo_image
        self.undo_image = None
        return True

    def reset(self):
        self.commit(self.original.copy())

    def histogram_pair(self, channel=None):
        """Возвращает списки гистограмм для состояний «до» и «после»."""
        channel = channel or self.channel
        if not self.loaded:
            return []
        images = (self.before, self.current)
        if channel == "Яркость":
            return [np.bincount(gray(image).ravel(), minlength=256)[None, :]
                    for image in images]
        arrays = [histogram(image) for image in images]
        if channel == "RGB":
            return arrays
        index = "RGB".index(channel)
        return [array[index][None, :] for array in arrays]
