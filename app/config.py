"""Global configuration and constants."""

from pathlib import Path

# App metadata
APP_NAME = "PhotoSorterAI"
APP_VERSION = "1.0.0"

# Face detection
FACE_MODEL = "buffalo_l"  # InsightFace model
FACE_EMBEDDING_DIM = 512
MIN_FACE_CONFIDENCE = 0.5

# Clustering
UMAP_N_COMPONENTS = 64
UMAP_METRIC = "cosine"
HDBSCAN_MIN_CLUSTER_SIZE = 2
HDBSCAN_CLUSTER_SELECTION_METHOD = "eom"
CHINESE_WHISPERS_THRESHOLD = 0.45
PERSON_MATCH_THRESHOLD = 0.55  # Known person matching (stricter than CW)
FILE_HASH_CHUNK_SIZE = 8192  # Hash: first 8KB + file size

# File operations
DEFAULT_OUTPUT_MODE = "copy"  # "copy" or "move"
UNSORTED_FOLDER_NAME = "_unsorted"
DUPLICATE_SUFFIX_PATTERN = "_{}"  # e.g., "_2", "_3"

# Supported image formats
SUPPORTED_FORMATS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".heic", ".heif"}

# Thumbnail generation
THUMBNAIL_SIZE = (150, 150)
THUMBNAIL_QUALITY = 85

# Database
DB_FILENAME = "photosortai_session.db"

# Threading
SCAN_BATCH_SIZE = 100  # for large collections
FACE_DETECTION_BATCH_SIZE = 10

# UI defaults
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
CLUSTER_CARD_WIDTH = 250
FACE_THUMBNAIL_SIZE = 100

# Logging
LOG_LEVEL = "INFO"
