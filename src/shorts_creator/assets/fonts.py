"""Font utilities for the shorts creator."""

from pathlib import Path
import logging

log = logging.getLogger(__name__)

# Font directory
FONTS_DIR = Path(__file__).parent / "fonts"

# Font paths
ROBOTO_REGULAR = FONTS_DIR / "Roboto-Regular.ttf"
ROBOTO_BOLD = FONTS_DIR / "Roboto-Bold.ttf"


def get_font_path(font_name: str = "roboto-bold") -> Path:
    """
    Get the path to a bundled font file.
    
    Args:
        font_name: The name of the font ("roboto-bold" or "roboto-regular")
        
    Returns:
        Path to the font file
        
    Raises:
        FileNotFoundError: If the font file doesn't exist
    """
    font_map = {
        "roboto-bold": ROBOTO_BOLD,
        "roboto-regular": ROBOTO_REGULAR,
    }
    
    font_path = font_map.get(font_name.lower())
    if not font_path:
        raise ValueError(f"Unknown font: {font_name}. Available: {list(font_map.keys())}")
    
    if not font_path.exists():
        raise FileNotFoundError(f"Font file not found: {font_path}")
    
    log.debug(f"Using font: {font_path}")
    return font_path