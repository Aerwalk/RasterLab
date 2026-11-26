from pathlib import Path
from itertools import combinations
import cv2
import numpy as np
from PIL import Image, ImageOps

OPERATIONS = [
    "Градации серого", "Линейная коррекция", "Гамма-коррекция", "Логарифмическая коррекция",
    "Эквализация", "Эрозия", "Дилатация", "Открытие", "Закрытие", "Градиент",
    "Резкость", "Размытие в движении", "Тиснение", "Медианный фильтр",
    "Canny", "Робертс", "Харрис", "SIFT", "FAST",
    "Бинаризация: порог", "Бинаризация: Оцу", "Бинаризация: адаптивная", "Контуры",
]


def load_image(path):
    with Image.open(path) as im:
        fmt, mode, size = im.format, im.mode, im.size
        depth = {"1": 1, "L": 8, "LA": 16, "P": 8, "RGB": 24, "RGBA": 32,
                 "CMYK": 32, "I": 32, "F": 32}.get(mode, 16 if mode.startswith("I;16") else None)
        # PNG stores source bit depth separately from Pillow's decoded mode.
        if fmt == "PNG":
            with open(path, "rb") as stream:
                header = stream.read(26)
            depth = header[24] * {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[header[25]]
        elif fmt == "BMP":
            with open(path, "rb") as stream:
                header = stream.read(30)
            dib_size = int.from_bytes(header[14:18], "little")
            offset = 24 if dib_size == 12 else 28
            depth = int.from_bytes(header[offset:offset + 2], "little")
        elif fmt == "TIFF":
            bits = im.tag_v2.get(258)
            if bits:
                depth = sum(bits) if isinstance(bits, tuple) else int(bits)
        info = {
            "Файл": str(Path(path).resolve()), "Размер на диске": f"{Path(path).stat().st_size:,} байт",
            "Разрешение файла": f"{size[0]} × {size[1]} px",
            "Глубина файла": f"{depth} бит/пиксель" if depth else "не определена",
            "Формат": fmt, "Режим файла": mode, "DPI": str(im.info.get("dpi", "не задан")),
            "Кадров": str(getattr(im, "n_frames", 1)),
            "ICC-профиль": "есть" if im.info.get("icc_profile") else "нет",
            "Рабочее представление": "sRGB-подобное RGB, 8 бит/канал; альфа на белом фоне",
        }
        oriented = ImageOps.exif_transpose(im)
        if mode.startswith("I;16") or (mode == "I" and fmt == "PNG"):
            a = np.asarray(oriented, dtype=float)
            oriented = Image.fromarray(np.uint8(np.clip(a / 257, 0, 255)))
        if "A" in oriented.getbands() or "transparency" in im.info:
            rgba = oriented.convert("RGBA")
            bg = Image.new("RGBA", rgba.size, "white")
            bg.alpha_composite(rgba)
            oriented = bg
        return np.array(oriented.convert("RGB")), info


def gray(image):
    return cv2.cvtColor(image, cv2.COLOR_RGB2GRAY) if image.ndim == 3 else image


def rgb(image):
    return cv2.cvtColor(image, cv2.COLOR_GRAY2RGB) if image.ndim == 2 else image


def adjust(image, brightness=0, contrast=1, saturation=1):
    a = np.clip((image.astype(float) - 127.5) * contrast + 127.5 + brightness, 0, 255).astype(np.uint8)
    hsv = cv2.cvtColor(rgb(a), cv2.COLOR_RGB2HSV).astype(float)
    hsv[..., 1] = np.clip(hsv[..., 1] * saturation, 0, 255)
    return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)


def process(image, operation, kernel=3, gamma=1.5, low=50, high=150, angle=0, threshold=127):
    k = int(kernel)
    if not 3 <= k <= 51 or k % 2 == 0:
        raise ValueError("Размер ядра должен быть нечётным: от 3 до 51.")
    g = gray(image)
    a = rgb(image).copy()
    note = ""
    morph = {"Эрозия": cv2.MORPH_ERODE, "Дилатация": cv2.MORPH_DILATE,
             "Открытие": cv2.MORPH_OPEN, "Закрытие": cv2.MORPH_CLOSE, "Градиент": cv2.MORPH_GRADIENT}
    if operation == "Градации серого":
        out = g
    elif operation == "Линейная коррекция":
        out = cv2.normalize(g, None, 0, 255, cv2.NORM_MINMAX) if g.max() != g.min() else g.copy()
    elif operation == "Гамма-коррекция":
        if not np.isfinite(gamma) or gamma <= 0:
            raise ValueError("Гамма должна быть положительной.")
        out = np.uint8(np.clip(255 * (g / 255.) ** gamma, 0, 255))
    elif operation == "Логарифмическая коррекция":
        out = np.uint8(255 * np.log1p(g.astype(float)) / np.log(256))
    elif operation == "Эквализация":
        out = cv2.equalizeHist(g)
    elif operation in morph:
        out = cv2.morphologyEx(g, morph[operation], np.ones((k, k), np.uint8))
    elif operation == "Резкость":
        out = cv2.addWeighted(a, 1.8, cv2.GaussianBlur(a, (k, k), 0), -.8, 0)
    elif operation == "Размытие в движении":
        filt = np.zeros((k, k), np.float32)
        filt[k // 2, :] = 1
        rotation = cv2.getRotationMatrix2D((k // 2, k // 2), angle, 1)
        filt = cv2.warpAffine(filt, rotation, (k, k))
        out = cv2.filter2D(a, -1, filt / filt.sum())
    elif operation == "Тиснение":
        filt = np.array([[-2, -1, 0], [-1, 1, 1], [0, 1, 2]], np.float32)
        out = np.uint8(np.clip(cv2.filter2D(g.astype(np.float32), -1, filt) + 128, 0, 255))
    elif operation == "Медианный фильтр":
        out = cv2.medianBlur(a, k)
    elif operation == "Canny":
        if not 0 <= low < high <= 255:
            raise ValueError("Для Canny нужно 0 ≤ нижний порог < верхний ≤ 255.")
        out = cv2.Canny(cv2.GaussianBlur(g, (k, k), 0), low, high)
    elif operation == "Робертс":
        x = cv2.filter2D(g.astype(np.float32), -1, np.array([[1, 0], [0, -1]], np.float32))
        y = cv2.filter2D(g.astype(np.float32), -1, np.array([[0, 1], [-1, 0]], np.float32))
        out = np.uint8(np.clip(np.hypot(x, y), 0, 255))
    elif operation == "Харрис":
        response = cv2.cornerHarris(g.astype(np.float32), 2, 3, .04)
        peaks = (response == cv2.dilate(response, None)) & (response > max(0, .01 * response.max()))
        points = np.argwhere(peaks)
        for y, x in points:
            cv2.circle(a, (int(x), int(y)), 3, (255, 60, 30), 1)
        out, note = a, f"Харрис: {len(points)} точек"
    elif operation in ("SIFT", "FAST"):
        detector = cv2.SIFT_create(nfeatures=1500) if operation == "SIFT" else cv2.FastFeatureDetector_create()
        points = detector.detect(g, None)
        out = cv2.drawKeypoints(a, points, None, color=(255, 60, 30),
                               flags=cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)
        note = f"{operation}: {len(points)} точек"
    elif operation == "Бинаризация: порог":
        out = cv2.threshold(g, threshold, 255, cv2.THRESH_BINARY)[1]
    elif operation in ("Бинаризация: Оцу", "Контуры"):
        t, out = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        note = f"Порог Оцу: {t:g}"
        if operation == "Контуры":
            contours, hierarchy = cv2.findContours(out, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            out = cv2.drawContours(a, contours, -1, (0, 255, 80), 2)
            note += f"; контуров: {len(contours)}"
            if hierarchy is not None:
                note += "\nИндекс: [следующий, предыдущий, первый ребёнок, родитель]\n"
                note += "\n".join(f"{i}: {h.tolist()}" for i, h in enumerate(hierarchy[0]))
    elif operation == "Бинаризация: адаптивная":
        out = cv2.adaptiveThreshold(g, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, k, 2)
    else:
        raise ValueError("Неизвестная операция")
    return rgb(out), note


def histogram(image):
    return np.array([np.bincount(c.ravel(), minlength=256) for c in rgb(image).transpose(2, 0, 1)])


def closest_pair(images):
    """Сходство цвета (Hellinger) + структуры (низкочастотный pHash)."""
    if not 3 <= len(images) <= 10:
        raise ValueError("Выберите от 3 до 10 изображений.")
    features = []
    for image in images:
        hsv = cv2.cvtColor(rgb(image), cv2.COLOR_RGB2HSV)
        hist = cv2.calcHist([hsv], [0, 1], None, [32, 32], [0, 180, 0, 256]).ravel()
        hist /= hist.sum()
        small = cv2.resize(gray(image), (32, 32)).astype(np.float32)
        dct = cv2.dct(small)[:8, :8].ravel()[1:]
        features.append((hist, dct > np.median(dct)))
    best = None
    for i, j in combinations(range(len(images)), 2):
        h1, p1 = features[i]
        h2, p2 = features[j]
        color = np.sqrt(max(0, 1 - float(np.sqrt(h1 * h2).sum())))
        distance = .5 * color + .5 * np.mean(p1 != p2)
        if best is None or distance < best[2]:
            best = i, j, float(distance)
    return best


class VideoProcessor:
    def __init__(self):
        self.background = cv2.createBackgroundSubtractorMOG2(history=300, varThreshold=25, detectShadows=True)

    def apply(self, frame):
        mask = self.background.apply(frame)
        mask = cv2.threshold(mask, 200, 255, cv2.THRESH_BINARY)[1]
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
        region = cv2.dilate(mask, np.ones((9, 9), np.uint8))
        blurred = cv2.GaussianBlur(frame, (31, 31), 0)
        result = np.where(region[..., None] > 0, blurred, frame)
        return mask, result
