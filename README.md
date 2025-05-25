# Photo Organizer

A Python package that organizes photos from different sources (iPhone and Android) by date and location using their metadata.

## Features
- Organizes photos by date (Year/Month)
- Creates location-based subfolders when GPS data is available
- Supports both iPhone and Android photo formats
- Preserves original files and metadata
- Handles duplicate filenames
- Parallel processing for faster organization
- Location caching to reduce API calls
- Detailed debug mode for troubleshooting

## Requirements
- Python 3.13+
- pipenv (for dependency management)

## Installation
1. Install pipenv if you haven't already:
```bash
brew install pipenv  # On macOS using Homebrew
# OR
pip install pipenv   # Using pip
```

2. Install dependencies using pipenv:
```bash
pipenv install
```

## Usage
Run the package using pipenv:
```bash
pipenv run python -m photo_organizer --input-folder /path/to/photos --output-folder /path/to/organized/photos
```

### Available Options
- `--input-folder`: Directory containing the photos to organize (required)
- `--output-folder`: Directory where organized photos will be stored (required)
- `--debug`: Enable debug mode for detailed logging
- `--workers`: Number of worker threads (default: CPU count * 2)
- `--no-cache`: Disable location caching (not recommended for large collections)

### Examples
Basic usage:
```bash
pipenv run python -m photo_organizer --input-folder ~/Downloads/photos --output-folder ~/Pictures/organized
```

With debug mode and custom worker count:
```bash
pipenv run python -m photo_organizer --input-folder ~/Photos --output-folder ~/Organized --debug --workers 4
```

## Output Structure
```
organized_photos/
├── 2024/
│   ├── 01-January/
│   │   ├── San Francisco/
│   │   │   └── IMG_20240101_123456.jpg
│   │   └── New York/
│   │       └── IMG_20240115_183000.jpg
│   └── 02-February/
│       └── Unknown Location/
│           └── IMG_20240201_140000.jpg
└── 2023/
    └── 12-December/
        └── London/
            └── IMG_20231225_160000.jpg
```

## Performance
- Uses parallel processing to handle large photo collections efficiently
- Caches location data to minimize API calls
- Typically processes hundreds of photos per minute
- Memory efficient, suitable for large collections 