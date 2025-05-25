"""Command-line interface for photo organizer."""

import argparse
import logging
import sys
from .organizer import PhotoOrganizer

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
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    try:
        organizer = PhotoOrganizer(
            args.input_folder,
            args.output_folder,
            debug=args.debug,
            max_workers=args.workers,
            use_cache=not args.no_cache
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