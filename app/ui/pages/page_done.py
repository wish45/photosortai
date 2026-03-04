"""Page 4: Completion summary."""

import logging
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont

from app.core.models import ScanResult, IncrementalScanResult
from app.workers.organize_worker import OrganizeWorker

logger = logging.getLogger(__name__)


class DonePage(QWidget):
    """Page showing completion summary."""

    new_scan_clicked = pyqtSignal()
    open_folder_clicked = pyqtSignal()

    def __init__(self):
        """Initialize done page."""
        super().__init__()
        self.scan_result = None
        self.worker = None
        self.is_organizing = False
        self._init_ui()

    def _init_ui(self) -> None:
        """Initialize UI components."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        self.title_label = QLabel("Organizing photos...")
        self.title_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        layout.addWidget(self.title_label)

        # Status
        self.status_label = QLabel("Processing files...")
        layout.addWidget(self.status_label)

        # Progress bar (initially hidden)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        layout.addSpacing(20)

        # Summary (shown after completion)
        self.summary_label = QLabel()
        self.summary_label.setWordWrap(True)
        self.summary_label.setStyleSheet("font-size: 12px; line-height: 1.5;")
        layout.addWidget(self.summary_label)

        layout.addStretch()

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.open_btn = QPushButton("Open Output Folder")
        self.open_btn.setMinimumWidth(150)
        self.open_btn.clicked.connect(self._on_open_folder)
        self.open_btn.setEnabled(False)
        button_layout.addWidget(self.open_btn)

        new_scan_btn = QPushButton("New Scan")
        new_scan_btn.setMinimumWidth(150)
        new_scan_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            """
        )
        new_scan_btn.clicked.connect(self._on_new_scan)
        button_layout.addWidget(new_scan_btn)

        layout.addLayout(button_layout)

    def set_scan_result(self, scan_result: ScanResult) -> None:
        """Set the scan result.

        Args:
            scan_result: ScanResult object
        """
        self.scan_result = scan_result

    def organize_files(self, scan_result: ScanResult, move_files: bool) -> None:
        """Start organizing files.

        Args:
            scan_result: ScanResult with labeled clusters
            move_files: Whether to move or copy files
        """
        self.scan_result = scan_result
        self.is_organizing = True
        self.progress_bar.setValue(0)
        self.open_btn.setEnabled(False)

        # Create worker
        self.worker = OrganizeWorker(scan_result, move_files)
        self.worker.progress.connect(self._on_progress)
        self.worker.status.connect(self._on_status)
        self.worker.finished_organize.connect(self._on_organize_complete)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_progress(self, value: int) -> None:
        """Update progress."""
        self.progress_bar.setValue(value)

    def _on_status(self, message: str) -> None:
        """Update status message."""
        self.status_label.setText(message)

    def _on_organize_complete(self, result: dict) -> None:
        """Handle organization completion.

        Args:
            result: Dictionary of person -> photo_paths
        """
        self.is_organizing = False
        self.progress_bar.setValue(100)
        self.title_label.setText("Organization Complete!")

        # Generate summary
        labeled_clusters = sum(1 for c in self.scan_result.clusters if c.label)
        photos_organized = sum(len(paths) for paths in result.values())

        if isinstance(self.scan_result, IncrementalScanResult) and self.scan_result.is_incremental:
            sr = self.scan_result
            auto_matched = len(sr.person_matches)
            summary = f"""
            <b>Incremental Scan Summary</b><br><br>
            Total files in folder: <b>{sr.total_files_in_folder}</b><br>
            Already processed (skipped): <b>{sr.skipped_already_processed}</b><br>
            New photos scanned: <b>{sr.new_photos_scanned}</b><br>
            Photos with faces: <b>{sr.photos_with_faces}</b><br>
            Auto-matched to known persons: <b>{auto_matched}</b><br>
            New clusters: <b>{labeled_clusters}</b><br>
            Photos organized: <b>{photos_organized}</b><br><br>
            <b>Output folder:</b> {sr.output_folder}
            """
        else:
            total_photos = self.scan_result.total_photos
            summary = f"""
            <b>Organization Summary</b><br><br>
            Total photos scanned: <b>{total_photos}</b><br>
            Photos with detected faces: <b>{self.scan_result.photos_with_faces}</b><br>
            Person clusters created: <b>{labeled_clusters}</b><br>
            Photos organized: <b>{photos_organized}</b><br><br>
            <b>Output folder:</b> {self.scan_result.output_folder}
            """

        self.summary_label.setText(summary)
        self.status_label.setText("Done!")
        self.open_btn.setEnabled(True)

        logger.info(f"Organization complete: {labeled_clusters} clusters, {photos_organized} photos")

    def _on_error(self, error_message: str) -> None:
        """Handle organization error."""
        logger.error(f"Organization error: {error_message}")
        self.is_organizing = False
        self.title_label.setText("Organization Error")
        self.status_label.setText(f"Error: {error_message}")
        self.open_btn.setEnabled(True)

    def _on_open_folder(self) -> None:
        """Open output folder."""
        self.open_folder_clicked.emit()

    def _on_new_scan(self) -> None:
        """Start a new scan."""
        self.new_scan_clicked.emit()
