import logging
import ffmpeg
from pathlib import Path
from shorts_creator.domain.models import YouTubeShort, Speech

log = logging.getLogger(__name__)


def create_subtitle_file(speech: Speech, start_time: float, end_time: float, output_path: Path) -> Path:
    """(Deprecated) Subtitle SRT creation. Unused in current pipeline."""
    srt_path = output_path.with_suffix('.srt')
    try:
        with open(srt_path, 'w', encoding='utf-8') as f:
            pass
    except Exception:
        pass
    return srt_path


def cut_video_segment_with_effects(
    input_video: Path, 
    output_video: Path, 
    start_time: float, 
    end_time: float,
    speech: Speech
) -> Path:
    """Cut a clean video segment only.

    Effects and formatting to 9:16 are applied later in video_effecter.
    """
    try:
        log.info(f"Cutting short segment: {start_time}s - {end_time}s")
        
        # Ensure output directory exists
        output_video.parent.mkdir(parents=True, exist_ok=True)

        # Simple accurate cut with re-encode
        duration = end_time - start_time
        
        input_stream = ffmpeg.input(str(input_video), ss=start_time, t=duration)
        output_stream = ffmpeg.output(
            input_stream, str(output_video), vcodec='libx264', acodec='aac', movflags='+faststart'
        )

        ffmpeg.run(output_stream, overwrite_output=True, capture_stdout=True, capture_stderr=True)

        log.info(f"Cut video saved to {output_video}")
        return output_video
        
    except ffmpeg.Error as e:
        log.error(f"FFmpeg error: stdout={e.stdout.decode()}, stderr={e.stderr.decode()}")
        raise
    except Exception as e:
        log.error(f"Error cutting video: {e}")
        raise


def create_short_video(
    input_video: Path,
    short: YouTubeShort,
    speech: Speech,
    output_dir: Path,
    short_index: int = 0
) -> Path:
    """Create an enhanced short video from a YouTubeShort analysis result."""
    output_filename = f"short_{short_index + 1}_{short.start_time:.0f}s-{short.end_time:.0f}s.mp4"
    output_path = output_dir / output_filename
    
    return cut_video_segment_with_effects(
        input_video=input_video,
        output_video=output_path,
        start_time=short.start_time,
        end_time=short.end_time,
        speech=speech
    )
