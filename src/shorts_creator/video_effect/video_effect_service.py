from pathlib import Path
from shorts_creator.video_effect.video_effect import VideoEffect
from shorts_creator.video_effect.strategies import VideoEffectsStrategy
from logging import getLogger
from datetime import datetime
import ffmpeg
import argparse

logger = getLogger(__name__)


def _create_file_name(
    video_name: str, video_ext: str, effect: VideoEffect, index: int
) -> str:
    return f"{video_name}_{effect.__class__.__name__}_{index}.{video_ext}"


def _write_output_video(video_streams: list[ffmpeg.nodes.Stream], output_file: Path):
    out_kwargs = {
        "vcodec": "libx264",
        "acodec": "aac",
        "video_bitrate": "5M",
        "audio_bitrate": "192k",
        "ar": 48000,
        "pix_fmt": "yuv420p",
        "preset": "fast",
        "force_key_frames": "0:00:00.000",
        "bf": 0,
        "g": 30 * 2,
        "movflags": "+faststart",
        "muxpreload": 0,
        "muxdelay": 0,
        "x264-params": "scenecut=0:open_gop=0:ref=1",
    }
    ffmpeg.output(
        *video_streams, str(output_file), **out_kwargs
    ).overwrite_output().run()


def _delete_old_files(old_video_files: list[Path]):
    for file in old_video_files:
        try:
            file.unlink()
        except Exception as e:
            logger.warning(f"Failed to delete old video file {file}: {e}")


def apply_effects(
    video_path: Path,
    strategy: VideoEffectsStrategy,
    output_dir: Path,
    debug: bool = False,
) -> Path:
    video_name, video_ext = video_path.name.split(".")
    execution_dir = output_dir / str(datetime.now())
    execution_dir.mkdir(parents=True, exist_ok=True)

    curr_video_path = video_path

    effects = strategy.create_effects()

    output_file = None
    old_video_files = []

    for i, effect in enumerate(effects):
        if output_file is not None:
            old_video_files.append(output_file)
        video_stream = ffmpeg.input(str(curr_video_path), fflags="+genpts")

        logger.info(
            f"Applying effect: video_path = {curr_video_path}, effect = {effect}"
        )
        output_file = execution_dir / _create_file_name(
            video_name, video_ext, effect, i
        )
        video_stream = effect.apply(video_stream)
        _write_output_video(video_stream, output_file)
        curr_video_path = output_file

    if not debug:
        _delete_old_files(old_video_files)

    return curr_video_path


if __name__ == "__main__":
    p = argparse.ArgumentParser(
        description="Speed up video by 1.35x and avoid black at start."
    )
    p.add_argument("input_file")
    p.add_argument("output_dir")
    args = p.parse_args()

    apply_effects(
        Path(args.input_file),
        VideoEffectsStrategy.BASIC,
        Path(args.output_dir),
        debug=True,
    )
