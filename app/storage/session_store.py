"""Session storage using sqlite3."""

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np

from app.config import DB_FILENAME
from app.core.models import FaceRecord, Cluster, ScanResult

logger = logging.getLogger(__name__)


class SessionStore:
    """Manages persistent storage of scan results."""

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize session store.

        Args:
            db_path: Path to database file. If None, uses default location.
        """
        if db_path is None:
            db_path = Path.home() / ".photosortai" / DB_FILENAME

        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database tables."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Scan results table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS scan_results (
                        id INTEGER PRIMARY KEY,
                        input_folder TEXT NOT NULL,
                        output_folder TEXT NOT NULL,
                        total_photos INTEGER,
                        photos_with_faces INTEGER,
                        scanned_at TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )

                # Face records table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS face_records (
                        id TEXT PRIMARY KEY,
                        scan_id INTEGER NOT NULL,
                        photo_path TEXT NOT NULL,
                        bbox TEXT NOT NULL,
                        embedding BLOB NOT NULL,
                        thumbnail_path TEXT,
                        cluster_id INTEGER DEFAULT -1,
                        FOREIGN KEY (scan_id) REFERENCES scan_results(id)
                    )
                    """
                )

                # Clusters table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS clusters (
                        id INTEGER PRIMARY KEY,
                        scan_id INTEGER NOT NULL,
                        cluster_id INTEGER NOT NULL,
                        label TEXT,
                        confirmed INTEGER DEFAULT 0,
                        FOREIGN KEY (scan_id) REFERENCES scan_results(id)
                    )
                    """
                )

                # Cluster members table
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS cluster_members (
                        cluster_table_id INTEGER NOT NULL,
                        face_id TEXT NOT NULL,
                        FOREIGN KEY (cluster_table_id) REFERENCES clusters(id),
                        FOREIGN KEY (face_id) REFERENCES face_records(id)
                    )
                    """
                )

                conn.commit()
                logger.info(f"Database initialized at {self.db_path}")

        except sqlite3.Error as e:
            logger.error(f"Database initialization failed: {e}")
            raise

    def save_scan_result(self, scan_result: ScanResult) -> int:
        """Save scan result to database.

        Args:
            scan_result: ScanResult object

        Returns:
            Scan ID
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Insert scan result
                cursor.execute(
                    """
                    INSERT INTO scan_results
                    (input_folder, output_folder, total_photos, photos_with_faces, scanned_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        str(scan_result.input_folder),
                        str(scan_result.output_folder),
                        scan_result.total_photos,
                        scan_result.photos_with_faces,
                        scan_result.scanned_at or datetime.now().isoformat(),
                    ),
                )

                scan_id = cursor.lastrowid

                # Insert face records
                for face in scan_result.face_records:
                    embedding_bytes = face.embedding.tobytes()
                    cursor.execute(
                        """
                        INSERT INTO face_records
                        (id, scan_id, photo_path, bbox, embedding, thumbnail_path, cluster_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            face.face_id,
                            scan_id,
                            str(face.photo_path),
                            json.dumps(list(face.bbox)),
                            embedding_bytes,
                            str(face.thumbnail_path) if face.thumbnail_path else None,
                            face.cluster_id,
                        ),
                    )

                # Insert clusters
                for cluster in scan_result.clusters:
                    cursor.execute(
                        """
                        INSERT INTO clusters
                        (scan_id, cluster_id, label, confirmed)
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            scan_id,
                            cluster.cluster_id,
                            cluster.label,
                            1 if cluster.confirmed else 0,
                        ),
                    )

                    cluster_table_id = cursor.lastrowid

                    # Insert cluster members
                    for face in cluster.face_records:
                        cursor.execute(
                            """
                            INSERT INTO cluster_members
                            (cluster_table_id, face_id)
                            VALUES (?, ?)
                            """,
                            (cluster_table_id, face.face_id),
                        )

                conn.commit()
                logger.info(f"Saved scan result {scan_id} to database")
                return scan_id

        except sqlite3.Error as e:
            logger.error(f"Failed to save scan result: {e}")
            raise

    def load_scan_result(self, scan_id: int) -> Optional[ScanResult]:
        """Load scan result from database.

        Args:
            scan_id: Scan ID

        Returns:
            ScanResult object or None if not found
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Load scan result
                cursor.execute(
                    "SELECT input_folder, output_folder, total_photos, photos_with_faces, scanned_at "
                    "FROM scan_results WHERE id = ?",
                    (scan_id,),
                )
                row = cursor.fetchone()

                if not row:
                    logger.warning(f"Scan result {scan_id} not found")
                    return None

                input_folder, output_folder, total_photos, photos_with_faces, scanned_at = row

                scan_result = ScanResult(
                    input_folder=Path(input_folder),
                    output_folder=Path(output_folder),
                    total_photos=total_photos,
                    photos_with_faces=photos_with_faces,
                    scanned_at=scanned_at,
                )

                # Load face records
                cursor.execute(
                    "SELECT id, photo_path, bbox, embedding, thumbnail_path, cluster_id "
                    "FROM face_records WHERE scan_id = ?",
                    (scan_id,),
                )

                faces_dict = {}
                for row in cursor.fetchall():
                    face_id, photo_path, bbox_json, embedding_bytes, thumbnail_path, cluster_id = row
                    embedding = np.frombuffer(embedding_bytes, dtype=np.float32)
                    bbox = tuple(json.loads(bbox_json))

                    face = FaceRecord(
                        face_id=face_id,
                        photo_path=Path(photo_path),
                        bbox=bbox,
                        embedding=embedding,
                        thumbnail_path=Path(thumbnail_path) if thumbnail_path else None,
                        cluster_id=cluster_id,
                    )
                    faces_dict[face_id] = face
                    scan_result.face_records.append(face)

                # Load clusters
                cursor.execute(
                    "SELECT id, cluster_id, label, confirmed FROM clusters WHERE scan_id = ?",
                    (scan_id,),
                )

                for row in cursor.fetchall():
                    cluster_table_id, cluster_id, label, confirmed = row

                    cluster = Cluster(
                        cluster_id=cluster_id,
                        label=label,
                        confirmed=bool(confirmed),
                    )

                    # Load cluster members
                    cursor.execute(
                        "SELECT face_id FROM cluster_members WHERE cluster_table_id = ?",
                        (cluster_table_id,),
                    )

                    for (face_id,) in cursor.fetchall():
                        if face_id in faces_dict:
                            cluster.add_face(faces_dict[face_id])

                    scan_result.clusters.append(cluster)

                logger.info(f"Loaded scan result {scan_id} from database")
                return scan_result

        except sqlite3.Error as e:
            logger.error(f"Failed to load scan result: {e}")
            return None

    def list_scan_results(self, limit: int = 10) -> list[dict]:
        """List recent scan results.

        Args:
            limit: Maximum number of results

        Returns:
            List of scan result metadata
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT id, input_folder, total_photos, photos_with_faces, scanned_at, created_at
                    FROM scan_results
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (limit,),
                )

                results = []
                for row in cursor.fetchall():
                    scan_id, input_folder, total_photos, photos_with_faces, scanned_at, created_at = row
                    results.append(
                        {
                            "id": scan_id,
                            "input_folder": input_folder,
                            "total_photos": total_photos,
                            "photos_with_faces": photos_with_faces,
                            "scanned_at": scanned_at,
                            "created_at": created_at,
                        }
                    )

                return results

        except sqlite3.Error as e:
            logger.error(f"Failed to list scan results: {e}")
            return []

    def delete_scan_result(self, scan_id: int) -> bool:
        """Delete scan result and related data.

        Args:
            scan_id: Scan ID

        Returns:
            True if successful
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Delete cluster members
                cursor.execute(
                    "DELETE FROM cluster_members WHERE cluster_table_id IN "
                    "(SELECT id FROM clusters WHERE scan_id = ?)",
                    (scan_id,),
                )

                # Delete clusters
                cursor.execute("DELETE FROM clusters WHERE scan_id = ?", (scan_id,))

                # Delete face records
                cursor.execute("DELETE FROM face_records WHERE scan_id = ?", (scan_id,))

                # Delete scan result
                cursor.execute("DELETE FROM scan_results WHERE id = ?", (scan_id,))

                conn.commit()
                logger.info(f"Deleted scan result {scan_id} from database")
                return True

        except sqlite3.Error as e:
            logger.error(f"Failed to delete scan result: {e}")
            return False
