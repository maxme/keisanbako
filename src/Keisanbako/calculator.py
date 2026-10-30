"""Keisanbako - A fast calculator with currency conversion and date arithmetic.

This module provides a PySide6-based calculator GUI with support for:
- Basic mathematical expressions
- Currency conversion
- Date arithmetic (using timedelta notation)
- Real-time calculation feedback
"""

import logging
import signal
import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

# PyInstaller support: add bundled module directory to path if running from bundle
if hasattr(sys, '_MEIPASS'):
    sys.path.insert(0, sys._MEIPASS)

# When running directly as a script (not via -m), add src to path immediately
src_dir = str(Path(__file__).parent.parent)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# Configure logging - use INFO level in production bundles, DEBUG in development
log_level = logging.INFO if hasattr(sys, '_MEIPASS') else logging.DEBUG
logging.basicConfig(level=log_level)
logger = logging.getLogger(__name__)

# Import UI components (try relative import first, fallback to absolute for direct execution)
try:
    from .ui import CalculatorWindow
except ImportError:
    from Keisanbako.ui import CalculatorWindow


def main():
    """Main entry point."""
    app = QApplication([])

    # Handle Ctrl-C (SIGINT) to gracefully shut down the app
    def handle_sigint(signum, frame):
        """Handle Ctrl-C signal."""
        app.quit()

    signal.signal(signal.SIGINT, handle_sigint)

    # Allow Ctrl-C to interrupt the event loop
    timer = QTimer()
    timer.timeout.connect(lambda: None)
    timer.start(100)

    window = CalculatorWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
