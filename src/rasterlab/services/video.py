"""Управление VideoCapture: чтение кадров, пауза, перезапуск, тайминг."""
from pathlib import Path
import cv2
import numpy as np
from ..core.video import FrameProcessor
from .files import resize_preview


class VideoSession:
    """Прикладной объект видеосессии, не зависимый от Tkinter."""

    def __init__(self):
        self.capture = None
        self.path = None
        self.processor = None
        self.fps = 25.0
        self.total_frames = 0
        self.frame_index = 0
        self.running = False
        self.mode = "mask"

    @property
    def loaded(self):
        return self.capture is not None

    @property
    def finished(self):
        return self.total_frames > 0 and self.frame_index >= self.total_frames

    def open(self, path):
        capture = cv2.VideoCapture(path)
        if not capture.isOpened():
            capture.release()
            raise ValueError("Не удалось открыть видео. Проверьте файл и поддержку кодека.")
        self.close()
        self.capture = capture
        self.path = path
        self.processor = FrameProcessor()
        fps = capture.get(cv2.CAP_PROP_FPS)
        self.fps = fps if np.isfinite(fps) and fps > 0 else 25.0
        self.total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        self.frame_index = 0
        self.running = True

    def close(self):
        if self.capture is not None:
            self.capture.release()
        self.capture = None
        self.processor = None
        self.running = False

    def stop(self):
        self.running = False

    def restart(self):
        if not self.path:
            raise ValueError("Сначала загрузите видео.")
        self.open(self.path)

    def next_frame(self, mode=None):
        """Возвращает (RGB-кадр, результат) или None в конце потока."""
        if not self.running or self.capture is None:
            return None
        ok, frame = self.capture.read()
        if not ok:
            self.stop()
            return None
        frame = resize_preview(frame)
        mask, blurred = self.processor.apply(frame)
        self.frame_index += 1
        chosen = mode or self.mode
        result = mask if chosen == "mask" else cv2.cvtColor(blurred, cv2.COLOR_BGR2RGB)
        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), result

    def delay_ms(self, elapsed):
        return max(1, int(1000 / self.fps - elapsed))

    def status(self):
        name = Path(self.path).name if self.path else ""
        phase = "Обучение фона" if self.frame_index < 30 else "Обработка"
        return (f"{name} | кадр {self.frame_index}/{self.total_frames} | "
                f"{self.frame_index / self.fps:.1f} с | {self.fps:.2f} FPS | {phase}")
