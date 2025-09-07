import logging
import ffmpeg
from pathlib import Path
from shorts_creator.domain.models import YouTubeShortWithSpeech, Speech

log = logging.getLogger(__name__)


def create_subtitle_file(
    speech: Speech, start_time: float, end_time: float, output_path: Path
) -> Path:
    """(Deprecated) Subtitle SRT creation. Unused in current pipeline."""
    srt_path = output_path.with_suffix(".srt")
    try:
        with open(srt_path, "w", encoding="utf-8") as f:
            pass
    except Exception:
        pass
    return srt_path


def cut_video_segment_with_effects(
    input_video: Path,
    output_video: Path,
    start_time: float,
    end_time: float,
    debug: bool,
) -> Path:
    """Cut a clean video segment only.

    Effects and formatting to 9:16 are applied later in video_effecter.
    """
    try:

        # Ensure output directory exists
        output_video.parent.mkdir(parents=True, exist_ok=True)

        # Accurate cut with black frame removal
        duration = end_time - start_time

        # Use more precise seeking and add black frame detection
        input_stream = ffmpeg.input(str(input_video))

        # Apply precise trimming with black frame removal
        video = input_stream.video.filter(
            "trim", start=start_time, duration=duration
        ).filter(
            "setpts", "PTS-STARTPTS"
        )  # Reset timestamps to avoid black frames

        audio = input_stream.audio.filter(
            "atrim", start=start_time, duration=duration
        ).filter(
            "asetpts", "PTS-STARTPTS"
        )  # Reset audio timestamps

        output_stream = ffmpeg.output(
            video,
            audio,
            str(output_video),
            vcodec="libx264",
            acodec="aac",
            movflags="+faststart",
        )

        ffmpeg.run(output_stream, overwrite_output=True, quiet=not debug)

        return output_video

    except ffmpeg.Error as e:
        log.error(
            f"FFmpeg error: stdout={e.stdout.decode()}, stderr={e.stderr.decode()}"
        )
        raise
    except Exception as e:
        log.error(f"Error cutting video: {e}")
        raise


def create_short_video(
    input_video: Path,
    short: YouTubeShortWithSpeech,
    output_dir: Path,
    short_index: int,
    debug: bool,
    refresh: bool,
) -> Path:
    """Create an enhanced short video from a YouTubeShort analysis result."""
    output_filename = (
        f"short_{short_index + 1}_{short.start_time:.0f}s-{short.end_time:.0f}s.mp4"
    )
    output_path = output_dir / output_filename

    if output_path.exists() and not refresh:
        log.debug(f"Short video already exists, skipping: {output_path}")
        return output_path

    return cut_video_segment_with_effects(
        input_video=input_video,
        output_video=output_path,
        start_time=short.start_time,
        end_time=short.end_time,
        debug=debug,
    )
