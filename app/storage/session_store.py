"""Session storage using sqlite3."""

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np

from app.config import DB_FILENAME
from app.core.models import FaceRecord, Cluster, ScanResult, KnownPerson

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
                    embedding = np.frombuffer(embedding_bytes, dtype=np.float32).copy()
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


class FaceRegistry:
    """Persistent registry for incremental face scanning."""

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            db_path = Path.home() / ".photosortai" / DB_FILENAME
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_registry_tables()

    def _init_registry_tables(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS processed_files (
                    file_hash TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    file_size INTEGER,
                    input_folder TEXT NOT NULL,
                    processed_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(file_hash, input_folder)
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS known_persons (
                    id INTEGER PRIMARY KEY,
                    label TEXT UNIQUE NOT NULL,
                    representative_embedding BLOB NOT NULL,
                    face_count INTEGER DEFAULT 0
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS known_faces (
                    id TEXT PRIMARY KEY,
                    person_id INTEGER NOT NULL,
                    file_hash TEXT NOT NULL,
                    embedding BLOB NOT NULL,
                    bbox TEXT,
                    photo_path TEXT,
                    FOREIGN KEY (person_id) REFERENCES known_persons(id)
                )
            """)
            conn.commit()

    # ── Query methods ──

    def get_processed_hashes(self, input_folder: str) -> set[str]:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT file_hash FROM processed_files WHERE input_folder = ?",
                (input_folder,),
            )
            return {row[0] for row in cur.fetchall()}

    def get_known_persons(self) -> list[KnownPerson]:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, label, representative_embedding, face_count FROM known_persons")
            result = []
            for row in cur.fetchall():
                pid, label, emb_bytes, fc = row
                emb = np.frombuffer(emb_bytes, dtype=np.float32).copy()
                result.append(KnownPerson(person_id=pid, label=label,
                                          representative_embedding=emb, face_count=fc))
            return result

    def get_person_by_label(self, label: str) -> Optional[KnownPerson]:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, label, representative_embedding, face_count FROM known_persons WHERE label = ?",
                (label,),
            )
            row = cur.fetchone()
            if not row:
                return None
            pid, lbl, emb_bytes, fc = row
            emb = np.frombuffer(emb_bytes, dtype=np.float32).copy()
            return KnownPerson(person_id=pid, label=lbl,
                               representative_embedding=emb, face_count=fc)

    def has_registry_data(self, input_folder: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(*) FROM processed_files WHERE input_folder = ?",
                (input_folder,),
            )
            return cur.fetchone()[0] > 0

    def get_registry_stats(self, input_folder: str) -> dict:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT COUNT(*) FROM processed_files WHERE input_folder = ?",
                (input_folder,),
            )
            files = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM known_persons")
            persons = cur.fetchone()[0]
            return {"processed_files": files, "known_persons": persons}

    # ── Registration methods ──

    def register_processed_file(
        self, file_hash: str, file_path: str, file_size: int, input_folder: str
    ) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO processed_files (file_hash, file_path, file_size, input_folder) "
                "VALUES (?, ?, ?, ?)",
                (file_hash, file_path, file_size, input_folder),
            )
            conn.commit()

    def register_known_person(self, label: str, embeddings: list[np.ndarray]) -> int:
        mean_emb = np.mean(embeddings, axis=0).astype(np.float32)
        norm = np.linalg.norm(mean_emb)
        if norm > 0:
            mean_emb /= norm
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO known_persons (label, representative_embedding, face_count) VALUES (?, ?, ?)",
                (label, mean_emb.tobytes(), len(embeddings)),
            )
            conn.commit()
            return cur.lastrowid

    def update_known_person_embedding(self, person_id: int, new_embeddings: list[np.ndarray]) -> None:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT representative_embedding, face_count FROM known_persons WHERE id = ?",
                (person_id,),
            )
            row = cur.fetchone()
            if not row:
                return
            old_emb = np.frombuffer(row[0], dtype=np.float32).copy()
            old_count = row[1]

            # Weighted average of old and new embeddings
            new_mean = np.mean(new_embeddings, axis=0).astype(np.float32)
            total = old_count + len(new_embeddings)
            combined = (old_emb * old_count + new_mean * len(new_embeddings)) / total
            norm = np.linalg.norm(combined)
            if norm > 0:
                combined /= norm

            cur.execute(
                "UPDATE known_persons SET representative_embedding = ?, face_count = ? WHERE id = ?",
                (combined.astype(np.float32).tobytes(), total, person_id),
            )
            conn.commit()

    def register_known_face(self, face: "FaceRecord", person_id: int, file_hash: str) -> None:
        import json
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO known_faces (id, person_id, file_hash, embedding, bbox, photo_path) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    face.face_id,
                    person_id,
                    file_hash,
                    face.embedding.tobytes(),
                    json.dumps(list(face.bbox)),
                    str(face.photo_path),
                ),
            )
            conn.commit()
