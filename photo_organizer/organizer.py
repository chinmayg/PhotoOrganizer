"""Main module for photo organization."""

import logging
import time
from pathlib import Path
from typing import Tuple, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import os
import sqlite3
from contextlib import closing

from .exif_handler import ExifHandler
from .gps_handler import GPSHandler
from .file_handler import FileHandler
from .video_handler import VideoHandler

logger = logging.getLogger(__name__)

class PhotoOrganizer:
    """Main class for organizing photos and videos."""
    
    def __init__(self, input_folder: str, output_folder: str, debug: bool = False,
                 max_workers: int = None, use_cache: bool = True, file_types: Optional[List[str]] = None):
        """Initialize the photo organizer."""
        self.input_folder = Path(input_folder)
        self.output_folder = Path(output_folder)
        self.debug = debug
        self.max_workers = max_workers or min(32, os.cpu_count() * 2)
        
        # Initialize handlers
        self.exif_handler = ExifHandler(debug=debug)
        self.video_handler = VideoHandler(debug=debug)
        self.gps_handler = GPSHandler(debug=debug, use_cache=use_cache)
        self.file_handler = FileHandler(output_folder, debug=debug, file_types=file_types)

    def is_video_file(self, file_path: Path) -> bool:
        """Check if the file is a video file."""
        return file_path.suffix.lower() in VideoHandler.SUPPORTED_FORMATS

    def process_photo(self, file_path: Path) -> Tuple[bool, str]:
        """Process a single media file."""
        try:
            if not file_path.is_file() or not self.file_handler.is_image_file(file_path):
                return False, f"Skipped {file_path.name}: Not a supported media file"

            # Handle videos and photos differently
            if self.is_video_file(file_path):
                # Get video metadata
                metadata = self.video_handler.get_metadata(file_path)
                date_taken = self.video_handler.get_date_taken(file_path, metadata)
                gps_data = self.video_handler.get_gps_data(file_path, metadata)
                location = self.gps_handler.get_location(gps_data)
            else:
                # Get EXIF data for photos
                exif_data = self.exif_handler.get_exif_data(file_path)
                date_taken = self.exif_handler.get_date_taken(file_path, exif_data)
                location = self.gps_handler.get_location(exif_data)
            
            # Create destination path and copy file
            dest_path = self.file_handler.create_destination_path(date_taken, location, file_path)
            if self.file_handler.copy_file(file_path, dest_path):
                return True, f"Successfully organized {file_path.name} to {dest_path}"
            else:
                return False, f"Failed to copy {file_path.name}"
            
        except Exception as e:
            if self.debug:
                logger.exception(f"Error processing {file_path.name}")
            return False, f"Error processing {file_path.name}: {str(e)}"

    def organize_photos(self) -> None:
        """Main method to organize media files."""
        start_time = time.time()
        logger.info(f"Starting media organization from {self.input_folder} to {self.output_folder}")
        
        # Create output directory if it doesn't exist
        self.output_folder.mkdir(parents=True, exist_ok=True)
        
        # Get list of all files first
        files = list(self.input_folder.rglob('*'))
        total_files = len(files)
        
        # Initialize counters
        processed = 0
        skipped = 0
        errors = 0
        
        # Process files in parallel with progress bar
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self.process_photo, file_path): file_path 
                      for file_path in files}
            
            with tqdm(total=total_files, desc="Processing media", unit="file") as pbar:
                for future in as_completed(futures):
                    success, message = future.result()
                    if success:
                        processed += 1
                    else:
                        if "Skipped" in message:
                            skipped += 1
                        else:
                            errors += 1
                    logger.debug(message)
                    pbar.update(1)
        
        # Calculate statistics
        end_time = time.time()
        duration = end_time - start_time
        files_per_second = processed / duration if duration > 0 else 0
        
        # Print summary
        logger.info("\nMedia Organization Summary:")
        logger.info(f"Total files found: {total_files}")
        logger.info(f"Successfully processed: {processed}")
        logger.info(f"Skipped: {skipped}")
        logger.info(f"Errors: {errors}")
        logger.info(f"Total time: {duration:.2f} seconds")
        logger.info(f"Processing speed: {files_per_second:.2f} files/second")
        
        if hasattr(self.gps_handler, 'cache_db'):
            with closing(sqlite3.connect(str(self.gps_handler.cache_db))) as conn:
                with closing(conn.cursor()) as cursor:
                    cursor.execute("SELECT COUNT(*) FROM geocoding_cache")
                    cache_size = cursor.fetchone()[0]
                    logger.info(f"Geocoding cache size: {cache_size} locations") 