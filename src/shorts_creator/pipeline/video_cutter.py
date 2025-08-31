import logging
import ffmpeg
from pathlib import Path
from shorts_creator.domain.models import YouTubeShort

log = logging.getLogger(__name__)


def cut_video_segment(
    input_video: Path, 
    output_video: Path, 
    start_time: float, 
    end_time: float,
    add_captions: bool = True,
    caption_text: str = ""
) -> Path:
    """Cut a video segment and optionally add captions."""
    try:
        log.info(f"Cutting video segment: {start_time}s - {end_time}s")
        
        # Ensure output directory exists
        output_video.parent.mkdir(parents=True, exist_ok=True)
        
        # Basic video cutting with duration
        duration = end_time - start_time
        input_stream = ffmpeg.input(str(input_video), ss=start_time, t=duration)
        
        if add_captions and caption_text:
            # Add text overlay with simpler styling
            output_stream = ffmpeg.filter(
                input_stream,
                'drawtext',
                text=caption_text.replace('"', '\\"').replace("'", "\\'"),
                fontsize=20,
                fontcolor='white',
                x='(w-text_w)/2',
                y='h-text_h-20'
            )
        else:
            output_stream = input_stream
        
        # Simple output without complex scaling
        output_stream = ffmpeg.output(
            output_stream,
            str(output_video)
        )
        
        ffmpeg.run(output_stream, overwrite_output=True, capture_stdout=True, capture_stderr=True)
        
        log.info(f"Video segment saved to {output_video}")
        return output_video
        
    except ffmpeg.Error as e:
        log.error(f"FFmpeg error cutting video segment: stdout={e.stdout.decode()}, stderr={e.stderr.decode()}")
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
    
    # Create caption text (first 100 chars to avoid cluttering)
    caption_text = short.full_transcript[:100] + "..." if len(short.full_transcript) > 100 else short.full_transcript
    
    return cut_video_segment(
        input_video=input_video,
        output_video=output_path,
        start_time=short.start_time,
        end_time=short.end_time,
        add_captions=True,
        caption_text=caption_text
    )