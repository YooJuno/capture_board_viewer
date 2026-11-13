"""Install a per-user launcher for either a source checkout or an extracted bundle."""

import argparse
import os
import shlex
import shutil
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", type=Path, help="Extracted CaptureViewer directory")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    executable = (
        args.bundle.resolve() / "CaptureViewer"
        if args.bundle
        else root / ".venv/bin/capture-viewer"
    )
    if not executable.is_file():
        parser.error(f"Executable not found: {executable}")
    data = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
    bin_dir = Path.home() / ".local/bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    launcher = bin_dir / "capture-viewer"
    launcher.write_text(f'#!/bin/sh\nexec {shlex.quote(str(executable))} "$@"\n')
    launcher.chmod(0o755)
    icons = data / "icons/hicolor/scalable/apps"
    icons.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(root / "src/capture_viewer/assets/icon.svg", icons / "capture-viewer.svg")
    applications = data / "applications"
    applications.mkdir(parents=True, exist_ok=True)
    template = (root / "packaging/linux/capture-viewer.desktop").read_text()
    # Desktop Entry Exec quoting is not shell quoting. Escape the reserved characters.
    quoted = (
        str(launcher)
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("`", "\\`")
        .replace("$", "\\$")
    )
    (applications / "capture-viewer.desktop").write_text(
        template.replace("Exec=capture-viewer", f'Exec="{quoted}"')
    )
    print(f"Installed: {applications / 'capture-viewer.desktop'}")


if __name__ == "__main__":
    main()
