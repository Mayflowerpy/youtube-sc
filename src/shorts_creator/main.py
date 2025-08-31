import asyncio
import logging
from pathlib import Path

from shorts_creator.pipeline import audio_retriever, speech_to_text, storage
from shorts_creator.settings.settings import parse_args


logging.basicConfig(level=logging.INFO)

log = logging.getLogger(__name__)


async def main():
    settings = parse_args()
    log.info(
        f"Starting shorts creation: refresh={settings.refresh}, video = {settings.video_path}"
    )

    audio_file = audio_retriever.retrieve_audio(
        settings.video_path,
        settings.data_dir / "audios/extracted_audio.mp3",
        refresh=settings.refresh,
        duration_seconds=300,
    )

    log.info(f"Audio extracted to {audio_file}")
    speech = speech_to_text.convert_speech_to_text(
        audio_file, settings.data_dir / "text/speech.json", refresh=settings.refresh
    )
    log.info("Shorts creation completed!")


if __name__ == "__main__":
    asyncio.run(main())
