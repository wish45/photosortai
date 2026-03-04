# PhotoSorterAI

Automatically organize photos by detected faces using AI clustering.

## Features

- **Automatic Face Detection**: Uses InsightFace (ArcFace) for robust face detection
- **Intelligent Clustering**: UMAP + HDBSCAN + Chinese Whispers for accurate grouping
- **Interactive Review**: Review detected clusters and assign names to people
- **Batch Organization**: Copy or move photos into person-specific folders
- **Session Persistence**: Save and load scan results using SQLite
- **Cross-Platform**: Built with PyQt6 for macOS, Windows, and Linux

## System Requirements

- **Python**: 3.11+
- **OS**: macOS 10.14+, Windows 10+, or Linux (Ubuntu 18.04+)
- **RAM**: 2GB minimum (4GB+ recommended for large libraries)
- **Disk Space**: ~2GB for models and dependencies

## Installation

### From Source

1. Clone the repository:
```bash
git clone https://github.com/yourusername/photosortai.git
cd photosortai
```

2. Create virtual environment:
```bash
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

### From Binary (Coming Soon)

- **macOS**: Download `.dmg` installer
- **Windows**: Download `.msi` installer
- **Linux**: Download AppImage

## Quick Start

### GUI Application

```bash
python main.py
```

Then follow the 4-step wizard:

1. **Select Folders**: Choose input (photos) and output folder
2. **Processing**: Watch real-time face detection and clustering
3. **Review**: Assign names to detected person clusters
4. **Done**: Confirm organization and open output folder

### CLI Demo (Testing Only)

For testing the ML pipeline without UI:

```bash
python cli_demo.py /path/to/photos -o /path/to/output -s
```

Options:
- `-o, --output`: Output folder (default: same as input)
- `-s, --save`: Save scan result to database

## Architecture

### Project Structure

```
photosortai/
├── main.py                      # Entry point
├── cli_demo.py                  # CLI for testing
├── photosortai.spec             # PyInstaller config
├── requirements.txt             # Python dependencies
│
├── app/
│   ├── config.py                # Global configuration
│   ├── core/                    # ML pipeline
│   │   ├── models.py            # Data classes
│   │   ├── scanner.py           # Image discovery
│   │   ├── face_detector.py     # Face detection
│   │   ├── clusterer.py         # Clustering
│   │   └── organizer.py         # File operations
│   ├── workers/                 # Background threads
│   │   ├── scan_worker.py
│   │   └── organize_worker.py
│   ├── ui/                      # User interface
│   │   ├── main_window.py       # Main window
│   │   ├── pages/               # 4-page wizard
│   │   ├── widgets/             # Custom widgets
│   │   └── styles/              # Qt stylesheets
│   └── storage/
│       └── session_store.py     # SQLite persistence
│
└── tests/                       # Unit tests
    ├── test_scanner.py
    ├── test_clusterer.py
    ├── test_organizer.py
    └── fixtures/
```

### ML Pipeline

```
Photos
  ↓
[ImageScanner] → Find all images
  ↓
[FaceDetector] → InsightFace (buffalo_l)
  ↓  512-dim ArcFace embeddings
[UMAP] → Reduce to 64 dimensions (cosine metric)
  ↓
[HDBSCAN] → Density-based clustering
  ↓
[Chinese Whispers] → Reassign noise points
  ↓
Clusters with person labels
  ↓
[PhotoOrganizer] → Copy/Move to person folders
```

## Configuration

Edit `app/config.py` to customize:

```python
# Face detection
FACE_MODEL = "buffalo_l"
MIN_FACE_CONFIDENCE = 0.5

# Clustering
UMAP_N_COMPONENTS = 64
HDBSCAN_MIN_CLUSTER_SIZE = 2
CHINESE_WHISPERS_THRESHOLD = 0.45

# File operations
DEFAULT_OUTPUT_MODE = "copy"  # or "move"
UNSORTED_FOLDER_NAME = "_unsorted"

# Performance
SCAN_BATCH_SIZE = 100
```

## Development

### Running Tests

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest tests/ -v

# Run specific test
pytest tests/test_scanner.py -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

### Code Style

```bash
# Format code
black app/ tests/ main.py

# Lint
flake8 app/ tests/

# Type checking
mypy app/
```

## Performance

Approximate timing on Apple M-series Mac:

- Face detection: 50-150ms per photo
- 500 photos scan: 2-4 minutes
- 3000 faces clustering: 10 seconds
- Memory usage: ~800MB peak (UMAP)

## Edge Cases Handled

| Situation | Handling |
|-----------|----------|
| No faces detected | Photos moved to `_unsorted/` folder |
| Invalid/corrupted files | Logged and skipped |
| Multiple people in one photo | Photo copied to each person's folder |
| Similar-looking faces | User can manually separate in review |
| Large collections (5000+) | Batch processing with reduced memory usage |
| Filename conflicts | Auto-suffix with `_2`, `_3`, etc. |

## Troubleshooting

### "ModuleNotFoundError: No module named 'insightface'"

Install ONNX runtime:
```bash
# macOS with Apple Silicon
pip install onnxruntime-silicon

# Other platforms
pip install onnxruntime
```

### "No module named 'cv2'"

Install OpenCV:
```bash
pip install opencv-python-headless
```

### "ONNX model not found"

Models are automatically downloaded on first use to `~/.insightface/models/`. Ensure you have:
- Internet connection
- ~500MB free disk space
- Write permissions to home directory

### UI doesn't appear

Check logs:
```bash
tail -f ~/.photosortai/app.log
```

## Roadmap

- [ ] GPU acceleration (CUDA/Metal)
- [ ] Advanced deduplication
- [ ] Manual face correction UI
- [ ] Batch operations (organize multiple folders)
- [ ] Export results (PDF report, JSON metadata)
- [ ] Integration with cloud storage (Google Photos, OneDrive)
- [ ] Mobile companion app

## License

MIT License - See LICENSE file

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## Citation

If you use PhotoSorterAI in research, please cite:

```bibtex
@software{photosortai2024,
  title={PhotoSorterAI: Automatic Photo Organization by Face Recognition},
  author={Your Name},
  year={2024},
  url={https://github.com/yourusername/photosortai}
}
```

## Support

- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions
- **Email**: support@photosortai.com

## Credits

- **InsightFace**: https://github.com/deepinsight/insightface
- **UMAP**: https://github.com/lmcinnes/umap
- **HDBSCAN**: https://github.com/scikit-learn-contrib/hdbscan
- **PyQt6**: https://www.riverbankcomputing.com/software/pyqt/

## Acknowledgments

Thanks to all contributors and users who have provided feedback and improvements.
