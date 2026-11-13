# Run through scripts/build.py so platform icons and version metadata exist.
import sys
import tomllib
import os
from pathlib import Path

from PyInstaller.utils.hooks import copy_metadata

root = Path(SPECPATH).parent
version = tomllib.loads((root / 'pyproject.toml').read_text())['project']['version']
assets = root / 'src/capture_viewer/assets'
datas = [(str(assets), 'capture_viewer/assets'),
         (str(root / 'README.md'), '.'),
         (str(root / 'THIRD_PARTY.md'), '.')]
for package in ['PySide6-Addons', 'PySide6-Essentials', 'shiboken6']:
    datas += copy_metadata(package)

analysis = Analysis(
    [str(root / 'packaging/entrypoint.py')],
    pathex=[str(root / 'src')],
    datas=datas,
    hiddenimports=['PySide6.QtSvg'],
    excludes=['PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'PySide6.QtQml', 'PIL'],
)
pyz = PYZ(analysis.pure)
icon = root / 'build/icons' / ('icon.ico' if sys.platform == 'win32' else 'icon.icns')
exe = EXE(pyz, analysis.scripts, [], exclude_binaries=True, name='CaptureViewer',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          console=False, icon=str(icon) if sys.platform != 'linux' else None,
          target_arch='universal2' if sys.platform == 'darwin' and
              os.environ.get('CAPTURE_MAC_UNIVERSAL') == '1' else None,
          entitlements_file=str(root / 'packaging/macos/entitlements.plist')
          if sys.platform == 'darwin' else None)
collection = COLLECT(exe, analysis.binaries, analysis.datas, strip=False, upx=False,
                     name='CaptureViewer')
if sys.platform == 'darwin':
    app = BUNDLE(collection, name='Capture Viewer.app', icon=str(icon),
                 bundle_identifier='io.github.YooJuno.CaptureViewer',
                 info_plist={
                     'CFBundleDisplayName': 'Capture Viewer',
                     'CFBundleShortVersionString': version,
                     'CFBundleVersion': version,
                     'LSMinimumSystemVersion': '13.0',
                     'NSHighResolutionCapable': True,
                     'NSCameraUsageDescription': '선택한 USB 캡처보드의 영상을 표시합니다.',
                 })
