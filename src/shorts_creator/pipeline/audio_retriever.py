from pathlib import Path
import ffmpeg
import logging

log = logging.getLogger(__name__)


def retrieve_audio(
    video_path: Path,
    output_file: Path,
    refresh: bool,
    duration_seconds: int | None = None,
) -> Path:
    if output_file.exists() and not refresh:
        return output_file
    try:
        kwargs = {}
        if duration_seconds:
            kwargs["t"] = duration_seconds

        log.info(
            f"Extracting audio: video = {video_path}, output = {output_file}, duration = {duration_seconds or -1}s"
        )
        ffmpeg.input(str(video_path)).output(
            str(output_file), acodec="libmp3lame", **kwargs
        ).overwrite_output().run(quiet=True)

    except Exception as e:
        log.error(
            "Error occurred while retrieving audio: video_path = %s, output_file = %s, error = %s",
            video_path,
            output_file,
            e,
            exc_info=True,
        )
        raise e

    return output_file
