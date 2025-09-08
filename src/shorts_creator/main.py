import logging
from pathlib import Path
from typing import Optional

from tqdm import tqdm
from shorts_creator.pipeline import (
    audio_retriever,
    speech_to_text,
    shorts_generator,
    storage,
    video_cutter,
)
from shorts_creator.domain.models import YouTubeShortsRecommendation
from shorts_creator.video_effect import video_effect_service
from shorts_creator.video_effect.strategies import VideoEffectsStrategy
from shorts_creator.settings.settings import parse_args, AppSettings
from shorts_creator.youtube.youtube import YouTubeService


log = logging.getLogger(__name__)


def process_shorts_with_progress(
    recommendation: YouTubeShortsRecommendation,
    settings: AppSettings,
    videos_output_dir: Path,
    youtube_service: Optional[YouTubeService] = None,
):
    with tqdm(
        total=len(recommendation.shorts),
        desc="Processing shorts",
        unit="short",
        dynamic_ncols=True,
    ) as pbar:
        for i, short in enumerate(recommendation.shorts):
            pbar.set_description(f"Processing short {i+1}/{len(recommendation.shorts)}")

            video_path = video_cutter.create_short_video(
                input_video=settings.video_path,
                short=short,
                output_dir=videos_output_dir,
                short_index=i,
                debug=settings.debug,
                refresh=settings.refresh,
            )
            pbar.set_postfix(
                step="Video cut",
                title=(
                    short.title[:20] + "..." if len(short.title) > 20 else short.title
                ),
            )

            final_path = video_effect_service.apply_effects(
                short,
                settings,
                video_path,
                settings.video_effect_strategy,
                videos_output_dir,
                short_index=i,
            )
            pbar.set_postfix(
                step="Effects applied",
                title=(
                    short.title[:20] + "..." if len(short.title) > 20 else short.title
                ),
            )
            video_path.unlink(missing_ok=True)
            final_path.rename(video_path)

            # Upload to YouTube if enabled
            if youtube_service:
                pbar.set_postfix(
                    step="Uploading",
                    title=(
                        short.title[:20] + "..."
                        if len(short.title) > 20
                        else short.title
                    ),
                )

                youtube_service.upload_video(
                    video_path=video_path,
                    title=short.title,
                    description=short.description,
                    tags=short.tags,
                    privacy=settings.youtube_privacy,
                )

            pbar.update(1)
            pbar.set_postfix(
                step="Complete",
                title=(
                    short.title[:20] + "..." if len(short.title) > 20 else short.title
                ),
            )


def main():
    settings = parse_args()
    logging.basicConfig(level=logging.DEBUG if settings.debug else logging.INFO)

    log.info(
        f"Starting shorts creation: refresh={settings.refresh}, video = {settings.video_path}"
    )

    settings.data_dir.mkdir(parents=True, exist_ok=True)

    audio_file = audio_retriever.retrieve_audio(
        settings.video_path,
        settings.data_dir / "extracted_audio.mp3",
        refresh=settings.refresh,
        duration_seconds=settings.duration_seconds,
        debug=settings.debug,
    )

    log.info(f"Audio extracted to {audio_file}")
    speech = speech_to_text.convert_speech_to_text(
        audio_file, settings.data_dir / "speech.json", settings=settings
    )

    shorts = shorts_generator.generate_youtube_shorts_recommendations(
        speech, settings, settings.data_dir / "shorts.json"
    )

    # Initialize YouTube service if upload is enabled
    youtube_service = None
    if settings.youtube_upload:
        if not settings.youtube_client_id or not settings.youtube_client_secret:
            log.error(
                "❌ YouTube upload enabled but credentials missing. Set YOUTUBE_SHORTS_YOUTUBE_CLIENT_ID and YOUTUBE_SHORTS_YOUTUBE_CLIENT_SECRET environment variables"
            )
            return

        youtube_service = YouTubeService(
            client_id=settings.youtube_client_id,
            client_secret=settings.youtube_client_secret,
            project_id=settings.youtube_project_id,
            data_dir=settings.data_dir,
        )

        # Check quota status before processing
        if not youtube_service.check_quota_status():
            log.error("❌ YouTube quota check failed. Skipping upload.")
            youtube_service = None

    process_shorts_with_progress(shorts, settings, settings.data_dir, youtube_service)

    if not settings.debug:
        audio_file.unlink(missing_ok=True)
    log.info("Shorts creation completed!")


if __name__ == "__main__":
    main()
