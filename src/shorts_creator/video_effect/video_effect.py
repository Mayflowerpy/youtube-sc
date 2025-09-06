from pathlib import Path
from abc import ABC, abstractmethod
from typing import Optional, Literal
from ffmpeg.nodes import Stream
from shorts_creator.assets.fonts import get_font_path


class VideoEffect(ABC):

    @abstractmethod
    def apply(self, video_stream: Stream) -> list[Stream]:
        pass


class IncreaseVideoSpeedEffect(VideoEffect):
    def __init__(self, speed_factor: float, fps: int):
        self.speed_factor = speed_factor
        self.fps = fps

    def apply(self, video_stream: Stream) -> list[Stream]:
        v = video_stream.video
        a = video_stream.audio
        v = v.filter("setpts", f"PTS/{self.speed_factor}")
        a = a.filter("atempo", self.speed_factor)
        v = v.filter("fps", fps=self.fps)
        v = v.filter("format", "yuv420p")
        return [a, v]


class VideoRatioConversionEffect(VideoEffect):
    def __init__(self, target_w: int, target_h: int):
        self.target_w = target_w
        self.target_h = target_h

    def apply(self, video_stream: Stream) -> list[Stream]:
        v = video_stream.video
        a = video_stream.audio

        # Calculate target aspect ratio for comparison in filter expressions
        target_ratio = self.target_w / self.target_h

        v = v.filter(
            "scale",
            f"if(gt(iw/ih,{target_ratio}),{self.target_w},-1)",
            f"if(gt(iw/ih,{target_ratio}),-1,{self.target_h})",
        )
        v = v.filter(
            "pad", self.target_w, self.target_h, "(ow-iw)/2", "(oh-ih)/2", "black"
        )

        return [v, a]


class TextEffect(VideoEffect):
    def __init__(
        self,
        text: str,
        text_align: Literal["top", "bottom"],
        font_size: Optional[int] = None,
        font_color: str = "white",
        font_name: str = "roboto-bold",
        target_w: int = 1080,
        target_h: int = 1920,
    ):
        self.text = text
        self.text_align = text_align
        # Set default font sizes based on alignment (matching original implementation)
        self.font_size = font_size or (84 if text_align == "top" else 70)
        self.font_color = font_color
        self.font_path = str(get_font_path(font_name))
        self.target_w = target_w
        self.target_h = target_h

    def _calculate_y_position(self) -> int:
        """Calculate Y position based on text alignment and black bar information"""
        if self.text_align == "top":
            return 150
        else:
            return self.target_h - 300

    def apply(self, video_stream: Stream) -> list[Stream]:
        v = video_stream.video
        a = video_stream.audio

        y_position = self._calculate_y_position()

        # Add text with shadow effect (similar to original implementation)
        # First add black shadow
        v = v.filter(
            "drawtext",
            text=self.text,
            fontfile=self.font_path,
            fontsize=self.font_size,
            fontcolor="black",
            x="(w-text_w)/2+2",
            y=f"{y_position}+2",
            alpha="0.8",
        )

        # Then add main text with border
        v = v.filter(
            "drawtext",
            text=self.text,
            fontfile=self.font_path,
            fontsize=self.font_size,
            fontcolor=self.font_color,
            x="(w-text_w)/2",
            y=str(y_position),
            borderw=3,
            bordercolor="black",
        )

        return [v, a]


class PixelateFilterStartVideoEffect(VideoEffect):
    def __init__(
        self, pixelation_level: int = 20, duration: float = 1.0, steps: int = 10
    ):
        self.pixelation_level = pixelation_level
        self.duration = duration
        self.steps = steps  # Number of pixelation steps for gradual decrease

    def apply(self, video_stream: Stream) -> list[Stream]:
        import ffmpeg

        v = video_stream.video
        a = video_stream.audio

        # Simple approach: apply pixelation to the entire video, then trim segments
        # This avoids dimension mismatch issues by keeping all operations on the same base

        # Get the first segment (pixelated start)
        v_pixelated = (
            v.filter(
                "scale", f"iw/{self.pixelation_level}", f"ih/{self.pixelation_level}"
            )
            .filter(
                "scale",
                f"iw*{self.pixelation_level}",
                f"ih*{self.pixelation_level}",
                flags="neighbor",
            )
            .filter("trim", start=0, end=self.duration)
            .filter("setpts", "PTS-STARTPTS")
        )

        # Get the remaining part (normal quality)
        v_normal = v.filter("trim", start=self.duration).filter(
            "setpts", "PTS-STARTPTS"
        )

        # Concatenate the two parts
        v = ffmpeg.concat(v_pixelated, v_normal, v=1, a=0)

        return [v, a]


class BlurFilterStartVideoEffect(VideoEffect):
    def __init__(self, blur_strength: int = 20, duration: float = 1.0, steps: int = 10):
        self.blur_strength = blur_strength
        self.duration = duration
        self.steps = steps  # Number of blur steps for gradual decrease

    def apply(self, video_stream: Stream) -> list[Stream]:
        import ffmpeg

        v = video_stream.video
        a = video_stream.audio

        # Create gradual blur decrease by creating multiple segments with different blur levels
        step_duration = self.duration / self.steps
        segments = []

        for i in range(self.steps):
            start_time = i * step_duration
            end_time = (i + 1) * step_duration

            # Calculate blur strength for this step (decreases linearly)
            blur_for_step = self.blur_strength * (1 - i / self.steps)

            # Apply blur first, then trim to avoid frame timing issues
            if blur_for_step > 0:
                # Apply blur to the entire video, then trim the segment
                segment = (
                    v.filter("boxblur", blur_for_step)
                    .filter("trim", start=start_time, end=end_time)
                    .filter("setpts", "PTS-STARTPTS")
                )
            else:
                # No blur for this segment, just trim
                segment = v.filter("trim", start=start_time, end=end_time).filter(
                    "setpts", "PTS-STARTPTS"
                )

            segments.append(segment)

        # Add the remaining part of the video (after blur duration) without blur
        remaining_part = v.filter("trim", start=self.duration).filter(
            "setpts", "PTS-STARTPTS"
        )
        segments.append(remaining_part)

        # Concatenate all segments with proper frame alignment
        v = ffmpeg.concat(*segments, v=1, a=0).filter("fps", fps=30)

        return [v, a]


class AudioNormalizationEffect(VideoEffect):
    def __init__(self, target_lufs: float = -14.0, peak_limit: float = -1.0):
        """
        Audio normalization effect for YouTube Shorts standards.

        Args:
            target_lufs: Target loudness in LUFS (-14.0 is YouTube standard)
            peak_limit: Peak limiter in dBFS (-1.0 prevents clipping)
        """
        self.target_lufs = target_lufs
        self.peak_limit = peak_limit

    def apply(self, video_stream: Stream) -> list[Stream]:
        v = video_stream.video
        a = video_stream.audio

        a = a.filter(
            "loudnorm",
            I=str(self.target_lufs),
            LRA="7.0",
            tp=str(self.peak_limit),
        )

        a = a.filter(
            "acompressor",
            threshold="0.1",
            ratio="3",
            attack="5",
            release="50",
            makeup="2",
        )

        a = a.filter("highpass", f="80")

        a = a.filter(
            "deesser",
            i="0.1",
            m="0.5",
            f="0.5",
            s="o",
        )

        return [v, a]
