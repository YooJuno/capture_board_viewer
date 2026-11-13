"""Launch the bundled executable with no physical camera, validate rendering and exit."""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    executable = ROOT / "dist/CaptureViewer/CaptureViewer"
    if sys.platform == "win32":
        executable = executable.with_suffix(".exe")
    elif sys.platform == "darwin":
        executable = ROOT / "dist/Capture Viewer.app/Contents/MacOS/CaptureViewer"
    output = ROOT / "build/bundle-preview.png"
    environment = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    subprocess.run(
        [str(executable), "--demo", "--screenshot", str(output), "--quit-after-ms", "1400"],
        env=environment,
        timeout=40,
        check=True,
    )
    from PIL import Image

    with Image.open(output) as image:
        assert image.width >= 850 and image.height >= 530, "Invalid UI screenshot"
        rgb = image.convert("RGB")
        colors = [rgb.getpixel((x, 220)) for x in [100, 250, 400, 550, 700]]
        assert len(set(colors)) >= 4, "The bundled preview did not render the test signal"
    print("Packaged GUI: rendered test signal, saved screenshot, exited cleanly")


if __name__ == "__main__":
    main()
