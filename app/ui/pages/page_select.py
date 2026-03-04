"""Page 1: Folder selection."""

import logging
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QCheckBox,
    QFileDialog,
    QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QUrl
from PyQt6.QtGui import QDropEvent, QDragEnterEvent

logger = logging.getLogger(__name__)


class SelectFolderPage(QWidget):
    """Page for selecting input and output folders."""

    scan_requested = pyqtSignal(Path, Path, bool)  # input_folder, output_folder, move_files

    def __init__(self):
        """Initialize folder selection page."""
        super().__init__()
        self.input_folder = None
        self.output_folder = None
        self._init_ui()

    def _init_ui(self) -> None:
        """Initialize UI components."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title = QLabel("Photo Sorter AI")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)

        subtitle = QLabel("Automatically organize photos by detected faces")
        subtitle.setStyleSheet("font-size: 12px; color: gray;")
        layout.addWidget(subtitle)

        layout.addSpacing(20)

        # Input folder section
        layout.addWidget(QLabel("Source folder (photos to organize):"))

        input_layout = QHBoxLayout()
        self.input_path = QLineEdit()
        self.input_path.setPlaceholderText("Drag and drop folder here or click Browse...")
        self.input_path.setReadOnly(True)
        input_layout.addWidget(self.input_path)

        input_browse = QPushButton("Browse...")
        input_browse.clicked.connect(self._on_input_browse)
        input_layout.addWidget(input_browse)
        layout.addLayout(input_layout)

        # Output folder section
        layout.addWidget(QLabel("Output folder (organized by person):"))

        output_layout = QHBoxLayout()
        self.output_path = QLineEdit()
        self.output_path.setPlaceholderText("Default: same as source")
        self.output_path.setReadOnly(True)
        output_layout.addWidget(self.output_path)

        output_browse = QPushButton("Browse...")
        output_browse.clicked.connect(self._on_output_browse)
        output_layout.addWidget(output_browse)
        layout.addLayout(output_layout)

        layout.addSpacing(10)

        # Options
        self.move_checkbox = QCheckBox("Move files instead of copying")
        self.move_checkbox.setChecked(False)
        layout.addWidget(self.move_checkbox)

        layout.addSpacing(20)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        scan_btn = QPushButton("Start Scan")
        scan_btn.setMinimumWidth(150)
        scan_btn.setStyleSheet(
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
        scan_btn.clicked.connect(self._on_scan)
        button_layout.addWidget(scan_btn)

        layout.addLayout(button_layout)
        layout.addStretch()

        # Enable drag and drop on the input field
        self.input_path.dragEnterEvent = self._on_drag_enter
        self.input_path.dropEvent = self._on_drop

    def _on_input_browse(self) -> None:
        """Browse for input folder."""
        folder = QFileDialog.getExistingDirectory(
            self, "Select folder with photos"
        )
        if folder:
            self.input_folder = Path(folder)
            self.input_path.setText(str(self.input_folder))
            # Auto-set output folder if not set
            if not self.output_folder:
                self.output_folder = self.input_folder

    def _on_output_browse(self) -> None:
        """Browse for output folder."""
        folder = QFileDialog.getExistingDirectory(
            self, "Select output folder"
        )
        if folder:
            self.output_folder = Path(folder)
            self.output_path.setText(str(self.output_folder))

    def _on_drag_enter(self, event: QDragEnterEvent) -> None:
        """Handle drag enter event."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def _on_drop(self, event: QDropEvent) -> None:
        """Handle drop event."""
        urls = event.mimeData().urls()
        if urls:
            path = Path(urls[0].toLocalFile())
            if path.is_dir():
                self.input_folder = path
                self.input_path.setText(str(self.input_folder))
                if not self.output_folder:
                    self.output_folder = self.input_folder
                event.acceptProposedAction()

    def _on_scan(self) -> None:
        """Handle scan button click."""
        if not self.input_folder:
            QMessageBox.warning(self, "Error", "Please select a source folder")
            return

        if not self.input_folder.exists():
            QMessageBox.warning(
                self, "Error", f"Folder not found: {self.input_folder}"
            )
            return

        # Use input folder as output if not specified
        output = self.output_folder or self.input_folder

        if self.input_folder == output:
            reply = QMessageBox.question(
                self,
                "Confirm",
                "Output folder is same as input. Files will be organized in place. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.No:
                return

        logger.info(f"Starting scan: {self.input_folder} -> {output}")
        self.scan_requested.emit(self.input_folder, output, self.move_checkbox.isChecked())

    def reset(self) -> None:
        """Reset the page for a new scan."""
        self.input_folder = None
        self.output_folder = None
        self.input_path.clear()
        self.output_path.clear()
        self.move_checkbox.setChecked(False)
