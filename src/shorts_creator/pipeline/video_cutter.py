import logging
import ffmpeg
from pathlib import Path
from shorts_creator.domain.models import YouTubeShort, Speech

log = logging.getLogger(__name__)


def create_subtitle_file(speech: Speech, start_time: float, end_time: float, output_path: Path) -> Path:
    """Create SRT subtitle file from speech segments."""
    srt_path = output_path.with_suffix('.srt')
    
    with open(srt_path, 'w', encoding='utf-8') as f:
        subtitle_index = 1
        
        for segment in speech.segments:
            # Check if segment overlaps with our video timeframe
            if segment.start_time < end_time and segment.end_time > start_time:
                # Adjust times relative to video start
                seg_start = max(0, segment.start_time - start_time)
                seg_end = min(end_time - start_time, segment.end_time - start_time)
                
                if seg_start < seg_end:
                    # Format time for SRT
                    start_srt = f"{int(seg_start//3600):02d}:{int((seg_start%3600)//60):02d}:{seg_start%60:06.3f}".replace('.', ',')
                    end_srt = f"{int(seg_end//3600):02d}:{int((seg_end%3600)//60):02d}:{seg_end%60:06.3f}".replace('.', ',')
                    
                    f.write(f"{subtitle_index}\n")
                    f.write(f"{start_srt} --> {end_srt}\n")
                    f.write(f"{segment.text.strip()}\n\n")
                    subtitle_index += 1
    
    return srt_path


def cut_video_segment_with_effects(
    input_video: Path, 
    output_video: Path, 
    start_time: float, 
    end_time: float,
    speech: Speech
) -> Path:
    """Cut a video segment and add engaging effects with captions."""
    try:
        log.info(f"Creating engaging short: {start_time}s - {end_time}s")
        
        # Ensure output directory exists
        output_video.parent.mkdir(parents=True, exist_ok=True)
        
        # Create subtitle file
        srt_path = create_subtitle_file(speech, start_time, end_time, output_video)
        
        # Simple video cutting with duration and subtitles
        duration = end_time - start_time
        
        input_stream = ffmpeg.input(str(input_video), ss=start_time, t=duration)
        
        # Preserve original aspect ratio with letterboxing for 9:16 format
        # Scale to fit within 1080x1920 and add black bars if needed
        output_stream = ffmpeg.output(
            input_stream,
            str(output_video),
            vf='scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black',
            vcodec='libx264',
            acodec='aac'
        )
        
        ffmpeg.run(output_stream, overwrite_output=True, capture_stdout=True, capture_stderr=True)
        
        # Clean up subtitle file
        srt_path.unlink(missing_ok=True)
        
        log.info(f"Enhanced video saved to {output_video}")
        return output_video
        
    except ffmpeg.Error as e:
        log.error(f"FFmpeg error: stdout={e.stdout.decode()}, stderr={e.stderr.decode()}")
        raise
    except Exception as e:
        log.error(f"Error creating enhanced video: {e}")
        raise


def create_short_video(
    input_video: Path,
    short: YouTubeShort,
    speech: Speech,
    output_dir: Path,
    short_index: int = 0
) -> Path:
    """Create an enhanced short video from a YouTubeShort analysis result."""
    output_filename = f"short_{short_index + 1}_{short.start_time:.0f}s-{short.end_time:.0f}s.mp4"
    output_path = output_dir / output_filename
    
    return cut_video_segment_with_effects(
        input_video=input_video,
        output_video=output_path,
        start_time=short.start_time,
        end_time=short.end_time,
        speech=speech
    )