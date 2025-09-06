from pathlib import Path
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
import argparse
from typing import Literal


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
    whisper_model_size: Literal["medium", "large"] = "large"

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
    args = parser.parse_args()
    return AppSettings(
        refresh=args.no_refresh,
        video_path=args.video,
        shorts_number=args.shorts,
        duration_seconds=args.duration,
        short_duration_seconds=args.short_duration,
    )  # type: ignore
