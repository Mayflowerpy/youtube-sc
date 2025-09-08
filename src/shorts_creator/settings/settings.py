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
    short_duration_seconds: int = 60
    speed_factor: float = 1.35
    whisper_model_size: Literal["medium", "large"] = "medium"
    video_effect_strategy: VideoEffectsStrategy
    debug: bool
    # YouTube upload settings
    youtube_upload: bool = False
    youtube_privacy: Literal["private", "public", "unlisted"] = "private"
    youtube_client_id: str | None = None
    youtube_client_secret: str | None = None
    youtube_project_id: str | None = None

    class Config:
        env_file = ".env"
        env_prefix = "YOUTUBE_SHORTS_"
        extra = "allow"


def parse_args() -> AppSettings:
    """Parse command line arguments and return config."""
    parser = argparse.ArgumentParser(description="YouTube Shorts Creator")
    parser.add_argument(
        "-nr",
        "--no-refresh",
        action="store_false",
        default=True,
        help="Do not refresh/regenerate content, use cached files if available",
    )
    parser.add_argument("-v", "--video", type=Path, help="Path to the video file")
    parser.add_argument(
        "-s",
        "--shorts",
        type=int,
        default=3,
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
        "-sd",
        "--short-duration",
        type=int,
        default=60,
        help="Duration of each short in seconds",
    )
    parser.add_argument(
        "--strategy",
        type=str,
        default="basic",
        help=f"Video effects strategy to use: {', '.join([s.name.lower() for s in VideoEffectsStrategy])}",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        default=False,
        help="Enable debug mode with verbose logging",
    )
    parser.add_argument(
        "--upload",
        action="store_true",
        default=False,
        help="Upload generated shorts to YouTube",
    )
    parser.add_argument(
        "--youtube-privacy",
        type=str,
        default="private",
        choices=["private", "public", "unlisted"],
        help="YouTube video privacy setting",
    )
    args = parser.parse_args()
    return AppSettings(
        refresh=args.no_refresh,
        video_path=args.video,
        shorts_number=args.shorts,
        duration_seconds=args.duration,
        short_duration_seconds=args.short_duration,
        video_effect_strategy=VideoEffectsStrategy[args.strategy.upper()],
        debug=args.debug,
        youtube_upload=args.upload,
        youtube_privacy=args.youtube_privacy,
    )  # type: ignore
