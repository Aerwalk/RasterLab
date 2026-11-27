"""Вкладка вычитания фона и размытия движущихся объектов."""
import time
import tkinter as tk
from tkinter import ttk
from ..image_view import ImageView
from ...services.files import VIDEO_TYPES
from ...services.video import VideoSession
from .base import Tab

MODES = [("Вычитание фона", "mask"), ("Размытие объектов", "blur")]


class VideoTab(Tab):
    name = "Видео"

    def __init__(self, parent, app):
        super().__init__(parent, app, self.name)
        self.session = VideoSession()
        self.job = None
        self.build()

    def build(self):
        row = ttk.Frame(self)
        row.pack(fill="x")
        self.button(row, "Открыть видео", self.open_video)
        self.button(row, "Пуск / пауза", self.toggle)
        self.button(row, "С начала", self.restart)
        self.video_mode = tk.StringVar(value=MODES[0][0])
        ttk.Combobox(row, textvariable=self.video_mode,
                     values=[label for label, _ in MODES],
                     state="readonly", width=24).pack(side="left", padx=8)
        self.video_info = ttk.Label(
            self, text="MOG2: первые кадры используются для обучения фона.",
            padding=10)
        self.video_info.pack(fill="x")
        views = ttk.Frame(self)
        views.pack(fill="both", expand=True)
        self.video_views = [ImageView(views, "Исходный кадр"),
                            ImageView(views, "Результат")]
        for view in self.video_views:
            view.pack(side="left", fill="both", expand=True)
        ttk.Label(self, text="Для неподвижной камеры. Тени исключаются из маски; "
                  "маска очищается морфологией.\nРазмытие применяется внутри "
                  "расширенной маски движения. Звук не воспроизводится.",
                  padding=10).pack(anchor="w")

    def open_video(self):
        path = self.app.dialogs.open_file("Открыть видео", VIDEO_TYPES)
        if path:
            self.start(path)

    def start(self, path):
        self.stop_timer()
        self.session.open(path)
        self.video_mode.set(MODES[0][0])
        self.session.mode = "mask"
        self.tick()

    def restart(self):
        self.session.restart()
        self.tick()

    def toggle(self):
        if not self.session.loaded:
            raise ValueError("Сначала загрузите видео.")
        if self.session.running:
            self.session.stop()
            self.stop_timer()
        else:
            self.session.running = True
            self.tick()

    def stop_timer(self):
        self.session.stop()
        if self.job is not None:
            self.app.after_cancel(self.job)
            self.job = None

    def tick(self):
        self.job = None
        if not self.session.running:
            return
        started = time.perf_counter()
        try:
            mode = dict(MODES)[self.video_mode.get()]
            pair = self.session.next_frame(mode)
            if pair is None:
                self.app.set_status(
                    "Конец видео. Для повторного просмотра нажмите «С начала».")
                return
            source, result = pair
            self.video_views[0].show(source)
            self.video_views[1].show(result)
            self.video_info.configure(text=self.session.status())
            elapsed = (time.perf_counter() - started) * 1000
            self.job = self.app.after(self.session.delay_ms(elapsed), self.tick)
        except Exception as exc:
            self.stop_timer()
            self.app.dialogs.error(self, str(exc))

    def close(self):
        self.stop_timer()
        self.session.close()
