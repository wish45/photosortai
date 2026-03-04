"""Page 3: Cluster review and labeling."""

import logging
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QScrollArea,
    QFrame,
    QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QPixmap

from app.core.models import ScanResult, Cluster

logger = logging.getLogger(__name__)


class ReviewPage(QWidget):
    """Page for reviewing and labeling detected clusters."""

    organize_requested = pyqtSignal(object)  # ScanResult
    back_clicked = pyqtSignal()

    def __init__(self):
        """Initialize review page."""
        super().__init__()
        self.scan_result = None
        self.cluster_widgets = []
        self._init_ui()

    def _init_ui(self) -> None:
        """Initialize UI components."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title = QLabel("Review Detected People")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        layout.addWidget(title)

        subtitle = QLabel(
            "Review the detected clusters and enter names for each person. "
            "Leave blank to skip."
        )
        subtitle.setStyleSheet("color: gray;")
        layout.addWidget(subtitle)

        layout.addSpacing(10)

        # Scrollable cluster area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_widget = QFrame()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_layout.setSpacing(15)
        self.scroll_area.setWidget(self.scroll_widget)
        layout.addWidget(self.scroll_area, 1)

        layout.addSpacing(10)

        # Buttons
        button_layout = QHBoxLayout()

        back_btn = QPushButton("Back")
        back_btn.setMinimumWidth(100)
        back_btn.clicked.connect(self._on_back)
        button_layout.addWidget(back_btn)

        button_layout.addStretch()

        organize_btn = QPushButton("Organize Files")
        organize_btn.setMinimumWidth(150)
        organize_btn.setStyleSheet(
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
        organize_btn.clicked.connect(self._on_organize)
        button_layout.addWidget(organize_btn)

        layout.addLayout(button_layout)

    def set_scan_result(self, scan_result: ScanResult) -> None:
        """Set the scan result and display clusters.

        Args:
            scan_result: ScanResult object
        """
        self.scan_result = scan_result
        self._display_clusters()

    def _display_clusters(self) -> None:
        """Display cluster cards."""
        # Clear existing
        for widget in self.cluster_widgets:
            self.scroll_layout.removeWidget(widget)
            widget.deleteLater()
        self.cluster_widgets.clear()

        if not self.scan_result or not self.scan_result.clusters:
            no_clusters = QLabel("No clusters found")
            self.scroll_layout.addWidget(no_clusters)
            return

        # Create cluster cards
        for cluster in self.scan_result.clusters:
            card = self._create_cluster_card(cluster)
            self.scroll_layout.addWidget(card)
            self.cluster_widgets.append(card)

        self.scroll_layout.addStretch()

    def _create_cluster_card(self, cluster: Cluster) -> QFrame:
        """Create a cluster card widget.

        Args:
            cluster: Cluster object

        Returns:
            Cluster card widget
        """
        card = QFrame()
        card.setStyleSheet(
            """
            QFrame {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 10px;
                background-color: #f9f9f9;
            }
            """
        )

        layout = QVBoxLayout(card)

        # Header with cluster info
        header_layout = QHBoxLayout()
        cluster_label = QLabel(f"Cluster {cluster.cluster_id} ({cluster.size} faces)")
        cluster_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        header_layout.addWidget(cluster_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Thumbnails
        thumb_layout = QHBoxLayout()
        thumb_layout.setSpacing(5)

        faces_to_show = min(6, len(cluster.face_records))
        for i, face in enumerate(cluster.face_records[:faces_to_show]):
            if face.thumbnail_path and face.thumbnail_path.exists():
                thumb = QPixmap(str(face.thumbnail_path))
                if not thumb.isNull():
                    thumb = thumb.scaledToHeight(100, Qt.TransformationMode.SmoothTransformation)
                    label = QLabel()
                    label.setPixmap(thumb)
                    label.setStyleSheet("border: 1px solid #ccc; border-radius: 4px;")
                    thumb_layout.addWidget(label)

        if len(cluster.face_records) > faces_to_show:
            more_label = QLabel(f"+{len(cluster.face_records) - faces_to_show} more")
            more_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            more_label.setStyleSheet(
                """
                border: 1px solid #ccc;
                border-radius: 4px;
                background-color: #eee;
                min-width: 100px;
                """
            )
            thumb_layout.addWidget(more_label)

        thumb_layout.addStretch()
        layout.addLayout(thumb_layout)

        layout.addSpacing(5)

        # Name input
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Person name:"))
        name_input = QLineEdit()
        name_input.setPlaceholderText("e.g., John Doe")
        name_input.setText(cluster.label or "")
        name_input.textChanged.connect(
            lambda text, c=cluster: self._on_name_changed(c, text)
        )
        name_layout.addWidget(name_input)
        layout.addLayout(name_layout)

        # Store reference
        card.cluster = cluster
        card.name_input = name_input

        return card

    def _on_name_changed(self, cluster: Cluster, name: str) -> None:
        """Handle name change.

        Args:
            cluster: Cluster object
            name: New name
        """
        cluster.label = name.strip() if name.strip() else None

    def _on_back(self) -> None:
        """Handle back button."""
        self.back_clicked.emit()

    def _on_organize(self) -> None:
        """Handle organize button."""
        # Validate that at least some clusters have labels
        labeled = sum(1 for c in self.scan_result.clusters if c.label)

        if labeled == 0:
            reply = QMessageBox.question(
                self,
                "No names entered",
                "No person names were entered. Photos with no labeled clusters will be skipped. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.No:
                return

        logger.info(f"Organizing {labeled} labeled clusters")
        self.organize_requested.emit(self.scan_result)
