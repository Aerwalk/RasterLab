"""Воспроизводимые учебные данные и результаты; запуск из корня проекта."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import csv
import cv2
import numpy as np
from PIL import Image
from rasterlab.processing import process, load_image, VideoProcessor


def main():
    folder = Path("examples")
    folder.mkdir(exist_ok=True)
    y, x = np.mgrid[:256, :384]
    a = np.stack((x * 255 / 383, y, (x + y) * 255 / 638), axis=-1).astype(np.uint8)
    cv2.rectangle(a, (35, 40), (135, 150), (240, 45, 60), -1)
    cv2.circle(a, (260, 130), 65, (20, 190, 70), -1)
    cv2.circle(a, (260, 130), 30, (0, 0, 0), -1)
    cv2.putText(a, "RasterLab", (70, 230), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    image = Image.fromarray(a)
    versions = [
        ("depth_1.png", image.convert("L").point(lambda p: 255 if p >= 128 else 0, "1"), {}),
        ("depth_4_palette.png", image.quantize(colors=16), {"bits": 4}),
        ("depth_8_gray.png", image.convert("L"), {}),
        ("depth_8_palette.png", image.quantize(colors=256), {"bits": 8}),
        ("depth_24.png", image, {}),
        ("depth_32.png", image.convert("RGBA"), {}),
    ]
    with (folder / "depth_analysis.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["Файл", "бит/пиксель", "байт на диске", "различных RGB-цветов", "MSE к RGB-оригиналу"])
        for name, im, kwargs in versions:
            path = folder / name
            im.save(path, **kwargs)
            decoded, info = load_image(path)
            mse = np.mean((decoded.astype(float) - a) ** 2)
            writer.writerow([name, info["Глубина файла"], path.stat().st_size,
                             len(np.unique(decoded.reshape(-1, 3), axis=0)), f"{mse:.3f}"])
    Image.fromarray(np.clip(a.astype(float) * .95 + 5, 0, 255).astype(np.uint8)).save(folder / "similar.png")
    Image.fromarray(255 - a).save(folder / "different.png")
    for operation, name in [("Градации серого", "gray"), ("Гамма-коррекция", "gamma"),
                             ("Canny", "canny"), ("Робертс", "roberts"), ("Харрис", "harris"),
                             ("SIFT", "sift"), ("FAST", "fast"), ("Эрозия", "erosion"),
                             ("Дилатация", "dilation"), ("Открытие", "opening"), ("Закрытие", "closing"),
                             ("Градиент", "gradient"), ("Резкость", "sharp"), ("Тиснение", "emboss"),
                             ("Размытие в движении", "motion"), ("Медианный фильтр", "median")]:
        result, _ = process(a, operation, kernel=5)
        Image.fromarray(result).save(folder / f"result_{name}.png")
    video_path = folder / "motion.avi"
    writer = cv2.VideoWriter(str(video_path), cv2.VideoWriter_fourcc(*"MJPG"), 25, (384, 256))
    if not writer.isOpened():
        raise RuntimeError("Кодек MJPG недоступен.")
    processor = VideoProcessor()
    try:
        for i in range(150):
            frame = np.full((256, 384, 3), 45, np.uint8)
            if i >= 40:
                left = 10 + (i - 40) * 2
                cv2.rectangle(frame, (left, 80), (left + 60, 160), (40, 200, 240), -1)
                for line in range(left, left + 60, 6):
                    cv2.line(frame, (line, 80), (line, 160), (0, 0, 0), 2)
            writer.write(frame)
            mask, blurred = processor.apply(frame)
            if i == 90:
                Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).save(folder / "video_original.png")
                Image.fromarray(mask).save(folder / "video_mask.png")
                Image.fromarray(cv2.cvtColor(blurred, cv2.COLOR_BGR2RGB)).save(folder / "video_blur.png")
    finally:
        writer.release()
    print(f"Примеры сохранены: {folder.resolve()}")


if __name__ == "__main__":
    main()
