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
        current_video = current_video.speedx(speed_factor)
        log.info(f"Applied speed factor: {speed_factor}x")
    except Exception as e:
        log.warning(f"Speed change not supported: {e}")
    
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
        bg = CompositeVideoClip([current_video.with_position(('center', y_offset))], size=(target_w, target_h))
        current_video = bg
    else:
        scale_factor = target_h / original_h
        scaled_w = int(original_w * scale_factor)
        scaled_h = target_h
        current_video = current_video.resized((scaled_w, scaled_h))
        
        x_offset = (target_w - scaled_w) // 2
        bg = CompositeVideoClip([current_video.with_position((x_offset, 'center'))], size=(target_w, target_h))
        current_video = bg
    
    final_video: Any = current_video
    
    if speech and hasattr(speech, 'transcript'):
        caption_text = getattr(speech, 'transcript', 'Caption')[:60]
        duration = getattr(final_video, 'duration', 5)
        if duration is None:
            duration = 5
        
        caption_clip = TextClip(
            text=caption_text,
            font_size=48,
            color='white',
            stroke_color='black',
            stroke_width=4,
            method='caption',
            size=(target_w - 100, None),
            duration=min(duration, 5)
        ).with_position(('center', target_h - 300))
        
        shadow_clip = TextClip(
            text=caption_text,
            font_size=48,
            color='black',
            method='caption',
            size=(target_w - 100, None),
            duration=min(duration, 5)
        ).with_position(('center', target_h - 298))
        
        final_video = CompositeVideoClip([final_video, shadow_clip, caption_clip])
    
    title_attr = getattr(short, 'title', None)
    if title_attr:
        title_text = title_attr[:40]
        
        title_bg = TextClip(
            text=title_text,
            font_size=40,
            color='black',
            method='caption',
            size=(target_w - 80, None),
            duration=2.0
        ).with_position(('center', 152))
        
        title_clip = TextClip(
            text=title_text,
            font_size=40,
            color='white',
            stroke_color='black',
            stroke_width=3,
            method='caption',
            size=(target_w - 80, None),
            duration=2.0
        ).with_position(('center', 150))
        
        final_video = CompositeVideoClip([final_video, title_bg, title_clip])
    
    log.info(f"Exporting video to {output_video}")
    
    final_video.write_videofile(
        str(output_video),
        codec='libx264',
        audio_codec='aac',
        fps=30,
        preset='medium',
        ffmpeg_params=[
            '-profile:v', 'high',
            '-level', '4.0',
            '-pix_fmt', 'yuv420p',
            '-b:v', '15M',
            '-maxrate', '20M',
            '-bufsize', '30M',
            '-b:a', '320k',
            '-ar', '48000'
        ]
    )
    
    if hasattr(final_video, 'close'):
        final_video.close()
    if video != final_video and hasattr(video, 'close'):
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
