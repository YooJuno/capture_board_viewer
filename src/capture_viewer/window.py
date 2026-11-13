import logging
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QEvent, QSettings, QStandardPaths, Qt, QTimer
from PySide6.QtGui import QAction, QDesktopServices, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from . import __version__
from .canvas import VideoCanvas
from .controller import CaptureController
from .demo import DemoSource
from .modes import describe_format, device_key, preferred_device
from .theme import STYLE

ASSETS = Path(__file__).parent / "assets"


def label(text, name=None):
    widget = QLabel(text)
    if name:
        widget.setObjectName(name)
    return widget


class MainWindow(QMainWindow):
    def __init__(self, *, demo=False, connect=False, settings=None):
        super().__init__()
        self.settings = settings if settings is not None else QSettings()
        self.demo_mode = demo
        self.last_saved = None
        self._normal_maximized = False
        self.setWindowTitle("Capture Viewer")
        self.setWindowIcon(QIcon(str(ASSETS / "icon.svg")))
        self.setMinimumSize(850, 530)
        self.resize(1280, 790)
        self.setStyleSheet(STYLE)
        self._build_ui()
        self.controller = CaptureController(
            self.video.videoSink(), self, devices=(lambda: []) if demo else None
        )
        self.demo = DemoSource(self.video.videoSink(), self)
        self.controller.state_changed.connect(self._state_changed)
        self.controller.devices_changed.connect(self._update_devices)
        self.controller.frame_changed.connect(self._frame_changed)
        self.controller.metrics_changed.connect(self._metrics_changed)
        self.controller.present_frame.connect(self.video.present)
        self.connect_button.clicked.connect(self._toggle_capture)
        self.refresh_button.clicked.connect(self.controller.refresh_devices)
        self.device_combo.currentIndexChanged.connect(self._device_changed)
        self.mode_combo.currentIndexChanged.connect(self._mode_changed)
        self.reconnect.setChecked(self.settings.value("auto_reconnect", True, type=bool))
        self.controller.set_auto_reconnect(self.reconnect.isChecked())
        self.reconnect.toggled.connect(self._reconnect_changed)
        self.autostart.setChecked(self.settings.value("auto_start", False, type=bool))
        self.autostart.toggled.connect(lambda value: self.settings.setValue("auto_start", value))
        self._update_devices(self.controller.available)
        self._shortcuts()
        if not demo:
            geometry = self.settings.value("geometry")
            if geometry:
                self.restoreGeometry(geometry)
        if demo:
            self.controller.start_demo()
            self.demo.start()
        elif connect or self.autostart.isChecked():
            QTimer.singleShot(0, self._toggle_capture)
        else:
            self._state_changed("stopped", "장치를 선택한 뒤 연결하세요")

    def _build_ui(self):
        root = QWidget(objectName="root")
        self.setCentralWidget(root)
        vertical = QVBoxLayout(root)
        vertical.setContentsMargins(0, 0, 0, 0)
        vertical.setSpacing(0)
        self.header = QWidget(objectName="header")
        top = QHBoxLayout(self.header)
        top.setContentsMargins(22, 16, 20, 16)
        icon = QLabel()
        icon.setPixmap(QIcon(str(ASSETS / "icon.svg")).pixmap(38, 38))
        top.addWidget(icon)
        title = QVBoxLayout()
        title.setSpacing(2)
        title.addWidget(label("Capture Viewer", "brand"))
        title.addWidget(label("USB VIDEO INPUT", "eyebrow"))
        top.addLayout(title)
        top.addStretch()
        self.snapshot_button = QPushButton("PNG 저장")
        self.snapshot_button.setToolTip("현재 프레임 저장 · Ctrl+S / ⌘S")
        self.snapshot_button.clicked.connect(self.save_snapshot)
        top.addWidget(self.snapshot_button)
        fullscreen = QPushButton("전체 화면")
        fullscreen.setToolTip("F11 · 더블클릭 · Esc로 나가기")
        fullscreen.clicked.connect(self.toggle_fullscreen)
        top.addWidget(fullscreen)
        vertical.addWidget(self.header)
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        preview = QWidget()
        stack = QStackedLayout(preview)
        stack.setStackingMode(QStackedLayout.StackingMode.StackAll)
        stack.setContentsMargins(0, 0, 0, 0)
        self.video = VideoCanvas()
        self.video.setStyleSheet("background: #0b0e12;")
        self.video.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.video.installEventFilter(self)
        stack.addWidget(self.video)
        self.empty = QWidget()
        self.empty.setStyleSheet("background: #0b0e12;")
        center = QVBoxLayout(self.empty)
        center.setAlignment(Qt.AlignmentFlag.AlignCenter)
        glyph = QLabel()
        glyph.setPixmap(QIcon(str(ASSETS / "icon.svg")).pixmap(76, 76))
        glyph.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center.addWidget(glyph)
        center.addSpacing(20)
        self.empty_title = label("캡처보드를 연결하세요", "emptyTitle")
        self.empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center.addWidget(self.empty_title)
        self.empty_text = label("HDMI 출력 → USB 캡처보드 → 이 PC", "emptyText")
        self.empty_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_text.setWordWrap(True)
        self.empty_text.setMaximumWidth(430)
        center.addWidget(self.empty_text)
        stack.addWidget(self.empty)
        stack.setCurrentWidget(self.empty)
        body.addWidget(preview, 1)
        self.sidebar = QWidget(objectName="sidebar")
        self.sidebar.setFixedWidth(300)
        side = QVBoxLayout(self.sidebar)
        side.setContentsMargins(22, 25, 22, 20)
        side.setSpacing(12)
        side.addWidget(label("입력 설정", "section"))
        side.addSpacing(10)
        side.addWidget(label("장치", "muted"))
        self.device_combo = QComboBox()
        self.device_combo.setAccessibleName("영상 입력 장치")
        self.device_combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.device_combo.setMinimumContentsLength(14)
        side.addWidget(self.device_combo)
        self.refresh_button = QPushButton("새로고침")
        side.addWidget(self.refresh_button, alignment=Qt.AlignmentFlag.AlignRight)
        side.addSpacing(5)
        side.addWidget(label("영상 형식", "muted"))
        self.mode_combo = QComboBox()
        self.mode_combo.setAccessibleName("영상 해상도와 프레임레이트")
        self.mode_combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.mode_combo.setMinimumContentsLength(14)
        side.addWidget(self.mode_combo)
        mode_hint = label("권장: 1920 × 1080 · 30 fps\n장치가 지원하는 형식만 표시됩니다.", "muted")
        mode_hint.setWordWrap(True)
        side.addWidget(mode_hint)
        side.addSpacing(14)
        self.connect_button = QPushButton("연결", objectName="connect")
        side.addWidget(self.connect_button)
        self.reconnect = QCheckBox("연결이 끊기면 다시 연결")
        self.autostart = QCheckBox("앱 시작 시 마지막 장치에 연결")
        side.addWidget(self.reconnect)
        side.addWidget(self.autostart)
        side.addStretch()
        side.addWidget(label("수신 정보", "section"))
        self.source_info = label("—", "muted")
        self.source_info.setWordWrap(True)
        side.addWidget(self.source_info)
        self.fps_info = label("— fps", "muted")
        side.addWidget(self.fps_info)
        side.addSpacing(16)
        help_button = QPushButton("연결 도움말")
        help_button.clicked.connect(self.show_help)
        side.addWidget(help_button)
        side.addWidget(label(f"Capture Viewer  {__version__}", "eyebrow"))
        body.addWidget(self.sidebar)
        vertical.addLayout(body, 1)
        self.footer = QWidget(objectName="footer")
        foot = QHBoxLayout(self.footer)
        foot.setContentsMargins(20, 10, 20, 10)
        self.status = label("●  연결 대기", "status")
        foot.addWidget(self.status)
        foot.addStretch()
        self.hint = label("F11  전체 화면    ·    Ctrl+S  PNG 저장", "muted")
        foot.addWidget(self.hint)
        vertical.addWidget(self.footer)

    def _shortcuts(self):
        for key, callback in [
            ("F11", self.toggle_fullscreen),
            ("Escape", self.leave_fullscreen),
            ("Ctrl+Return", self._toggle_capture),
            ("Ctrl+R", self.controller.refresh_devices),
        ]:
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.activated.connect(callback)
        save = QAction(self)
        save.setShortcut(QKeySequence.StandardKey.Save)
        save.triggered.connect(self.save_snapshot)
        self.addAction(save)

    def _update_devices(self, devices):
        if self.demo_mode:
            self.device_combo.clear()
            self.device_combo.addItem("데모 신호", "")
            self.mode_combo.clear()
            self.mode_combo.addItem("1280 × 720 · 30 fps", "")
            return
        selected = self.device_combo.currentData() or self.settings.value("device", "")
        chosen = preferred_device(devices, selected)
        self.device_combo.blockSignals(True)
        self.device_combo.clear()
        for device in devices:
            self.device_combo.addItem(device.description(), device_key(device))
        if selected and chosen is None:
            self.device_combo.addItem("마지막 장치 · 연결되지 않음", selected)
            self.device_combo.setCurrentIndex(self.device_combo.count() - 1)
        elif chosen is not None:
            self.device_combo.setCurrentIndex(self.device_combo.findData(device_key(chosen)))
        else:
            self.device_combo.addItem("연결된 영상 장치 없음", "")
        self.device_combo.blockSignals(False)
        self._device_changed()

    def _device_changed(self, *_args):
        key = self.device_combo.currentData() or ""
        device = next((d for d in self.controller.available if device_key(d) == key), None)
        self.mode_combo.blockSignals(True)
        self.mode_combo.clear()
        self.mode_combo.addItem("자동 · 1080p / 30 fps 우선", "")
        if device:
            seen = set()
            formats = sorted(
                device.videoFormats(),
                key=lambda f: (
                    -f.resolution().width(),
                    -f.resolution().height(),
                    -f.maxFrameRate(),
                ),
            )
            for fmt in formats:
                mode = describe_format(fmt)
                if mode.key not in seen:
                    self.mode_combo.addItem(mode.label, mode.key)
                    seen.add(mode.key)
            saved = self.settings.value(f"format/{key}", "")
            index = self.mode_combo.findData(saved)
            self.mode_combo.setCurrentIndex(max(0, index))
            self.settings.setValue("device", key)
        self.mode_combo.blockSignals(False)
        if not self.controller.want_running:
            self.connect_button.setEnabled(bool(key))

    def _mode_changed(self, *_args):
        key = self.device_combo.currentData()
        if key:
            self.settings.setValue(f"format/{key}", self.mode_combo.currentData() or "")

    def _reconnect_changed(self, enabled):
        self.settings.setValue("auto_reconnect", enabled)
        self.controller.set_auto_reconnect(enabled)

    def _toggle_capture(self):
        if self.controller.want_running:
            self.demo.stop()
            self.controller.stop()
        elif self.demo_mode:
            self.controller.start_demo()
            self.demo.start()
        else:
            self.controller.start(
                self.device_combo.currentData(), self.mode_combo.currentData() or ""
            )

    def _state_changed(self, state, detail):
        streaming = state in ("streaming", "demo")
        self.empty.setVisible(not streaming)
        text = {
            "stopped": "연결 대기",
            "connecting": "연결 중",
            "waiting": "재연결 대기",
            "streaming": "영상 수신 중",
            "error": "연결 오류",
            "demo": "데모",
        }[state]
        color = {
            "streaming": "#81d5bd",
            "demo": "#87b7ed",
            "error": "#f19c98",
            "waiting": "#e5c27e",
            "connecting": "#e5c27e",
        }.get(state, "#9aa8b8")
        self.status.setText(f"●  {text}")
        self.status.setStyleSheet(f"color: {color};")
        self.status.setToolTip(detail)
        self.empty_title.setText(text if state != "stopped" else "캡처보드를 연결하세요")
        self.empty_text.setText(detail)
        running = self.controller.want_running
        self.connect_button.setText("연결 해제" if running else "연결")
        self.connect_button.setObjectName("disconnect" if running else "connect")
        self.connect_button.style().unpolish(self.connect_button)
        self.connect_button.style().polish(self.connect_button)
        self.connect_button.setEnabled(
            running or self.demo_mode or bool(self.device_combo.currentData())
        )
        self.device_combo.setEnabled(not running and not self.demo_mode)
        self.mode_combo.setEnabled(not running and not self.demo_mode)
        self.snapshot_button.setEnabled(streaming)
        if not streaming:
            self.video.clear()
            self.source_info.setText("—")
            self.fps_info.setText("— fps")

    def _frame_changed(self, width, height, pixel_format):
        self.source_info.setText(f"{width} × {height}  ·  {pixel_format}")

    def _metrics_changed(self, fps, age):
        if self.controller.state in ("streaming", "demo"):
            self.fps_info.setText(f"{fps:.1f} fps  ·  수신 간격 {max(0, age) * 1000:.0f} ms")
            self.fps_info.setToolTip(
                "최근 2초의 수신 FPS / 마지막 프레임 이후 시간. 전체 영상 지연 측정값은 아닙니다."
            )

    def save_snapshot(self, path=None):
        frame = self.controller.last_frame
        if not frame.isValid():
            return False
        image = frame.toImage()
        if image.isNull():
            QMessageBox.warning(self, "저장 실패", "이 프레임을 이미지로 변환하지 못했습니다.")
            return False
        if path is None or isinstance(path, bool):
            pictures = QStandardPaths.writableLocation(
                QStandardPaths.StandardLocation.PicturesLocation
            )
            directory = Path(
                self.settings.value("snapshot_dir", str(Path(pictures) / "Capture Viewer"))
            )
            filename = directory / f"capture_{datetime.now():%Y%m%d_%H%M%S_%f}.png"
            path, _ = QFileDialog.getSaveFileName(
                self, "현재 프레임 저장", str(filename), "PNG (*.png)"
            )
            if not path:
                return False
        path = Path(path).with_suffix(".png")
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            if not image.save(str(path), "PNG"):
                raise OSError("이미지 파일을 쓸 수 없습니다")
            self.last_saved = path
            self.settings.setValue("snapshot_dir", str(path.parent))
            self.status.setText(f"✓  저장됨 · {path.name}")
            self.status.setToolTip(str(path))
            logging.getLogger(__name__).info("Snapshot saved: %s", path)
            return True
        except OSError as error:
            QMessageBox.warning(self, "저장 실패", str(error))
            return False

    def eventFilter(self, watched, event):
        if watched is self.video and event.type() == QEvent.Type.MouseButtonDblClick:
            self.toggle_fullscreen()
            return True
        return super().eventFilter(watched, event)

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.leave_fullscreen()
        else:
            self._normal_maximized = self.isMaximized()
            for widget in (self.header, self.sidebar, self.footer):
                widget.hide()
            self.showFullScreen()

    def leave_fullscreen(self):
        if not self.isFullScreen():
            return
        for widget in (self.header, self.sidebar, self.footer):
            widget.show()
        self.showMaximized() if self._normal_maximized else self.showNormal()

    def show_help(self):
        box = QMessageBox(self)
        box.setWindowTitle("연결 도움말")
        box.setText("영상 입력 확인")
        box.setInformativeText(
            "1. 출력 장비의 HDMI/DP → 캡처보드의 HDMI IN → PC의 USB 순서로 연결하세요.\n\n"
            "2. 장치를 사용 중인 OBS·카메라·ffplay를 종료하세요.\n\n"
            "3. Windows·macOS에서는 카메라 접근 권한을 허용하세요.\n\n"
            "4. 영상이 끊기면 1080p/30 fps 또는 720p 형식을 선택하세요.\n\n"
            "수신 상태는 USB 프레임 수신을 뜻합니다. "
            "검은 화면·컬러바도 캡처보드가 보내는 영상일 수 있습니다.\n\n"
            "F11 / 더블클릭: 전체 화면   ·   Esc: 나가기   ·   Ctrl+S / ⌘S: PNG 저장"
        )
        folder_button = box.addButton("로그 폴더", QMessageBox.ButtonRole.ActionRole)
        box.addButton(QMessageBox.StandardButton.Close)
        box.exec()
        if box.clickedButton() is folder_button:
            from PySide6.QtCore import QUrl

            QDesktopServices.openUrl(
                QUrl.fromLocalFile(
                    QStandardPaths.writableLocation(
                        QStandardPaths.StandardLocation.AppLocalDataLocation
                    )
                )
            )

    def closeEvent(self, event):
        if not self.demo_mode:
            if self.isFullScreen():
                self.leave_fullscreen()
            self.settings.setValue("geometry", self.saveGeometry())
        self.demo.stop()
        self.controller.shutdown()
        self.settings.sync()
        event.accept()
