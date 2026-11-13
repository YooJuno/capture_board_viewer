import time

from PySide6.QtGui import QColor, QImage
from PySide6.QtMultimedia import QCamera, QVideoFrame

from capture_viewer.modes import describe_format, device_key, preferred_device, recommended_format
from tests.fakes import FakeDevice, FakeFormat


def frame(color="red"):
    image = QImage(64, 36, QImage.Format.Format_RGB32)
    image.fill(QColor(color))
    return QVideoFrame(image)


def test_prefers_capture_device_over_webcam():
    webcam = FakeDevice(b"webcam", "Built-in Camera")
    capture = FakeDevice(b"usb", "MACROSILICON USB3 Video")
    assert preferred_device([webcam, capture]) is capture
    assert preferred_device([webcam], device_key(capture)) is None


def test_recommended_mode_prefers_1080p30_over_usb_heavy_modes():
    modes = [FakeFormat(3840, 2160, 60), FakeFormat(1920, 1080, 60), FakeFormat()]
    assert recommended_format(modes) is modes[-1]
    assert recommended_format([]) is None


def test_connection_becomes_streaming_only_after_a_real_frame(controller):
    core, devices, cameras, sink = controller
    device = FakeDevice()
    devices.append(device)
    core.start(device_key(device))
    assert core.state == "connecting"
    assert cameras[0].started
    sink.setVideoFrame(frame())
    core.present_latest()
    assert core.state == "streaming"
    assert core.last_frame.isValid()


def test_unplug_never_switches_to_another_camera(controller):
    core, devices, cameras, _ = controller
    capture, webcam = FakeDevice(), FakeDevice(b"webcam", "Built-in Camera")
    devices.extend([capture, webcam])
    core.start(device_key(capture))
    devices.remove(capture)
    core.refresh_devices()
    core._attempt_start()
    assert core.state == "waiting"
    assert cameras[0].stopped
    assert len(cameras) == 1
    assert core.target == device_key(capture)
    devices.append(capture)
    core._attempt_start()
    assert len(cameras) == 2
    assert cameras[1].device is capture


def test_manual_stop_cancels_pending_reconnection(controller):
    core, devices, cameras, _ = controller
    device = FakeDevice()
    core.start(device_key(device))
    assert core.retry.isActive()
    core.stop()
    devices.append(device)
    core.refresh_devices()
    core._attempt_start()
    assert not core.retry.isActive()
    assert not cameras


def test_reconnect_can_be_disabled(controller):
    core, devices, _, _ = controller
    device = FakeDevice()
    devices.append(device)
    core.auto_reconnect = False
    core.start(device_key(device))
    core._camera_error(core.camera, QCamera.Error.CameraError, "Device is busy")
    assert core.state == "error"
    assert not core.retry.isActive()
    assert not core.want_running


def test_error_from_old_camera_does_not_kill_new_camera(controller):
    core, devices, cameras, _ = controller
    device = FakeDevice()
    devices.append(device)
    core.start(device_key(device))
    old = cameras[-1]
    core.start(device_key(device))
    core._camera_error(old, QCamera.Error.CameraError, "late error")
    assert core.camera is cameras[-1]
    assert core.state == "connecting"


def test_initial_frame_timeout_releases_device_before_retry(controller):
    core, devices, cameras, _ = controller
    device = FakeDevice()
    devices.append(device)
    core.start(device_key(device))
    core.started_at = time.monotonic() - 9
    core.check_stream()
    assert core.state == "waiting"
    assert core.camera is None
    assert cameras[-1].stopped


def test_missing_selected_mode_is_reported_instead_of_silently_changed(controller):
    core, devices, cameras, _ = controller
    device = FakeDevice()
    devices.append(device)
    core.start(device_key(device), describe_format(FakeFormat(3840, 2160, 60)).key)
    assert core.state == "error"
    assert not cameras


def test_only_latest_frame_is_retained_when_ui_is_busy(controller):
    core, _, cameras, sink = controller
    core.start_demo()
    presented = []
    core.present_frame.connect(presented.append)
    for color in ["red"] * 100 + ["blue"]:
        sink.setVideoFrame(frame(color))
    assert not presented
    core.present_latest()
    assert len(presented) == 1
    assert presented[0].toImage().pixelColor(0, 0) == QColor("blue")
    assert not cameras


def test_stop_drops_frame_and_does_not_present_late_frames(controller):
    core, _, _, sink = controller
    core.start_demo()
    sink.setVideoFrame(frame())
    core.stop()
    core.present_latest()
    assert not core.last_frame.isValid()
