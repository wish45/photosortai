#!/usr/bin/env python3
"""CLI demo for testing PhotoSorterAI ML pipeline without UI."""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

from app.core.scanner import ImageScanner
from app.core.face_detector import FaceDetector
from app.core.clusterer import FaceClusterer
from app.core.models import ScanResult
from app.storage.session_store import SessionStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def scan_and_cluster(input_folder: Path, output_folder: Path) -> ScanResult:
    """Scan folder and cluster faces.

    Args:
        input_folder: Folder with photos
        output_folder: Output folder

    Returns:
        ScanResult object
    """
    print(f"\n{'='*60}")
    print(f"PhotoSorterAI - CLI Demo")
    print(f"{'='*60}\n")

    print(f"Input folder: {input_folder}")
    print(f"Output folder: {output_folder}")

    # Create result object
    scan_result = ScanResult(
        input_folder=input_folder,
        output_folder=output_folder,
        scanned_at=datetime.now().isoformat(),
    )

    # Step 1: Scan images
    print("\n[1/4] Scanning for images...")
    scanner = ImageScanner(recursive=True)
    images = scanner.find_images(input_folder)
    scan_result.total_photos = len(images)
    print(f"Found {len(images)} images")

    if not images:
        print("No images found. Exiting.")
        return scan_result

    # Step 2: Detect faces
    print("\n[2/4] Initializing face detector...")
    try:
        detector = FaceDetector()
    except Exception as e:
        print(f"Error initializing face detector: {e}")
        print("Note: InsightFace requires ONNX runtime. Install with:")
        print("  pip install onnxruntime")
        return scan_result

    print("Detecting faces...")
    face_count = 0
    for idx, image_path in enumerate(images):
        if (idx + 1) % 10 == 0 or (idx + 1) == len(images):
            print(f"  {idx + 1}/{len(images)} images processed...")

        faces = detector.detect_faces(image_path)

        if faces:
            scan_result.photos_with_faces += 1
            face_count += len(faces)

            # Create thumbnails
            for face in faces:
                thumbnail_path = (
                    output_folder / ".thumbnails" / f"{face.face_id}.jpg"
                )
                if detector.extract_face_thumbnail(
                    image_path, face.bbox, thumbnail_path
                ):
                    face.thumbnail_path = thumbnail_path

            scan_result.face_records.extend(faces)

    print(f"Detected {face_count} faces in {scan_result.photos_with_faces} photos")

    if not scan_result.face_records:
        print("No faces detected. Exiting.")
        return scan_result

    # Step 3: Cluster faces
    print("\n[3/4] Clustering faces...")
    clusterer = FaceClusterer()
    clusters = clusterer.cluster(scan_result.face_records)
    scan_result.clusters = clusters

    print(f"Created {len(clusters)} clusters")
    for cluster in clusters:
        print(f"  Cluster {cluster.cluster_id}: {cluster.size} faces")

    # Step 4: Summary
    print("\n[4/4] Scan Complete!")
    print(f"\n{'='*60}")
    print("Summary:")
    print(f"  Total photos: {scan_result.total_photos}")
    print(f"  Photos with faces: {scan_result.photos_with_faces}")
    print(f"  Total faces detected: {len(scan_result.face_records)}")
    print(f"  Clusters created: {len(clusters)}")
    print(f"{'='*60}\n")

    return scan_result


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="PhotoSorterAI CLI Demo - Test ML pipeline"
    )
    parser.add_argument(
        "input_folder",
        type=Path,
        help="Folder containing photos to organize",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output folder (default: same as input)",
    )
    parser.add_argument(
        "-s",
        "--save",
        action="store_true",
        help="Save scan result to database",
    )

    args = parser.parse_args()

    # Validate input folder
    if not args.input_folder.exists():
        print(f"Error: Input folder not found: {args.input_folder}")
        sys.exit(1)

    # Set output folder
    output_folder = args.output or args.input_folder
    output_folder.mkdir(parents=True, exist_ok=True)

    try:
        # Run pipeline
        scan_result = scan_and_cluster(args.input_folder, output_folder)

        # Save if requested
        if args.save:
            print("Saving scan result to database...")
            store = SessionStore()
            scan_id = store.save_scan_result(scan_result)
            print(f"Saved as scan ID: {scan_id}")

        return 0

    except KeyboardInterrupt:
        print("\nCancelled by user")
        return 1
    except Exception as e:
        logger.exception("Unexpected error")
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
