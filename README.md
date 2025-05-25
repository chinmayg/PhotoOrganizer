# Photo Organizer

A Python package that organizes photos and videos from different sources (iPhone and Android) by date and location using their metadata.

## Features
- Organizes photos and videos by date (Year/Month/Day)
- Creates location-based subfolders when GPS data is available
- Uses Google Maps Geocoding API for accurate location data
- Supports both iPhone and Android media formats
- Supports common image formats (JPG, PNG, HEIC) and video formats (MOV)
- Customizable file type filtering
- Preserves original files and metadata
- Handles duplicate filenames
- Parallel processing for faster organization
- Location caching to reduce API calls
- Detailed debug mode for troubleshooting

## Requirements
- Python 3.13+
- pipenv (for dependency management)
- Google Maps API key (for location services)

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

3. Set up Google Maps API key:
   - Go to the [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one
   - Enable the Geocoding API for your project
   - Create credentials (API key) for the Geocoding API
   - Set the API key as an environment variable:
```bash
export GOOGLE_MAPS_API_KEY='your-api-key-here'
```
   Note: You can add this to your shell's startup file (.bashrc, .zshrc, etc.) to make it permanent.

## Usage
Run the package using pipenv:
```bash
pipenv run python -m photo_organizer --input-folder /path/to/photos --output-folder /path/to/organized/photos
```

### Available Options
- `--input-folder`: Directory containing the media files to organize (required)
- `--output-folder`: Directory where organized files will be stored (required)
- `--debug`: Enable debug mode for detailed logging
- `--workers`: Number of worker threads (default: CPU count * 2)
- `--no-cache`: Disable location caching (not recommended for large collections)
- `--file-types`: Comma-separated list of file extensions to process (e.g., "jpg,mov,heic")
  Default: jpg,jpeg,png,heic,heif,gif,mov

### Examples
Basic usage:
```bash
pipenv run python -m photo_organizer --input-folder ~/Downloads/photos --output-folder ~/Pictures/organized
```

With debug mode and custom worker count:
```bash
pipenv run python -m photo_organizer --input-folder ~/Photos --output-folder ~/Organized --debug --workers 4
```

Process only JPG and MOV files:
```bash
pipenv run python -m photo_organizer --input-folder ~/Photos --output-folder ~/Organized --file-types jpg,mov
```

## Output Structure
```
organized_photos/
├── 2024/
│   ├── 01-January/
│   │   ├── 01/
│   │   │   ├── San Francisco/
│   │   │   │   ├── IMG_20240101_123456.jpg
│   │   │   │   └── VID_20240101_123457.mov
│   │   ├── 15/
│   │   │   └── New York/
│   │   │       └── IMG_20240115_183000.jpg
│   └── 02-February/
│       └── 01/
│           └── Unknown Location/
│               └── IMG_20240201_140000.jpg
└── 2023/
    └── 12-December/
        └── 25/
            └── London/
                └── IMG_20231225_160000.jpg
```

## Performance
- Uses parallel processing to handle large media collections efficiently
- Caches location data to minimize API calls and reduce costs
- Typically processes hundreds of files per minute
- Memory efficient, suitable for large collections

## Notes
- If the Google Maps API key is not set, location services will default to "Unknown Location"
- The Google Maps Geocoding API has usage limits and may incur costs depending on your usage
- Location caching helps reduce API calls and associated costs
- File type filtering is case-insensitive and handles extensions with or without dots
- Video files (MOV) are organized using the same date/location structure as photos 