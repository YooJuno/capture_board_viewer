"""Archive the tested bundle without losing executable bits or macOS symlinks."""

import hashlib
import platform
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    machine = platform.machine().lower()
    architecture = "arm64" if machine in ("arm64", "aarch64") else "x64"
    system = {"win32": "windows", "darwin": "macos"}.get(sys.platform, "linux")
    output = ROOT / "release"
    output.mkdir(exist_ok=True)
    name = f"CaptureViewer-{version}-{system}-{architecture}"
    if system == "macos":
        artifact = output / f"{name}.zip"
        subprocess.run(
            [
                "ditto",
                "-c",
                "-k",
                "--sequesterRsrc",
                "--keepParent",
                str(ROOT / "dist/Capture Viewer.app"),
                str(artifact),
            ],
            check=True,
        )
    else:
        archive = "zip" if system == "windows" else "gztar"
        artifact = Path(
            shutil.make_archive(str(output / name), archive, ROOT / "dist", "CaptureViewer")
        )
    checksum = hashlib.sha256(artifact.read_bytes()).hexdigest()
    (output / f"{artifact.name}.sha256").write_text(f"{checksum}  {artifact.name}\n")
    print(artifact)


if __name__ == "__main__":
    main()
