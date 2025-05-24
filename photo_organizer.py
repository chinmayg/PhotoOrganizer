#!/usr/bin/env python3

import os
import shutil
import argparse
from datetime import datetime
from pathlib import Path
import exifread
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from dateutil import parser
import logging
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import time
import json
from typing import Dict, Any, Optional, Tuple, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import hashlib
from functools import lru_cache
import sqlite3
from contextlib import closing

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PhotoOrganizer:
    def __init__(self, input_folder, output_folder, debug=False, max_workers=None, use_cache=True):
        self.input_folder = Path(input_folder)
        self.output_folder = Path(output_folder)
        self.debug = debug
        self.max_workers = max_workers or min(32, os.cpu_count() * 2)
        self.use_cache = use_cache
        self.geolocator = Nominatim(user_agent="photo_organizer")
        self.month_names = {
            1: "01-January", 2: "02-February", 3: "03-March", 4: "04-April",
            5: "05-May", 6: "06-June", 7: "07-July", 8: "08-August",
            9: "09-September", 10: "10-October", 11: "11-November", 12: "12-December"
        }
        
        # Initialize cache
        if use_cache:
            self.init_cache()

    def init_cache(self):
        """Initialize SQLite cache for geocoding results"""
        cache_dir = Path.home() / '.photo_organizer'
        cache_dir.mkdir(exist_ok=True)
        self.cache_db = cache_dir / 'geocoding_cache.db'
        
        with closing(sqlite3.connect(str(self.cache_db))) as conn:
            with closing(conn.cursor()) as cursor:
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS geocoding_cache (
                        coordinates TEXT PRIMARY KEY,
                        location TEXT,
                        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                conn.commit()

    @lru_cache(maxsize=1024)
    def get_cached_location(self, lat: float, lon: float) -> Optional[str]:
        """Get cached location for coordinates"""
        if not self.use_cache:
            return None
            
        coord_key = f"{lat},{lon}"
        with closing(sqlite3.connect(str(self.cache_db))) as conn:
            with closing(conn.cursor()) as cursor:
                cursor.execute(
                    "SELECT location FROM geocoding_cache WHERE coordinates = ?",
                    (coord_key,)
                )
                result = cursor.fetchone()
                return result[0] if result else None

    def cache_location(self, lat: float, lon: float, location: str):
        """Cache location for coordinates"""
        if not self.use_cache:
            return
            
        coord_key = f"{lat},{lon}"
        with closing(sqlite3.connect(str(self.cache_db))) as conn:
            with closing(conn.cursor()) as cursor:
                cursor.execute(
                    "INSERT OR REPLACE INTO geocoding_cache (coordinates, location) VALUES (?, ?)",
                    (coord_key, location)
                )
                conn.commit()

    def process_photo(self, file_path: Path) -> Tuple[bool, str]:
        """Process a single photo file"""
        try:
            if not file_path.is_file() or not self.is_image_file(file_path):
                return False, f"Skipped {file_path.name}: Not a supported image file"

            # Get EXIF data
            exif_data = self.get_exif_data(file_path)
            
            # Get date and location
            date_taken = self.get_date_taken(file_path, exif_data)
            location = self.get_location(exif_data)
            
            # Create destination path and copy file
            dest_path = self.create_destination_path(date_taken, location, file_path)
            shutil.copy2(file_path, dest_path)
            
            return True, f"Successfully organized {file_path.name} to {dest_path}"
            
        except Exception as e:
            if self.debug:
                logger.exception(f"Error processing {file_path.name}")
            return False, f"Error processing {file_path.name}: {str(e)}"

    def get_location(self, exif_data: Dict[str, Any]) -> str:
        """Extract location information from EXIF data."""
        try:
            if self.debug:
                self.debug_gps_data(exif_data)
                
            if 'GPS GPSLatitude' not in exif_data or 'GPS GPSLongitude' not in exif_data:
                if self.debug:
                    logger.debug("Missing required GPS coordinates")
                return "Unknown Location"

            try:
                lat = self.convert_to_degrees(exif_data['GPS GPSLatitude'])
                lon = self.convert_to_degrees(exif_data['GPS GPSLongitude'])
                
                # Get and apply the reference (N/S, E/W)
                lat_ref = str(exif_data.get('GPS GPSLatitudeRef', 'N')).upper()
                lon_ref = str(exif_data.get('GPS GPSLongitudeRef', 'E')).upper()
                
                if self.debug:
                    logger.debug(f"Before applying reference:")
                    logger.debug(f"  Raw latitude: {lat} ({lat_ref})")
                    logger.debug(f"  Raw longitude: {lon} ({lon_ref})")
                
                # Apply references
                if lat_ref == 'S':
                    lat = -lat
                if lon_ref == 'W':
                    lon = -abs(lon)

                # Check cache first
                cached_location = self.get_cached_location(lat, lon)
                if cached_location:
                    if self.debug:
                        logger.debug(f"Found cached location: {cached_location}")
                    return cached_location

                # Get location name with retry mechanism
                for attempt in range(3):
                    try:
                        location = self.geolocator.reverse(f"{lat}, {lon}", language='en', timeout=10)
                        if location:
                            address = location.raw.get('address', {})
                            city = (address.get('city') or 
                                   address.get('town') or
                                   address.get('village') or
                                   address.get('suburb') or
                                   address.get('state') or
                                   address.get('county') or
                                   'Unknown Location')
                            
                            # Cache the result
                            self.cache_location(lat, lon, city)
                            return city
                        
                        time.sleep(1)
                    except GeocoderTimedOut:
                        time.sleep(2)
                        continue
                    except Exception as e:
                        logger.error(f"Error getting location name: {e}")
                        break
                
            except Exception as e:
                if self.debug:
                    logger.debug(f"Error processing GPS coordinates: {e}")
                
        except Exception as e:
            logger.error(f"Error processing GPS data: {e}")
        
        return "Unknown Location"

    def organize_photos(self) -> None:
        """Main method to organize photos."""
        start_time = time.time()
        logger.info(f"Starting photo organization from {self.input_folder} to {self.output_folder}")
        
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
            futures = {executor.submit(self.process_photo, file_path): file_path for file_path in files}
            
            with tqdm(total=total_files, desc="Processing photos", unit="photo") as pbar:
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
        photos_per_second = processed / duration if duration > 0 else 0
        
        # Print summary
        logger.info("\nPhoto Organization Summary:")
        logger.info(f"Total files found: {total_files}")
        logger.info(f"Successfully processed: {processed}")
        logger.info(f"Skipped: {skipped}")
        logger.info(f"Errors: {errors}")
        logger.info(f"Total time: {duration:.2f} seconds")
        logger.info(f"Processing speed: {photos_per_second:.2f} photos/second")
        
        if self.use_cache:
            with closing(sqlite3.connect(str(self.cache_db))) as conn:
                with closing(conn.cursor()) as cursor:
                    cursor.execute("SELECT COUNT(*) FROM geocoding_cache")
                    cache_size = cursor.fetchone()[0]
                    logger.info(f"Geocoding cache size: {cache_size} locations")

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

    def debug_gps_data(self, exif_data: Dict[str, Any]) -> None:
        """Debug GPS-related EXIF data."""
        if not self.debug:
            return

        logger.debug("\nGPS Data Analysis:")
        logger.debug("-" * 20)
        
        # List all GPS-related tags
        gps_tags = [tag for tag in exif_data.keys() if tag.startswith('GPS ')]
        if not gps_tags:
            logger.debug("No GPS tags found in EXIF data")
            return
            
        logger.debug("Found GPS tags:")
        for tag in gps_tags:
            logger.debug(f"{tag}: {exif_data[tag]}")

    def convert_to_degrees(self, value) -> float:
        """Convert GPS coordinates to degrees."""
        try:
            if self.debug:
                logger.debug(f"Converting GPS value: {value}")
                logger.debug(f"Value type: {type(value)}")
                logger.debug(f"Raw values: {value.values}")

            d = float(value.values[0].num) / float(value.values[0].den)
            m = float(value.values[1].num) / float(value.values[1].den)
            s = float(value.values[2].num) / float(value.values[2].den)
            
            result = d + (m / 60.0) + (s / 3600.0)
            
            if self.debug:
                logger.debug(f"Conversion details:")
                logger.debug(f"  Degrees: {d} = {value.values[0].num}/{value.values[0].den}")
                logger.debug(f"  Minutes: {m} = {value.values[1].num}/{value.values[1].den}")
                logger.debug(f"  Seconds: {s} = {value.values[2].num}/{value.values[2].den}")
                logger.debug(f"  Final result: {result}")
            
            return result
        except Exception as e:
            if self.debug:
                logger.debug(f"Error converting GPS value to degrees: {e}")
                logger.debug(f"Full value object: {vars(value)}")
            raise

    def create_destination_path(self, date_taken: datetime, location: str, original_path: Path) -> Path:
        """Create the destination path based on date and location."""
        year_folder = str(date_taken.year)
        month_folder = self.month_names[date_taken.month]
        day_folder = f"{date_taken.day:02d}"  # Pad with zero for single digit days
        
        # Create path components
        dest_path = self.output_folder / year_folder / month_folder / day_folder / location
        dest_path.mkdir(parents=True, exist_ok=True)
        
        # Handle filename conflicts
        filename = original_path.name
        counter = 1
        final_path = dest_path / filename
        
        while final_path.exists():
            name = original_path.stem
            suffix = original_path.suffix
            final_path = dest_path / f"{name}_{counter}{suffix}"
            counter += 1
            
        if self.debug:
            logger.debug(f"Final destination path: {final_path}")
        return final_path

    def is_image_file(self, file_path: Path) -> bool:
        """Check if the file is an image."""
        image_extensions = {'.jpg', '.jpeg', '.png', '.heic', '.heif', '.gif'}
        return file_path.suffix.lower() in image_extensions

def main():
    parser = argparse.ArgumentParser(description='Organize photos by date and location.')
    parser.add_argument('--input-folder', required=True, help='Input folder containing photos')
    parser.add_argument('--output-folder', required=True, help='Output folder for organized photos')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode for detailed information')
    parser.add_argument('--workers', type=int, help='Number of worker threads (default: CPU count * 2)')
    parser.add_argument('--no-cache', action='store_true', help='Disable geocoding cache')
    
    args = parser.parse_args()
    
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    organizer = PhotoOrganizer(
        args.input_folder,
        args.output_folder,
        debug=args.debug,
        max_workers=args.workers,
        use_cache=not args.no_cache
    )
    organizer.organize_photos()

if __name__ == "__main__":
    main() 