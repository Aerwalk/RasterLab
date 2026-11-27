"""Операции над массивом изображения: представление, коррекция, фильтры, гистограммы."""
import cv2
import numpy as np

OPERATIONS = [
    "Градации серого", "Линейная коррекция", "Гамма-коррекция", "Логарифмическая коррекция",
    "Эквализация", "Эрозия", "Дилатация", "Открытие", "Закрытие", "Градиент",
    "Резкость", "Размытие в движении", "Тиснение", "Медианный фильтр",
    "Canny", "Робертс", "Харрис", "SIFT", "FAST",
    "Бинаризация: порог", "Бинаризация: Оцу", "Бинаризация: адаптивная", "Контуры",
]

MORPH = {"Эрозия": cv2.MORPH_ERODE, "Дилатация": cv2.MORPH_DILATE,
         "Открытие": cv2.MORPH_OPEN, "Закрытие": cv2.MORPH_CLOSE,
         "Градиент": cv2.MORPH_GRADIENT}


def gray(image):
    return cv2.cvtColor(image, cv2.COLOR_RGB2GRAY) if image.ndim == 3 else image


def rgb(image):
    return cv2.cvtColor(image, cv2.COLOR_GRAY2RGB) if image.ndim == 2 else image


def adjust(image, brightness=0, contrast=1, saturation=1):
    """Яркость/контраст в RGB и насыщенность в HSV."""
    a = np.clip((image.astype(float) - 127.5) * contrast + 127.5 + brightness, 0, 255).astype(np.uint8)
    hsv = cv2.cvtColor(rgb(a), cv2.COLOR_RGB2HSV).astype(float)
    hsv[..., 1] = np.clip(hsv[..., 1] * saturation, 0, 255)
    return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)


def linear_stretch(g):
    return cv2.normalize(g, None, 0, 255, cv2.NORM_MINMAX) if g.max() != g.min() else g.copy()


def gamma_correction(g, gamma):
    if not np.isfinite(gamma) or gamma <= 0:
        raise ValueError("Гамма должна быть положительной.")
    return np.uint8(np.clip(255 * (g / 255.) ** gamma, 0, 255))


def motion_blur(image, kernel, angle):
    k = int(kernel)
    filt = np.zeros((k, k), np.float32)
    filt[k // 2, :] = 1
    rotation = cv2.getRotationMatrix2D((k // 2, k // 2), angle, 1)
    filt = cv2.warpAffine(filt, rotation, (k, k))
    return cv2.filter2D(image, -1, filt / filt.sum())


def roberts(g):
    x = cv2.filter2D(g.astype(np.float32), -1, np.array([[1, 0], [0, -1]], np.float32))
    y = cv2.filter2D(g.astype(np.float32), -1, np.array([[0, 1], [-1, 0]], np.float32))
    return np.uint8(np.clip(np.hypot(x, y), 0, 255))


def _harris(image, g):
    response = cv2.cornerHarris(g.astype(np.float32), 2, 3, .04)
    peaks = (response == cv2.dilate(response, None)) & (response > max(0, .01 * response.max()))
    points = np.argwhere(peaks)
    for y, x in points:
        cv2.circle(image, (int(x), int(y)), 3, (255, 60, 30), 1)
    return image, f"Харрис: {len(points)} точек"


def _keypoints(image, g, method):
    detector = cv2.SIFT_create(nfeatures=1500) if method == "SIFT" else cv2.FastFeatureDetector_create()
    points = detector.detect(g, None)
    out = cv2.drawKeypoints(image, points, None, color=(255, 60, 30),
                            flags=cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS)
    return out, f"{method}: {len(points)} точек"


def _contours(image, out, threshold_value):
    note = f"Порог Оцу: {threshold_value:g}"
    contours, hierarchy = cv2.findContours(out, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    out = cv2.drawContours(image, contours, -1, (0, 255, 80), 2)
    note += f"; контуров: {len(contours)}"
    if hierarchy is not None:
        note += "\nИндекс: [следующий, предыдущий, первый ребёнок, родитель]\n"
        note += "\n".join(f"{i}: {h.tolist()}" for i, h in enumerate(hierarchy[0]))
    return out, note


def process(image, operation, kernel=3, gamma=1.5, low=50, high=150, angle=0, threshold=127):
    """Возвращает (RGB-изображение uint8, информационная строка)."""
    k = int(kernel)
    if not 3 <= k <= 51 or k % 2 == 0:
        raise ValueError("Размер ядра должен быть нечётным: от 3 до 51.")
    g, a = gray(image), rgb(image).copy()
    note = ""
    if operation == "Градации серого":
        out = g
    elif operation == "Линейная коррекция":
        out = linear_stretch(g)
    elif operation == "Гамма-коррекция":
        out = gamma_correction(g, gamma)
    elif operation == "Логарифмическая коррекция":
        out = np.uint8(255 * np.log1p(g.astype(float)) / np.log(256))
    elif operation == "Эквализация":
        out = cv2.equalizeHist(g)
    elif operation in MORPH:
        out = cv2.morphologyEx(g, MORPH[operation], np.ones((k, k), np.uint8))
    elif operation == "Резкость":
        out = cv2.addWeighted(a, 1.8, cv2.GaussianBlur(a, (k, k), 0), -.8, 0)
    elif operation == "Размытие в движении":
        out = motion_blur(a, k, angle)
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
        out = roberts(g)
    elif operation == "Харрис":
        out, note = _harris(a, g)
    elif operation in ("SIFT", "FAST"):
        out, note = _keypoints(a, g, operation)
    elif operation == "Бинаризация: порог":
        out = cv2.threshold(g, threshold, 255, cv2.THRESH_BINARY)[1]
    elif operation in ("Бинаризация: Оцу", "Контуры"):
        t, out = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        if operation == "Контуры":
            out, extra = _contours(a, out, t)
            note += "; " + extra
        else:
            note = f"Порог Оцу: {t:g}"
    elif operation == "Бинаризация: адаптивная":
        out = cv2.adaptiveThreshold(g, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, k, 2)
    else:
        raise ValueError("Неизвестная операция")
    return rgb(out), note


def histogram(image):
    """Массив 3×256: число пикселей каждого уровня в каналах R, G, B."""
    return np.array([np.bincount(c.ravel(), minlength=256) for c in rgb(image).transpose(2, 0, 1)])
