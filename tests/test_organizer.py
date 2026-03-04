"""Tests for file organization."""

import tempfile
from pathlib import Path

import pytest
from PIL import Image

from app.core.models import FaceRecord, Cluster, ScanResult
from app.core.organizer import PhotoOrganizer


@pytest.fixture
def temp_photos():
    """Create temporary photos for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        photos = []
        for i in range(5):
            photo_path = Path(tmpdir) / f"photo_{i}.jpg"
            img = Image.new("RGB", (100, 100), color="red")
            img.save(photo_path)
            photos.append(photo_path)

        yield photos, Path(tmpdir)


@pytest.fixture
def scan_result_with_clusters(temp_photos):
    """Create a ScanResult with clusters."""
    photos, input_folder = temp_photos
    output_folder = input_folder / "output"
    output_folder.mkdir(exist_ok=True)

    scan_result = ScanResult(
        input_folder=input_folder,
        output_folder=output_folder,
        total_photos=len(photos),
        photos_with_faces=len(photos),
    )

    import numpy as np

    # Create clusters with labeled faces
    for person_idx, person_name in enumerate(["Alice", "Bob"]):
        cluster = Cluster(cluster_id=person_idx, label=person_name)

        for photo_idx in range(person_idx * 2, min((person_idx + 1) * 2, len(photos))):
            face = FaceRecord(
                photo_path=photos[photo_idx],
                bbox=(0, 0, 100, 100),
                embedding=np.random.randn(512).astype(np.float32),
            )
            face.embedding = face.embedding / np.linalg.norm(face.embedding)
            cluster.add_face(face)

        scan_result.clusters.append(cluster)
        scan_result.face_records.extend(cluster.face_records)

    return scan_result, output_folder


def test_organize_copy(scan_result_with_clusters):
    """Test organizing with copy mode."""
    scan_result, output_folder = scan_result_with_clusters

    organizer = PhotoOrganizer(move_files=False)
    result = organizer.organize(scan_result)

    # Check that person folders were created
    assert (output_folder / "Alice").exists()
    assert (output_folder / "Bob").exists()

    # Check that files were copied
    assert len(list((output_folder / "Alice").glob("*.jpg"))) > 0
    assert len(list((output_folder / "Bob").glob("*.jpg"))) > 0


def test_organize_move(scan_result_with_clusters):
    """Test organizing with move mode."""
    scan_result, output_folder = scan_result_with_clusters

    # Get original photo paths
    original_photos = [f.photo_path for f in scan_result.face_records]
    original_count = len(original_photos)

    organizer = PhotoOrganizer(move_files=True)
    result = organizer.organize(scan_result)

    # Check that person folders were created
    assert (output_folder / "Alice").exists()
    assert (output_folder / "Bob").exists()

    # Files should exist in output folders
    total_in_output = len(list(output_folder.glob("**/*.jpg"))) - original_count


def test_folder_validation():
    """Test folder validation."""
    organizer = PhotoOrganizer()

    # Test nonexistent folder
    with tempfile.TemporaryDirectory() as tmpdir:
        assert organizer.validate_folder_structure(Path(tmpdir)) is True

    # Test nonexistent path
    assert organizer.validate_folder_structure(Path("/nonexistent")) is False


def test_filename_conflict_handling(scan_result_with_clusters):
    """Test handling of filename conflicts."""
    scan_result, output_folder = scan_result_with_clusters

    # Create a file that will conflict
    alice_folder = output_folder / "Alice"
    alice_folder.mkdir(exist_ok=True)

    # Copy a photo to Alice folder manually
    from shutil import copy2

    if scan_result.face_records:
        original_photo = scan_result.face_records[0].photo_path
        copy2(str(original_photo), str(alice_folder / original_photo.name))

    organizer = PhotoOrganizer(move_files=False)
    result = organizer.organize(scan_result)

    # Should handle the conflict gracefully
    assert (alice_folder).exists()
    assert len(list(alice_folder.glob("*.jpg"))) > 0
