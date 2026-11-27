"""Преобразования sRGB, упрощённого CMYK, HSL, HSV, Lab D65, YCbCr BT.601."""
import colorsys
import numpy as np

MODELS = {
    "RGB": (("R", "G", "B"), ((0, 255),) * 3),
    "CMYK": (("C", "M", "Y", "K"), ((0, 100),) * 4),
    "HSL": (("H", "S", "L"), ((0, 360), (0, 100), (0, 100))),
    "HSV": (("H", "S", "V"), ((0, 360), (0, 100), (0, 100))),
    "LAB": (("L*", "a*", "b*"), ((0, 100), (-128, 127), (-128, 127))),
    "YCbCr": (("Y", "Cb", "Cr"), ((0, 255),) * 3),
}

M = np.array([[.4124564, .3575761, .1804375],
              [.2126729, .7151522, .0721750],
              [.0193339, .1191920, .9503041]])
WHITE = np.array([.95047, 1., 1.08883])
YCC = np.array([[.299, .587, .114], [-.168736, -.331264, .5],
                [.5, -.418688, -.081312]])


def to_rgb(model, values):
    """Приводит компоненты модели к линейному нормированному RGB [0,1]."""
    v = np.asarray(values, dtype=float)
    if len(v) != len(MODELS[model][0]) or not np.all(np.isfinite(v)):
        raise ValueError("Неверное количество компонентов или нечисловое значение.")
    if any(not lo <= x <= hi for x, (lo, hi) in zip(v, MODELS[model][1])):
        raise ValueError("Компоненты выходят за диапазоны, указанные рядом с полями.")
    if model == "RGB":
        rgb = v / 255
    elif model == "CMYK":
        rgb = (1 - v[:3] / 100) * (1 - v[3] / 100)
    elif model == "HSL":
        rgb = colorsys.hls_to_rgb(v[0] / 360, v[2] / 100, v[1] / 100)
    elif model == "HSV":
        rgb = colorsys.hsv_to_rgb(v[0] / 360, v[1] / 100, v[2] / 100)
    elif model == "YCbCr":
        rgb = np.linalg.solve(YCC, v - [0, 128, 128]) / 255
    else:
        fy = (v[0] + 16) / 116
        f = np.array([fy + v[1] / 500, fy, fy - v[2] / 200])
        d = 6 / 29
        xyz = np.where(f > d, f ** 3, 3 * d * d * (f - 4 / 29)) * WHITE
        linear = np.linalg.solve(M, xyz)
        rgb = np.where(linear <= .0031308, 12.92 * linear,
                       1.055 * np.maximum(linear, 0) ** (1 / 2.4) - .055)
    return np.clip(rgb, 0, 1)


def from_rgb(model, rgb):
    """Переводит нормированное RGB [0,1] в компоненты заданной модели."""
    r, g, b = rgb = np.clip(np.asarray(rgb, dtype=float), 0, 1)
    if model == "RGB":
        return rgb * 255
    if model == "CMYK":
        k = 1 - max(rgb)
        return np.array([0, 0, 0, 100]) if k == 1 else np.r_[(1 - rgb - k) / (1 - k), k] * 100
    if model == "HSL":
        h, l, s = colorsys.rgb_to_hls(r, g, b)
        return np.array([h * 360, s * 100, l * 100])
    if model == "HSV":
        h, s, v = colorsys.rgb_to_hsv(r, g, b)
        return np.array([h * 360, s * 100, v * 100])
    if model == "YCbCr":
        return np.clip(YCC @ (rgb * 255) + [0, 128, 128], 0, 255)
    linear = np.where(rgb <= .04045, rgb / 12.92, ((rgb + .055) / 1.055) ** 2.4)
    t = M @ linear / WHITE
    d = 6 / 29
    f = np.where(t > d ** 3, np.cbrt(t), t / (3 * d * d) + 4 / 29)
    return np.array([np.clip(116 * f[1] - 16, 0, 100),
                     500 * (f[0] - f[1]), 200 * (f[1] - f[2])])


def convert(source, target, values):
    """Перевод A -> RGB -> B."""
    return from_rgb(target, to_rgb(source, values))
