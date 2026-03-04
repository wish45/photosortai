"""Face detection using InsightFace."""

import logging
import os
import sys
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

# Patch broken Cython extensions before importing insightface
import app.core._insightface_patch  # noqa: F401

from insightface.app import FaceAnalysis
from PIL import Image

from app.config import FACE_MODEL, FACE_EMBEDDING_DIM, MIN_FACE_CONFIDENCE
from app.core.models import FaceRecord

logger = logging.getLogger(__name__)


class FaceDetector:
    """Wrapper around InsightFace FaceAnalysis."""

    def __init__(self, model_name: str = FACE_MODEL, device: str = "auto"):
        """Initialize face detector.

        Args:
            model_name: InsightFace model name (e.g., 'buffalo_l')
            device: Device to use ('cpu', 'gpu', or 'auto')
        """
        self.model_name = model_name
        self.device = device
        self.app = None
        self._init_app()

    def _init_app(self) -> None:
        """Initialize FaceAnalysis app with proper device selection."""
        try:
            # Get model root path - handle PyInstaller bundled models
            if getattr(sys, "frozen", False):
                # Running as PyInstaller bundle
                model_root = Path(sys.executable).parent / "insightface"
            else:
                model_root = None

            # Determine execution provider
            if self.device == "auto":
                providers = self._get_providers()
            else:
                providers = [self.device]

            # Initialize FaceAnalysis
            kwargs = dict(name=self.model_name, providers=providers)
            if model_root:
                kwargs["root"] = str(model_root)
            self.app = FaceAnalysis(**kwargs)
            self.app.prepare(ctx_id=0, det_thresh=MIN_FACE_CONFIDENCE)

            logger.info(f"Initialized {self.model_name} on {providers}")
        except Exception as e:
            logger.error(f"Failed to initialize FaceAnalysis: {e}")
            raise

    def _get_providers(self) -> list[str]:
        """Get optimal execution providers based on platform.

        Returns:
            List of providers to try
        """
        import platform

        providers = []

        try:
            import onnxruntime as ort
            available = ort.get_available_providers()

            # Windows NVIDIA GPU
            if "CUDAExecutionProvider" in available:
                providers.append("CUDAExecutionProvider")

            # Windows DirectML (AMD/Intel/NVIDIA)
            if "DmlExecutionProvider" in available:
                providers.append("DmlExecutionProvider")

            # Apple Silicon
            if sys.platform == "darwin" and "CoreMLExecutionProvider" in available:
                providers.append("CoreMLExecutionProvider")
        except ImportError:
            pass

        # Fallback — always available
        providers.append("CPUExecutionProvider")

        return providers

    def detect_faces(self, image_path: Path) -> list[FaceRecord]:
        """Detect faces in an image.

        Args:
            image_path: Path to image file

        Returns:
            List of FaceRecord objects
        """
        if not self.app:
            raise RuntimeError("FaceAnalysis not initialized")

        try:
            # Load image
            img = self._load_image(image_path)
            if img is None:
                return []

            # Detect faces
            faces = self.app.get(img)

            # Convert to FaceRecord objects
            records = []
            for face in faces:
                # Get bounding box
                bbox = face.bbox.astype(int)
                x1, y1, x2, y2 = bbox[0], bbox[1], bbox[2], bbox[3]

                # Get embedding (normalize to L2)
                embedding = face.embedding.astype(np.float32)
                embedding = embedding / np.linalg.norm(embedding)

                record = FaceRecord(
                    photo_path=image_path,
                    bbox=(int(x1), int(y1), int(x2), int(y2)),
                    embedding=embedding,
                )
                records.append(record)

            logger.debug(
                f"Detected {len(records)} faces in {image_path.name}"
            )
            return records

        except Exception as e:
            logger.error(f"Error detecting faces in {image_path}: {e}")
            return []

    def _load_image(self, image_path: Path) -> Optional[np.ndarray]:
        """Load image from file, handling HEIC format.

        Args:
            image_path: Path to image

        Returns:
            Image array in BGR format, or None if failed
        """
        try:
            # Handle HEIC files with pillow-heif
            if image_path.suffix.lower() in {".heic", ".heif"}:
                try:
                    from PIL import Image as PILImage

                    img = PILImage.open(image_path).convert("RGB")
                    # Convert PIL to numpy BGR
                    img_array = np.array(img)
                    return cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
                except Exception as e:
                    logger.debug(f"HEIC loading failed for {image_path}: {e}")

            # Standard image loading with OpenCV
            img = cv2.imread(str(image_path))
            if img is None:
                logger.warning(f"Failed to load image: {image_path}")
                return None

            return img

        except Exception as e:
            logger.error(f"Error loading image {image_path}: {e}")
            return None

    def extract_face_thumbnail(
        self,
        image_path: Path,
        bbox: tuple[int, int, int, int],
        output_path: Path,
        size: tuple[int, int] = (150, 150),
    ) -> bool:
        """Extract and save face thumbnail.

        Args:
            image_path: Path to source image
            bbox: Bounding box (x1, y1, x2, y2)
            output_path: Where to save thumbnail
            size: Thumbnail size

        Returns:
            True if successful
        """
        try:
            img = self._load_image(image_path)
            if img is None:
                return False

            x1, y1, x2, y2 = bbox
            face_img = img[max(0, y1) : y2, max(0, x1) : x2]

            if face_img.size == 0:
                return False

            # Convert BGR to RGB and save
            face_rgb = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(face_rgb)
            pil_img.thumbnail(size, Image.Resampling.LANCZOS)

            output_path.parent.mkdir(parents=True, exist_ok=True)
            pil_img.save(str(output_path), quality=85, optimize=True)

            logger.debug(f"Saved thumbnail to {output_path}")
            return True

        except Exception as e:
            logger.error(f"Error extracting face thumbnail: {e}")
            return False
