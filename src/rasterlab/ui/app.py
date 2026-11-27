"""Главное окно: связывает вкладки, модель и диалоги."""
import tkinter as tk
from tkinter import ttk
from .model import ImageModel
from .tabs import ColorTab, CompareTab, ImageTab, VideoTab
from .widgets import Dialogs


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("RasterLab — практическая работа")
        self.geometry("1380x900")
        self.minsize(1000, 720)
        self.protocol("WM_DELETE_WINDOW", self.close)

        self.model = ImageModel()
        self.dialogs = Dialogs()
        self.status = tk.StringVar(value="Загрузите изображение или видео.")
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True, padx=8, pady=8)

        self.image_tab = ImageTab(self.tabs, self)
        self.color_tab = ColorTab(self.tabs, self)
        self.compare_tab = CompareTab(self.tabs, self)
        self.video_tab = VideoTab(self.tabs, self)
        ttk.Label(self, textvariable=self.status, anchor="w").pack(
            fill="x", padx=10, pady=4)

    def guarded(self, action):
        try:
            return action()
        except Exception as exc:
            self.dialogs.error(self, str(exc))
            self.set_status(str(exc))
            return None

    def set_status(self, text):
        self.status.set(text)

    def pick_pixel(self, x, y, pixel):
        self.color_tab.set_pixel(pixel)
        self.set_status(f"Выбран пиксель x={x}, y={y}, RGB={tuple(pixel)}")

    def close(self):
        self.video_tab.close()
        self.destroy()


def main():
    App().mainloop()
