"""Aspect-preserving display. Qt coalesces paints; old frames are never queued."""

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtMultimedia import QVideoFrame, QVideoSink
from PySide6.QtWidgets import QWidget


class VideoCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.sink = QVideoSink(self)
        self.frame = QVideoFrame()
        self.image = QImage()
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)

    def videoSink(self):
        return self.sink

    def present(self, frame):
        self.frame = QVideoFrame(frame)
        self.image = QImage()
        self.update()

    def clear(self):
        self.frame = QVideoFrame()
        self.image = QImage()
        self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#0b0e12"))
        if self.image.isNull() and self.frame.isValid():
            self.image = self.frame.toImage()
        if not self.image.isNull():
            size = self.image.size().scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio)
            target = QRect(
                (self.width() - size.width()) // 2,
                (self.height() - size.height()) // 2,
                size.width(),
                size.height(),
            )
            painter.drawImage(target, self.image)
        painter.end()
