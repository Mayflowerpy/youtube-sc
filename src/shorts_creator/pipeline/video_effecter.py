import logging
from pathlib import Path
import ffmpeg
import json
from typing import Literal
from shorts_creator.domain.models import Speech, YouTubeShort
from shorts_creator.assets.fonts import get_font_path

log = logging.getLogger(__name__)

EffectsStrategy = Literal["basic_effects"]


def _get_video_dimensions(input_video: Path):
    probe = ffmpeg.probe(str(input_video))
    video_stream = next(s for s in probe["streams"] if s["codec_type"] == "video")

    duration = video_stream.get("duration")
    if duration is None:
        format_info = probe.get("format", {})
        duration = format_info.get("duration")

    if duration is None:
        raise ValueError(f"Could not determine video duration for {input_video}")

    return {
        "width": int(video_stream["width"]),
        "height": int(video_stream["height"]),
        "duration": float(duration),
    }


def _calculate_aspect_ratio_conversion(
    original_w: int, original_h: int, target_w: int, target_h: int
):
    original_ratio = original_w / original_h
    target_ratio = target_w / target_h

    if original_ratio > target_ratio:
        scale_factor = target_w / original_w
        scaled_h = int(original_h * scale_factor)
        y_offset = (target_h - scaled_h) // 2
        return {
            "is_wide": True,
            "black_bar_top_height": y_offset,
            "black_bar_bottom_height": target_h - (y_offset + scaled_h),
            "video_content_start_y": y_offset,
            "video_content_end_y": y_offset + scaled_h,
        }
    else:
        scale_factor = target_h / original_h
        scaled_w = int(original_w * scale_factor)
        x_offset = (target_w - scaled_w) // 2
        return {
            "is_wide": False,
            "black_bar_top_height": 80,
            "black_bar_left_width": x_offset,
            "black_bar_right_width": target_w - (x_offset + scaled_w),
            "video_content_start_x": x_offset,
            "video_content_end_x": x_offset + scaled_w,
        }


def _apply_speed_scaling(input_stream, speed_factor: float):
    video = input_stream.video.filter("setpts", f"PTS/{speed_factor}")
    audio = input_stream.audio.filter("atempo", speed_factor)
    return video, audio


def _apply_aspect_ratio_conversion(
    video, conversion_info: dict, target_w: int, target_h: int
):
    if conversion_info["is_wide"]:
        log.info("Wide video: scaling and centering vertically")
        return video.filter("scale", target_w, -1).filter(
            "pad", target_w, target_h, 0, "(oh-ih)/2", "black"
        )
    else:
        log.info("Tall/square video: scaling and centering horizontally")
        return video.filter("scale", -1, target_h).filter(
            "pad", target_w, target_h, "(ow-iw)/2", 0, "black"
        )


def _detect_and_trim_grey_screen(input_video: Path):
    try:
        detect_cmd = (
            ffmpeg.input(str(input_video))
            .filter("blackdetect", threshold=0.3, duration=0.2)
            .output("pipe:", format="null", loglevel="info")
        )

        result = ffmpeg.run(detect_cmd, capture_stderr=True, capture_stdout=True)
        stderr_output = result[1].decode("utf-8") if result[1] else ""

        for line in stderr_output.split("\n"):
            if "black_end:" in line and "black_start:0" in line:
                end_time_str = line.split("black_end:")[1].split()[0]
                detected_time = float(end_time_str)
                if detected_time >= 0.2:
                    return detected_time + 0.1
        return 0.0
    except Exception:
        return 0.0


def _apply_pixelate_transition(video, duration: float):
    # Use geq filter for time-based pixelate effect that works with expressions
    return video.filter(
        'geq',
        lum=f'if(lt(t,{duration}), lum(floor(X/20)*20, floor(Y/20)*20), lum(X,Y))',
        cb=f'if(lt(t,{duration}), cb(floor(X/20)*20, floor(Y/20)*20), cb(X,Y))', 
        cr=f'if(lt(t,{duration}), cr(floor(X/20)*20, floor(Y/20)*20), cr(X,Y))'
    )


def _calculate_title_position(black_bar_top_height: int):
    if black_bar_top_height > 60:
        return black_bar_top_height // 2 - 15
    return 40


def _calculate_subscribe_position(conversion_info: dict, target_h: int):
    if conversion_info["is_wide"] and conversion_info["black_bar_bottom_height"] > 60:
        return target_h - conversion_info["black_bar_bottom_height"] // 2 - 15
    return target_h - 80


def _apply_title_animation(
    video, title_text: str, title_y_position: int, title_duration: float, font_path: str
):
    words = title_text.split()
    word_delay = 0.8
    total_words = len(words)

    for i, word in enumerate(words):
        word_start_time = i * word_delay
        word_end_time = (i + 1) * word_delay if i < total_words - 1 else title_duration

        if word_start_time >= title_duration:
            break

        progressive_text = " ".join(words[: i + 1])

        video = video.filter(
            "drawtext",
            text=progressive_text,
            fontfile=font_path,
            fontsize=56,
            fontcolor="black",
            x=f"(w-text_w)/2+2",
            y=title_y_position + 2,
            enable=f"between(t,{word_start_time},{word_end_time})",
            alpha=f"0.8*min(1,(t-{word_start_time})*10)",
        )

        video = video.filter(
            "drawtext",
            text=progressive_text,
            fontfile=font_path,
            fontsize=56,
            fontcolor="white",
            x="(w-text_w)/2",
            y=title_y_position,
            borderw=3,
            bordercolor="black",
            enable=f"between(t,{word_start_time},{word_end_time})",
            alpha=f"min(1,(t-{word_start_time})*10)",
        )

    return video


def _apply_static_subscribe_text(
    video, subscribe_y_position: int, video_duration: float, font_path: str
):
    subscribe_text = "SUBSCRIBE ON ME"

    video = video.filter(
        "drawtext",
        text=subscribe_text,
        fontfile=font_path,
        fontsize=42,
        fontcolor="black",
        x=f"(w-text_w)/2+2",
        y=subscribe_y_position + 2,
        enable=f"lt(t,{video_duration})",
        alpha="0.8",
    )

    video = video.filter(
        "drawtext",
        text=subscribe_text,
        fontfile=font_path,
        fontsize=42,
        fontcolor="white",
        x="(w-text_w)/2",
        y=subscribe_y_position,
        borderw=3,
        bordercolor="black",
        enable=f"lt(t,{video_duration})",
    )

    return video


def _export_video(video, audio, output_path: Path):
    output = ffmpeg.output(
        video,
        audio,
        str(output_path),
        vcodec="libx264",
        acodec="aac",
        video_bitrate="12M",
        audio_bitrate="320k",
        ar=48000,
        pix_fmt="yuv420p",
        preset="fast",
    )

    try:
        ffmpeg.run(
            output, overwrite_output=True, capture_stdout=True, capture_stderr=True
        )
    except ffmpeg.Error as e:
        log.error(f"FFmpeg command failed:")
        log.error(f"stdout: {e.stdout.decode() if e.stdout else 'None'}")
        log.error(f"stderr: {e.stderr.decode() if e.stderr else 'None'}")
        raise


def __basic_effects(
    input_video: Path,
    output_video: Path,
) -> Path:
    log.info("Starting basic_effects strategy with FFmpeg")

    try:
        dimensions = _get_video_dimensions(input_video)
        target_w, target_h = 1080, 1920

        conversion_info = _calculate_aspect_ratio_conversion(
            dimensions["width"], dimensions["height"], target_w, target_h
        )

        # Disable grey screen detection to isolate black screen source
        # grey_screen_duration = _detect_and_trim_grey_screen(input_video)
        #
        # if grey_screen_duration > 0:
        #     input_stream = ffmpeg.input(str(input_video), ss=grey_screen_duration)
        #     log.info(f"Trimming {grey_screen_duration}s grey screen from start")
        # else:
        #     input_stream = ffmpeg.input(str(input_video))
        input_stream = ffmpeg.input(str(input_video))

        speed_factor = 1.35

        video, audio = _apply_speed_scaling(input_stream, speed_factor)
        video = _apply_aspect_ratio_conversion(
            video, conversion_info, target_w, target_h
        )
        video = _apply_pixelate_transition(video, 3.0)

        title_text = "NEW VIDEO"
        title_duration = dimensions["duration"] / speed_factor
        title_y_position = _calculate_title_position(
            conversion_info["black_bar_top_height"]
        )
        subscribe_y_position = _calculate_subscribe_position(conversion_info, target_h)
        font_path = str(get_font_path("roboto-bold"))

        # Disable title and subscribe text to isolate black screen source
        video = _apply_title_animation(
            video, title_text, title_y_position, title_duration, font_path
        )
        video = _apply_static_subscribe_text(
            video, subscribe_y_position, title_duration, font_path
        )

        _export_video(video, audio, output_video)

        log.info("basic_effects strategy completed successfully")
        return output_video

    except Exception as e:
        log.error(f"Error in basic_effects strategy: {e}")
        raise


strategies = {"basic_effects": __basic_effects}


def apply_video_effects(
    input_video: Path,
    output_video: Path,
    strategy: EffectsStrategy,
) -> Path:
    return strategies[strategy](input_video, output_video)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Apply video effects to create YouTube Shorts"
    )
    parser.add_argument("input_video", type=Path, help="Path to input video file")
    parser.add_argument("output_video", type=Path, help="Path to output video file")
    parser.add_argument(
        "--strategy",
        type=str,
        choices=["basic_effects"],
        default="basic_effects",
        help="Effects strategy to apply",
    )

    args = parser.parse_args()

    try:
        result = apply_video_effects(
            input_video=args.input_video,
            output_video=args.output_video,
            strategy=args.strategy,
        )
        print(f"Video processing completed: {result}")
    except Exception as e:
        print(f"Error processing video: {e}")
        exit(1)
