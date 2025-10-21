from pathlib import Path
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
import argparse
from typing import Literal
from shorts_creator.video_effect.strategies import VideoEffectsStrategy


class AppSettings(BaseSettings):
    openai_api_key: str
    openai_base_url: str = "https://openrouter.ai/api/v1"
    model_name: str = "openai/gpt-5-mini"
    data_dir: Path = Path("shorts-creator")
    refresh: bool = True
    video_path: Path
    shorts_number: int = 5
    duration_seconds: int | None = None
    start_offset_seconds: int = 0
    short_duration_seconds: int = 60
    speed_factor: float = 1.35
    whisper_model_size: Literal["tiny", "base", "small", "medium", "large"] = "medium"
    video_effect_strategy: VideoEffectsStrategy = VideoEffectsStrategy.BASIC
    debug: bool = False
    audio_stream_index: int | None = None
    # YouTube upload settings
    youtube_upload: bool = False
    youtube_privacy: Literal["private", "public", "unlisted"] = "private"
    youtube_client_id: str | None = None
    youtube_client_secret: str | None = None
    youtube_project_id: str | None = None
    ffmpeg_path: Path | None = None

    class Config:
        env_file = ".env"
        env_prefix = "YOUTUBE_SHORTS_"
        extra = "allow"


def parse_args() -> AppSettings:
    """Parse command line arguments and return config."""
    parser = argparse.ArgumentParser(description="YouTube Shorts Creator")
    parser.add_argument(
        "--refresh",
        dest="refresh",
        action="store_true",
        default=None,
        help="Force regeneration even if cached files exist",
    )
    parser.add_argument(
        "-nr",
        "--no-refresh",
        dest="refresh",
        action="store_false",
        help="Do not refresh/regenerate content, use cached files if available",
    )
    parser.add_argument(
        "-v",
        "--video",
        type=Path,
        default=None,
        help="Path to the video file",
    )
    parser.add_argument(
        "-s",
        "--shorts",
        type=int,
        default=None,
        help="Maximum number of shorts to generate",
    )
    parser.add_argument(
        "-d",
        "--duration",
        type=int,
        default=None,
        help="Maximum duration of video to process in seconds",
    )
    parser.add_argument(
        "--start-offset",
        type=int,
        default=None,
        help="Start offset (in seconds) to seek into the input video before processing",
    )
    parser.add_argument(
        "-sd",
        "--short-duration",
        type=int,
        default=None,
        help="Duration of each short in seconds",
    )
    parser.add_argument(
        "--strategy",
        type=str,
        default=None,
        help=f"Video effects strategy to use: {', '.join([s.name.lower() for s in VideoEffectsStrategy])}",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        default=None,
        help="Enable debug mode with verbose logging",
    )
    parser.add_argument(
        "--whisper-model",
        type=str,
        default=None,
        choices=["tiny", "base", "small", "medium", "large"],
        help="Size of the Whisper model for transcription (smaller models use less memory)",
    )
    parser.add_argument(
        "--model-name",
        type=str,
        default=None,
        help="Override the OpenRouter/OpenAI-compatible model ID (e.g. openai/gpt-4o-mini)",
    )
    parser.add_argument(
        "--ffmpeg-path",
        type=Path,
        default=None,
        help="Explicit path to the ffmpeg executable. Overrides PATH lookup.",
    )
    parser.add_argument(
        "--audio-stream-index",
        type=int,
        default=None,
        help="Index аудиодорожки (0-based) для извлечения",
    )
    parser.add_argument(
        "--upload",
        action="store_true",
        default=None,
        help="Upload generated shorts to YouTube",
    )
    parser.add_argument(
        "--youtube-privacy",
        type=str,
        default=None,
        choices=["private", "public", "unlisted"],
        help="YouTube video privacy setting",
    )
    args = parser.parse_args()
    settings_kwargs: dict[str, object] = {}

    if args.refresh is not None:
        settings_kwargs["refresh"] = args.refresh
    if args.video is not None:
        settings_kwargs["video_path"] = args.video
    if args.shorts is not None:
        settings_kwargs["shorts_number"] = args.shorts
    if args.duration is not None:
        settings_kwargs["duration_seconds"] = args.duration
    if args.start_offset is not None:
        settings_kwargs["start_offset_seconds"] = args.start_offset
    if args.short_duration is not None:
        settings_kwargs["short_duration_seconds"] = args.short_duration
    if args.strategy is not None:
        settings_kwargs["video_effect_strategy"] = VideoEffectsStrategy[
            args.strategy.upper()
        ]
    if args.debug is not None:
        settings_kwargs["debug"] = args.debug
    if args.upload is not None:
        settings_kwargs["youtube_upload"] = args.upload
    if args.youtube_privacy is not None:
        settings_kwargs["youtube_privacy"] = args.youtube_privacy
    if args.ffmpeg_path is not None:
        settings_kwargs["ffmpeg_path"] = args.ffmpeg_path
    if args.audio_stream_index is not None:
        settings_kwargs["audio_stream_index"] = args.audio_stream_index
    if args.whisper_model is not None:
        settings_kwargs["whisper_model_size"] = args.whisper_model
    if args.model_name:
        settings_kwargs["model_name"] = args.model_name

    return AppSettings(**settings_kwargs)  # type: ignore
