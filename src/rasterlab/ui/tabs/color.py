"""Вкладка перевода цвета пикселя между шестью моделями."""
import tkinter as tk
from tkinter import ttk
from ...core import colors
from .base import Tab


class ColorTab(Tab):
    name = "Цвет пикселя"

    def __init__(self, parent, app):
        super().__init__(parent, app, self.name)
        self.components = []
        self.build()

    def build(self):
        ttk.Label(self, text="Выберите исходную модель, задайте компоненты "
                  "или кликните по изображению.", padding=12).pack(anchor="w")
        self.source_model = tk.StringVar(value="RGB")
        combo = ttk.Combobox(self, values=list(colors.MODELS),
                             textvariable=self.source_model, state="readonly")
        combo.pack(anchor="w", padx=12)
        combo.bind("<<ComboboxSelected>>", lambda _: self.build_fields())
        self.color_form = ttk.Frame(self)
        self.color_form.pack(fill="x", padx=12, pady=10)
        self.build_fields()
        row = ttk.Frame(self)
        row.pack(fill="x", padx=10)
        self.button(row, "Перевести во все модели", self.convert)
        self.color_result = tk.Text(self, height=16, font=("Consolas", 12),
                                    wrap="word")
        self.color_result.pack(fill="both", expand=True, padx=12, pady=12)
        ttk.Label(self, text="LAB: D65/2°, sRGB. CMYK: без ICC-профиля. "
                  "YCbCr: BT.601, полный диапазон.\n"
                  "Цвета вне охвата sRGB обрезаются; поэтому обратный перевод "
                  "может отличаться.", padding=12).pack(anchor="w")

    def build_fields(self):
        for child in self.color_form.winfo_children():
            child.destroy()
        self.components.clear()
        names, ranges = colors.MODELS[self.source_model.get()]
        for name, (low, high) in zip(names, ranges):
            ttk.Label(self.color_form,
                      text=f"{name} [{low}…{high}]").pack(side="left", padx=4)
            var = tk.StringVar(value="0")
            self.components.append(var)
            ttk.Entry(self.color_form, textvariable=var,
                      width=10).pack(side="left", padx=4)

    def convert(self):
        values = [float(var.get()) for var in self.components]
        rgb = colors.to_rgb(self.source_model.get(), values)
        lines = []
        for model, (names, _) in colors.MODELS.items():
            components = colors.from_rgb(model, rgb)
            lines.append(f"{model:6s}: " + ", ".join(
                f"{name}={value:.4f}" for name, value in zip(names, components)))
        self.color_result.delete("1.0", "end")
        self.color_result.insert("1.0", "\n".join(lines))

    def set_pixel(self, pixel):
        self.source_model.set("RGB")
        self.build_fields()
        for var, value in zip(self.components, pixel):
            var.set(str(value))
        self.convert()
        self.app.tabs.select(self)
