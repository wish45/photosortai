"""Scanner for finding and validating image files."""

import hashlib
import struct
from pathlib import Path
from typing import Generator, Optional
import logging
from PIL import Image

from app.config import SUPPORTED_FORMATS, FILE_HASH_CHUNK_SIZE

logger = logging.getLogger(__name__)


class FileHasher:
    """Computes content-based hashes for duplicate detection."""

    @staticmethod
    def compute_hash(file_path: Path) -> str:
        """SHA-256 of (file_size as 8 bytes + first 8KB).

        Detects content changes while ignoring renames.
        """
        size = file_path.stat().st_size
        h = hashlib.sha256()
        h.update(struct.pack("<Q", size))
        with open(file_path, "rb") as f:
            h.update(f.read(FILE_HASH_CHUNK_SIZE))
        return h.hexdigest()


class ImageScanner:
    """Scans folders for supported image files."""

    def __init__(self, recursive: bool = True):
        """Initialize scanner.

        Args:
            recursive: Whether to scan subdirectories
        """
        self.recursive = recursive

    def find_images(self, folder: Path) -> list[Path]:
        """Find all supported images in a folder.

        Args:
            folder: Path to folder to scan

        Returns:
            List of image paths
        """
        if not folder.is_dir():
            raise ValueError(f"Not a directory: {folder}")

        images = []
        pattern = "**/*" if self.recursive else "*"

        for fmt in SUPPORTED_FORMATS:
            images.extend(folder.glob(pattern + fmt.lower()))
            images.extend(folder.glob(pattern + fmt.upper()))

        # Remove duplicates and sort
        return sorted(set(images))

    def validate_image(self, path: Path) -> bool:
        """Check if file is a valid image.

        Args:
            path: Path to image file

        Returns:
            True if image is valid, False otherwise
        """
        try:
            # Handle HEIC files
            if path.suffix.lower() in {".heic", ".heif"}:
                try:
                    from PIL import Image as PILImage

                    PILImage.open(path).verify()
                    return True
                except Exception:
                    return False

            # Standard image validation
            with Image.open(path) as img:
                img.verify()
            return True
        except Exception as e:
            logger.warning(f"Invalid image file {path}: {e}")
            return False

    def scan_images(self, folder: Path) -> Generator[Path, None, None]:
        """Yield valid images from folder.

        Args:
            folder: Path to folder to scan

        Yields:
            Valid image paths
        """
        images = self.find_images(folder)
        for img_path in images:
            if self.validate_image(img_path):
                yield img_path
            else:
                logger.debug(f"Skipping invalid image: {img_path}")

    def find_new_images(
        self, folder: Path, known_hashes: set[str]
    ) -> tuple[list[Path], int, dict[Path, str]]:
        """Filter images, returning only those not in known_hashes.

        Returns:
            (new_images, skipped_count, hash_map) where hash_map maps path -> hash
        """
        all_images = self.find_images(folder)
        new_images = []
        skipped = 0
        hash_map = {}

        for img_path in all_images:
            try:
                file_hash = FileHasher.compute_hash(img_path)
                hash_map[img_path] = file_hash
                if file_hash in known_hashes:
                    skipped += 1
                else:
                    new_images.append(img_path)
            except Exception as e:
                logger.warning(f"Hash error for {img_path}: {e}")
                new_images.append(img_path)

        return new_images, skipped, hash_map

    def count_images(self, folder: Path) -> int:
        """Count total valid images in folder.

        Args:
            folder: Path to folder to scan

        Returns:
            Number of valid images
        """
        return sum(1 for _ in self.scan_images(folder))
