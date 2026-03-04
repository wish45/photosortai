"""Background worker for scanning and clustering."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QThread, pyqtSignal

from app.core.models import FaceRecord, ScanResult, IncrementalScanResult

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
        incremental: bool = False,
    ):
        super().__init__()
        self.input_folder = Path(input_folder)
        self.output_folder = Path(output_folder)
        self.incremental = incremental
        self.is_cancelled = False

    def run(self) -> None:
        """Execute the scan and clustering pipeline."""
        try:
            self.status.emit("Initializing...")
            self.progress.emit(0)

            # Lazy imports — heavy ML libs loaded only when scan actually runs
            from app.core.scanner import ImageScanner
            from app.core.face_detector import FaceDetector
            from app.core.clusterer import FaceClusterer

            scanner = ImageScanner(recursive=True)

            if self.incremental:
                scan_result = self._run_incremental(scanner, FaceDetector, FaceClusterer)
            else:
                scan_result = self._run_full(scanner, FaceDetector, FaceClusterer)

            if scan_result is not None:
                self.progress.emit(100)
                self.status.emit("Scan complete")
                self.finished_scan.emit(scan_result)

        except Exception as e:
            logger.exception("Scan worker error")
            self.error.emit(str(e))

    def _run_full(self, scanner, FaceDetector, FaceClusterer):
        """Original full scan path."""
        scan_result = ScanResult(
            input_folder=self.input_folder,
            output_folder=self.output_folder,
            scanned_at=datetime.now().isoformat(),
        )

        self.status.emit("Scanning for images...")
        images = scanner.find_images(self.input_folder)
        scan_result.total_photos = len(images)

        if not images:
            self.status.emit("No images found")
            return scan_result

        self.status.emit("Initializing face detector...")
        detector = FaceDetector()

        for idx, image_path in enumerate(images):
            if self.is_cancelled:
                self.cancelled.emit()
                return None

            progress_pct = int((idx / len(images)) * 70)
            self.progress.emit(progress_pct)
            self.status.emit(f"Detecting faces: {image_path.name} ({idx + 1}/{len(images)})")

            faces = detector.detect_faces(image_path)
            if faces:
                scan_result.photos_with_faces += 1
                for face in faces:
                    thumbnail_path = self.output_folder / ".thumbnails" / f"{face.face_id}.jpg"
                    if detector.extract_face_thumbnail(image_path, face.bbox, thumbnail_path):
                        face.thumbnail_path = thumbnail_path
                        self.face_detected.emit(face.face_id, str(thumbnail_path))
                    scan_result.face_records.append(face)

        if not scan_result.face_records:
            self.status.emit("No faces detected")
            return scan_result

        self.status.emit("Clustering faces...")
        clusterer = FaceClusterer()
        scan_result.clusters = clusterer.cluster(scan_result.face_records)
        return scan_result

    def _run_incremental(self, scanner, FaceDetector, FaceClusterer):
        """Incremental scan: hash compare → detect new → match known → cluster rest."""
        from app.storage.session_store import FaceRegistry

        registry = FaceRegistry()
        input_str = str(self.input_folder)

        # Step 1: Hash-based filtering
        self.status.emit("Comparing with previous scan...")
        known_hashes = registry.get_processed_hashes(input_str)
        new_images, skipped, hash_map = scanner.find_new_images(self.input_folder, known_hashes)

        scan_result = IncrementalScanResult(
            input_folder=self.input_folder,
            output_folder=self.output_folder,
            scanned_at=datetime.now().isoformat(),
            is_incremental=True,
            total_files_in_folder=len(new_images) + skipped,
            skipped_already_processed=skipped,
            new_photos_scanned=len(new_images),
            hash_map={str(k): v for k, v in hash_map.items()},
        )
        scan_result.total_photos = len(new_images)

        self.status.emit(f"Found {len(new_images)} new photos ({skipped} skipped)")

        if not new_images:
            self.status.emit("No new photos to process")
            return scan_result

        # Step 2: Face detection on new photos
        self.status.emit("Initializing face detector...")
        detector = FaceDetector()

        for idx, image_path in enumerate(new_images):
            if self.is_cancelled:
                self.cancelled.emit()
                return None

            progress_pct = int((idx / len(new_images)) * 60)
            self.progress.emit(progress_pct)
            self.status.emit(f"Detecting faces: {image_path.name} ({idx + 1}/{len(new_images)})")

            faces = detector.detect_faces(image_path)
            if faces:
                scan_result.photos_with_faces += 1
                for face in faces:
                    thumbnail_path = self.output_folder / ".thumbnails" / f"{face.face_id}.jpg"
                    if detector.extract_face_thumbnail(image_path, face.bbox, thumbnail_path):
                        face.thumbnail_path = thumbnail_path
                        self.face_detected.emit(face.face_id, str(thumbnail_path))
                    scan_result.face_records.append(face)

        if not scan_result.face_records:
            self.status.emit("No faces detected in new photos")
            return scan_result

        # Step 3: Match against known persons
        self.progress.emit(70)
        self.status.emit("Matching against known persons...")
        known_persons = registry.get_known_persons()
        clusterer = FaceClusterer()

        if known_persons:
            matched, unmatched = clusterer.match_against_known_persons(
                scan_result.face_records, known_persons
            )
            scan_result.person_matches = matched
        else:
            unmatched = scan_result.face_records

        # Step 4: Cluster unmatched faces
        if unmatched:
            self.status.emit("Clustering new faces...")
            self.progress.emit(80)
            scan_result.clusters = clusterer.cluster(unmatched)
        else:
            scan_result.clusters = []

        return scan_result

    def cancel(self) -> None:
        """Cancel the scanning process."""
        self.is_cancelled = True
