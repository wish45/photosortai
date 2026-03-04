"""Clustering pipeline: UMAP + HDBSCAN + Chinese Whispers."""

import logging
from typing import Optional

import numpy as np
from hdbscan import HDBSCAN
from umap import UMAP
import networkx as nx

from app.config import (
    UMAP_N_COMPONENTS,
    UMAP_METRIC,
    HDBSCAN_MIN_CLUSTER_SIZE,
    HDBSCAN_CLUSTER_SELECTION_METHOD,
    CHINESE_WHISPERS_THRESHOLD,
)
from app.core.models import FaceRecord, Cluster

logger = logging.getLogger(__name__)


class FaceClusterer:
    """Clusters face embeddings using UMAP + HDBSCAN + Chinese Whispers."""

    def __init__(
        self,
        n_components: int = UMAP_N_COMPONENTS,
        metric: str = UMAP_METRIC,
        min_cluster_size: int = HDBSCAN_MIN_CLUSTER_SIZE,
        cw_threshold: float = CHINESE_WHISPERS_THRESHOLD,
    ):
        """Initialize clusterer.

        Args:
            n_components: UMAP dimensionality
            metric: Distance metric for UMAP
            min_cluster_size: Minimum cluster size for HDBSCAN
            cw_threshold: Chinese Whispers similarity threshold
        """
        self.n_components = n_components
        self.metric = metric
        self.min_cluster_size = min_cluster_size
        self.cw_threshold = cw_threshold
        self.umap_model = None
        self.hdbscan_model = None

    def cluster(self, faces: list[FaceRecord]) -> list[Cluster]:
        """Cluster faces by embedding similarity.

        Args:
            faces: List of FaceRecord objects with embeddings

        Returns:
            List of Cluster objects
        """
        if not faces:
            return []

        if len(faces) == 1:
            cluster = Cluster(cluster_id=0)
            cluster.add_face(faces[0])
            return [cluster]

        logger.info(f"Starting clustering of {len(faces)} faces")

        # Extract embeddings
        embeddings = np.array([f.embedding for f in faces])

        # Step 1: UMAP dimensionality reduction
        logger.debug("Running UMAP dimensionality reduction")
        umap_embeddings = self._umap_reduce(embeddings)

        # Step 2: HDBSCAN clustering
        logger.debug("Running HDBSCAN clustering")
        labels = self._hdbscan_cluster(umap_embeddings)

        # Step 3: Handle noise points with Chinese Whispers
        logger.debug("Processing noise points with Chinese Whispers")
        labels = self._handle_noise_points(labels, embeddings)

        # Step 4: Convert labels to Cluster objects
        clusters = self._labels_to_clusters(labels, faces)

        logger.info(f"Clustering complete: {len(clusters)} clusters")
        return clusters

    def _umap_reduce(self, embeddings: np.ndarray) -> np.ndarray:
        """Reduce embeddings dimensionality with UMAP.

        Args:
            embeddings: Array of shape (n_samples, 512)

        Returns:
            Array of shape (n_samples, n_components)
        """
        try:
            n_neighbors = max(2, min(15, len(embeddings) - 1))
            self.umap_model = UMAP(
                n_components=self.n_components,
                n_neighbors=n_neighbors,
                metric=self.metric,
                random_state=None,  # No random state to allow parallelization
                low_memory=len(embeddings) > 5000,
                init="random",  # Use random init instead of spectral
            )
            return self.umap_model.fit_transform(embeddings)
        except Exception as e:
            logger.error(f"UMAP reduction failed: {e}")
            raise

    def _hdbscan_cluster(self, embeddings: np.ndarray) -> np.ndarray:
        """Cluster embeddings with HDBSCAN.

        Args:
            embeddings: Array of reduced embeddings

        Returns:
            Array of cluster labels (-1 for noise)
        """
        try:
            self.hdbscan_model = HDBSCAN(
                min_cluster_size=self.min_cluster_size,
                min_samples=1,
                cluster_selection_method=HDBSCAN_CLUSTER_SELECTION_METHOD,
                cluster_selection_epsilon=0.3,
                prediction_data=True,
            )
            return self.hdbscan_model.fit_predict(embeddings)
        except Exception as e:
            logger.error(f"HDBSCAN clustering failed: {e}")
            raise

    def _handle_noise_points(
        self, labels: np.ndarray, embeddings: np.ndarray
    ) -> np.ndarray:
        """Reassign noise points using Chinese Whispers algorithm.

        Args:
            labels: HDBSCAN labels
            embeddings: Original face embeddings (512-dim)

        Returns:
            Updated labels array
        """
        noise_mask = labels == -1
        if not np.any(noise_mask):
            return labels

        noise_indices = np.where(noise_mask)[0]
        logger.debug(f"Processing {len(noise_indices)} noise points")

        if len(noise_indices) == 0:
            return labels

        # Build similarity graph between noise points and clusters
        max_label = int(np.max(labels[~noise_mask])) if np.any(~noise_mask) else -1

        if max_label == -1:
            # All points are noise, create clusters from noise
            noise_embeddings = embeddings[noise_mask]
            noise_clusters = self._chinese_whispers(
                noise_embeddings, noise_indices
            )
            for idx, label in noise_clusters.items():
                labels[idx] = label + max_label + 1
        else:
            # Assign noise to nearest cluster (only if similarity exceeds threshold)
            noise_assign_threshold = self.cw_threshold  # 0.45
            remaining_noise = []

            for noise_idx in noise_indices:
                noise_emb = embeddings[noise_idx]
                cluster_labels = np.unique(labels[~noise_mask])

                best_cluster = None
                best_sim = -1

                for cluster_label in cluster_labels:
                    cluster_mask = labels == cluster_label
                    cluster_embs = embeddings[cluster_mask]
                    mean_emb = np.mean(cluster_embs, axis=0)
                    mean_emb = mean_emb / np.linalg.norm(mean_emb)

                    sim = np.dot(noise_emb, mean_emb)
                    if sim > best_sim:
                        best_sim = sim
                        best_cluster = cluster_label

                if best_cluster is not None and best_sim >= noise_assign_threshold:
                    labels[noise_idx] = best_cluster
                else:
                    remaining_noise.append(noise_idx)

            # Remaining noise points form their own clusters via Chinese Whispers
            if remaining_noise:
                new_max = int(np.max(labels[labels >= 0])) + 1 if np.any(labels >= 0) else 0
                remaining_embs = embeddings[remaining_noise]
                remaining_indices = np.array(remaining_noise)
                noise_clusters = self._chinese_whispers(remaining_embs, remaining_indices)
                for idx, label in noise_clusters.items():
                    labels[idx] = label + new_max

        return labels

    def _chinese_whispers(
        self, embeddings: np.ndarray, indices: np.ndarray
    ) -> dict[int, int]:
        """Apply Chinese Whispers to cluster noise points.

        Args:
            embeddings: Array of embeddings
            indices: Original indices in full array

        Returns:
            Dictionary mapping index -> cluster_id
        """
        if len(embeddings) <= 1:
            return {indices[0]: 0} if len(indices) == 1 else {}

        # Build similarity graph
        G = nx.Graph()
        for i, idx in enumerate(indices):
            G.add_node(i)

        # Add edges based on cosine similarity
        for i in range(len(embeddings)):
            for j in range(i + 1, len(embeddings)):
                sim = np.dot(embeddings[i], embeddings[j])
                if sim > self.cw_threshold:
                    G.add_edge(i, j, weight=sim)

        # Apply Chinese Whispers
        clusters = self._chinese_whispers_algorithm(G)

        # Map back to original indices
        result = {}
        for node_idx, cluster_id in clusters.items():
            result[indices[node_idx]] = cluster_id

        return result

    def _chinese_whispers_algorithm(self, G: nx.Graph) -> dict[int, int]:
        """Chinese Whispers clustering algorithm.

        Args:
            G: NetworkX graph with edge weights

        Returns:
            Dictionary mapping node -> cluster_id
        """
        if len(G) == 0:
            return {}

        # Initialize labels
        labels = {node: node for node in G.nodes()}
        converged = False
        max_iterations = 100
        iteration = 0

        while not converged and iteration < max_iterations:
            converged = True
            iteration += 1

            for node in G.nodes():
                # Get neighboring labels with weights
                neighbors = {}
                for neighbor in G.neighbors(node):
                    weight = G[node][neighbor].get("weight", 1.0)
                    label = labels[neighbor]
                    neighbors[label] = neighbors.get(label, 0) + weight

                # Assign most common label
                if neighbors:
                    new_label = max(neighbors.items(), key=lambda x: x[1])[0]
                    if new_label != labels[node]:
                        labels[node] = new_label
                        converged = False

        # Relabel clusters to be sequential
        unique_labels = sorted(set(labels.values()))
        label_map = {old: new for new, old in enumerate(unique_labels)}
        return {node: label_map[label] for node, label in labels.items()}

    def _labels_to_clusters(
        self, labels: np.ndarray, faces: list[FaceRecord]
    ) -> list[Cluster]:
        """Convert label array to Cluster objects.

        Args:
            labels: Cluster labels for each face
            faces: List of FaceRecord objects

        Returns:
            List of Cluster objects
        """
        clusters_dict = {}

        for face, label in zip(faces, labels):
            cluster_id = int(label)
            if cluster_id not in clusters_dict:
                clusters_dict[cluster_id] = Cluster(cluster_id=cluster_id)
            clusters_dict[cluster_id].add_face(face)

        return sorted(clusters_dict.values(), key=lambda c: c.cluster_id)
