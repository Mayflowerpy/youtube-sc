import argparse
import ffmpeg

def speed_up_video(input_file: str, output_file: str, speed: float = 1.35, trim: float = 0.06, fps: int = 30):
    """
    Speed up a video by `speed` while avoiding an initial black/grey flash.

    - Uses one input for both A/V
    - Trims a tiny sliver at start to skip priming frames
    - Resets PTS to 0
    - Normalizes to CFR at `fps`
    """

    inp = ffmpeg.input(input_file, fflags='+genpts')

    # Video: tiny trim, reset PTS, speed up, normalize FPS (CFR)
    v = (
        inp.video
        .filter('trim', start=trim)
        .filter('setpts', f'(PTS-STARTPTS)/{speed}')
        .filter('fps', fps=fps)
    )

    # Audio: tiny trim, reset PTS, speed up
    a = (
        inp.audio
        .filter('atrim', start=trim)
        .filter('asetpts', 'PTS-STARTPTS')
        .filter('atempo', speed)  # 1.35 is within 0.5–2.0
    )

    (
        ffmpeg
        .output(
            v, a, output_file,
            vcodec='libx264',
            acodec='aac',
            video_bitrate='5M',
            audio_bitrate='192k',
            ar=48000,
            pix_fmt='yuv420p',
            preset='fast',
            movflags='+faststart',
            vsync='cfr',                  # enforce CFR at 30 fps
            g=fps * 2,                    # sane GOP
            avoid_negative_ts='make_zero',
            shortest=None                 # stop with the shortest stream
        )
        .overwrite_output()
        .run()
    )

if __name__ == '__main__':
    p = argparse.ArgumentParser(description='Speed up video by 1.35x without initial black frame.')
    p.add_argument('input_file')
    p.add_argument('output_file')
    p.add_argument('--speed', type=float, default=1.35, help='Speed factor (default: 1.35)')
    p.add_argument('--trim', type=float, default=0.06, help='Seconds to trim at start (default: 0.06)')
    p.add_argument('--fps', type=int, default=30, help='Output FPS (default: 30)')
    args = p.parse_args()

    speed_up_video(args.input_file, args.output_file, speed=args.speed, trim=args.trim, fps=args.fps)
