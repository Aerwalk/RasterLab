"""Вкладка обработки изображения и гистограмм."""
import tkinter as tk
from tkinter import ttk
import numpy as np
from ..histogram import draw as draw_histogram
from ..image_view import ImageView
from ...core.image import OPERATIONS, adjust, process
from ...services.files import IMAGE_TYPES, load_image, save_image
from .base import Tab

SLIDERS = [
    ("brightness", "Яркость (смещение)", -255, 255, 0, 1),
    ("contrast", "Контраст (коэффициент)", 0, 3, 1, .05),
    ("saturation", "Насыщенность (коэффициент)", 0, 3, 1, .05),
]
PARAMETERS = [
    ("kernel", "Ядро (нечётное 3…51)", "3"),
    ("gamma", "Гамма (>0)", "1.5"),
    ("low", "Canny: нижний порог", "50"),
    ("high", "Canny: верхний порог", "150"),
    ("angle", "Угол движения (°)", "0"),
    ("threshold", "Порог бинаризации (0…255)", "127"),
]


class ImageTab(Tab):
    name = "Изображение"

    def __init__(self, parent, app):
        super().__init__(parent, app, self.name)
        self.sliders = {}
        self.parameters = {}
        self.build()

    def build(self):
        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x")
        self.button(toolbar, "Открыть", self.open_image)
        self.button(toolbar, "Сохранить результат", self.save_result)
        self.button(toolbar, "Отменить шаг", self.undo)
        self.button(toolbar, "Сбросить", self.reset)
        ttk.Label(toolbar, text="Клик по изображению → цвет пикселя").pack(side="right", padx=8)

        body = ttk.Panedwindow(self, orient="horizontal")
        body.pack(fill="both", expand=True)
        controls = ttk.Frame(body, width=300)
        display = ttk.Frame(body)
        body.add(controls, weight=0)
        body.add(display, weight=1)
        self._build_info(controls)
        self._build_sliders(controls)
        self._build_operations(controls)
        self._build_views(display)

    def _build_info(self, parent):
        self.info = tk.Text(parent, width=38, height=10, wrap="word",
                            font=("Segoe UI", 9))
        self.info.pack(fill="x", padx=5)
        self.info.configure(state="disabled")

    def _build_sliders(self, parent):
        frame = ttk.LabelFrame(parent, text="Яркостные преобразования")
        frame.pack(fill="x", padx=5, pady=5)
        for key, title, low, high, default, step in SLIDERS:
            var = tk.DoubleVar(value=default)
            self.sliders[key] = var
            tk.Scale(frame, label=title, variable=var, from_=low, to=high,
                     resolution=step, orient="horizontal", length=260).pack(fill="x")
        self.button(frame, "Применить", self.apply_adjust)

    def _build_operations(self, parent):
        frame = ttk.LabelFrame(parent, text="Фильтры и анализ")
        frame.pack(fill="x", padx=5, pady=5)
        self.operation = tk.StringVar(value=OPERATIONS[0])
        ttk.Combobox(frame, textvariable=self.operation, values=OPERATIONS,
                     state="readonly", width=33).pack(fill="x", padx=3)
        for key, title, default in PARAMETERS:
            row = ttk.Frame(frame)
            row.pack(fill="x", padx=3, pady=1)
            ttk.Label(row, text=title).pack(side="left")
            var = tk.StringVar(value=default)
            self.parameters[key] = var
            ttk.Entry(row, textvariable=var, width=7).pack(side="right")
        self.button(frame, "Выполнить", self.apply_operation)

    def _build_views(self, parent):
        views = ttk.Frame(parent)
        views.pack(fill="both", expand=True)
        self.left = ImageView(views, "До последней операции", self.app.pick_pixel)
        self.right = ImageView(views, "Результат", self.app.pick_pixel)
        self.left.pack(side="left", fill="both", expand=True, padx=3)
        self.right.pack(side="left", fill="both", expand=True, padx=3)

        histbar = ttk.Frame(parent)
        histbar.pack(fill="x")
        ttk.Label(histbar, text="Гистограммы:").pack(side="left")
        self.channel = tk.StringVar(value="RGB")
        combo = ttk.Combobox(histbar, textvariable=self.channel,
                             values=["RGB", "R", "G", "B", "Яркость"],
                             state="readonly", width=10)
        combo.pack(side="left")
        combo.bind("<<ComboboxSelected>>", lambda _: self.draw_histograms())
        self.log_hist = tk.BooleanVar()
        ttk.Checkbutton(histbar, text="Логарифмическая шкала",
                        variable=self.log_hist,
                        command=self.draw_histograms).pack(side="left")
        self.histcanvas = tk.Canvas(parent, height=170, bg="white",
                                    highlightthickness=0)
        self.histcanvas.pack(fill="x", padx=4, pady=4)
        self.histcanvas.bind("<Configure>", lambda _: self.draw_histograms())

    # --- операции ---------------------------------------------------------
    def open_image(self):
        path = self.app.dialogs.open_file("Открыть изображение", IMAGE_TYPES)
        if not path:
            return
        image, info = load_image(path)
        self.app.model.load(image)
        self.info.configure(state="normal")
        self.info.delete("1.0", "end")
        self.info.insert("1.0", "\n".join(f"{k}: {v}" for k, v in info.items()))
        self.info.configure(state="disabled")
        self.refresh()
        self.app.set_status(f"Загружено: {path.name if hasattr(path, 'name') else path}")

    def save_result(self):
        self.app.model.require_loaded()
        path = self.app.dialogs.save_file("Сохранить результат", "result.png")
        if path:
            save_image(self.app.model.current, path)
            self.app.set_status(f"Сохранено: {path}")

    def undo(self):
        if self.app.model.undo():
            self.refresh()
            self.app.set_status("Последний шаг отменён.")

    def reset(self):
        self.app.model.reset()
        self._reset_sliders()
        self.refresh()
        self.app.set_status("Восстановлено исходное изображение.")

    def apply_adjust(self):
        params = {key: var.get() for key, var in self.sliders.items()}
        result = adjust(self.app.model.current, **params)
        self._commit(result, "Применены яркость, контраст и насыщенность.")
        self._reset_sliders()

    def apply_operation(self):
        params = {key: float(var.get()) for key, var in self.parameters.items()}
        if any(not np.isfinite(v) for v in params.values()):
            raise ValueError("Параметры должны быть конечными числами.")
        if params["kernel"] != int(params["kernel"]):
            raise ValueError("Размер ядра должен быть целым.")
        if not 0 <= params["threshold"] <= 255:
            raise ValueError("Порог должен быть от 0 до 255.")
        result, note = process(self.app.model.current, self.operation.get(), **params)
        self._commit(result, note or self.operation.get())
        if "\n" in note:
            self._show_note(note)

    def _commit(self, result, status):
        self.app.model.commit(result)
        self.refresh()
        self.app.set_status(status.split("\n")[0])

    def _reset_sliders(self):
        for key, var in self.sliders.items():
            var.set(0 if key == "brightness" else 1)

    def _show_note(self, note):
        window = tk.Toplevel(self)
        window.title("Иерархия контуров")
        text = tk.Text(window, width=75, height=25)
        text.pack(fill="both", expand=True)
        text.insert("1.0", note)
        text.configure(state="disabled")

    def refresh(self):
        model = self.app.model
        if not model.loaded:
            return
        self.left.show(model.before)
        self.right.show(model.current)
        self.draw_histograms()

    def draw_histograms(self):
        model = self.app.model
        if not model.loaded:
            return
        draw_histogram(self.histcanvas, model.histogram_pair(self.channel.get()),
                       self.channel.get(), self.log_hist.get())
