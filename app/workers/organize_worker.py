"""Background worker for file organization."""

import logging

from PyQt6.QtCore import QThread, pyqtSignal

from app.core.models import ScanResult
from app.core.organizer import PhotoOrganizer

logger = logging.getLogger(__name__)


class OrganizeWorker(QThread):
    """QThread worker for organizing files."""

    progress = pyqtSignal(int)  # Progress percentage
    status = pyqtSignal(str)  # Status message
    finished_organize = pyqtSignal(dict)  # Result: person_name -> photo_paths
    error = pyqtSignal(str)  # Error message
    cancelled = pyqtSignal()  # Cancelled signal

    def __init__(self, scan_result: ScanResult, move_files: bool = False):
        """Initialize organize worker.

        Args:
            scan_result: ScanResult object with clusters
            move_files: If True, move files instead of copying
        """
        super().__init__()
        self.scan_result = scan_result
        self.move_files = move_files
        self.is_cancelled = False

    def run(self) -> None:
        """Execute the file organization pipeline."""
        try:
            self.status.emit("Preparing to organize...")
            self.progress.emit(0)

            organizer = PhotoOrganizer(move_files=self.move_files)

            # Validate output folder
            if not organizer.validate_folder_structure(self.scan_result.output_folder):
                raise ValueError(
                    f"Invalid output folder: {self.scan_result.output_folder}"
                )

            self.status.emit("Organizing photos...")
            result = organizer.organize(self.scan_result)

            self.progress.emit(100)
            self.status.emit("Organization complete")
            self.finished_organize.emit(result)

        except Exception as e:
            logger.exception("Organize worker error")
            self.error.emit(str(e))

    def cancel(self) -> None:
        """Cancel the organization process."""
        self.is_cancelled = True
