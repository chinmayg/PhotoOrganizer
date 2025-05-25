"""Module for handling GPS data extraction and location services."""

import logging
import json
import time
from typing import Dict, Any, Optional, Tuple
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import sqlite3
from contextlib import closing
from pathlib import Path
from functools import lru_cache

logger = logging.getLogger(__name__)

class GPSHandler:
    """Handles GPS data extraction and location services."""
    
    def __init__(self, debug: bool = False, use_cache: bool = True):
        self.debug = debug
        self.use_cache = use_cache
        self.geolocator = Nominatim(user_agent="photo_organizer")
        
        if use_cache:
            self.init_cache()

    def init_cache(self):
        """Initialize SQLite cache for geocoding results."""
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

    @lru_cache(maxsize=1024)
    def get_cached_location(self, lat: float, lon: float) -> Optional[str]:
        """Get cached location for coordinates."""
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
        """Cache location for coordinates."""
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
                        if self.debug:
                            logger.debug(f"Geocoding attempt {attempt + 1}/3")
                            logger.debug(f"Querying coordinates: {lat}, {lon}")
                        
                        location = self.geolocator.reverse(f"{lat}, {lon}", language='en', timeout=10)
                        if location:
                            if self.debug:
                                logger.debug("Received response from geocoder")
                                logger.debug(f"Raw response: {json.dumps(location.raw, indent=2)}")
                            
                            address = location.raw.get('address', {})
                            if self.debug:
                                logger.debug(f"Address components: {json.dumps(address, indent=2)}")
                            
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
                        else:
                            if self.debug:
                                logger.debug("Geocoder returned no results")
                        
                        time.sleep(1)
                    except GeocoderTimedOut:
                        if self.debug:
                            logger.debug(f"Geocoding timed out, attempt {attempt + 1}")
                        time.sleep(2)
                        continue
                    except Exception as e:
                        logger.error(f"Error getting location name: {e}")
                        if self.debug:
                            logger.exception("Detailed geocoding error:")
                        break
                
            except Exception as e:
                if self.debug:
                    logger.debug(f"Error processing GPS coordinates: {e}")
                    logger.exception("Detailed GPS processing error:")
                
        except Exception as e:
            logger.error(f"Error processing GPS data: {e}")
            if self.debug:
                logger.exception("Detailed error information:")
        
        return "Unknown Location" 