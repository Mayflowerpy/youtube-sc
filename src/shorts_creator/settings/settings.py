from pathlib import Path
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
import argparse


class AppSettings(BaseSettings):
    openai_api_key: str
    openai_base_url: str = "https://openrouter.ai/api/v1"
    model_name: str = "deepseek/deepseek-chat"
    data_dir: Path = Path("data")
    refresh: bool
    video_path: Path

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
    args = parser.parse_args()
    return AppSettings(refresh=args.refresh, video_path=args.video)  # type: ignore
