"""Page 2: Processing/Progress display."""

import logging
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QScrollArea,
    QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QPixmap, QFont

from app.core.models import ScanResult
from app.workers.scan_worker import ScanWorker

logger = logging.getLogger(__name__)


class ProcessingPage(QWidget):
    """Page showing scan and clustering progress."""

    scan_complete = pyqtSignal(object)  # ScanResult
    scan_cancelled = pyqtSignal()

    def __init__(self):
        """Initialize processing page."""
        super().__init__()
        self.worker = None
        self.current_thumbnails = []
        self._init_ui()

    def _init_ui(self) -> None:
        """Initialize UI components."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title = QLabel("Processing...")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        layout.addWidget(title)

        # Status label
        self.status_label = QLabel("Initializing...")
        layout.addWidget(self.status_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        layout.addWidget(self.progress_bar)

        layout.addSpacing(10)

        # Thumbnail preview area
        preview_label = QLabel("Detected faces:")
        layout.addWidget(preview_label)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("border: 1px solid #ddd; border-radius: 4px;")
        self.scroll_widget = QFrame()
        self.scroll_layout = QHBoxLayout(self.scroll_widget)
        self.scroll_layout.setSpacing(5)
        self.scroll_layout.addStretch()
        self.scroll_area.setWidget(self.scroll_widget)
        layout.addWidget(self.scroll_area, 1)

        layout.addSpacing(10)

        # Cancel button
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setMinimumWidth(100)
        self.cancel_btn.clicked.connect(self._on_cancel)
        button_layout.addWidget(self.cancel_btn)

        layout.addLayout(button_layout)

    def start_scan(
        self, input_folder: Path, output_folder: Path, incremental: bool = False
    ) -> None:
        """Start the scan process."""
        logger.debug(f"Starting scan: {input_folder} (incremental={incremental})")

        self.progress_bar.setValue(0)
        self.status_label.setText("Initializing...")
        self.current_thumbnails.clear()
        self._clear_thumbnails()

        self.worker = ScanWorker(input_folder, output_folder, incremental=incremental)
        self.worker.progress.connect(self._on_progress)
        self.worker.status.connect(self._on_status)
        self.worker.face_detected.connect(self._on_face_detected)
        self.worker.finished_scan.connect(self._on_scan_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_progress(self, value: int) -> None:
        """Update progress bar."""
        self.progress_bar.setValue(value)

    def _on_status(self, message: str) -> None:
        """Update status message."""
        self.status_label.setText(message)

    def _on_face_detected(self, face_id: str, thumbnail_path: str) -> None:
        """Handle face detection with thumbnail.

        Args:
            face_id: Face ID
            thumbnail_path: Path to thumbnail image
        """
        try:
            thumb = QPixmap(thumbnail_path)
            if not thumb.isNull():
                # Scale thumbnail
                thumb = thumb.scaledToHeight(80, Qt.TransformationMode.SmoothTransformation)

                # Create label and add to scroll layout
                label = QLabel()
                label.setPixmap(thumb)
                label.setStyleSheet(
                    """
                    border: 1px solid #ccc;
                    border-radius: 4px;
                    padding: 2px;
                    """
                )
                label.setToolTip(face_id[:8])
                self.scroll_layout.insertWidget(
                    len(self.current_thumbnails), label
                )
                self.current_thumbnails.append(label)

                # Keep only last 20 thumbnails visible
                if len(self.current_thumbnails) > 20:
                    old_label = self.current_thumbnails.pop(0)
                    self.scroll_layout.removeWidget(old_label)
                    old_label.deleteLater()

        except Exception as e:
            logger.debug(f"Error displaying thumbnail: {e}")

    def _on_scan_finished(self, scan_result: ScanResult) -> None:
        """Handle scan completion."""
        logger.info("Scan completed")
        self.progress_bar.setValue(100)
        self.status_label.setText("Scan complete! Clustering...")
        self.scan_complete.emit(scan_result)

    def _on_error(self, error_message: str) -> None:
        """Handle scan error."""
        logger.error(f"Scan error: {error_message}")
        self.status_label.setText(f"Error: {error_message}")
        self.cancel_btn.setEnabled(True)

    def _on_cancel(self) -> None:
        """Handle cancel button click."""
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.status_label.setText("Cancelling...")
            self.cancel_btn.setEnabled(False)

        QTimer.singleShot(1000, self._on_cancel_confirmed)

    def _on_cancel_confirmed(self) -> None:
        """Confirm cancellation after worker stops."""
        self.scan_cancelled.emit()

    def _clear_thumbnails(self) -> None:
        """Clear all thumbnails."""
        for label in self.current_thumbnails:
            self.scroll_layout.removeWidget(label)
            label.deleteLater()
        self.current_thumbnails.clear()
