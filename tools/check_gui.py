"""Интеграционная smoke-проверка Tkinter и реального видеодекодера."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tempfile
from unittest.mock import patch
import numpy as np
from src.rasterlab.ui import App


def main():
    app = App()
    image_tab = app.image_tab
    color_tab = app.color_tab
    compare_tab = app.compare_tab
    video_tab = app.video_tab
    try:
        app.update()
        with patch.object(app.dialogs, "open_file", return_value="examples/depth_24.png"):
            image_tab.open_image()
        app.update()
        assert app.model.current.shape == (256, 384, 3)
        assert image_tab.left.mapping is not None

        app.pick_pixel(0, 0, app.model.current[0, 0])
        assert "YCbCr" in color_tab.color_result.get("1.0", "end")

        image_tab.sliders["brightness"].set(20)
        image_tab.apply_adjust()
        assert not np.array_equal(app.model.current, app.model.original)
        image_tab.undo()
        np.testing.assert_array_equal(app.model.current, app.model.original)

        image_tab.operation.set("Canny")
        image_tab.apply_operation()
        assert len(image_tab.histcanvas.find_all()) > 5

        with tempfile.TemporaryDirectory() as directory:
            filename = str(Path(directory) / "result.png")
            with patch.object(app.dialogs, "save_file", return_value=filename):
                image_tab.save_result()
            assert Path(filename).is_file()

        paths = ("examples/depth_24.png", "examples/similar.png",
                 "examples/different.png")
        with patch.object(app.dialogs, "open_files", return_value=paths):
            compare_tab.compare()
        assert compare_tab.pair_views[0].image is not None

        video_tab.start("examples/motion.avi")
        assert video_tab.session.frame_index == 1
        video_tab.stop_timer()
        video_tab.video_mode.set("Размытие объектов")
        for _ in range(150):
            video_tab.session.running = True
            video_tab.tick()
            video_tab.stop_timer()
        assert video_tab.session.frame_index == 150
        assert not video_tab.session.running
        video_tab.restart()
        assert video_tab.session.frame_index == 1
        video_tab.stop_timer()
        app.update()
        print("GUI smoke OK: loading, pixel, adjustment, undo, Canny, histogram, "
              "save, compare, 150 video frames, restart")
    finally:
        app.close()


if __name__ == "__main__":
    main()
