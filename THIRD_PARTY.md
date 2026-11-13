# Third-party components

Capture Viewer uses Python, PySide6 / Qt, and the FFmpeg libraries supplied with Qt Multimedia.
Their original notices and licenses apply. PySide6-Addons, PySide6-Essentials and shiboken6
distribution metadata (including their license files) are included in the application bundle.
The binaries remain separate shared libraries in the directory distribution.

- Python: https://docs.python.org/3/license.html
- Qt / PySide: https://doc.qt.io/qtforpython-6/licenses.html
- FFmpeg: https://ffmpeg.org/legal.html
- PyInstaller bootloader: https://pyinstaller.org/en/stable/license.html

The viewer does not ship a separately modified Qt or FFmpeg build. Corresponding upstream
source releases are available from https://download.qt.io/official_releases/QtForPython/pyside6/
and https://ffmpeg.org/releases/ .
