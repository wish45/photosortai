"""Tests for face clustering."""

from pathlib import Path

import numpy as np
import pytest

from app.core.models import FaceRecord
from app.core.clusterer import FaceClusterer


@pytest.fixture
def sample_embeddings():
    """Create sample face embeddings for testing."""
    np.random.seed(42)

    # Create 10 embeddings: 3 similar to [1,0,...], 4 similar to [0,1,...], 3 similar to [-1,0,...]
    embeddings = []
    faces = []

    # Cluster 1: embeddings similar to [1, 0, ...]
    base1 = np.array([1.0] + [0.0] * 511)
    base1 = base1 / np.linalg.norm(base1)
    for i in range(3):
        emb = base1 + np.random.normal(0, 0.05, 512)
        emb = emb / np.linalg.norm(emb)
        embeddings.append(emb)
        faces.append(
            FaceRecord(
                photo_path=Path(f"/test/photo_{i}.jpg"),
                bbox=(0, 0, 100, 100),
                embedding=emb,
            )
        )

    # Cluster 2: embeddings similar to [0, 1, ...]
    base2 = np.array([0.0, 1.0] + [0.0] * 510)
    base2 = base2 / np.linalg.norm(base2)
    for i in range(4):
        emb = base2 + np.random.normal(0, 0.05, 512)
        emb = emb / np.linalg.norm(emb)
        embeddings.append(emb)
        faces.append(
            FaceRecord(
                photo_path=Path(f"/test/photo_{3+i}.jpg"),
                bbox=(0, 0, 100, 100),
                embedding=emb,
            )
        )

    # Cluster 3: embeddings similar to [-1, 0, ...]
    base3 = np.array([-1.0] + [0.0] * 511)
    base3 = base3 / np.linalg.norm(base3)
    for i in range(3):
        emb = base3 + np.random.normal(0, 0.05, 512)
        emb = emb / np.linalg.norm(emb)
        embeddings.append(emb)
        faces.append(
            FaceRecord(
                photo_path=Path(f"/test/photo_{7+i}.jpg"),
                bbox=(0, 0, 100, 100),
                embedding=emb,
            )
        )

    return faces


def test_clustering_basic(sample_embeddings):
    """Test basic clustering."""
    clusterer = FaceClusterer()
    clusters = clusterer.cluster(sample_embeddings)

    assert len(clusters) > 0
    assert len(clusters) <= len(sample_embeddings)

    # Check that all faces are assigned
    total_faces = sum(len(c.face_records) for c in clusters)
    assert total_faces == len(sample_embeddings)


def test_clustering_single_face():
    """Test clustering with single face."""
    face = FaceRecord(
        photo_path=Path("/test/photo.jpg"),
        bbox=(0, 0, 100, 100),
        embedding=np.random.randn(512).astype(np.float32),
    )
    face.embedding = face.embedding / np.linalg.norm(face.embedding)

    clusterer = FaceClusterer()
    clusters = clusterer.cluster([face])

    assert len(clusters) == 1
    assert len(clusters[0].face_records) == 1


def test_clustering_empty():
    """Test clustering with empty list."""
    clusterer = FaceClusterer()
    clusters = clusterer.cluster([])

    assert len(clusters) == 0


def test_cluster_properties(sample_embeddings):
    """Test cluster properties."""
    clusterer = FaceClusterer()
    clusters = clusterer.cluster(sample_embeddings)

    for cluster in clusters:
        # All faces should be assigned to this cluster
        assert all(f.cluster_id == cluster.cluster_id for f in cluster.face_records)

        # Size property should match
        assert cluster.size == len(cluster.face_records)


def test_cluster_merge(sample_embeddings):
    """Test cluster merging."""
    clusterer = FaceClusterer()
    clusters = clusterer.cluster(sample_embeddings)

    if len(clusters) >= 2:
        cluster1 = clusters[0]
        cluster2 = clusters[1]
        original_size = cluster1.size + cluster2.size

        cluster1.merge_with(cluster2)

        assert cluster1.size == original_size
        assert len(cluster2.face_records) == 0
