import logging
from pathlib import Path
from moviepy import VideoFileClip, TextClip, CompositeVideoClip
from typing import Any, Literal, Union
from shorts_creator.domain.models import Speech, YouTubeShort

log = logging.getLogger(__name__)

EffectsStrategy = Literal["basic_effects"]


def __basic_effects(
    video: VideoFileClip,
    output_video: Path,
    short: YouTubeShort,
    speech: Speech,
) -> Path:
    log.info("Starting basic_effects strategy")
    
    final_video = None  # Initialize for proper scoping
    try:
        current_video: Any = video

        # Apply speed scaling (1.35x as per strategy)
        speed_factor = 1.35
        log.info(f"Applying speed factor: {speed_factor}x")
        current_video = current_video.with_speed_scaled(speed_factor)

        # Get video dimensions and calculate aspect ratios
        original_w, original_h = current_video.size
        target_w, target_h = 1080, 1920  # 9:16 vertical format
        log.info(f"Converting from {original_w}x{original_h} to {target_w}x{target_h}")

        original_ratio = original_w / original_h
        target_ratio = target_w / target_h

        # Smart reframe to 9:16 with aspect ratio preservation
        if original_ratio > target_ratio:
            # Video is wider - fit to width, center vertically
            scale_factor = target_w / original_w
            scaled_w = target_w
            scaled_h = int(original_h * scale_factor)
            current_video = current_video.resized((scaled_w, scaled_h))

            y_offset = (target_h - scaled_h) // 2
            current_video = CompositeVideoClip(
                [current_video.with_position(("center", y_offset))],
                size=(target_w, target_h),
            )
            log.info(f"Wide video: scaled to {scaled_w}x{scaled_h}, y_offset: {y_offset}")
        else:
            # Video is taller or square - fit to height, center horizontally  
            scale_factor = target_h / original_h
            scaled_w = int(original_w * scale_factor)
            scaled_h = target_h
            current_video = current_video.resized((scaled_w, scaled_h))

            x_offset = (target_w - scaled_w) // 2
            current_video = CompositeVideoClip(
                [current_video.with_position((x_offset, "center"))],
                size=(target_w, target_h),
            )
            log.info(f"Tall/square video: scaled to {scaled_w}x{scaled_h}, x_offset: {x_offset}")

        final_video: Any = current_video

        # Get actual video duration
        video_duration = getattr(final_video, "duration", 30)
        if video_duration is None:
            video_duration = 30
        log.info(f"Video duration: {video_duration:.2f} seconds")

        # Generate dynamic title from short content
        if short.key_topics:
            title_text = " • ".join(short.key_topics[:2])  # Use first 2 topics
        else:
            title_text = "YouTube Short"
        
        # Ensure title is not too long (max 50 characters for mobile readability)
        if len(title_text) > 50:
            title_text = title_text[:47] + "..."
        log.info(f"Generated title: '{title_text}'")

        # Create title overlay with shadow (as per strategy requirements)
        title_shadow = TextClip(
            text=title_text,
            font_size=52,
            color="black",
            method="caption",
            size=(target_w - 100, None),
            duration=min(video_duration, 3.0),  # Show for max 3 seconds as per strategy
        ).with_position(("center", 82))

        title_clip = TextClip(
            text=title_text,
            font_size=52,
            color="white",
            stroke_color="black",
            stroke_width=4,
            method="caption",
            size=(target_w - 100, None),
            duration=min(video_duration, 3.0),  # Show for max 3 seconds as per strategy
        ).with_position(("center", 80))

        # Compose final video with overlays
        final_video = CompositeVideoClip([final_video, title_shadow, title_clip])

        log.info(f"Exporting video to {output_video}")

        # Export with optimized settings for YouTube Shorts
        final_video.write_videofile(
            str(output_video),
            codec="libx264",
            audio_codec="aac",
            fps=30,
            preset="fast",
            threads=4,
            verbose=False,
            logger=None,
            ffmpeg_params=[
                "-profile:v", "high",
                "-level", "4.0",
                "-pix_fmt", "yuv420p",
                "-b:v", "12M",        # 12 Mbps video bitrate as per strategy
                "-maxrate", "15M",
                "-bufsize", "20M",
                "-b:a", "320k",       # 320 kbps audio as per strategy
                "-ar", "48000",       # 48 kHz audio sample rate
                "-movflags", "+faststart",
            ],
        )

        log.info("basic_effects strategy completed successfully")
        return output_video
        
    except Exception as e:
        log.error(f"Error in basic_effects strategy: {e}")
        raise
    finally:
        # Proper resource cleanup
        try:
            if hasattr(final_video, "close"):
                final_video.close()
            if hasattr(video, "close"):
                video.close()
        except:
            pass  # Ignore cleanup errors


strategies = {"basic_effects": __basic_effects}


def apply_video_effects(
    input_video: Path,
    output_video: Path,
    short: YouTubeShort,
    speech: Speech,
    strategy: EffectsStrategy,
) -> Path:
    video = VideoFileClip(str(input_video))

    return strategies[strategy](video, output_video, short, speech)
