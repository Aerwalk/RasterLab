"""Интеграционная smoke-проверка Tkinter и реального видеодекодера."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import tempfile
from unittest.mock import patch
import numpy as np
from rasterlab.gui import App


def main():
    app = App()
    try:
        app.update()
        with patch("rasterlab.gui.filedialog.askopenfilename", return_value="examples/depth_24.png"):
            app.open_image()
        app.update()
        assert app.current.shape == (256, 384, 3)
        assert app.left.mapping is not None
        app.pick_pixel(0, 0, app.current[0, 0])
        assert "YCbCr" in app.color_result.get("1.0", "end")
        app.tabs.select(app.image_tab)
        app.sliders["brightness"].set(20)
        app.apply_adjust()
        assert not np.array_equal(app.current, app.original)
        app.undo()
        np.testing.assert_array_equal(app.current, app.original)
        app.operation.set("Canny")
        app.apply_operation()
        assert len(app.histcanvas.find_all()) > 5
        with tempfile.TemporaryDirectory() as directory:
            filename = str(Path(directory) / "result.png")
            with patch("rasterlab.gui.filedialog.asksaveasfilename", return_value=filename):
                app.save_image()
            assert Path(filename).is_file()
        paths = ("examples/depth_24.png", "examples/similar.png", "examples/different.png")
        with patch("rasterlab.gui.filedialog.askopenfilenames", return_value=paths):
            app.compare()
        assert app.pair_views[0].image is not None
        app.start_video("examples/motion.avi")
        assert app.frame_index == 1
        app.stop_video()
        # Process the complete clip synchronously, using the actual GUI callback.
        # after() jobs are cancelled each step, so there are no duplicate callbacks.
        app.video_mode.set("Размытие объектов")
        for _ in range(150):
            app.running = True
            app.video_tick()
            app.stop_video()
        assert app.frame_index == 150
        assert not app.running
        app.restart_video()
        assert app.frame_index == 1
        app.stop_video()
        app.update()
        print("GUI smoke OK: loading, pixel, adjustment, undo, Canny, histogram, save, compare, 150 video frames, restart")
    finally:
        app.close()


if __name__ == "__main__":
    main()
