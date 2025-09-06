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

        # Smart reframe to 9:16 with aspect ratio preservation
        if original_ratio > target_ratio:
            # Video is wider - fit to width, center vertically
            log.info("Wide video: scaling and centering vertically")
            video = video.filter('scale', target_w, -1).filter('pad', target_w, target_h, 0, '(oh-ih)/2', 'black')
        else:
            # Video is taller or square - fit to height, center horizontally
            log.info("Tall/square video: scaling and centering horizontally")  
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
        
        # Position title higher up - between top border and main content area
        title_y_position = 120  # Higher position for better mobile viewing
        
        log.info(f"Animating title '{title_text}' word-by-word with {len(words)} words")
        
        # Animate each word with staggered timing
        for i, word in enumerate(words):
            word_start_time = i * word_delay
            word_end_time = min(word_start_time + title_duration, title_duration)
            
            # Skip if word would start after title duration
            if word_start_time >= title_duration:
                break
            
            # Build the progressive text (show all previous words + current word)
            progressive_text = " ".join(words[:i+1])
            
            # Create shadow for current progressive text with slide-in effect
            video = video.filter('drawtext',
                text=progressive_text,
                fontfile=roboto_font_path,
                fontsize=56,  # Slightly larger for better mobile visibility
                fontcolor='black',
                x=f'(w-text_w)/2+2',  # Slight offset for shadow
                y=title_y_position + 2,
                enable=f'between(t,{word_start_time},{word_end_time})',
                alpha=f'0.8*min(1,(t-{word_start_time})*8)'  # Fade in effect
            )
            
            # Create main text with slide-in and bounce effect
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
                alpha=f'min(1,(t-{word_start_time})*8)'  # Fade in effect
            )
        
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
