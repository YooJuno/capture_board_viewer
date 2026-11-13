from PySide6.QtCore import QByteArray, QObject, QSize, Signal
from PySide6.QtMultimedia import QVideoFrameFormat


class FakeFormat:
    def __init__(self, width=1920, height=1080, fps=30, pixel="Format_Jpeg"):
        self.width, self.height, self.fps, self.pixel = width, height, fps, pixel

    def resolution(self):
        return QSize(self.width, self.height)

    def minFrameRate(self):
        return self.fps

    def maxFrameRate(self):
        return self.fps

    def pixelFormat(self):
        return getattr(QVideoFrameFormat.PixelFormat, self.pixel)

    def isNull(self):
        return False


class FakeDevice:
    def __init__(self, identity=b"capture", name="USB Capture", formats=None):
        self.identity, self.name = identity, name
        self.formats = formats if formats is not None else [FakeFormat()]

    def id(self):
        return QByteArray(self.identity)

    def description(self):
        return self.name

    def videoFormats(self):
        return self.formats


class FakeSession:
    def setVideoSink(self, sink):
        self.sink = sink

    def setCamera(self, camera):
        self.camera = camera


class FakeCamera(QObject):
    errorOccurred = Signal(object, str)

    def __init__(self, device):
        super().__init__()
        self.device = device
        self.started = False
        self.stopped = False
        self.format = None

    def setCameraFormat(self, fmt):
        self.format = fmt

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True
