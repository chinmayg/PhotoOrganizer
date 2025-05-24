# Photo Organizer

A Python script that organizes photos from different sources (iPhone and Android) by date and location using their metadata.

## Features
- Organizes photos by date (Year/Month)
- Creates location-based subfolders when GPS data is available
- Supports both iPhone and Android photo formats
- Preserves original files
- Handles duplicate filenames

## Requirements
- Python 3.13+
- pipenv (for dependency management)

## Installation
1. Install pipenv if you haven't already:
```bash
pip install pipenv
```

2. Install dependencies using pipenv:
```bash
pipenv install
```

## Usage
Run the script using pipenv:
```bash
pipenv run python photo_organizer.py --input-folder /path/to/photos --output-folder /path/to/organized/photos
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