from pathlib import Path
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import cv2
import numpy as np
from PIL import Image, ImageTk
from . import colors
from .processing import (load_image, process, adjust, histogram, closest_pair,
                         VideoProcessor, OPERATIONS)

IMAGE_TYPES = [("Изображения", "*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp *.gif"), ("Все файлы", "*.*")]


class ImageView(ttk.Frame):
    def __init__(self, parent, title, click=None):
        super().__init__(parent)
        ttk.Label(self, text=title, anchor="center").pack(fill="x")
        self.canvas = tk.Canvas(self, background="#18212f", highlightthickness=0, width=400, height=300)
        self.canvas.pack(fill="both", expand=True)
        self.image = None
        self.mapping = None
        self.canvas.bind("<Configure>", lambda _: self.redraw())
        if click:
            self.canvas.bind("<Button-1>", lambda event: self.pick(event, click))

    def show(self, image):
        self.image = image
        self.redraw()

    def redraw(self):
        if self.image is None:
            return
        w, h = max(10, self.canvas.winfo_width()), max(10, self.canvas.winfo_height())
        im = Image.fromarray(self.image)
        im.thumbnail((w, h), Image.Resampling.LANCZOS)
        self.photo = ImageTk.PhotoImage(im)
        x, y = (w - im.width) // 2, (h - im.height) // 2
        self.mapping = (x, y, im.width, im.height)
        self.canvas.delete("all")
        self.canvas.create_image(x, y, image=self.photo, anchor="nw")

    def pick(self, event, callback):
        if self.image is None or self.mapping is None:
            return
        x, y, w, h = self.mapping
        if x <= event.x < x + w and y <= event.y < y + h:
            px = int((event.x - x) * self.image.shape[1] / w)
            py = int((event.y - y) * self.image.shape[0] / h)
            callback(px, py, self.image[py, px])


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("RasterLab — практическая работа")
        self.geometry("1380x900")
        self.minsize(1000, 720)
        self.original = self.current = self.before = None
        self.undo_image = None
        self.capture = None
        self.video_job = None
        self.running = False
        self.video_path = None
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.status = tk.StringVar(value="Загрузите изображение или видео.")
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True, padx=8, pady=8)
        self.image_tab = ttk.Frame(self.tabs)
        self.color_tab = ttk.Frame(self.tabs)
        self.compare_tab = ttk.Frame(self.tabs)
        self.video_tab = ttk.Frame(self.tabs)
        for tab, text in [(self.image_tab, "Изображение"), (self.color_tab, "Цвет пикселя"),
                          (self.compare_tab, "Похожие изображения"), (self.video_tab, "Видео")]:
            self.tabs.add(tab, text=text)
        self.build_image()
        self.build_colors()
        self.build_compare()
        self.build_video()
        ttk.Label(self, textvariable=self.status, anchor="w").pack(fill="x", padx=10, pady=4)

    def guarded(self, action):
        try:
            action()
        except Exception as exc:
            messagebox.showerror("Ошибка", str(exc), parent=self)
            self.status.set(str(exc))

    def button(self, parent, text, action):
        button = ttk.Button(parent, text=text, command=lambda: self.guarded(action))
        button.pack(side="left", padx=3, pady=4)
        return button

    def build_image(self):
        toolbar = ttk.Frame(self.image_tab)
        toolbar.pack(fill="x")
        for text, action in [("Открыть", self.open_image), ("Сохранить результат", self.save_image),
                             ("Отменить шаг", self.undo), ("Сбросить", self.reset)]:
            self.button(toolbar, text, action)
        ttk.Label(toolbar, text="Клик по изображению → цвет пикселя").pack(side="right", padx=8)
        body = ttk.Panedwindow(self.image_tab, orient="horizontal")
        body.pack(fill="both", expand=True)
        controls = ttk.Frame(body, width=300)
        display = ttk.Frame(body)
        body.add(controls, weight=0)
        body.add(display, weight=1)
        self.info = tk.Text(controls, width=38, height=10, wrap="word", font=("Segoe UI", 9))
        self.info.pack(fill="x", padx=5)
        self.info.configure(state="disabled")
        sliders = ttk.LabelFrame(controls, text="Яркостные преобразования")
        sliders.pack(fill="x", padx=5, pady=5)
        self.sliders = {}
        for key, title, lo, hi, default, step in [
            ("brightness", "Яркость (смещение)", -255, 255, 0, 1),
            ("contrast", "Контраст (коэффициент)", 0, 3, 1, .05),
            ("saturation", "Насыщенность (коэффициент)", 0, 3, 1, .05),
        ]:
            var = tk.DoubleVar(value=default)
            self.sliders[key] = var
            tk.Scale(sliders, label=title, variable=var, from_=lo, to=hi, resolution=step,
                     orient="horizontal", length=260).pack(fill="x")
        self.button(sliders, "Применить", self.apply_adjust)
        ops = ttk.LabelFrame(controls, text="Фильтры и анализ")
        ops.pack(fill="x", padx=5, pady=5)
        self.operation = tk.StringVar(value=OPERATIONS[0])
        ttk.Combobox(ops, textvariable=self.operation, values=OPERATIONS, state="readonly", width=33).pack(fill="x", padx=3)
        self.parameters = {}
        for key, title, default in [("kernel", "Ядро (нечётное 3…51)", "3"),
                                    ("gamma", "Гамма (>0)", "1.5"),
                                    ("low", "Canny: нижний порог", "50"),
                                    ("high", "Canny: верхний порог", "150"),
                                    ("angle", "Угол движения (°)", "0"),
                                    ("threshold", "Порог бинаризации (0…255)", "127")]:
            row = ttk.Frame(ops)
            row.pack(fill="x", padx=3, pady=1)
            ttk.Label(row, text=title).pack(side="left")
            var = tk.StringVar(value=default)
            self.parameters[key] = var
            ttk.Entry(row, textvariable=var, width=7).pack(side="right")
        self.button(ops, "Выполнить", self.apply_operation)
        views = ttk.Frame(display)
        views.pack(fill="both", expand=True)
        self.left = ImageView(views, "До последней операции", self.pick_pixel)
        self.right = ImageView(views, "Результат", self.pick_pixel)
        self.left.pack(side="left", fill="both", expand=True, padx=3)
        self.right.pack(side="left", fill="both", expand=True, padx=3)
        histbar = ttk.Frame(display)
        histbar.pack(fill="x")
        ttk.Label(histbar, text="Гистограммы:").pack(side="left")
        self.channel = tk.StringVar(value="RGB")
        combo = ttk.Combobox(histbar, textvariable=self.channel, values=["RGB", "R", "G", "B", "Яркость"],
                             state="readonly", width=10)
        combo.pack(side="left")
        combo.bind("<<ComboboxSelected>>", lambda _: self.draw_histograms())
        self.log_hist = tk.BooleanVar()
        ttk.Checkbutton(histbar, text="Логарифмическая шкала", variable=self.log_hist,
                        command=self.draw_histograms).pack(side="left")
        self.histcanvas = tk.Canvas(display, height=170, bg="white", highlightthickness=0)
        self.histcanvas.pack(fill="x", padx=4, pady=4)
        self.histcanvas.bind("<Configure>", lambda _: self.draw_histograms())

    def require_image(self):
        if self.current is None:
            raise ValueError("Сначала загрузите изображение.")

    def open_image(self):
        path = filedialog.askopenfilename(filetypes=IMAGE_TYPES)
        if not path:
            return
        image, info = load_image(path)
        self.original = image.copy()
        self.current = image
        self.before = image.copy()
        self.undo_image = None
        self.info.configure(state="normal")
        self.info.delete("1.0", "end")
        self.info.insert("1.0", "\n".join(f"{key}: {value}" for key, value in info.items()))
        self.info.configure(state="disabled")
        self.refresh()
        self.status.set(f"Загружено: {Path(path).name}")

    def refresh(self):
        self.left.show(self.before)
        self.right.show(self.current)
        self.draw_histograms()

    def commit(self, image, text):
        self.undo_image = self.current.copy()
        self.before = self.current.copy()
        self.current = image
        self.refresh()
        self.status.set(text.split("\n")[0])

    def save_image(self):
        self.require_image()
        path = filedialog.asksaveasfilename(defaultextension=".png",
                                           filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg"), ("TIFF", "*.tif")])
        if path:
            Image.fromarray(self.current).save(path)
            self.status.set(f"Сохранено: {path}")

    def undo(self):
        self.require_image()
        if self.undo_image is not None:
            previous = self.undo_image
            self.before = self.current.copy()
            self.current = previous
            self.undo_image = None
            self.refresh()
            self.status.set("Последний шаг отменён.")

    def reset(self):
        self.require_image()
        self.commit(self.original.copy(), "Восстановлено исходное изображение.")
        for key, value in self.sliders.items():
            value.set(0 if key == "brightness" else 1)

    def apply_adjust(self):
        self.require_image()
        self.commit(adjust(self.current, **{k: v.get() for k, v in self.sliders.items()}),
                    "Применены яркость, контраст и насыщенность. Гистограммы: до / после.")
        for key, value in self.sliders.items():
            value.set(0 if key == "brightness" else 1)

    def apply_operation(self):
        self.require_image()
        params = {key: float(var.get()) for key, var in self.parameters.items()}
        if any(not np.isfinite(v) for v in params.values()):
            raise ValueError("Параметры должны быть конечными числами.")
        if params["kernel"] != int(params["kernel"]):
            raise ValueError("Размер ядра должен быть целым.")
        if not 0 <= params["threshold"] <= 255:
            raise ValueError("Порог должен быть от 0 до 255.")
        result, note = process(self.current, self.operation.get(), **params)
        self.commit(result, note or self.operation.get())
        if "\n" in note:
            window = tk.Toplevel(self)
            window.title("Иерархия контуров")
            text = tk.Text(window, width=75, height=25)
            text.pack(fill="both", expand=True)
            text.insert("1.0", note)
            text.configure(state="disabled")

    def draw_histograms(self):
        if self.current is None:
            return
        canvas = self.histcanvas
        canvas.delete("all")
        width, height = max(300, canvas.winfo_width()), 170
        arrays = []
        for image in (self.before, self.current):
            if self.channel.get() == "Яркость":
                g = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
                arrays.append([np.bincount(g.ravel(), minlength=256)])
            else:
                h = histogram(image)
                arrays.append(h if self.channel.get() == "RGB" else [h["RGB".index(self.channel.get())]])
        if self.log_hist.get():
            arrays = [np.log1p(a) for a in arrays]
        maximum = max(1, max(np.max(a) for a in arrays))
        palette = ["#e04545", "#26924e", "#3976dd"] if self.channel.get() == "RGB" else [{
            "R": "#e04545", "G": "#26924e", "B": "#3976dd", "Яркость": "#333333"}[self.channel.get()]]
        for index, hist in enumerate(arrays):
            x0, y0 = index * width / 2 + 48, height - 25
            chart_w = width / 2 - 65
            canvas.create_text(x0 + chart_w / 2, 12, text="До" if index == 0 else "После")
            canvas.create_line(x0, 28, x0, y0, x0 + chart_w, y0, fill="#999")
            canvas.create_text(x0 - 4, 30, text=f"{maximum:.0f}", anchor="e", font=("Arial", 8))
            for series, color in zip(hist, palette):
                points = []
                for i, count in enumerate(series):
                    points.extend((x0 + i * chart_w / 255, y0 - count / maximum * (y0 - 30)))
                canvas.create_line(*points, fill=color)
            canvas.create_text(x0, y0 + 12, text="0")
            canvas.create_text(x0 + chart_w, y0 + 12, text="255")

    def build_colors(self):
        ttk.Label(self.color_tab, text="Выберите исходную модель, задайте компоненты или кликните по изображению.",
                  padding=12).pack(anchor="w")
        self.source_model = tk.StringVar(value="RGB")
        combo = ttk.Combobox(self.color_tab, values=list(colors.MODELS), textvariable=self.source_model,
                             state="readonly")
        combo.pack(anchor="w", padx=12)
        combo.bind("<<ComboboxSelected>>", lambda _: self.color_fields())
        self.color_form = ttk.Frame(self.color_tab)
        self.color_form.pack(fill="x", padx=12, pady=10)
        self.color_fields()
        row = ttk.Frame(self.color_tab)
        row.pack(fill="x", padx=10)
        self.button(row, "Перевести во все модели", self.convert_color)
        self.color_result = tk.Text(self.color_tab, height=16, font=("Consolas", 12), wrap="word")
        self.color_result.pack(fill="both", expand=True, padx=12, pady=12)
        ttk.Label(self.color_tab, text="LAB: D65/2°, sRGB. CMYK: без ICC-профиля. YCbCr: BT.601, полный диапазон.\n"
                  "Цвета вне охвата sRGB обрезаются; поэтому обратный перевод может отличаться.", padding=12).pack(anchor="w")

    def color_fields(self):
        for child in self.color_form.winfo_children():
            child.destroy()
        self.components = []
        names, ranges = colors.MODELS[self.source_model.get()]
        for name, (lo, hi) in zip(names, ranges):
            ttk.Label(self.color_form, text=f"{name} [{lo}…{hi}]").pack(side="left", padx=4)
            value = tk.StringVar(value="0")
            self.components.append(value)
            ttk.Entry(self.color_form, textvariable=value, width=10).pack(side="left", padx=4)

    def convert_color(self):
        values = [float(v.get()) for v in self.components]
        rgb = colors.to_rgb(self.source_model.get(), values)
        lines = []
        for model, (names, _) in colors.MODELS.items():
            components = colors.from_rgb(model, rgb)
            lines.append(f"{model:6s}: " + ", ".join(f"{n}={v:.4f}" for n, v in zip(names, components)))
        self.color_result.delete("1.0", "end")
        self.color_result.insert("1.0", "\n".join(lines))

    def pick_pixel(self, x, y, pixel):
        self.source_model.set("RGB")
        self.color_fields()
        for var, value in zip(self.components, pixel):
            var.set(str(value))
        self.convert_color()
        self.tabs.select(self.color_tab)
        self.status.set(f"Выбран пиксель x={x}, y={y}, RGB={tuple(pixel)}")

    def build_compare(self):
        row = ttk.Frame(self.compare_tab)
        row.pack(fill="x")
        self.button(row, "Загрузить 3–10 изображений и найти пару", self.compare)
        ttk.Label(self.compare_tab, text="Метрика: 50% расстояния цветовых гистограмм + 50% расстояния pHash.\n"
                  "Это визуальное, а не семантическое сходство; меньшая дистанция означает большее сходство.",
                  padding=10).pack(anchor="w")
        self.pair_label = ttk.Label(self.compare_tab, text="", padding=10, wraplength=950)
        self.pair_label.pack(fill="x")
        views = ttk.Frame(self.compare_tab)
        views.pack(fill="both", expand=True)
        self.pair_views = [ImageView(views, "Первое изображение"), ImageView(views, "Второе изображение")]
        for view in self.pair_views:
            view.pack(side="left", fill="both", expand=True)

    def compare(self):
        paths = filedialog.askopenfilenames(filetypes=IMAGE_TYPES)
        if not paths:
            return
        if not 3 <= len(paths) <= 10:
            raise ValueError("Необходимо выбрать от 3 до 10 файлов.")
        self.status.set("Сравнение изображений…")
        self.update_idletasks()
        images = [load_image(path)[0] for path in paths]
        i, j, distance = closest_pair(images)
        for view, index in zip(self.pair_views, (i, j)):
            view.show(images[index])
        self.pair_label.configure(text=f"{paths[i]}\n{paths[j]}\nДистанция: {distance:.5f} (0 — совпадение признаков)")
        self.status.set(f"Сравнено {len(paths)} изображений; проверены все пары.")

    def build_video(self):
        row = ttk.Frame(self.video_tab)
        row.pack(fill="x")
        self.button(row, "Открыть видео", self.open_video)
        self.play_button = self.button(row, "Пуск / пауза", self.toggle_video)
        self.button(row, "С начала", self.restart_video)
        self.video_mode = tk.StringVar(value="Вычитание фона")
        ttk.Combobox(row, textvariable=self.video_mode, values=["Вычитание фона", "Размытие объектов"],
                     state="readonly", width=24).pack(side="left", padx=8)
        self.video_info = ttk.Label(self.video_tab, text="MOG2: первые кадры используются для обучения фона.", padding=10)
        self.video_info.pack(fill="x")
        views = ttk.Frame(self.video_tab)
        views.pack(fill="both", expand=True)
        self.video_views = [ImageView(views, "Исходный кадр"), ImageView(views, "Результат")]
        for view in self.video_views:
            view.pack(side="left", fill="both", expand=True)
        ttk.Label(self.video_tab, text="Для неподвижной камеры. Тени исключаются из маски; маска очищается морфологией.\n"
                  "Размытие применяется внутри расширенной маски движения. Звук не воспроизводится.",
                  padding=10).pack(anchor="w")

    def stop_video(self):
        self.running = False
        if self.video_job is not None:
            self.after_cancel(self.video_job)
            self.video_job = None

    def open_video(self):
        path = filedialog.askopenfilename(filetypes=[("Видео", "*.mp4 *.avi *.mov *.mkv *.webm"), ("Все файлы", "*.*")])
        if path:
            self.start_video(path)

    def start_video(self, path):
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            cap.release()
            raise ValueError("Не удалось открыть видео. Проверьте файл и поддержку кодека.")
        self.stop_video()
        if self.capture:
            self.capture.release()
        self.capture = cap
        self.video_path = path
        self.processor = VideoProcessor()
        fps = cap.get(cv2.CAP_PROP_FPS)
        self.fps = fps if np.isfinite(fps) and fps > 0 else 25
        self.total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.frame_index = 0
        self.running = True
        self.video_tick()

    def restart_video(self):
        if not self.video_path:
            raise ValueError("Сначала загрузите видео.")
        self.start_video(self.video_path)

    def toggle_video(self):
        if self.capture is None:
            raise ValueError("Сначала загрузите видео.")
        if self.running:
            self.stop_video()
        else:
            self.running = True
            self.video_tick()

    def video_tick(self):
        self.video_job = None
        if not self.running:
            return
        started = time.perf_counter()
        try:
            ok, frame = self.capture.read()
            if not ok:
                self.stop_video()
                self.status.set("Конец видео. Для повторного просмотра нажмите «С начала».")
                return
            # Limit preview processing cost without distorting aspect ratio.
            h, w = frame.shape[:2]
            if w > 960:
                frame = cv2.resize(frame, (960, round(h * 960 / w)))
            mask, blurred = self.processor.apply(frame)
            result = mask if self.video_mode.get() == "Вычитание фона" else cv2.cvtColor(blurred, cv2.COLOR_BGR2RGB)
            self.video_views[0].show(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            self.video_views[1].show(result)
            self.frame_index += 1
            self.video_info.configure(text=f"{Path(self.video_path).name} | кадр {self.frame_index}/{self.total_frames} | "
                                      f"{self.frame_index / self.fps:.1f} с | {self.fps:.2f} FPS | "
                                      + ("Обучение фона" if self.frame_index < 30 else "Обработка"))
            delay = max(1, int(1000 / self.fps - (time.perf_counter() - started) * 1000))
            self.video_job = self.after(delay, self.video_tick)
        except Exception as exc:
            self.stop_video()
            messagebox.showerror("Ошибка видео", str(exc), parent=self)

    def close(self):
        self.stop_video()
        if self.capture:
            self.capture.release()
        self.destroy()


def main():
    app = App()
    app.mainloop()
