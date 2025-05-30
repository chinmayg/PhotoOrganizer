"""Module for handling video metadata extraction and processing."""

import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import os
from hachoir.parser import createParser
from hachoir.metadata import extractMetadata
import ffmpeg

logger = logging.getLogger(__name__)

class VideoHandler:
    """Handles metadata extraction and processing from video files."""
    
    SUPPORTED_FORMATS = {'.mov', '.mp4'}
    
    def __init__(self, debug: bool = False):
        self.debug = debug

    def debug_metadata(self, video_path: Path, metadata: Dict[str, Any]) -> None:
        """Print detailed metadata information when in debug mode."""
        if not self.debug:
            return

        logger.debug(f"\n{'='*50}")
        logger.debug(f"Detailed video metadata for: {video_path.name}")
        logger.debug(f"{'='*50}")

        if not metadata:
            logger.debug("No metadata found!")
            return

        for key, value in metadata.items():
            logger.debug(f"{key}: {value}")

    def get_ffmpeg_metadata(self, video_path: Path) -> Dict[str, Any]:
        """Extract metadata using ffmpeg as a fallback."""
        try:
            if self.debug:
                logger.debug("Attempting to extract metadata using ffmpeg...")
            
            probe = ffmpeg.probe(str(video_path))
            metadata = {}
            
            # Get video stream information
            video_info = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
            if video_info:
                if self.debug:
                    logger.debug("Found video stream information")
                
                # Get basic video information
                if 'width' in video_info:
                    metadata['width'] = int(video_info['width'])
                if 'height' in video_info:
                    metadata['height'] = int(video_info['height'])
                if 'duration' in video_info:
                    metadata['duration'] = float(video_info['duration'])
                
                # Get creation time if available
                if 'tags' in video_info and 'creation_time' in video_info['tags']:
                    try:
                        from dateutil import parser
                        metadata['creation_date'] = parser.parse(video_info['tags']['creation_time'])
                    except Exception as e:
                        if self.debug:
                            logger.debug(f"Error parsing creation time: {e}")
                
                # Get GPS data if available
                if 'tags' in video_info:
                    for key, value in video_info['tags'].items():
                        if 'gps' in key.lower():
                            metadata[key] = value
            
            if self.debug:
                self.debug_metadata(video_path, metadata)
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error extracting metadata using ffmpeg: {e}")
            if self.debug:
                logger.exception("Detailed ffmpeg error:")
            return {}

    def get_metadata(self, video_path: Path) -> Dict[str, Any]:
        """Extract metadata from a video file."""
        try:
            metadata = {}
            
            if self.debug:
                logger.debug(f"\nAttempting to extract metadata from: {video_path}")
                logger.debug(f"File size: {os.path.getsize(video_path)} bytes")
                logger.debug(f"File extension: {video_path.suffix.lower()}")
            
            # First try with hachoir
            parser = createParser(str(video_path))
            if parser:
                try:
                    if self.debug:
                        logger.debug("Parser created successfully, attempting to extract metadata...")
                    
                    hachoir_metadata = extractMetadata(parser)
                    if hachoir_metadata:
                        # Get creation date
                        if hachoir_metadata.has('creation_date'):
                            metadata['creation_date'] = hachoir_metadata.get('creation_date')
                            if self.debug:
                                logger.debug(f"Found creation date: {metadata['creation_date']}")

                        # Get basic video information
                        if hachoir_metadata.has('duration'):
                            metadata['duration'] = hachoir_metadata.get('duration').total_seconds()
                            if self.debug:
                                logger.debug(f"Found duration: {metadata['duration']} seconds")
                        
                        if hachoir_metadata.has('width') and hachoir_metadata.has('height'):
                            metadata['width'] = hachoir_metadata.get('width')
                            metadata['height'] = hachoir_metadata.get('height')
                            if self.debug:
                                logger.debug(f"Found dimensions: {metadata['width']}x{metadata['height']}")
                        
                        # Get all available metadata for debugging
                        if self.debug:
                            logger.debug("\nAll available metadata fields:")
                            for key, value in hachoir_metadata._Metadata__data.items():
                                logger.debug(f"{key}: {value.value}")
                        
                        # Get GPS data if available
                        for key, value in hachoir_metadata._Metadata__data.items():
                            if 'gps' in key.lower():
                                metadata[key] = value.value
                                if self.debug:
                                    logger.debug(f"Found GPS data: {key}={value.value}")
                    
                except Exception as e:
                    if self.debug:
                        logger.debug(f"Error extracting metadata with hachoir: {e}")
                        logger.debug("Falling back to ffmpeg...")
                finally:
                    parser.close()
            
            # If hachoir failed to get metadata, try ffmpeg
            if not metadata:
                if self.debug:
                    logger.debug("No metadata extracted from hachoir, trying ffmpeg...")
                metadata = self.get_ffmpeg_metadata(video_path)
            
            # If we still couldn't get any metadata, try to get basic file information
            if not metadata and self.debug:
                logger.debug("No metadata extracted, falling back to basic file information")
                try:
                    stat = os.stat(video_path)
                    logger.debug(f"File creation time: {datetime.fromtimestamp(stat.st_ctime)}")
                    logger.debug(f"File modification time: {datetime.fromtimestamp(stat.st_mtime)}")
                except Exception as e:
                    logger.debug(f"Error getting file information: {e}")
                    
            return metadata
        except Exception as e:
            logger.error(f"Error reading metadata from {video_path}: {e}")
            if self.debug:
                logger.exception("Detailed error information:")
            return {}

    def get_date_taken(self, video_path: Path, metadata: Dict[str, Any]) -> datetime:
        """Extract the date when the video was taken."""
        try:
            # Try to get date from metadata
            if 'creation_date' in metadata:
                try:
                    # Hachoir returns datetime objects in UTC
                    date = metadata['creation_date']
                    if self.debug:
                        logger.debug(f"Found creation date in metadata: {date}")
                    return date
                except (ValueError, TypeError) as e:
                    if self.debug:
                        logger.debug(f"Could not parse creation_date: {e}")
            
            # Fallback to file system timestamps
            stat = os.stat(video_path)
            # Use the earlier of creation and modification time
            date = datetime.fromtimestamp(min(stat.st_mtime, stat.st_ctime))
            
            if self.debug:
                logger.debug(f"Using file timestamp for date: {date}")
            
            return date
            
        except Exception as e:
            logger.error(f"Error getting date for {video_path}: {e}")
            if self.debug:
                logger.exception("Detailed error information:")
            # Last resort: use file creation time
            return datetime.fromtimestamp(os.path.getctime(video_path))

    def get_gps_data(self, video_path: Path, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Extract GPS data from video metadata."""
        try:
            gps_data = {}
            
            # Look for GPS data in metadata
            # Different video formats might store GPS data differently
            for key, value in metadata.items():
                key_lower = key.lower()
                if 'gps' in key_lower:
                    if 'latitude' in key_lower:
                        try:
                            lat = float(value)
                            gps_data['GPS GPSLatitude'] = abs(lat)
                            gps_data['GPS GPSLatitudeRef'] = 'N' if lat >= 0 else 'S'
                        except (ValueError, TypeError):
                            pass
                    elif 'longitude' in key_lower:
                        try:
                            lon = float(value)
                            gps_data['GPS GPSLongitude'] = abs(lon)
                            gps_data['GPS GPSLongitudeRef'] = 'E' if lon >= 0 else 'W'
                        except (ValueError, TypeError):
                            pass
            
            if self.debug and gps_data:
                logger.debug("Found GPS data in video metadata:")
                for key, value in gps_data.items():
                    logger.debug(f"{key}: {value}")
            
            return gps_data
            
        except Exception as e:
            logger.error(f"Error extracting GPS data from {video_path}: {e}")
            if self.debug:
                logger.exception("Detailed error information:")
            return {} 