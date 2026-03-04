"""Main application window."""

import logging
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow,
    QStackedWidget,
    QWidget,
    QVBoxLayout,
)
from PyQt6.QtCore import Qt

from app.config import APP_NAME, APP_VERSION, WINDOW_WIDTH, WINDOW_HEIGHT
from app.core.models import ScanResult
from app.ui.pages.page_select import SelectFolderPage
from app.ui.pages.page_processing import ProcessingPage
from app.ui.pages.page_review import ReviewPage
from app.ui.pages.page_done import DonePage

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main application window with wizard-style navigation."""

    # Page indices
    PAGE_SELECT = 0
    PAGE_PROCESSING = 1
    PAGE_REVIEW = 2
    PAGE_DONE = 3

    def __init__(self):
        """Initialize main window."""
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setGeometry(100, 100, WINDOW_WIDTH, WINDOW_HEIGHT)

        # Current state
        self.scan_result = None
        self.move_files = False

        # Create stacked widget
        self.stacked = QStackedWidget()
        self.setCentralWidget(self.stacked)

        # Create pages
        self.page_select = SelectFolderPage()
        self.page_processing = ProcessingPage()
        self.page_review = ReviewPage()
        self.page_done = DonePage()

        # Add pages to stacked widget
        self.stacked.addWidget(self.page_select)
        self.stacked.addWidget(self.page_processing)
        self.stacked.addWidget(self.page_review)
        self.stacked.addWidget(self.page_done)

        # Connect signals
        self._connect_signals()

        # Show first page
        self.stacked.setCurrentIndex(self.PAGE_SELECT)

    def _connect_signals(self) -> None:
        """Connect page signals."""
        # Page select signals
        self.page_select.scan_requested.connect(self._on_scan_requested)

        # Page processing signals
        self.page_processing.scan_complete.connect(self._on_scan_complete)
        self.page_processing.scan_cancelled.connect(self._on_scan_cancelled)

        # Page review signals
        self.page_review.organize_requested.connect(self._on_organize_requested)
        self.page_review.back_clicked.connect(self._on_back_to_select)

        # Page done signals
        self.page_done.new_scan_clicked.connect(self._on_new_scan)
        self.page_done.open_folder_clicked.connect(self._on_open_output_folder)

    def _on_scan_requested(
        self, input_folder: Path, output_folder: Path, move_files: bool
    ) -> None:
        """Handle scan request from select page.

        Args:
            input_folder: Folder with photos
            output_folder: Output folder
            move_files: Whether to move or copy files
        """
        self.scan_result = ScanResult(
            input_folder=input_folder,
            output_folder=output_folder,
        )
        self.move_files = move_files

        # Start processing page
        self.page_processing.start_scan(input_folder, output_folder)
        self.stacked.setCurrentIndex(self.PAGE_PROCESSING)

    def _on_scan_complete(self, scan_result: ScanResult) -> None:
        """Handle scan completion.

        Args:
            scan_result: Completed scan result
        """
        self.scan_result = scan_result
        self.page_review.set_scan_result(scan_result)
        self.stacked.setCurrentIndex(self.PAGE_REVIEW)

    def _on_scan_cancelled(self) -> None:
        """Handle scan cancellation."""
        self.stacked.setCurrentIndex(self.PAGE_SELECT)

    def _on_organize_requested(self, scan_result: ScanResult) -> None:
        """Handle organization request from review page.

        Args:
            scan_result: Updated scan result with labels
        """
        self.scan_result = scan_result
        self.page_done.set_scan_result(scan_result)
        self.page_done.organize_files(scan_result, self.move_files)
        self.stacked.setCurrentIndex(self.PAGE_DONE)

    def _on_back_to_select(self) -> None:
        """Go back to folder selection page."""
        self.stacked.setCurrentIndex(self.PAGE_SELECT)

    def _on_new_scan(self) -> None:
        """Start a new scan."""
        self.scan_result = None
        self.page_select.reset()
        self.stacked.setCurrentIndex(self.PAGE_SELECT)

    def _on_open_output_folder(self) -> None:
        """Open the output folder in file explorer."""
        if self.scan_result:
            import subprocess
            import platform

            try:
                if platform.system() == "Darwin":  # macOS
                    subprocess.run(["open", str(self.scan_result.output_folder)])
                elif platform.system() == "Windows":
                    subprocess.run(["explorer", str(self.scan_result.output_folder)])
                else:  # Linux
                    subprocess.run(["xdg-open", str(self.scan_result.output_folder)])
            except Exception as e:
                logger.error(f"Failed to open folder: {e}")

    def closeEvent(self, event):
        """Handle window close event."""
        # Cancel any running operations
        if self.page_processing.worker and self.page_processing.worker.isRunning():
            self.page_processing.worker.cancel()
            self.page_processing.worker.wait()

        if self.page_done.worker and self.page_done.worker.isRunning():
            self.page_done.worker.cancel()
            self.page_done.worker.wait()

        super().closeEvent(event)
