"""One capture session, one retained frame, and bounded reconnection attempts."""

import logging
import threading
import time
from collections import deque

from PySide6.QtCore import QCameraPermission, QCoreApplication, QObject, Qt, QTimer, Signal
from PySide6.QtMultimedia import QCamera, QMediaCaptureSession, QMediaDevices, QVideoFrame

from .modes import describe_format, device_key, recommended_format

log = logging.getLogger(__name__)


class CaptureController(QObject):
    state_changed = Signal(str, str)
    devices_changed = Signal(object)
    frame_changed = Signal(int, int, str)
    metrics_changed = Signal(float, float)
    present_frame = Signal(QVideoFrame)

    def __init__(self, sink, parent=None, *, devices=None, camera_factory=None, session=None):
        super().__init__(parent)
        self.sink = sink
        self.session = session if session is not None else QMediaCaptureSession(self)
        self.session.setVideoSink(sink)
        self._devices = devices or QMediaDevices.videoInputs
        self._camera_factory = camera_factory or (lambda device: QCamera(device, self))
        self._needs_permission = camera_factory is None
        self._permission_pending = False
        self.media_devices = QMediaDevices(self) if devices is None else None
        if self.media_devices:
            self.media_devices.videoInputsChanged.connect(self.refresh_devices)
        self.camera = None
        self.target = ""
        self.mode_key = ""
        self.want_running = False
        self.auto_reconnect = True
        self.state = "stopped"
        self.detail = "입력 장치를 선택하세요"
        self.available = []
        self.last_frame = QVideoFrame()
        self.last_received = 0.0
        self.started_at = 0.0
        self._frame_times = deque(maxlen=180)
        self._frame_shape = None
        self._mailbox_lock = threading.Lock()
        self._pending_frame = None
        self.retry = QTimer(self)
        self.retry.setSingleShot(True)
        self.retry.setInterval(2000)
        self.retry.timeout.connect(self._attempt_start)
        self.watchdog = QTimer(self)
        self.watchdog.setInterval(500)
        self.watchdog.timeout.connect(self.check_stream)
        self.watchdog.start()
        self.poll = QTimer(self)
        self.poll.setInterval(2000)
        self.poll.timeout.connect(self.refresh_devices)
        self.poll.start()
        # Capture callbacks only replace one slot. No queued Python image/frame
        # callbacks may accumulate while a dialog or the UI thread is busy.
        self.sink.videoFrameChanged.connect(
            self._receive_latest, Qt.ConnectionType.DirectConnection
        )
        self.presenter = QTimer(self)
        self.presenter.setInterval(16)
        self.presenter.timeout.connect(self.present_latest)
        self.presenter.start()
        self.refresh_devices()

    def _state(self, state, detail):
        if (self.state, self.detail) != (state, detail):
            log.info("Capture state: %s — %s", state, detail)
        self.state, self.detail = state, detail
        self.state_changed.emit(state, detail)

    def refresh_devices(self):
        devices = list(self._devices())
        changed = [(device_key(d), d.description()) for d in devices] != [
            (device_key(d), d.description()) for d in self.available
        ]
        self.available = devices
        if changed:
            self.devices_changed.emit(devices)
        if self.want_running and self.state != "demo":
            present = any(device_key(d) == self.target for d in devices)
            if not present and self.camera is not None:
                self._recover("장치 연결이 끊겼습니다. 같은 장치를 기다립니다.")
            elif present and self.camera is None and not self.retry.isActive():
                self._attempt_start()

    def start(self, target, mode_key=""):
        self.stop()
        if not target:
            self._state("error", "입력 장치를 선택하세요")
            return
        self.target, self.mode_key = target, mode_key
        self.want_running = True
        self._attempt_start()

    def _attempt_start(self):
        if not self.want_running or self.camera is not None or self.state == "demo":
            return
        device = next((d for d in self._devices() if device_key(d) == self.target), None)
        if device is None:
            self._recover("장치를 찾을 수 없습니다. 같은 장치를 기다립니다.")
            return
        if self._needs_permission and not self._camera_permission():
            return
        formats = list(device.videoFormats())
        chosen = next((f for f in formats if describe_format(f).key == self.mode_key), None)
        if self.mode_key and chosen is None:
            self.want_running = False
            self._state("error", "선택한 영상 형식을 지원하지 않습니다. 형식을 다시 선택하세요.")
            return
        chosen = chosen or recommended_format(formats)
        try:
            camera = self._camera_factory(device)
            self.camera = camera
            camera.errorOccurred.connect(
                lambda error, message, owner=camera: self._camera_error(owner, error, message)
            )
            if chosen is not None:
                camera.setCameraFormat(chosen)
            self.session.setCamera(camera)
            self.started_at = time.monotonic()
            self.last_received = 0.0
            self._frame_times.clear()
            self._state("connecting", "영상 입력을 여는 중입니다")
            camera.start()
        except Exception as error:
            log.exception("Could not open camera")
            self._recover(str(error))

    def _camera_permission(self):
        app = QCoreApplication.instance()
        permission = QCameraPermission()
        status = app.checkPermission(permission)
        if status == Qt.PermissionStatus.Granted:
            return True
        if status == Qt.PermissionStatus.Denied:
            self.want_running = False
            self._state("error", "카메라 접근 권한이 없습니다. 운영체제 설정에서 허용하세요.")
        elif not self._permission_pending:
            self._permission_pending = True
            self._state("connecting", "카메라 접근 권한을 허용하세요")

            def completed(_permission):
                self._permission_pending = False
                if self.want_running:
                    self._attempt_start()

            app.requestPermission(permission, self, completed)
        return False

    def _camera_error(self, owner, error, message):
        if owner is self.camera and error != QCamera.Error.NoError:
            self._recover(message or "영상 입력을 열 수 없습니다")

    def _drop_camera(self):
        camera, self.camera = self.camera, None
        self.session.setCamera(None)
        if camera is not None:
            camera.stop()
            camera.deleteLater()
        self.last_frame = QVideoFrame()
        self.sink.setVideoFrame(QVideoFrame())
        self.last_received = 0.0
        self._frame_times.clear()
        self._frame_shape = None
        with self._mailbox_lock:
            self._pending_frame = None

    def _recover(self, reason):
        self._drop_camera()
        if self.want_running and self.auto_reconnect:
            self._state("waiting", reason)
            if not self.retry.isActive():
                self.retry.start()
        else:
            self.want_running = False
            self._state("error", reason)

    def stop(self):
        self.want_running = False
        self.retry.stop()
        self._drop_camera()
        self._state("stopped", "연결 대기")
        self.metrics_changed.emit(0.0, -1.0)

    def shutdown(self):
        self.stop()
        self.watchdog.stop()
        self.poll.stop()
        self.presenter.stop()
        self.session.setVideoSink(None)

    def set_auto_reconnect(self, enabled):
        self.auto_reconnect = bool(enabled)
        if not enabled and self.state == "waiting":
            self.stop()

    def start_demo(self):
        self.stop()
        self.want_running = True
        self._state("demo", "데모 화면 · 실제 캡처 입력이 아닙니다")

    def _receive_latest(self, frame):
        if frame.isValid():
            with self._mailbox_lock:
                received = time.monotonic()
                self._pending_frame = (QVideoFrame(frame), received)
                self._frame_times.append(received)

    def present_latest(self):
        with self._mailbox_lock:
            item, self._pending_frame = self._pending_frame, None
        if item:
            self._on_frame(*item)

    def _on_frame(self, frame, received=None):
        if not frame.isValid() or not self.want_running:
            return
        if self.camera is None and self.state != "demo":
            return
        self.last_frame = QVideoFrame(frame)
        self.last_received = received if received is not None else time.monotonic()
        if self.state != "demo" and self.state != "streaming":
            self._state("streaming", "영상 수신 중")
        shape = (frame.width(), frame.height(), frame.pixelFormat().name.removeprefix("Format_"))
        if shape != self._frame_shape:
            self._frame_shape = shape
            self.frame_changed.emit(*shape)
        self.present_frame.emit(self.last_frame)

    def check_stream(self):
        now = time.monotonic()
        if self.want_running and self.camera is not None:
            limit = 3.0 if self.last_received else 8.0
            anchor = self.last_received or self.started_at
            if now - anchor > limit:
                self._recover(
                    "프레임이 수신되지 않습니다. 입력 신호와 장치 사용 여부를 확인하세요."
                )
        with self._mailbox_lock:
            recent = [t for t in self._frame_times if now - t <= 2.0]
        fps = (len(recent) - 1) / (recent[-1] - recent[0]) if len(recent) > 1 else 0.0
        age = now - self.last_received if self.last_received else -1.0
        self.metrics_changed.emit(fps, age)
