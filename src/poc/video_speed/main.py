import argparse
import ffmpeg


def speed_up_clean_mp4(
    input_path: str,
    output_path: str,
    speed: float = 1.35,
    fps: int | None = None,
    micro_trim_sec: float = 0.0,
):
    """
    Speed up video by `speed` while avoiding initial black caused by
    edit lists / re-order delay / timestamp quirks in MP4 players.
    """

    # One input for both audio and video; genpts rebuilds clean PTS
    inp = ffmpeg.input(input_path, fflags="+genpts")

    v = inp.video
    a = inp.audio

    # (Optional) micro-trim a few ms to dodge player head glitches without changing content perceptibly
    if micro_trim_sec > 0:
        v = v.filter("trim", start=micro_trim_sec).filter("setpts", "PTS-STARTPTS")
        a = a.filter("atrim", start=micro_trim_sec).filter("asetpts", "PTS-STARTPTS")

    # Speed change — wiki method
    v = v.filter("setpts", f"PTS/{speed}")
    a = a.filter("atempo", speed)
    v = v.filter("fps", fps=fps)

    # Safer format for broad player compat
    v = v.filter("format", "yuv420p")

    out_kwargs = {
        # Video/audio encoders
        "vcodec": "libx264",
        "acodec": "aac",
        "video_bitrate": "5M",
        "audio_bitrate": "192k",
        "ar": 48000,
        "pix_fmt": "yuv420p",
        "preset": "fast",
        # Make frame 0 immediately displayable
        "force_key_frames": "0:00:00.000",  # IDR at t=0
        "bf": 0,  # disable B-frames (no re-order delay)
        "g": (fps or 30) * 2,  # sane GOP
        # MP4 container behavior
        "movflags": "+faststart",  # relocate moov
        "muxpreload": 0,  # don't preload
        "muxdelay": 0,  # don't delay
        # NOTE: DO NOT set avoid_negative_ts=make_zero here; it can create an empty edit at t=0 on some players
        # Also skip vsync=cfr unless we explicitly chose CFR via fps=
    }

    # Helpful x264 params (stable GOP at the head)
    out_kwargs.update({"x264-params": "scenecut=0:open_gop=0:ref=1"})

    (ffmpeg.output(v, a, output_path, **out_kwargs).overwrite_output().run())


if __name__ == "__main__":
    p = argparse.ArgumentParser(
        description="Speed up video by 1.35x and avoid black at start."
    )
    p.add_argument("input_file")
    p.add_argument("output_file")
    p.add_argument(
        "--speed", type=float, default=1.35, help="Speed factor (default 1.35)"
    )
    p.add_argument(
        "--fps",
        type=int,
        default=30,
        help="Force CFR at this FPS (omit to keep source cadence)",
    )
    p.add_argument(
        "--micro-trim-ms",
        type=float,
        default=0.0,
        help="Micro-trim at start in milliseconds (0–20ms typical)",
    )
    args = p.parse_args()

    speed_up_clean_mp4(
        args.input_file,
        args.output_file,
        speed=args.speed,
        fps=args.fps,
        micro_trim_sec=(args.micro_trim_ms / 1000.0),
    )
