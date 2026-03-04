"""Tests for image scanner."""

import tempfile
from pathlib import Path

import pytest
from PIL import Image

from app.core.scanner import ImageScanner


@pytest.fixture
def temp_image_folder():
    """Create a temporary folder with test images."""
    with tempfile.TemporaryDirectory() as tmpdir:
        folder = Path(tmpdir)

        # Create some test images
        for i in range(3):
            img = Image.new("RGB", (100, 100), color="red")
            img.save(folder / f"test_{i}.jpg")

        # Create subdirectory with images
        subfolder = folder / "subfolder"
        subfolder.mkdir()
        for i in range(2):
            img = Image.new("RGB", (100, 100), color="blue")
            img.save(subfolder / f"test_{i}.png")

        # Create invalid file
        (folder / "invalid.jpg").write_text("not an image")

        yield folder


def test_find_images_recursive(temp_image_folder):
    """Test finding images recursively."""
    scanner = ImageScanner(recursive=True)
    images = scanner.find_images(temp_image_folder)

    assert len(images) >= 5  # At least 5 valid image files


def test_find_images_non_recursive(temp_image_folder):
    """Test finding images non-recursively."""
    scanner = ImageScanner(recursive=False)
    images = scanner.find_images(temp_image_folder)

    assert len(images) == 3  # Only top-level images


def test_validate_image(temp_image_folder):
    """Test image validation."""
    scanner = ImageScanner()

    # Valid image
    valid_img = temp_image_folder / "test_0.jpg"
    assert scanner.validate_image(valid_img) is True

    # Invalid image
    invalid_img = temp_image_folder / "invalid.jpg"
    assert scanner.validate_image(invalid_img) is False


def test_scan_images(temp_image_folder):
    """Test scanning images generator."""
    scanner = ImageScanner(recursive=True)
    images = list(scanner.scan_images(temp_image_folder))

    assert len(images) >= 5
    assert all(img.is_file() for img in images)


def test_count_images(temp_image_folder):
    """Test counting images."""
    scanner = ImageScanner(recursive=True)
    count = scanner.count_images(temp_image_folder)

    assert count >= 5


def test_invalid_folder():
    """Test handling of invalid folder."""
    scanner = ImageScanner()

    with pytest.raises(ValueError):
        scanner.find_images(Path("/nonexistent/path"))
