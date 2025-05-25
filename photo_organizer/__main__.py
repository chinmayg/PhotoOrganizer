"""Command-line interface for photo organizer."""

import argparse
import logging
import sys
from typing import List
from .organizer import PhotoOrganizer
from .file_handler import FileHandler

def parse_file_types(file_types_str: str) -> List[str]:
    """Parse comma-separated file types string into a list."""
    if not file_types_str:
        return []
    return [ext.strip() for ext in file_types_str.split(',')]

def main():
    """Main entry point for the photo organizer."""
    parser = argparse.ArgumentParser(description='Organize photos by date and location.')
    parser.add_argument('--input-folder', required=True,
                      help='Input folder containing photos')
    parser.add_argument('--output-folder', required=True,
                      help='Output folder for organized photos')
    parser.add_argument('--debug', action='store_true',
                      help='Enable debug mode for detailed information')
    parser.add_argument('--workers', type=int,
                      help='Number of worker threads (default: CPU count * 2)')
    parser.add_argument('--no-cache', action='store_true',
                      help='Disable geocoding cache')
    parser.add_argument('--file-types',
                      help='Comma-separated list of file extensions to process (e.g., "jpg,png,heic"). '
                           f'Default: {",".join(ext[1:] for ext in FileHandler.DEFAULT_EXTENSIONS)}')
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Parse file types
    file_types = parse_file_types(args.file_types) if args.file_types else None
    
    try:
        organizer = PhotoOrganizer(
            args.input_folder,
            args.output_folder,
            debug=args.debug,
            max_workers=args.workers,
            use_cache=not args.no_cache,
            file_types=file_types
        )
        organizer.organize_photos()
    except KeyboardInterrupt:
        logging.info("\nProcess interrupted by user")
        sys.exit(1)
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        if args.debug:
            logging.exception("Detailed error information:")
        sys.exit(1)

if __name__ == "__main__":
    main() 