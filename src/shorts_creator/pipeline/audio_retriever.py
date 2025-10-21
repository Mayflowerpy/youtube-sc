from pathlib import Path
import os
import shutil
import ffmpeg
import logging

log = logging.getLogger(__name__)


def retrieve_audio(
    video_path: Path,
    output_file: Path,
    refresh: bool,
    duration_seconds: int | None,
    start_offset_seconds: int,
    debug: bool,
    ffmpeg_path: Path | None = None,
) -> Path:
    if not video_path.exists():
        raise FileNotFoundError(
            f"Video file not found: {video_path.resolve() if video_path.is_absolute() else (Path.cwd() / video_path).resolve()}"
        )

    resolved_ffmpeg = _resolve_ffmpeg_binary(ffmpeg_path)

    if output_file.exists() and not refresh:
        return output_file
    try:
        kwargs = {}
        if start_offset_seconds:
            kwargs["ss"] = start_offset_seconds
        if duration_seconds:
            kwargs["t"] = duration_seconds

        log.info(
            "Extracting audio: video = %s, output = %s, offset = %ss, duration = %ss, ffmpeg = %s",
            video_path,
            output_file,
            start_offset_seconds,
            duration_seconds if duration_seconds is not None else "full",
            resolved_ffmpeg,
        )
        ffmpeg.input(str(video_path)).output(
            str(output_file), acodec="libmp3lame", **kwargs
        ).overwrite_output().run(quiet=not debug, cmd=resolved_ffmpeg)

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


def _resolve_ffmpeg_binary(ffmpeg_path: Path | None) -> str:
    candidates: list[str] = []

    if ffmpeg_path is not None:
        candidates.append(str(ffmpeg_path))

    # Check environment variables
    env_ffmpeg = os.getenv("FFMPEG_PATH") or os.getenv("FFMPEG_BINARY")
    if env_ffmpeg:
        candidates.append(env_ffmpeg)

    # Check system PATH
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        candidates.append(system_ffmpeg)

    # Common Windows installation paths
    common_paths = [
        "C:\\ffmpeg\\bin\\ffmpeg.exe",
        "C:\\Program Files\\ffmpeg\\bin\\ffmpeg.exe",
        "C:\\Program Files (x86)\\ffmpeg\\bin\\ffmpeg.exe",
    ]
    candidates.extend(common_paths)

    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return str(Path(candidate).resolve())

    raise RuntimeError(
        "ffmpeg executable not found. Please provide the full path using --ffmpeg-path or set FFMPEG_PATH/FFMPEG_BINARY environment variable."
    )
