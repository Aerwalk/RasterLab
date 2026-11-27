"""Масштабируемый просмотр numpy-изображения на Canvas Tkinter."""
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk


class ImageView(ttk.Frame):
    """Показывает RGB/gray-массив с сохранением пропорций."""

    def __init__(self, parent, title, click=None):
        super().__init__(parent)
        ttk.Label(self, text=title, anchor="center").pack(fill="x")
        self.canvas = tk.Canvas(self, background="#18212f", highlightthickness=0,
                                width=400, height=300)
        self.canvas.pack(fill="both", expand=True)
        self.image = None
        self.mapping = None
        self.canvas.bind("<Configure>", lambda _: self.redraw())
        if click:
            self.canvas.bind("<Button-1>", lambda event: self.pick(event, click))

    def show(self, image):
        self.image = image
        self.redraw()

    def clear(self):
        self.image = None
        self.mapping = None
        self.canvas.delete("all")

    def redraw(self):
        if self.image is None:
            return
        width = max(10, self.canvas.winfo_width())
        height = max(10, self.canvas.winfo_height())
        im = Image.fromarray(self.image)
        im.thumbnail((width, height), Image.Resampling.LANCZOS)
        self.photo = ImageTk.PhotoImage(im)
        x, y = (width - im.width) // 2, (height - im.height) // 2
        self.mapping = (x, y, im.width, im.height)
        self.canvas.delete("all")
        self.canvas.create_image(x, y, image=self.photo, anchor="nw")

    def pick(self, event, callback):
        if self.image is None or self.mapping is None:
            return
        x, y, width, height = self.mapping
        if x <= event.x < x + width and y <= event.y < y + height:
            px = int((event.x - x) * self.image.shape[1] / width)
            py = int((event.y - y) * self.image.shape[0] / height)
            callback(px, py, self.image[py, px])
