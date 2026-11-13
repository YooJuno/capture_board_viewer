"""Device-independent format selection; no device is opened here."""

from dataclasses import dataclass


@dataclass(frozen=True)
class VideoMode:
    width: int
    height: int
    min_fps: float
    max_fps: float
    pixel_format: str

    @property
    def key(self) -> str:
        return f"{self.width}x{self.height}:{self.min_fps:g}-{self.max_fps:g}:{self.pixel_format}"

    @property
    def label(self) -> str:
        return f"{self.width} × {self.height}   ·   {self.max_fps:g} fps   ·   {self.pixel_format}"


def describe_format(camera_format) -> VideoMode:
    size = camera_format.resolution()
    name = camera_format.pixelFormat().name.removeprefix("Format_")
    return VideoMode(
        size.width(),
        size.height(),
        camera_format.minFrameRate(),
        camera_format.maxFrameRate(),
        name,
    )


def recommended_format(formats):
    """Prefer a practical 1080p/30 format, not the device's largest USB payload."""
    formats = [f for f in formats if not f.isNull()]
    if not formats:
        return None

    def rank(value):
        mode = describe_format(value)
        resolution = abs(mode.width - 1920) / 1920 + abs(mode.height - 1080) / 1080
        fps = abs(mode.max_fps - 30) / 30
        return (resolution + fps * 0.4, mode.pixel_format.lower() not in ("jpeg", "mjpeg"))

    return min(formats, key=rank)


def device_key(device) -> str:
    return bytes(device.id()).hex()


def preferred_device(devices, saved_key=""):
    if not devices:
        return None
    if saved_key:
        return next((d for d in devices if device_key(d) == saved_key), None)
    keywords = ("capture", "macrosilicon", "hdmi", "usb video", "usb3 video", "cam link")
    return next(
        (d for d in devices if any(k in d.description().lower() for k in keywords)), devices[0]
    )
