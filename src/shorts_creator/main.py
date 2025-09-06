import asyncio
import logging
from pathlib import Path

from shorts_creator.pipeline import (
    audio_retriever,
    speech_to_text,
    shorts_generator,
    storage,
    video_cutter,
    video_effecter,
)
from shorts_creator.video_effect import video_effect_service
from shorts_creator.video_effect.strategies import VideoEffectsStrategy
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
        duration_seconds=60,
    )

    log.info(f"Audio extracted to {audio_file}")
    speech = speech_to_text.convert_speech_to_text(
        audio_file, settings.data_dir / "text/speech.json", refresh=settings.refresh
    )

    shorts = shorts_generator.generate_youtube_shorts_recommendations(speech, settings)

    storage.save(
        settings.data_dir / "shorts/shorts.json", shorts.model_dump_json(indent=2)
    )

    # Create video shorts
    videos_output_dir = settings.data_dir / "shorts/videos"
    videos_output_dir.mkdir(parents=True, exist_ok=True)

    for i, short in enumerate(shorts.shorts):
        # 1) Cut the raw short from the source video
        video_path = video_cutter.create_short_video(
            input_video=settings.video_path,
            short=short,
            output_dir=videos_output_dir,
            short_index=i,
        )
        log.info(f"Created short video {i+1}: {video_path}")

        final_path = video_effect_service.apply_effects(
            short,
            video_path,
            VideoEffectsStrategy.BASIC,
            videos_output_dir,
        )
        
        # Replace the original video with the enhanced version
        video_path.unlink(missing_ok=True)  # Remove original file
        final_video_path = final_path.rename(video_path)  # Rename enhanced file to original name
        log.info(f"Enhanced short video {i+1}: {final_video_path}")

    log.info("Shorts creation completed!")


if __name__ == "__main__":
    asyncio.run(main())
