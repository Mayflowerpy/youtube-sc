import logging
from pathlib import Path
from moviepy import *

from shorts_creator.domain.models import Speech, YouTubeShort

log = logging.getLogger(__name__)


def apply_video_effects(
    input_video: Path,
    output_video: Path,
    short: YouTubeShort,
    speech: Speech,
) -> Path:
    video = VideoFileClip(str(input_video))
    
    return input_video
