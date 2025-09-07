"""Font utilities for the shorts creator."""

from pathlib import Path
import logging

log = logging.getLogger(__name__)

# Font directory
FONTS_DIR = Path(__file__).parent / "fonts"

# Font paths
ROBOTO_REGULAR = FONTS_DIR / "Roboto-Regular.ttf"
ROBOTO_BOLD = FONTS_DIR / "Roboto-Bold.ttf"
COMIC_NEUE_BOLD = FONTS_DIR / "ComicNeue-Bold.ttf"


def get_font_path(font_name: str = "roboto-bold") -> Path:
    """
    Get the path to a bundled font file.
    
    Args:
        font_name: The name of the font ("roboto-bold", "roboto-regular", or "comic-neue-bold")
        
    Returns:
        Path to the font file
        
    Raises:
        FileNotFoundError: If the font file doesn't exist
    """
    font_map = {
        "roboto-bold": ROBOTO_BOLD,
        "roboto-regular": ROBOTO_REGULAR,
        "comic-neue-bold": COMIC_NEUE_BOLD,
    }
    
    font_path = font_map.get(font_name.lower())
    if not font_path:
        raise ValueError(f"Unknown font: {font_name}. Available: {list(font_map.keys())}")
    
    if not font_path.exists():
        raise FileNotFoundError(f"Font file not found: {font_path}")
    
    log.debug(f"Using font: {font_path}")
    return font_path