"""Module for handling file operations and organization."""

import logging
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Set

logger = logging.getLogger(__name__)

class FileHandler:
    """Handles file operations and organization."""
    
    def __init__(self, output_folder: Path, debug: bool = False):
        self.output_folder = Path(output_folder)
        self.debug = debug
        self.month_names = {
            1: "01-January", 2: "02-February", 3: "03-March", 4: "04-April",
            5: "05-May", 6: "06-June", 7: "07-July", 8: "08-August",
            9: "09-September", 10: "10-October", 11: "11-November", 12: "12-December"
        }
        self.supported_extensions: Set[str] = {'.jpg', '.jpeg', '.png', '.heic', '.heif', '.gif'}

    def is_image_file(self, file_path: Path) -> bool:
        """Check if the file is a supported image."""
        return file_path.suffix.lower() in self.supported_extensions

    def create_destination_path(self, date_taken: datetime, location: str, original_path: Path) -> Path:
        """Create the destination path based on date and location."""
        year_folder = str(date_taken.year)
        month_folder = self.month_names[date_taken.month]
        
        # Create path components
        dest_path = self.output_folder / year_folder / month_folder / location
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

    def copy_file(self, source: Path, destination: Path) -> bool:
        """Copy file with metadata preservation."""
        try:
            shutil.copy2(source, destination)
            if self.debug:
                logger.debug(f"Successfully copied {source.name} to {destination}")
            return True
        except Exception as e:
            logger.error(f"Error copying {source.name}: {e}")
            if self.debug:
                logger.exception("Detailed copy error:")
            return False 