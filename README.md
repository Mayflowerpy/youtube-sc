# youtube-shorts-creator

PoC project to convert long YouTube videos into YouTube shorts.

## Effects Pipeline

- Uses `ffmpeg` to cut shorts to requested time ranges.
- Applies optional MoviePy effects (`src/shorts_creator/pipeline/video_effecter.py`):
  - 9:16 vertical format with blurred background
  - Subtle Ken Burns zoom on foreground
  - Timed captions from transcript segments
  - Animated progress bar along the bottom

If MoviePy or system font/rendering is unavailable, the pipeline gracefully skips effects and keeps the raw cut. Enhanced outputs are saved with `_fx` suffix next to the raw cut in `data/shorts/videos`.
