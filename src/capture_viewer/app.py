"""Application entry point; demo/CI mode never opens a camera."""

import argparse
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QEvent, QStandardPaths, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from . import __version__


def main(argv=None):
    parser = argparse.ArgumentParser(description="USB capture device viewer")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--demo", action="store_true", help="Test signal; never open a device")
    parser.add_argument("--connect", action="store_true", help="Connect to last selected device")
    parser.add_argument("--screenshot", type=Path, help="Save a UI screenshot (requires --demo)")
    parser.add_argument(
        "--quit-after-ms", type=int, default=0, help="Close after a bounded UI smoke test"
    )
    args = parser.parse_args(argv)
    if args.screenshot and not args.demo:
        parser.error("--screenshot requires --demo to prevent unintended camera access")
    if args.quit_after_ms < 0:
        parser.error("--quit-after-ms cannot be negative")
    QCoreApplication.setOrganizationName("YooJuno")
    QCoreApplication.setApplicationName("CaptureViewer")
    QCoreApplication.setApplicationVersion(__version__)
    app = QApplication([sys.argv[0]])
    app.setFont(QFont("Noto Sans CJK KR" if sys.platform.startswith("linux") else "", 10))
    app.setStyle("Fusion")
    log_dir = Path(
        QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)
    )
    log_dir.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        log_dir / "viewer.log", maxBytes=1_000_000, backupCount=2, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logging.getLogger().addHandler(handler)
    logging.getLogger().setLevel(logging.INFO)
    from .window import MainWindow

    window = MainWindow(demo=args.demo, connect=args.connect)
    window.show()
    result = [0]
    if args.screenshot:

        def save_ui():
            args.screenshot.parent.mkdir(parents=True, exist_ok=True)
            if not window.grab().save(str(args.screenshot)):
                result[0] = 1

        QTimer.singleShot(900, save_ui)
    if args.quit_after_ms:
        QTimer.singleShot(max(args.quit_after_ms, 1100 if args.screenshot else 1), window.close)
    exit_code = app.exec()
    window.deleteLater()
    app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    handler.close()
    logging.getLogger().removeHandler(handler)
    return exit_code or result[0]
