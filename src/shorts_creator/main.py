import asyncio
import logging
from pathlib import Path

from shorts_creator.pipeline.audio_retriever import retrieve_audio


logging.basicConfig(level=logging.INFO)

log = logging.getLogger(__name__)


async def main():
    log.info("Starting shorts creation...")
    video_path = Path("data/videos/long_video.mp4")
    output_file = Path("data/audios/extracted_audio.mp3")
    audio_file = retrieve_audio(video_path, output_file, duration_seconds=300)

    log.info(f"Audio extracted to {audio_file}")
    log.info("Shorts creation completed!")


if __name__ == "__main__":
    asyncio.run(main())
