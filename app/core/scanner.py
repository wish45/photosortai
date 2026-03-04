"""Scanner for finding and validating image files."""

from pathlib import Path
from typing import Generator, Optional
import logging
from PIL import Image

from app.config import SUPPORTED_FORMATS

logger = logging.getLogger(__name__)


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

    def count_images(self, folder: Path) -> int:
        """Count total valid images in folder.

        Args:
            folder: Path to folder to scan

        Returns:
            Number of valid images
        """
        return sum(1 for _ in self.scan_images(folder))
