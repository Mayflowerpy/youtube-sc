import logging
import ffmpeg
from pathlib import Path
from shorts_creator.domain.models import YouTubeShort

log = logging.getLogger(__name__)


def cut_video_segment(
    input_video: Path, 
    output_video: Path, 
    start_time: float, 
    end_time: float
) -> Path:
    """Cut a video segment using ffmpeg."""
    try:
        log.info(f"Cutting video segment: {start_time}s - {end_time}s")
        
        # Ensure output directory exists
        output_video.parent.mkdir(parents=True, exist_ok=True)
        
        # Simple video cutting with ffmpeg
        duration = end_time - start_time
        
        (
            ffmpeg
            .input(str(input_video), ss=start_time, t=duration)
            .output(str(output_video))
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
        
        log.info(f"Video segment saved to {output_video}")
        return output_video
        
    except ffmpeg.Error as e:
        log.error(f"FFmpeg error: stdout={e.stdout.decode()}, stderr={e.stderr.decode()}")
        raise
    except Exception as e:
        log.error(f"Error cutting video segment: {e}")
        raise


def create_short_video(
    input_video: Path,
    short: YouTubeShort,
    output_dir: Path,
    short_index: int = 0
) -> Path:
    """Create a short video from a YouTubeShort analysis result."""
    output_filename = f"short_{short_index + 1}_{short.start_time:.0f}s-{short.end_time:.0f}s.mp4"
    output_path = output_dir / output_filename
    
    return cut_video_segment(
        input_video=input_video,
        output_video=output_path,
        start_time=short.start_time,
        end_time=short.end_time
    )