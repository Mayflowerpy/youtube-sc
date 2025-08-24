import logging
from pathlib import Path
import ffmpeg

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

log = logging.getLogger(__name__)


def extract_audio():
    """Extract audio from hardcoded video file and save to audios directory."""
    input_file = "data/videos/long_video.mp4"
    output_dir = Path("data/audios")
    output_file = output_dir / "extracted_audio.mp3"
    
    # Ensure output directory exists
    output_dir.mkdir(exist_ok=True)
    
    log.info(f"Extracting audio from {input_file}")
    
    try:
        # Extract audio using ffmpeg-python
        (
            ffmpeg
            .input(input_file)
            .output(str(output_file), acodec='libmp3lame')
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
        log.info(f"Audio successfully extracted to {output_file}")
        
    except ffmpeg.Error as e:
        log.error(f"FFmpeg error: {e.stderr.decode()}")
        raise
    except Exception as e:
        log.error(f"Unexpected error: {e}")
        raise


if __name__ == "__main__":
    log.info("Starting audio extraction")
    extract_audio()
    log.info("Audio extraction completed")
