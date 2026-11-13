"""Build a native, self-contained directory bundle on the current OS."""

import os
import platform
import runpy
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    os.chdir(ROOT)
    document = tomllib.loads((ROOT / "pyproject.toml").read_text())
    version = document["project"]["version"]
    app_version = runpy.run_path(str(ROOT / "src/capture_viewer/__init__.py"))["__version__"]
    if version != app_version:
        raise SystemExit("pyproject.toml and application versions must match")
    if os.environ.get("GITHUB_REF_TYPE") == "tag":
        if os.environ["GITHUB_REF_NAME"] != f"v{version}":
            raise SystemExit("Release tag must match pyproject.toml version")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PIL import Image
    from PySide6.QtCore import QRectF
    from PySide6.QtGui import QGuiApplication, QImage, QPainter
    from PySide6.QtSvg import QSvgRenderer

    app = QGuiApplication([])
    icon_dir = ROOT / "build/icons"
    icon_dir.mkdir(parents=True, exist_ok=True)
    image = QImage(1024, 1024, QImage.Format.Format_ARGB32)
    image.fill(0)
    painter = QPainter(image)
    renderer = QSvgRenderer(str(ROOT / "src/capture_viewer/assets/icon.svg"))
    renderer.render(painter, QRectF(0, 0, 1024, 1024))
    painter.end()
    image.save(str(icon_dir / "icon.png"))
    with Image.open(icon_dir / "icon.png") as raster:
        raster.save(icon_dir / "icon.ico", sizes=[(s, s) for s in [16, 32, 48, 64, 128, 256]])
        raster.save(icon_dir / "icon.icns")
    del renderer, painter, image, app
    subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            str(ROOT / "packaging/CaptureViewer.spec"),
        ],
        check=True,
    )
    print(f"Built Capture Viewer {version} on {platform.system()} {platform.machine()}")


if __name__ == "__main__":
    main()
