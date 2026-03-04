"""Main application entry point."""

import logging
import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

from app.config import APP_NAME, APP_VERSION
from app.ui.main_window import MainWindow

# Configure logging
log_dir = Path.home() / ".photosortai"
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_dir / "app.log"),
    ],
)

logger = logging.getLogger(__name__)


def main():
    """Main application entry point."""
    logger.info(f"Starting {APP_NAME} v{APP_VERSION}")

    # Create QApplication
    app = QApplication(sys.argv)

    # Set application metadata
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)

    # Create and show main window
    window = MainWindow()
    window.show()

    # Run event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
