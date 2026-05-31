"""Entry point for EPUB Metadata Editor (Python/PyQt6)."""
import sys
import os

# Ensure src/ is on path when run directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication
from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("EPUB Metadata Editor")
    app.setApplicationVersion("3.0.0")
    window = MainWindow()
    window.show()
    # Force Windows DWM to redraw caption buttons by a tiny resize
    def _force_redraw():
        g = window.geometry()
        window.resize(g.width() + 1, g.height())
        window.resize(g.width(), g.height())
    QTimer.singleShot(50, _force_redraw)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
