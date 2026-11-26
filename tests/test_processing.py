import tempfile
import unittest
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from rasterlab.colors import MODELS, convert
from rasterlab.processing import (load_image, process, histogram, adjust, closest_pair,
                                  VideoProcessor, OPERATIONS)


class ColorTests(unittest.TestCase):
    def test_known_colors(self):
        np.testing.assert_allclose(convert("RGB", "LAB", [255, 255, 255]), [100, 0, 0], atol=.001)
        np.testing.assert_allclose(convert("RGB", "LAB", [255, 0, 0]), [53.2408, 80.0925, 67.2032], atol=.001)
        np.testing.assert_allclose(convert("RGB", "CMYK", [0, 0, 0]), [0, 0, 0, 100])
        np.testing.assert_allclose(convert("RGB", "YCbCr", [0, 0, 0]), [0, 128, 128])

    def test_all_models_roundtrip(self):
        for model in MODELS:
            for rgb in ([0, 0, 0], [255, 255, 255], [255, 0, 0], [25, 130, 241], [128, 128, 128]):
                with self.subTest(model=model, rgb=rgb):
                    value = convert("RGB", model, rgb)
                    # Numerical white L* can exceed 100 by a few millionths.
                    limits = MODELS[model][1]
                    value = np.array([np.clip(v, lo, hi) for v, (lo, hi) in zip(value, limits)])
                    # Full-range YCbCr clips chroma 255.5 to the 8-bit limit 255.
                    np.testing.assert_allclose(convert(model, "RGB", value), rgb,
                                               atol=1 if model == "YCbCr" else .002)

    def test_reject_invalid(self):
        for value in ([256, 0, 0], [float("nan"), 0, 0], [0, 0]):
            with self.assertRaises(ValueError):
                convert("RGB", "HSV", value)


class ProcessingTests(unittest.TestCase):
    def setUp(self):
        self.image = np.zeros((96, 128, 3), np.uint8)
        self.image[20:70, 30:90] = [240, 120, 50]
        self.image[35:50, 45:60] = 0

    def test_all_operations(self):
        for operation in OPERATIONS:
            with self.subTest(operation=operation):
                result, _ = process(self.image, operation)
                self.assertEqual(result.shape, self.image.shape)
                self.assertEqual(result.dtype, np.uint8)
                self.assertTrue(np.isfinite(result).all())

    def test_morphology_geometry(self):
        area = lambda op: np.count_nonzero(process(self.image, op)[0][..., 0])
        original_area = np.count_nonzero(self.image[..., 0])
        self.assertLess(area("Эрозия"), original_area)
        self.assertGreater(area("Дилатация"), original_area)

    def test_histogram_and_adjust(self):
        np.testing.assert_equal(histogram(self.image).sum(axis=1), 96 * 128)
        a = np.full((8, 8, 3), 100, np.uint8)
        np.testing.assert_equal(adjust(a, brightness=30), 130)
        np.testing.assert_equal(adjust(a, brightness=-200), 0)
        np.testing.assert_equal(adjust(a, contrast=0), 127)

    def test_gamma_direction(self):
        a = np.full((8, 8, 3), 100, np.uint8)
        self.assertLess(process(a, "Гамма-коррекция", gamma=2)[0].mean(), 100)
        self.assertGreater(process(a, "Гамма-коррекция", gamma=.5)[0].mean(), 100)

    def test_matching(self):
        other = np.full_like(self.image, 255)
        i, j, distance = closest_pair([self.image, other, self.image.copy()])
        self.assertEqual((i, j), (0, 2))
        self.assertLess(distance, .001)
        with self.assertRaises(ValueError):
            closest_pair([self.image])

    def test_metadata_and_unicode_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            for mode, bits in [("1", 1), ("L", 8), ("RGB", 24), ("RGBA", 32)]:
                path = Path(directory) / f"проверка_{mode}.png"
                Image.fromarray(self.image).convert(mode).save(path)
                result, info = load_image(path)
                self.assertEqual(result.shape, self.image.shape)
                self.assertEqual(info["Глубина файла"], f"{bits} бит/пиксель")
            path = Path(directory) / "16.png"
            Image.fromarray(np.full((8, 8), 65535, np.uint16)).save(path)
            result, info = load_image(path)
            self.assertEqual(info["Глубина файла"], "16 бит/пиксель")
            np.testing.assert_equal(result, 255)

    def test_motion_mask_and_blur(self):
        processor = VideoProcessor()
        base = np.full((120, 160, 3), 40, np.uint8)
        for _ in range(40):
            processor.apply(base)
        frame = base.copy()
        frame[40:80, 60:100] = 230
        frame[50:70:2, 60:100] = 70
        mask, blurred = processor.apply(frame)
        self.assertGreater(np.count_nonzero(mask[40:80, 60:100]), 500)
        np.testing.assert_array_equal(blurred[:20], frame[:20])
        self.assertLess(blurred[45:75, 65:95].var(), frame[45:75, 65:95].var())


if __name__ == "__main__":
    unittest.main()
