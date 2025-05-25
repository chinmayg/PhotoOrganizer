"""Module for handling EXIF data extraction and processing."""

import logging
from pathlib import Path
from typing import Dict, Any, Optional
import exifread
from PIL import Image
from PIL.ExifTags import TAGS
from datetime import datetime
from dateutil import parser
import os

logger = logging.getLogger(__name__)

class ExifHandler:
    """Handles EXIF data extraction and processing from images."""
    
    def __init__(self, debug: bool = False):
        self.debug = debug

    def debug_exif(self, image_path: Path, exif_data: Dict[str, Any]) -> None:
        """Print detailed EXIF information when in debug mode."""
        if not self.debug:
            return

        logger.debug(f"\n{'='*50}")
        logger.debug(f"Detailed EXIF data for: {image_path.name}")
        logger.debug(f"{'='*50}")

        if not exif_data:
            logger.debug("No EXIF data found!")
            return

        # Common EXIF tags to look for
        important_tags = [
            'Image Make', 'Image Model', 'EXIF DateTimeOriginal', 'Image DateTime',
            'EXIF ExifImageWidth', 'EXIF ExifImageLength', 'EXIF ISOSpeedRatings',
            'EXIF FocalLength', 'EXIF ExposureTime', 'EXIF Flash',
            'GPS GPSLatitude', 'GPS GPSLongitude', 'GPS GPSAltitude'
        ]

        # Print important tags first
        logger.debug("\nImportant EXIF Tags:")
        logger.debug("-" * 20)
        for tag in important_tags:
            if tag in exif_data:
                logger.debug(f"{tag}: {exif_data[tag]}")

        # Print all other tags
        logger.debug("\nAll EXIF Tags:")
        logger.debug("-" * 20)
        for tag, value in exif_data.items():
            if tag not in important_tags:
                logger.debug(f"{tag}: {value}")

    def get_exif_data(self, image_path: Path) -> Dict[str, Any]:
        """Extract EXIF data from an image file."""
        try:
            with open(image_path, 'rb') as f:
                exif_data = exifread.process_file(f, details=False)
                
            if self.debug:
                self.debug_exif(image_path, exif_data)
                
                # Try to also get PIL EXIF data for comparison
                try:
                    with Image.open(image_path) as img:
                        pil_exif = img.getexif()
                        if pil_exif:
                            logger.debug("\nPIL EXIF Data:")
                            logger.debug("-" * 20)
                            for tag_id in pil_exif:
                                tag = TAGS.get(tag_id, tag_id)
                                data = pil_exif.get(tag_id)
                                logger.debug(f"{tag}: {data}")
                except Exception as e:
                    logger.debug(f"Could not read PIL EXIF data: {e}")
                    
            return exif_data
        except Exception as e:
            logger.error(f"Error reading EXIF data from {image_path}: {e}")
            return {}

    def get_date_taken(self, image_path: Path, exif_data: Dict[str, Any]) -> datetime:
        """Extract the date when the photo was taken."""
        try:
            # Try to get date from EXIF data
            date_field = exif_data.get('EXIF DateTimeOriginal', 
                        exif_data.get('Image DateTime'))
            
            if date_field:
                if self.debug:
                    logger.debug(f"Raw date field from EXIF: {date_field!r}")
                    logger.debug(f"Date field type: {type(date_field)}")
                
                # Convert exifread's tag to string properly
                date_str = str(date_field).strip()
                
                if self.debug:
                    logger.debug(f"Converted date string: {date_str!r}")
                
                # Common EXIF date formats
                date_formats = [
                    '%Y:%m:%d %H:%M:%S',  # Standard EXIF format
                    '%Y-%m-%d %H:%M:%S',  # Alternative format
                    '%Y:%m:%d %H:%M:%S.%f',  # Format with microseconds
                    '%Y-%m-%d %H:%M:%S.%f'   # Alternative with microseconds
                ]
                
                # Try parsing with different formats
                for date_format in date_formats:
                    try:
                        if self.debug:
                            logger.debug(f"Trying format: {date_format}")
                        date = datetime.strptime(date_str, date_format)
                        if self.debug:
                            logger.debug(f"Successfully parsed date: {date} using format: {date_format}")
                        return date
                    except ValueError:
                        if self.debug:
                            logger.debug(f"Format {date_format} did not match")
                        continue
                
                # If standard formats fail, try dateutil parser as fallback
                try:
                    if self.debug:
                        logger.debug("Trying dateutil parser as fallback")
                    date = parser.parse(date_str)
                    if self.debug:
                        logger.debug(f"Successfully parsed date with dateutil: {date}")
                    return date
                except Exception as e:
                    if self.debug:
                        logger.debug(f"dateutil parser failed: {e}")
                    raise ValueError(f"Could not parse date string: {date_str}")
            
            # If no EXIF date, try getting file creation/modification date
            stat = os.stat(image_path)
            date = datetime.fromtimestamp(min(stat.st_mtime, stat.st_ctime))
            if self.debug:
                logger.debug(f"No EXIF date found. Using file timestamp: {date}")
            return date
            
        except Exception as e:
            logger.error(f"Error getting date for {image_path}: {e}")
            date = datetime.fromtimestamp(os.path.getctime(image_path))
            if self.debug:
                logger.debug(f"Error getting date, falling back to creation time: {date}")
            return date 