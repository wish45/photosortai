"""Background worker for file organization."""

import logging

from PyQt6.QtCore import QThread, pyqtSignal

from app.core.models import ScanResult, IncrementalScanResult
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

            # Update registry (both full and incremental scans)
            self.status.emit("Updating face registry...")
            if isinstance(self.scan_result, IncrementalScanResult):
                self._update_registry(self.scan_result, result)
            else:
                self._update_registry_full(self.scan_result, result)

            self.progress.emit(100)
            self.status.emit("Organization complete")
            self.finished_organize.emit(result)

        except Exception as e:
            logger.exception("Organize worker error")
            self.error.emit(str(e))

    def _update_registry(self, scan_result: IncrementalScanResult, organize_result: dict) -> None:
        """Register processed files and persons in the face registry."""
        from app.storage.session_store import FaceRegistry
        from pathlib import Path

        registry = FaceRegistry()
        input_str = str(scan_result.input_folder)

        # 1. Register all processed file hashes
        for path_str, file_hash in scan_result.hash_map.items():
            p = Path(path_str)
            try:
                size = p.stat().st_size if p.exists() else 0
            except OSError:
                size = 0
            registry.register_processed_file(file_hash, path_str, size, input_str)

        # 2. Update matched persons' embeddings
        person_new_faces = {}  # person_id -> list of (face, file_hash)
        for pm in scan_result.person_matches:
            pid = pm.person.person_id
            fh = scan_result.hash_map.get(str(pm.face_record.photo_path), "")
            if pid not in person_new_faces:
                person_new_faces[pid] = []
            person_new_faces[pid].append((pm.face_record, fh))

        for pid, face_list in person_new_faces.items():
            embs = [f.embedding for f, _ in face_list]
            registry.update_known_person_embedding(pid, embs)
            for face, fh in face_list:
                registry.register_known_face(face, pid, fh)

        # 3. Register new clusters as new persons (or merge with existing)
        for cluster in scan_result.clusters:
            if not cluster.label:
                continue
            existing = registry.get_person_by_label(cluster.label)
            if existing:
                embs = [f.embedding for f in cluster.face_records]
                registry.update_known_person_embedding(existing.person_id, embs)
                for face in cluster.face_records:
                    fh = scan_result.hash_map.get(str(face.photo_path), "")
                    registry.register_known_face(face, existing.person_id, fh)
            else:
                embs = [f.embedding for f in cluster.face_records]
                pid = registry.register_known_person(cluster.label, embs)
                for face in cluster.face_records:
                    fh = scan_result.hash_map.get(str(face.photo_path), "")
                    registry.register_known_face(face, pid, fh)

        logger.info("Face registry updated (incremental)")

    def _update_registry_full(self, scan_result: ScanResult, organize_result: dict) -> None:
        """Register data from a full scan into the face registry for future incremental runs."""
        from app.storage.session_store import FaceRegistry
        from app.core.scanner import FileHasher
        from pathlib import Path

        registry = FaceRegistry()
        input_str = str(scan_result.input_folder)

        # Compute hashes for all photos that had faces and register them
        photo_hashes = {}
        all_photos = set()
        for face in scan_result.face_records:
            all_photos.add(face.photo_path)

        for photo_path in all_photos:
            try:
                fh = FileHasher.compute_hash(photo_path)
                photo_hashes[photo_path] = fh
                registry.register_processed_file(fh, str(photo_path), photo_path.stat().st_size, input_str)
            except Exception as e:
                logger.warning(f"Hash error for {photo_path}: {e}")

        # Register persons from labeled clusters
        for cluster in scan_result.clusters:
            if not cluster.label:
                continue
            existing = registry.get_person_by_label(cluster.label)
            if existing:
                embs = [f.embedding for f in cluster.face_records]
                registry.update_known_person_embedding(existing.person_id, embs)
                for face in cluster.face_records:
                    fh = photo_hashes.get(face.photo_path, "")
                    registry.register_known_face(face, existing.person_id, fh)
            else:
                embs = [f.embedding for f in cluster.face_records]
                pid = registry.register_known_person(cluster.label, embs)
                for face in cluster.face_records:
                    fh = photo_hashes.get(face.photo_path, "")
                    registry.register_known_face(face, pid, fh)

        logger.info("Face registry updated (full scan)")

    def cancel(self) -> None:
        """Cancel the organization process."""
        self.is_cancelled = True
