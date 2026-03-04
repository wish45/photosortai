"""File organization and folder creation."""

import logging
import shutil
from pathlib import Path
from typing import Optional

from app.config import UNSORTED_FOLDER_NAME, DUPLICATE_SUFFIX_PATTERN
from app.core.models import Cluster, ScanResult, IncrementalScanResult, FaceRecord

logger = logging.getLogger(__name__)


class PhotoOrganizer:
    """Organizes photos by person based on clustering."""

    def __init__(self, move_files: bool = False):
        """Initialize organizer.

        Args:
            move_files: If True, move files instead of copying
        """
        self.move_files = move_files

    def organize(self, scan_result: ScanResult) -> dict[str, list[Path]]:
        """Organize photos into person folders.

        Args:
            scan_result: ScanResult object with clusters and face records

        Returns:
            Dictionary mapping person name -> list of photo paths
        """
        if not scan_result.output_folder.exists():
            scan_result.output_folder.mkdir(parents=True, exist_ok=True)

        # Add person_matches (from incremental mode) to mapping
        photo_to_persons = self._build_photo_to_persons_mapping(scan_result)

        if isinstance(scan_result, IncrementalScanResult):
            for pm in scan_result.person_matches:
                p = pm.face_record.photo_path
                if p not in photo_to_persons:
                    photo_to_persons[p] = set()
                photo_to_persons[p].add(pm.person.label)

        # Create folders and organize files
        result = {}
        for photo_path, person_names in photo_to_persons.items():
            if not person_names:
                # No faces in this photo
                person_names = {UNSORTED_FOLDER_NAME}

            for person_name in person_names:
                folder = self._get_or_create_folder(
                    scan_result.output_folder, person_name
                )
                self._copy_or_move_file(photo_path, folder)

                if person_name not in result:
                    result[person_name] = []
                result[person_name].append(photo_path)

        logger.info(f"Organization complete: {len(result)} person folders")
        return result

    def _build_photo_to_persons_mapping(
        self, scan_result: ScanResult
    ) -> dict[Path, set[str]]:
        """Build mapping of photo path to person names.

        Args:
            scan_result: ScanResult object

        Returns:
            Dictionary mapping photo path -> set of person names
        """
        photo_to_persons = {}

        for cluster in scan_result.clusters:
            # Skip unconfirmed or unnamed clusters
            if not cluster.label:
                logger.warning(f"Skipping cluster {cluster.cluster_id}: no label")
                continue

            for face in cluster.face_records:
                if face.photo_path not in photo_to_persons:
                    photo_to_persons[face.photo_path] = set()
                photo_to_persons[face.photo_path].add(cluster.label)

        # Add photos with no faces detected
        all_face_photos = {f.photo_path for f in scan_result.face_records}
        for i in range(scan_result.total_photos):
            # This is simplified - in practice you'd track all scanned photos
            pass

        return photo_to_persons

    def _get_or_create_folder(self, base_folder: Path, person_name: str) -> Path:
        """Get or create person folder. Reuses existing folder for the same person.

        Args:
            base_folder: Base output folder
            person_name: Person's name

        Returns:
            Path to person folder
        """
        folder = base_folder / person_name
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def _copy_or_move_file(self, src: Path, dest_folder: Path) -> bool:
        """Copy or move file to destination, handling name conflicts.

        Args:
            src: Source file path
            dest_folder: Destination folder path

        Returns:
            True if successful
        """
        try:
            dest = dest_folder / src.name

            # Handle filename conflicts
            if dest.exists():
                stem = src.stem
                suffix = src.suffix
                counter = 2
                while dest.exists():
                    new_name = f"{stem}{DUPLICATE_SUFFIX_PATTERN.format(counter)}{suffix}"
                    dest = dest_folder / new_name
                    counter += 1
                    if counter > 1000:  # Safety limit
                        logger.error(f"Too many name conflicts for {src}")
                        return False

            # Copy or move
            if self.move_files:
                shutil.move(str(src), str(dest))
                logger.debug(f"Moved {src.name} to {dest_folder.name}")
            else:
                shutil.copy2(str(src), str(dest))
                logger.debug(f"Copied {src.name} to {dest_folder.name}")

            return True

        except Exception as e:
            logger.error(f"Error copying/moving {src}: {e}")
            return False

    def validate_folder_structure(self, folder: Path) -> bool:
        """Validate that folder structure is correct.

        Args:
            folder: Folder to validate

        Returns:
            True if valid
        """
        if not folder.is_dir():
            logger.error(f"Not a directory: {folder}")
            return False

        if not folder.exists():
            logger.error(f"Folder does not exist: {folder}")
            return False

        return True
