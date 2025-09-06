from pathlib import Path
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
import argparse


class AppSettings(BaseSettings):
    openai_api_key: str = ""
    openai_base_url: str = "https://openrouter.ai/api/v1"
    model_name: str = "deepseek/deepseek-chat"
    data_dir: Path = Path("data")
    refresh: bool = False
    video_path: Path = Path("data/videos/long_video.mp4")
    shorts_number: int = 3
    duration_seconds: int | None = None

    class Config:
        env_file = ".env"
        env_prefix = "YOUTUBE_SHORTS_"
        extra = "allow"


def parse_args() -> AppSettings:
    """Parse command line arguments and return config."""
    parser = argparse.ArgumentParser(description="YouTube Shorts Creator")
    parser.add_argument(
        "-r", "--refresh", action="store_true", help="Refresh/regenerate content"
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
    args = parser.parse_args()
    return AppSettings(refresh=args.refresh, video_path=args.video, shorts_number=args.shorts, duration=args.duration)  # type: ignore
