import logging
from pathlib import Path
from moviepy import VideoFileClip, TextClip, CompositeVideoClip
from moviepy.video.fx import MultiplySpeed, Resize
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
        current_video = current_video.with_fx(MultiplySpeed, speed_factor)
        log.info(f"Applied speed factor: {speed_factor}x")
    except Exception as e:
        log.warning(f"Speed change not supported: {e}")
    
    original_w, original_h = current_video.size
    target_w, target_h = 1080, 1920
    
    original_ratio = original_w / original_h
    target_ratio = target_w / target_h
    
    if original_ratio > target_ratio:
        if original_h >= target_h:
            scale_factor = target_h / original_h
            scaled_w = int(original_w * scale_factor)
            scaled_h = target_h
            
            if scaled_w > target_w:
                current_video = current_video.with_fx(Resize, (scaled_w, scaled_h))
                crop_x = (scaled_w - target_w) // 2
                current_video = current_video.with_fx(current_video.crop, x1=crop_x, x2=crop_x + target_w)
            else:
                current_video = current_video.with_fx(Resize, (scaled_w, scaled_h))
                bg = current_video.with_fx(Resize, (target_w, target_h))
                x_pos = (target_w - scaled_w) // 2
                current_video = CompositeVideoClip([bg, current_video.with_position((x_pos, 0))])
        else:
            current_video = current_video.with_fx(Resize, (target_w, target_h))
    else:
        current_video = current_video.with_fx(Resize, (target_w, target_h))
    
    final_video: Any = current_video.with_fx(Resize, (target_w, target_h))
    
    if speech and hasattr(speech, 'transcript'):
        caption_text = getattr(speech, 'transcript', 'Caption')[:60]
        duration = getattr(final_video, 'duration', 5)
        if duration is None:
            duration = 5
        
        caption_clip = TextClip(
            text=caption_text,
            font_size=42,
            color='white',
            stroke_color='black',
            stroke_width=2,
            duration=min(duration, 5)
        ).with_position(('center', target_h - 200))
        
        final_video = CompositeVideoClip([final_video, caption_clip])
    
    title_attr = getattr(short, 'title', None)
    if title_attr:
        title_text = title_attr[:50]
        title_clip = TextClip(
            text=title_text,
            font_size=36,
            color='white',
            bg_color='black',
            stroke_color='black',
            stroke_width=1,
            duration=1.5
        ).with_position(('center', 120))
        
        final_video = CompositeVideoClip([final_video, title_clip])
    
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
