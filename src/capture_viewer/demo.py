"""Explicit, hardware-free test signal for UI and packaged-app verification."""

import time

from PySide6.QtCore import QObject, QRect, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QImage, QPainter
from PySide6.QtMultimedia import QVideoFrame


class DemoSource(QObject):
    def __init__(self, sink, parent=None):
        super().__init__(parent)
        self.sink = sink
        self.started = time.monotonic()
        self.timer = QTimer(self)
        self.timer.setInterval(33)
        self.timer.timeout.connect(self.draw)

    def start(self):
        self.started = time.monotonic()
        self.timer.start()
        self.draw()

    def stop(self):
        self.timer.stop()

    def draw(self):
        image = QImage(1280, 720, QImage.Format.Format_RGB32)
        image.fill(QColor("#101820"))
        painter = QPainter(image)
        colors = ["#d9e0df", "#e4ca6e", "#6bbfb7", "#76a97b", "#ab88b7", "#a76664", "#5a75a8"]
        for i, color in enumerate(colors):
            painter.fillRect(QRect(i * 183, 0, 184, 468), QColor(color))
        painter.fillRect(0, 468, 1280, 252, QColor("#101820"))
        painter.setPen(QColor("#f2f4f6"))
        painter.setFont(QFont("monospace", 28))
        painter.drawText(QRect(55, 515, 1100, 60), Qt.AlignmentFlag.AlignLeft, "CAPTURE VIEWER")
        seconds = time.monotonic() - self.started
        painter.setFont(QFont("monospace", 18))
        painter.setPen(QColor("#9baab6"))
        painter.drawText(55, 615, f"DEMO SIGNAL     1280 × 720     {seconds:08.2f}")
        painter.fillRect(55, 665, int(seconds * 110) % 1170, 3, QColor("#77c6b5"))
        painter.end()
        self.sink.setVideoFrame(QVideoFrame(image))
