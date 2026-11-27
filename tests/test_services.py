"""Тесты прикладного слоя: файлы, модель UI и видеосессия."""
import tempfile
import unittest
from pathlib import Path
import cv2
import numpy as np
from rasterlab.services.files import load_image, save_image, resize_preview
from rasterlab.services.video import VideoSession
from rasterlab.ui import ImageModel, draw_histograms


class ServiceTests(unittest.TestCase):
    def test_file_service_roundtrip(self):
        image = np.zeros((30, 40, 3), np.uint8)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "тест.png"
            save_image(image, path)
            loaded, info = load_image(path)
            np.testing.assert_array_equal(loaded, image)
            self.assertEqual(info["Разрешение файла"], "40 × 30 px")

    def test_resize_preview(self):
        frame = np.zeros((400, 2000, 3), np.uint8)
        small = resize_preview(frame)
        self.assertEqual(small.shape[1], 960)
        self.assertEqual(small.shape[0], 192)

    def test_video_session_end_and_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "clip.avi"
            writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"),
                                     10, (160, 120))
            self.assertTrue(writer.isOpened())
            try:
                for _ in range(5):
                    writer.write(np.full((120, 160, 3), 40, np.uint8))
            finally:
                writer.release()
            session = VideoSession()
            session.open(path)
            self.assertEqual(session.fps, 10)
            self.assertEqual(session.total_frames, 5)
            for _ in range(5):
                self.assertIsNotNone(session.next_frame())
            self.assertTrue(session.finished)
            self.assertIsNone(session.next_frame())
            session.restart()
            self.assertEqual(session.frame_index, 0)
            self.assertIsNotNone(session.next_frame("blur"))
            session.close()
            self.assertFalse(session.loaded)


class UiModelTests(unittest.TestCase):
    def test_history(self):
        model = ImageModel()
        first = np.zeros((8, 8, 3), np.uint8)
        second = np.full_like(first, 255)
        model.load(first)
        self.assertTrue(model.loaded)
        model.commit(second)
        np.testing.assert_array_equal(model.before, first)
        self.assertTrue(model.undo())
        np.testing.assert_array_equal(model.current, first)
        self.assertFalse(model.undo())

    def test_histogram_channels(self):
        model = ImageModel()
        image = np.zeros((4, 4, 3), np.uint8)
        image[..., 0] = 30
        model.load(image)
        self.assertEqual(len(model.histogram_pair("RGB")), 2)
        self.assertEqual(model.histogram_pair("RGB")[0].shape, (3, 256))
        self.assertEqual(model.histogram_pair("R")[0].shape, (1, 256))
        self.assertEqual(model.histogram_pair("Яркость")[0].shape, (1, 256))


if __name__ == "__main__":
    unittest.main()
