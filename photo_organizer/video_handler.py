"""Module for handling video metadata extraction and processing."""

import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import os
from moviepy.editor import VideoFileClip

logger = logging.getLogger(__name__)

class VideoHandler:
    """Handles metadata extraction and processing from video files."""
    
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

    def get_metadata(self, video_path: Path) -> Dict[str, Any]:
        """Extract metadata from a video file."""
        try:
            metadata = {}
            with VideoFileClip(str(video_path)) as clip:
                # Get basic video information
                metadata['duration'] = clip.duration
                metadata['size'] = (clip.size[0], clip.size[1])
                metadata['fps'] = clip.fps
                
                if hasattr(clip.reader, 'infos'):
                    # MoviePy can sometimes access ffmpeg metadata
                    metadata.update(clip.reader.infos)
                
            if self.debug:
                self.debug_metadata(video_path, metadata)
                    
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
            # MOV files often store creation time in metadata
            if 'creation_time' in metadata:
                try:
                    return datetime.strptime(metadata['creation_time'], '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    if self.debug:
                        logger.debug(f"Could not parse creation_time: {metadata['creation_time']}")
            
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
            
            # MOV files might store GPS data in metadata
            if 'location' in metadata:
                location = metadata['location']
                if isinstance(location, dict):
                    if 'latitude' in location and 'longitude' in location:
                        gps_data['GPS GPSLatitude'] = location['latitude']
                        gps_data['GPS GPSLongitude'] = location['longitude']
                        gps_data['GPS GPSLatitudeRef'] = 'N' if location['latitude'] >= 0 else 'S'
                        gps_data['GPS GPSLongitudeRef'] = 'E' if location['longitude'] >= 0 else 'W'
            
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