import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def app():
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def controller(app):
    from PySide6.QtMultimedia import QVideoSink

    from capture_viewer.controller import CaptureController
    from tests.fakes import FakeCamera, FakeSession

    devices = []
    sink = QVideoSink()
    session = FakeSession()
    created = []

    def make_camera(device):
        camera = FakeCamera(device)
        created.append(camera)
        return camera

    core = CaptureController(
        sink, devices=lambda: list(devices), camera_factory=make_camera, session=session
    )
    yield core, devices, created, sink
    core.shutdown()
    core.deleteLater()
    app.processEvents()
