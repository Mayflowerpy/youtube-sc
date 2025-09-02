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
    current_video = current_video.fl_time(lambda t: t/speed_factor, apply_to=['mask', 'audio'])
    log.info(f"Applied speed factor using time mapping: {speed_factor}x")

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

    if speech and hasattr(speech, "segments"):
        from moviepy import ColorClip

        video_duration = getattr(final_video, "duration", 30)
        if video_duration is None:
            video_duration = 30

        caption_border = (
            ColorClip(
                size=(target_w - 40, 130),
                color=(255, 215, 0),
                duration=video_duration,
            )
            .with_opacity(1.0)
            .with_position(("center", target_h - 180))
        )

        caption_bg = (
            ColorClip(
                size=(target_w - 50, 120), color=(20, 20, 20), duration=video_duration
            )
            .with_opacity(0.95)
            .with_position(("center", target_h - 175))
        )

        caption_clips = []
        for segment in speech.segments:
            if (
                hasattr(segment, "text")
                and hasattr(segment, "start_time")
                and hasattr(segment, "end_time")
            ):
                segment_text = segment.text.strip()
                start_time = float(segment.start_time)
                end_time = float(segment.end_time)
                segment_duration = end_time - start_time

                if segment_text and segment_duration > 0:
                    caption_clip = (
                        TextClip(
                            text=segment_text,
                            font_size=42,
                            color="#FFE135",
                            method="caption",
                            size=(target_w - 80, None),
                            duration=segment_duration,
                        )
                        .with_position(("center", target_h - 145))
                        .with_start(start_time)
                    )

                    caption_clips.append(caption_clip)

        if caption_clips:
            final_video = CompositeVideoClip(
                [final_video, caption_border, caption_bg] + caption_clips
            )
        else:
            fallback_caption = TextClip(
                text="Caption",
                font_size=42,
                color="#FFE135",
                method="caption",
                size=(target_w - 80, None),
                duration=5,
            ).with_position(("center", target_h - 145))

            final_video = CompositeVideoClip(
                [final_video, caption_border, caption_bg, fallback_caption]
            )

    video_duration = getattr(final_video, "duration", 30)
    if video_duration is None:
        video_duration = 30
    
    from moviepy import ColorClip
    
    title_text = "Test YouTube Video"
    
    title_border = (
        ColorClip(
            size=(target_w - 60, 100),
            color=(255, 20, 147),
            duration=min(3.0, video_duration),
        )
        .with_opacity(1.0)
        .with_position(("center", 80))
    )
    
    title_bg = (
        ColorClip(
            size=(target_w - 70, 90),
            color=(30, 30, 30),
            duration=min(3.0, video_duration),
        )
        .with_opacity(0.95)
        .with_position(("center", 85))
    )
    
    title_shadow = TextClip(
        text=title_text,
        font_size=48,
        color="black",
        method="caption",
        size=(target_w - 100, None),
        duration=min(3.0, video_duration),
    ).with_position(("center", 122))
    
    title_clip = TextClip(
        text=title_text,
        font_size=48,
        color="#FF1493",
        stroke_color="white",
        stroke_width=2,
        method="caption",
        size=(target_w - 100, None),
        duration=min(3.0, video_duration),
    ).with_position(("center", 120))
    
    final_video = CompositeVideoClip([final_video, title_border, title_bg, title_shadow, title_clip])

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
