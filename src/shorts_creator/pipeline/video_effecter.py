import logging
from pathlib import Path
import ffmpeg
import json
from typing import Literal
from shorts_creator.domain.models import Speech, YouTubeShort

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

        # Detect and remove grey screen at start
        # Use blackdetect filter to find solid color frames (grey screens)
        # This will detect frames with low pixel variance (solid colors)
        blackdetect_threshold = 0.1  # Adjust for grey detection sensitivity
        log.info("Detecting grey screen at video start")
        
        # First pass: detect grey/black frames at start
        detect_cmd = (
            ffmpeg
            .input(str(input_video))
            .filter('blackdetect', threshold=blackdetect_threshold, duration=0.1)
            .output('pipe:', format='null', loglevel='info')
        )
        
        # Run detection to find where content starts
        try:
            result = ffmpeg.run(detect_cmd, capture_stderr=True, capture_stdout=True)
            stderr_output = result[1].decode('utf-8') if result[1] else ""
            
            # Parse blackdetect output to find first non-grey frame
            start_time = 0.0
            lines = stderr_output.split('\n')
            for line in lines:
                if 'black_end:' in line:
                    # Extract the time when grey screen ends
                    end_time_str = line.split('black_end:')[1].split()[0]
                    start_time = float(end_time_str)
                    log.info(f"Grey screen detected until {start_time}s, trimming start")
                    break
        except Exception as e:
            log.warning(f"Grey screen detection failed, proceeding without trim: {e}")
            start_time = 0.0

        # Build FFmpeg filter chain
        if start_time > 0:
            input_stream = ffmpeg.input(str(input_video), ss=start_time)
            log.info(f"Trimming {start_time}s from start to remove grey screen")
        else:
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

        # Add title overlay with shadow effect (show for max 3 seconds)
        title_duration = min(duration / speed_factor, 3.0)
        
        # Create shadow text with Roboto font
        video = video.filter('drawtext', 
            text=title_text,
            fontfile='/Library/Fonts/Roboto-Bold.ttf',
            fontsize=52,
            fontcolor='black',
            x='(w-text_w)/2',
            y=82,
            enable=f'lt(t,{title_duration})'
        )
        
        # Create main title text with stroke and Roboto font
        video = video.filter('drawtext',
            text=title_text, 
            fontfile='/Library/Fonts/Roboto-Bold.ttf',
            fontsize=52,
            fontcolor='white',
            x='(w-text_w)/2',
            y=80,
            borderw=4,
            bordercolor='black',
            enable=f'lt(t,{title_duration})'
        )

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
        
        ffmpeg.run(output, overwrite_output=True, capture_stdout=True, capture_stderr=True)

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
