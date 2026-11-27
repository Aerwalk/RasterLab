"""Вкладка поиска двух наиболее похожих изображений."""
from tkinter import ttk
from ..image_view import ImageView
from ...core.features import closest_pair
from ...services.files import IMAGE_TYPES, load_image
from .base import Tab


class CompareTab(Tab):
    name = "Похожие изображения"

    def __init__(self, parent, app):
        super().__init__(parent, app, self.name)
        self.build()

    def build(self):
        row = ttk.Frame(self)
        row.pack(fill="x")
        self.button(row, "Загрузить 3–10 изображений и найти пару", self.compare)
        ttk.Label(self, text="Метрика: 50% расстояния цветовых гистограмм + "
                  "50% расстояния pHash.\nЭто визуальное, а не семантическое "
                  "сходство; меньшая дистанция означает большее сходство.",
                  padding=10).pack(anchor="w")
        self.pair_label = ttk.Label(self, text="", padding=10, wraplength=950)
        self.pair_label.pack(fill="x")
        views = ttk.Frame(self)
        views.pack(fill="both", expand=True)
        self.pair_views = [ImageView(views, "Первое изображение"),
                           ImageView(views, "Второе изображение")]
        for view in self.pair_views:
            view.pack(side="left", fill="both", expand=True)

    def compare(self):
        paths = self.app.dialogs.open_files("Выберите 3–10 изображений", IMAGE_TYPES)
        if not paths:
            return
        if not 3 <= len(paths) <= 10:
            raise ValueError("Необходимо выбрать от 3 до 10 файлов.")
        self.app.set_status("Сравнение изображений…")
        self.app.update_idletasks()
        images = [load_image(path)[0] for path in paths]
        i, j, distance = closest_pair(images)
        for view, index in zip(self.pair_views, (i, j)):
            view.show(images[index])
        self.pair_label.configure(
            text=f"{paths[i]}\n{paths[j]}\nДистанция: {distance:.5f} "
                 "(0 — совпадение признаков)")
        self.app.set_status(f"Сравнено {len(paths)} изображений; проверены все пары.")
