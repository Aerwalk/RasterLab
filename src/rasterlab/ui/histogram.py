"""Отрисовка двух гистограмм с общей шкалой."""
import numpy as np

PALETTE = {"R": "#e04545", "G": "#26924e", "B": "#3976dd", "Яркость": "#333333"}


def draw(canvas, arrays, channel="RGB", logarithmic=False):
    canvas.delete("all")
    width, height = max(300, canvas.winfo_width()), 170
    if logarithmic:
        arrays = [np.log1p(a) for a in arrays]
    maximum = max(1, max(np.max(a) for a in arrays)) if arrays else 1
    colors = [PALETTE[c] for c in channel] if channel == "RGB" else [PALETTE[channel]]
    for index, hist in enumerate(arrays):
        x0, y0 = index * width / 2 + 48, height - 25
        chart_width = width / 2 - 65
        canvas.create_text(x0 + chart_width / 2, 12,
                           text="До" if index == 0 else "После")
        canvas.create_line(x0, 28, x0, y0, x0 + chart_width, y0, fill="#999")
        canvas.create_text(x0 - 4, 30, text=f"{maximum:.0f}", anchor="e",
                           font=("Arial", 8))
        for series, color in zip(hist, colors):
            points = []
            for i, count in enumerate(series):
                points.extend((x0 + i * chart_width / 255,
                               y0 - count / maximum * (y0 - 30)))
            canvas.create_line(*points, fill=color)
        canvas.create_text(x0, y0 + 12, text="0")
        canvas.create_text(x0 + chart_width, y0 + 12, text="255")
