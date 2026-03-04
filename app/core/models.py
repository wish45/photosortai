"""Data models for face detection and clustering."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import uuid
import numpy as np


@dataclass
class FaceRecord:
    """Represents a detected face in a photo."""

    photo_path: Path
    bbox: tuple[int, int, int, int]  # (x1, y1, x2, y2)
    embedding: np.ndarray  # 512-dim ArcFace, L2 normalized
    face_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    thumbnail_path: Optional[Path] = None
    cluster_id: int = -1

    def __post_init__(self):
        """Normalize paths and validate embedding."""
        if isinstance(self.photo_path, str):
            self.photo_path = Path(self.photo_path)
        if isinstance(self.thumbnail_path, str):
            self.thumbnail_path = Path(self.thumbnail_path)

        if not isinstance(self.embedding, np.ndarray):
            raise ValueError("embedding must be numpy array")
        if self.embedding.shape != (512,):
            raise ValueError(f"embedding must be 512-dim, got {self.embedding.shape}")


@dataclass
class Cluster:
    """Represents a group of faces belonging to the same person."""

    cluster_id: int
    face_records: list[FaceRecord] = field(default_factory=list)
    label: Optional[str] = None  # User-assigned name
    confirmed: bool = False

    @property
    def size(self) -> int:
        """Number of faces in this cluster."""
        return len(self.face_records)

    def add_face(self, face: FaceRecord) -> None:
        """Add a face to this cluster."""
        face.cluster_id = self.cluster_id
        self.face_records.append(face)

    def merge_with(self, other: "Cluster") -> None:
        """Merge another cluster into this one."""
        for face in other.face_records:
            face.cluster_id = self.cluster_id
            self.face_records.append(face)
        other.face_records.clear()


@dataclass
class ScanResult:
    """Stores the result of scanning a folder for faces."""

    input_folder: Path
    output_folder: Path
    face_records: list[FaceRecord] = field(default_factory=list)
    clusters: list[Cluster] = field(default_factory=list)
    total_photos: int = 0
    photos_with_faces: int = 0
    scanned_at: Optional[str] = None  # ISO timestamp

    def __post_init__(self):
        """Normalize paths."""
        if isinstance(self.input_folder, str):
            self.input_folder = Path(self.input_folder)
        if isinstance(self.output_folder, str):
            self.output_folder = Path(self.output_folder)

    @property
    def photos_without_faces(self) -> int:
        """Number of photos without detected faces."""
        return self.total_photos - self.photos_with_faces

    @property
    def num_clusters(self) -> int:
        """Number of clusters."""
        return len(self.clusters)

    def get_cluster_by_id(self, cluster_id: int) -> Optional[Cluster]:
        """Get cluster by ID."""
        for cluster in self.clusters:
            if cluster.cluster_id == cluster_id:
                return cluster
        return None


@dataclass
class KnownPerson:
    """A previously identified person stored in the registry."""

    person_id: int
    label: str
    representative_embedding: np.ndarray  # Average of all face embeddings
    face_count: int = 0


@dataclass
class PersonMatch:
    """A face matched to a known person."""

    face_record: FaceRecord
    person: KnownPerson
    similarity: float


@dataclass
class IncrementalScanResult(ScanResult):
    """Extended scan result for incremental mode."""

    total_files_in_folder: int = 0
    skipped_already_processed: int = 0
    new_photos_scanned: int = 0
    person_matches: list[PersonMatch] = field(default_factory=list)
    is_incremental: bool = False
    hash_map: dict = field(default_factory=dict)  # path -> hash for DB registration
