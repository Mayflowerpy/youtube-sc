import logging
from pathlib import Path
import ffmpeg
import json
from typing import Literal
from shorts_creator.domain.models import Speech, YouTubeShort
from shorts_creator.assets.fonts import get_font_path

log = logging.getLogger(__name__)

EffectsStrategy = Literal["basic_effects"]


def __basic_effects(
    input_video: Path,
    output_video: Path,
    short: YouTubeShort,
    speech: Speech,
) -> Path:
    log.info("Starting basic_effects strategy with FFmpeg")
    
    try:
        # Get video info to determine aspect ratio and dimensions
        probe = ffmpeg.probe(str(input_video))
        video_stream = next(s for s in probe['streams'] if s['codec_type'] == 'video')
        original_w = int(video_stream['width'])
        original_h = int(video_stream['height'])
        duration = float(video_stream.get('duration', 30))
        
        target_w, target_h = 1080, 1920  # 9:16 vertical format
        log.info(f"Converting from {original_w}x{original_h} to {target_w}x{target_h}")

        original_ratio = original_w / original_h
        target_ratio = target_w / target_h

        # Use specified title
        title_text = "NEW VIDEO"
        
        # Ensure title is not too long (max 50 characters for mobile readability)
        if len(title_text) > 50:
            title_text = title_text[:47] + "..."
        log.info(f"Generated title: '{title_text}'")

        # Apply smooth opening transition instead of grey screen (YouTube Shorts best practice)
        # Use engaging fade-in with scale animation for professional look
        log.info("Applying smooth fade-in opening transition")
        
        # Always start from beginning - we'll use transition to mask any grey screen
        input_stream = ffmpeg.input(str(input_video))
        
        # Apply speed scaling (1.35x)
        speed_factor = 1.35
        log.info(f"Applying speed factor: {speed_factor}x")
        video = input_stream.video.filter('setpts', f'PTS/{speed_factor}')
        audio = input_stream.audio.filter('atempo', speed_factor)

        # Smart reframe to 9:16 with aspect ratio preservation + coordinate calculation
        if original_ratio > target_ratio:
            # Video is wider - fit to width, center vertically (horizontal black bars)
            log.info("Wide video: scaling and centering vertically")
            scale_factor = target_w / original_w
            scaled_h = int(original_h * scale_factor)
            y_offset = (target_h - scaled_h) // 2
            
            # Calculate black bar dimensions for title positioning
            video_content_start_y = y_offset
            video_content_end_y = y_offset + scaled_h
            black_bar_top_height = y_offset
            black_bar_bottom_height = target_h - video_content_end_y
            
            log.info(f"Video content: y={video_content_start_y} to y={video_content_end_y}")
            log.info(f"Black bars: top={black_bar_top_height}px, bottom={black_bar_bottom_height}px")
            
            video = video.filter('scale', target_w, -1).filter('pad', target_w, target_h, 0, '(oh-ih)/2', 'black')
        else:
            # Video is taller or square - fit to height, center horizontally (vertical black bars)
            log.info("Tall/square video: scaling and centering horizontally")
            scale_factor = target_h / original_h
            scaled_w = int(original_w * scale_factor)
            x_offset = (target_w - scaled_w) // 2
            
            # Calculate black bar dimensions for title positioning
            video_content_start_x = x_offset
            video_content_end_x = x_offset + scaled_w
            video_content_start_y = 0  # Full height video
            video_content_end_y = target_h
            black_bar_left_width = x_offset
            black_bar_right_width = target_w - video_content_end_x
            
            # For vertical bars, we can place title at top of video or in side bars
            # We'll use top area which is still safe
            black_bar_top_height = 80  # Safe top area above video content
            
            log.info(f"Video content: x={video_content_start_x} to x={video_content_end_x} (full height)")
            log.info(f"Black bars: left={black_bar_left_width}px, right={black_bar_right_width}px")
            
            video = video.filter('scale', -1, target_h).filter('pad', target_w, target_h, '(ow-iw)/2', 0, 'black')

        # Apply smooth opening transition (YouTube Shorts 2024 best practices)
        transition_duration = 0.6  # 600ms smooth transition - optimal for mobile attention
        log.info(f"Adding {transition_duration}s opening transition: fade-in effect")
        
        # Create engaging entrance effect that masks any grey screen
        # Simple fade-in from black (professional entrance)
        video = video.filter('fade', type='in', duration=transition_duration, start_time=0)

        # Add animated title with word-by-word reveal (YouTube Shorts best practices)
        title_duration = min(duration / speed_factor, 3.0)
        
        # Get bundled Roboto Bold font path
        roboto_font_path = str(get_font_path("roboto-bold"))
        log.info(f"Using font: {roboto_font_path}")
        
        # Split title into words for animation
        words = title_text.split()
        word_delay = 0.4  # 400ms between words for good pacing
        
        # Calculate smart title positioning based on actual black bar dimensions
        if black_bar_top_height > 60:  # Enough space for title in top black bar
            # Center title in top black bar area
            title_y_position = black_bar_top_height // 2 - 15  # Account for font height
            log.info(f"Positioning title in top black bar: y={title_y_position} (bar height: {black_bar_top_height}px)")
        else:
            # Fallback: use safe top area
            title_y_position = 40
            log.info(f"Using fallback title position: y={title_y_position} (insufficient top black bar: {black_bar_top_height}px)")
        
        log.info(f"Animating title '{title_text}' word-by-word with {len(words)} words")
        
        # Animate words with proper timing to avoid overlap
        total_words = len(words)
        
        for i, word in enumerate(words):
            word_start_time = i * word_delay
            # Each text version shows until the next word appears OR until title duration ends
            if i < total_words - 1:
                # Not the last word - show until next word appears
                word_end_time = (i + 1) * word_delay
            else:
                # Last word - show until title duration ends
                word_end_time = title_duration
            
            # Skip if word would start after title duration
            if word_start_time >= title_duration:
                break
            
            # Build the progressive text (show all words up to current word)
            progressive_text = " ".join(words[:i+1])
            
            # Create shadow for current progressive text with fade-in effect
            video = video.filter('drawtext',
                text=progressive_text,
                fontfile=roboto_font_path,
                fontsize=56,
                fontcolor='black',
                x=f'(w-text_w)/2+2',  # Slight offset for shadow
                y=title_y_position + 2,
                enable=f'between(t,{word_start_time},{word_end_time})',
                alpha=f'0.8*min(1,(t-{word_start_time})*10)'  # Faster fade in
            )
            
            # Create main text with fade-in effect
            video = video.filter('drawtext',
                text=progressive_text,
                fontfile=roboto_font_path,
                fontsize=56,
                fontcolor='white',
                x='(w-text_w)/2',
                y=title_y_position,
                borderw=3,
                bordercolor='black',
                enable=f'between(t,{word_start_time},{word_end_time})',
                alpha=f'min(1,(t-{word_start_time})*10)'  # Faster fade in
            )
            
            log.info(f"Word {i+1}/{total_words} '{progressive_text}': {word_start_time:.1f}s to {word_end_time:.1f}s")
        
        log.info(f"Title animation configured: {len(words)} words over {title_duration:.1f}s")

        log.info(f"Exporting video to {output_video}")

        # Export with optimized settings for YouTube Shorts
        output = ffmpeg.output(
            video, audio, str(output_video),
            vcodec='libx264',
            acodec='aac',
            video_bitrate='12M',
            maxrate='15M',
            bufsize='20M',
            audio_bitrate='320k',
            ar=48000,
            profile='high',
            level='4.0',
            pix_fmt='yuv420p',
            movflags='+faststart',
            preset='fast'
        )
        
        try:
            ffmpeg.run(output, overwrite_output=True, capture_stdout=True, capture_stderr=True)
        except ffmpeg.Error as e:
            log.error(f"FFmpeg command failed:")
            log.error(f"stdout: {e.stdout.decode() if e.stdout else 'None'}")
            log.error(f"stderr: {e.stderr.decode() if e.stderr else 'None'}")
            raise

        log.info("basic_effects strategy completed successfully")
        return output_video
        
    except Exception as e:
        log.error(f"Error in basic_effects strategy: {e}")
        raise


strategies = {"basic_effects": __basic_effects}


def apply_video_effects(
    input_video: Path,
    output_video: Path,
    short: YouTubeShort,
    speech: Speech,
    strategy: EffectsStrategy,
) -> Path:
    return strategies[strategy](input_video, output_video, short, speech)
