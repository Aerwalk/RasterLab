"""Морфологически очищенная маска движения и размытие движущихся областей."""
import cv2
import numpy as np


class FrameProcessor:
    """Инкрементальная обработка последовательности кадров BGR."""

    def __init__(self):
        self.background = cv2.createBackgroundSubtractorMOG2(
            history=300, varThreshold=25, detectShadows=True)

    def apply(self, frame):
        mask = self.background.apply(frame)
        mask = cv2.threshold(mask, 200, 255, cv2.THRESH_BINARY)[1]
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
        region = cv2.dilate(mask, np.ones((9, 9), np.uint8))
        blurred = cv2.GaussianBlur(frame, (31, 31), 0)
        result = np.where(region[..., None] > 0, blurred, frame)
        return mask, result
