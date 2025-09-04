import logging
from pathlib import Path
from moviepy import VideoFileClip, TextClip, CompositeVideoClip
from typing import Any, Literal
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

    current_video: Any = video

    speed_factor = 1.35
    try:
        def time_transform(get_frame, t):
            return get_frame(t * speed_factor)
        
        current_video = current_video.fl(time_transform, apply_to=['mask'])
        if current_video.audio is not None:
            current_video = current_video.with_audio(current_video.audio.fl(lambda gf, t: gf(t * speed_factor), apply_to=[]))
        
        new_duration = current_video.duration / speed_factor
        current_video = current_video.with_duration(new_duration)
        
        log.info(f"Applied speed factor with proper frame sampling: {speed_factor}x")
    except Exception as e:
        log.warning(f"Speed change failed: {e}")
        log.info("Continuing without speed change")

    original_w, original_h = current_video.size
    target_w, target_h = 1080, 1920

    original_ratio = original_w / original_h
    target_ratio = target_w / target_h

    if original_ratio > target_ratio:
        scale_factor = target_w / original_w
        scaled_w = target_w
        scaled_h = int(original_h * scale_factor)
        current_video = current_video.resized((scaled_w, scaled_h))

        y_offset = (target_h - scaled_h) // 2
        current_video = CompositeVideoClip(
            [current_video.with_position(("center", y_offset))],
            size=(target_w, target_h),
        )
    else:
        scale_factor = target_h / original_h
        scaled_w = int(original_w * scale_factor)
        scaled_h = target_h
        current_video = current_video.resized((scaled_w, scaled_h))

        x_offset = (target_w - scaled_w) // 2
        current_video = CompositeVideoClip(
            [current_video.with_position((x_offset, "center"))],
            size=(target_w, target_h),
        )

    final_video: Any = current_video


    video_duration = getattr(final_video, "duration", 30)
    if video_duration is None:
        video_duration = 30
    
    title_text = "Test YouTube Video"
    
    title_shadow = TextClip(
        text=title_text,
        font_size=52,
        color="black",
        method="caption",
        size=(target_w - 100, None),
        duration=video_duration,
    ).with_position(("center", 82))
    
    title_clip = TextClip(
        text=title_text,
        font_size=52,
        color="white",
        stroke_color="black",
        stroke_width=4,
        method="caption",
        size=(target_w - 100, None),
        duration=video_duration,
    ).with_position(("center", 80))
    
    final_video = CompositeVideoClip([final_video, title_shadow, title_clip])

    log.info(f"Exporting video to {output_video}")

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
            "-b:v", "12M",
            "-maxrate", "15M", 
            "-bufsize", "20M",
            "-b:a", "256k",
            "-ar", "48000",
            "-movflags", "+faststart"
        ],
    )

    if hasattr(final_video, "close"):
        final_video.close()
    if hasattr(video, "close"):
        video.close()

    log.info("basic_effects strategy completed")
    return output_video


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
