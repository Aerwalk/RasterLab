"""Поиск визуально похожих изображений по гистограмме цвета и pHash."""
from itertools import combinations
import cv2
import numpy as np
from .image import gray, rgb


def extract(image):
    hsv = cv2.cvtColor(rgb(image), cv2.COLOR_RGB2HSV)
    hist = cv2.calcHist([hsv], [0, 1], None, [32, 32], [0, 180, 0, 256]).ravel()
    hist /= hist.sum()
    small = cv2.resize(gray(image), (32, 32)).astype(np.float32)
    dct = cv2.dct(small)[:8, :8].ravel()[1:]
    return hist, dct > np.median(dct)


def distance(a, b):
    h1, p1 = a
    h2, p2 = b
    color = np.sqrt(max(0, 1 - float(np.sqrt(h1 * h2).sum())))
    return .5 * color + .5 * np.mean(p1 != p2)


def closest_pair(images):
    """Возвращает (i, j, distance) для наиболее похожей пары."""
    if not 3 <= len(images) <= 10:
        raise ValueError("Выберите от 3 до 10 изображений.")
    features = [extract(image) for image in images]
    best = None
    for i, j in combinations(range(len(images)), 2):
        d = distance(features[i], features[j])
        if best is None or d < best[2]:
            best = i, j, float(d)
    return best
