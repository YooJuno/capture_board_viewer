from PySide6.QtCore import QEvent, QSettings
from PySide6.QtGui import QColor, QImage

from capture_viewer.window import MainWindow


def test_demo_screenshot_fullscreen_and_clean_close(app, tmp_path):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window = MainWindow(demo=True, settings=settings)
    try:
        window.show()
        app.processEvents()
        window.controller.present_latest()
        app.processEvents()
        assert window.controller.state == "demo"
        assert window.controller.camera is None
        assert window.snapshot_button.isEnabled()
        image = window.grab().toImage()
        # The actual preview must paint its test signal, not merely show a live badge.
        assert image.pixelColor(100, 220) != QColor("#0b0e12")
        path = tmp_path / "frame.png"
        assert window.save_snapshot(path)
        saved = QImage(str(path))
        assert (saved.width(), saved.height()) == (1280, 720)
        window.toggle_fullscreen()
        app.processEvents()
        assert window.isFullScreen()
        assert window.sidebar.isHidden()
        window.leave_fullscreen()
        app.processEvents()
        assert not window.isFullScreen()
        assert not window.sidebar.isHidden()
    finally:
        window.close()
        assert not window.controller.presenter.isActive()
        assert not window.demo.timer.isActive()
        window.deleteLater()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def test_opening_app_never_opens_a_camera_without_connect(app, tmp_path):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    window = MainWindow(settings=settings)
    try:
        app.processEvents()
        assert window.controller.camera is None
        assert not window.controller.want_running
        assert not window.save_snapshot(tmp_path / "absent.png")
        assert not (tmp_path / "absent.png").exists()
    finally:
        window.close()
        window.deleteLater()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
