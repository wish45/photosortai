"""Background worker for scanning and clustering."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal

from app.core.models import FaceRecord, ScanResult

logger = logging.getLogger(__name__)


class ScanWorker(QThread):
    """QThread worker for scanning and clustering faces."""

    progress = pyqtSignal(int)  # Progress percentage (0-100)
    status = pyqtSignal(str)  # Status message
    face_detected = pyqtSignal(str, str)  # face_id, thumbnail_path
    finished_scan = pyqtSignal(object)  # ScanResult
    error = pyqtSignal(str)  # Error message
    cancelled = pyqtSignal()  # Cancelled signal

    def __init__(
        self,
        input_folder: Path,
        output_folder: Path,
    ):
        """Initialize scan worker.

        Args:
            input_folder: Folder containing photos
            output_folder: Folder for output files
        """
        super().__init__()
        self.input_folder = Path(input_folder)
        self.output_folder = Path(output_folder)
        self.is_cancelled = False

    def run(self) -> None:
        """Execute the scan and clustering pipeline."""
        try:
            self.status.emit("Initializing...")
            self.progress.emit(0)

            # Create result object
            scan_result = ScanResult(
                input_folder=self.input_folder,
                output_folder=self.output_folder,
                scanned_at=datetime.now().isoformat(),
            )

            # Lazy imports — heavy ML libs loaded only when scan actually runs
            from app.core.scanner import ImageScanner
            from app.core.face_detector import FaceDetector
            from app.core.clusterer import FaceClusterer

            # Step 1: Scan images
            self.status.emit("Scanning for images...")
            scanner = ImageScanner(recursive=True)
            images = scanner.find_images(self.input_folder)
            scan_result.total_photos = len(images)

            if not images:
                self.status.emit("No images found")
                self.finished_scan.emit(scan_result)
                return

            # Step 2: Detect faces
            self.status.emit("Initializing face detector...")
            detector = FaceDetector()

            for idx, image_path in enumerate(images):
                if self.is_cancelled:
                    self.cancelled.emit()
                    return

                progress_pct = int((idx / len(images)) * 70)  # 0-70% for detection
                self.progress.emit(progress_pct)
                self.status.emit(f"Detecting faces: {image_path.name} ({idx + 1}/{len(images)})")

                faces = detector.detect_faces(image_path)

                if faces:
                    scan_result.photos_with_faces += 1

                    # Create thumbnails and add to results
                    for face in faces:
                        thumbnail_path = (
                            self.output_folder / ".thumbnails" / f"{face.face_id}.jpg"
                        )

                        if detector.extract_face_thumbnail(
                            image_path, face.bbox, thumbnail_path
                        ):
                            face.thumbnail_path = thumbnail_path
                            self.face_detected.emit(face.face_id, str(thumbnail_path))

                        scan_result.face_records.append(face)

            if not scan_result.face_records:
                self.status.emit("No faces detected")
                self.finished_scan.emit(scan_result)
                return

            # Step 3: Cluster faces
            self.status.emit("Clustering faces...")
            clusterer = FaceClusterer()
            clusters = clusterer.cluster(scan_result.face_records)
            scan_result.clusters = clusters

            self.progress.emit(100)
            self.status.emit("Scan complete")
            self.finished_scan.emit(scan_result)

        except Exception as e:
            logger.exception("Scan worker error")
            self.error.emit(str(e))

    def cancel(self) -> None:
        """Cancel the scanning process."""
        self.is_cancelled = True
