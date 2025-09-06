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
        self.font_size = font_size or (56 if text_align == "top" else 42)
        self.font_color = font_color
        self.font_path = str(get_font_path(font_name))
        self.target_w = target_w
        self.target_h = target_h

    def _calculate_y_position(self) -> int:
        """Calculate Y position based on text alignment and black bar information"""
        if self.text_align == "top":
            return 100
        else:
            return self.target_h - 200

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
    def __init__(self, pixelation_level: int = 20, duration: float = 3.0):
        self.pixelation_level = pixelation_level
        self.duration = duration

    def apply(self, video_stream: Stream) -> list[Stream]:
        import ffmpeg
        v = video_stream.video
        a = video_stream.audio

        # Create pixelate effect by splitting video into two parts:
        # 1. Pixelated part for the first duration seconds
        # 2. Normal part for the rest
        
        # Create pixelated version (scale down then up)
        v_pixelated = v.filter(
            "scale", f"iw/{self.pixelation_level}", f"ih/{self.pixelation_level}"
        ).filter(
            "scale", f"iw*{self.pixelation_level}", f"ih*{self.pixelation_level}", flags="neighbor"
        )
        
        # Trim pixelated version to duration and normal version from duration onwards
        v_pixelated_part = v_pixelated.filter("trim", start=0, end=self.duration).filter("setpts", "PTS-STARTPTS")
        v_normal_part = v.filter("trim", start=self.duration).filter("setpts", "PTS-STARTPTS")
        
        # Concatenate the two parts using ffmpeg.concat
        v = ffmpeg.concat(v_pixelated_part, v_normal_part, v=1, a=0)

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
            
            if blur_for_step > 0:
                # Apply blur and trim to step duration
                segment = v.filter("boxblur", blur_for_step).filter(
                    "trim", start=start_time, end=end_time
                ).filter("setpts", "PTS-STARTPTS")
            else:
                # No blur for this segment
                segment = v.filter(
                    "trim", start=start_time, end=end_time
                ).filter("setpts", "PTS-STARTPTS")
            
            segments.append(segment)
        
        # Add the remaining part of the video (after blur duration) without blur
        remaining_part = v.filter("trim", start=self.duration).filter("setpts", "PTS-STARTPTS")
        segments.append(remaining_part)
        
        # Concatenate all segments
        v = ffmpeg.concat(*segments, v=1, a=0)

        return [v, a]