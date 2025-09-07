from pathlib import Path
from abc import ABC, abstractmethod
from typing import Optional, Literal, List
import logging
import re
import tempfile
from ffmpeg.nodes import Stream
from shorts_creator.assets.fonts import get_font_path
import pysubs2
from pysubs2 import SSAFile, SSAEvent, SSAStyle, Alignment, Color
from shorts_creator.domain.models import YouTubeShortWithSpeech


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
        self.font_size = font_size or (65 if text_align == "top" else 51)
        self.font_color = font_color
        self.font_path = str(get_font_path(font_name))
        self.target_w = target_w
        self.target_h = target_h

    def _calculate_y_position(self) -> int:
        """Calculate Y position based on text alignment and black bar information"""
        if self.text_align == "top":
            return 300
        else:
            return self.target_h - 400

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


class CaptionsEffect(VideoEffect):
    def __init__(
        self,
        youtube_short: YouTubeShortWithSpeech,
        font_name: str = "Arial",
        font_size: int = 42,
        font_color: tuple[int, int, int] = (255, 255, 255),
        outline_color: tuple[int, int, int] = (0, 0, 0),
        outline_width: int = 3,
        margin_bottom: int = 120,
        max_chars_per_line: int = 30,
        alignment: Alignment = Alignment.BOTTOM_CENTER,
        bold: bool = True,
        target_w: int = 1080,
        target_h: int = 1920,
    ):
        """
        Generate and apply ASS subtitle captions to video with configurable styling.
        
        Args:
            youtube_short: Short with speech segments
            font_name: Font family name (default: Arial)
            font_size: Font size in pixels (default: 42)
            font_color: RGB color tuple for text (default: white)
            outline_color: RGB color tuple for outline (default: black)
            outline_width: Outline width in pixels (default: 3)
            margin_bottom: Bottom margin in pixels (default: 120)
            max_chars_per_line: Maximum characters per line (default: 30)
            alignment: Text alignment (default: BOTTOM_CENTER)
            bold: Whether to use bold text (default: True)
            target_w: Target video width (default: 1080)
            target_h: Target video height (default: 1920)
        """
        self.youtube_short = youtube_short
        self.font_name = font_name
        self.font_size = font_size
        self.font_color = font_color
        self.outline_color = outline_color
        self.outline_width = outline_width
        self.margin_bottom = margin_bottom
        self.max_chars_per_line = max_chars_per_line
        self.alignment = alignment
        self.bold = bold
        self.target_w = target_w
        self.target_h = target_h
        self.log = logging.getLogger(__name__)
        
        # Create temporary ASS file that OS can clean up
        self.temp_file = tempfile.NamedTemporaryFile(
            mode='w+', 
            suffix='.ass', 
            prefix='captions_', 
            delete=False,
            encoding='utf-8'
        )
        self.output_path = Path(self.temp_file.name)
        
        # Generate the ASS file
        self._generate_ass_file()

    def _wrap_text_for_mobile(self, text: str) -> str:
        """
        Wrap text intelligently for mobile YouTube Shorts captions.
        
        Args:
            text: Text to wrap
        
        Returns:
            Formatted text with \\N line breaks for ASS format (max 2 lines)
        """
        # Clean up text - remove extra spaces and normalize
        text = re.sub(r'\s+', ' ', text.strip())
        
        # If text fits in one line, return as is
        if len(text) <= self.max_chars_per_line:
            return text
        
        # Try to split at natural word boundaries
        words = text.split()
        lines = []
        current_line = ""
        
        for word in words:
            # Check if adding this word would exceed line limit
            test_line = f"{current_line} {word}".strip()
            
            if len(test_line) <= self.max_chars_per_line:
                current_line = test_line
            else:
                # If current line is empty and single word is too long, force break
                if not current_line and len(word) > self.max_chars_per_line:
                    lines.append(word[:self.max_chars_per_line])
                    current_line = word[self.max_chars_per_line:]
                else:
                    # Save current line and start new one
                    if current_line:
                        lines.append(current_line)
                    current_line = word
                    
                    # Limit to 2 lines maximum
                    if len(lines) >= 1:
                        break
        
        # Add remaining text to last line (truncate if necessary)
        if current_line:
            if len(lines) >= 1:
                # We're at the limit - combine remaining text with truncation if needed
                remaining_space = self.max_chars_per_line
                if len(current_line) <= remaining_space:
                    lines.append(current_line)
                else:
                    # Truncate and add ellipsis if needed
                    lines.append(current_line[:remaining_space-1] + "…")
            else:
                lines.append(current_line)
        
        # Ensure we return at most 2 lines and join with ASS line break
        return "\\N".join(lines[:2])

    def _create_style(self) -> SSAStyle:
        """Create ASS style with configurable parameters."""
        return SSAStyle(
            fontname=self.font_name,
            fontsize=self.font_size,
            primarycolor=Color(r=self.font_color[0], g=self.font_color[1], b=self.font_color[2], a=0),
            outlinecolor=Color(r=self.outline_color[0], g=self.outline_color[1], b=self.outline_color[2], a=0),
            outline=self.outline_width,
            shadow=0,  # No shadow (outline provides contrast)
            alignment=self.alignment,
            marginv=self.margin_bottom,
            bold=self.bold,
            encoding=1  # UTF-8 encoding
        )

    def _generate_ass_file(self) -> str:
        """
        Generate ASS subtitle file for the YouTube Short.
        
        Returns:
            ASS file content as string
        """
        self.log.info(f"Generating ASS captions for short: {self.youtube_short.title}")
        
        # Create new SSA file with proper resolution for YouTube Shorts (9:16)
        subs = SSAFile()
        subs.info["Title"] = self.youtube_short.title
        subs.info["PlayResX"] = str(self.target_w)
        subs.info["PlayResY"] = str(self.target_h)
        
        # Add configurable style
        subs.styles["CaptionsStyle"] = self._create_style()
        
        # Calculate timing offset (short's actual start time)
        offset_ms = int(self.youtube_short.start_time * 1000)  # Convert to milliseconds
        
        # Generate subtitle events for each speech segment
        for segment in self.youtube_short.speech:
            if segment.text.strip():  # Skip empty segments
                # Convert to milliseconds and adjust for short offset
                start_ms = int(segment.start_time * 1000) - offset_ms
                end_ms = int(segment.end_time * 1000) - offset_ms
                
                # Ensure positive timing
                start_ms = max(0, start_ms)
                end_ms = max(start_ms + 100, end_ms)  # Minimum 100ms duration
                
                # Wrap text for mobile viewing
                formatted_text = self._wrap_text_for_mobile(segment.text)
                
                # Create subtitle event
                event = SSAEvent(
                    start=start_ms,
                    end=end_ms,
                    text=formatted_text,
                    style="CaptionsStyle"
                )
                
                subs.append(event)
        
        # Save ASS file
        subs.save(str(self.output_path), encoding="utf-8")
        
        # Also return the content as string for debugging/testing
        ass_content = ""
        with open(self.output_path, 'r', encoding='utf-8') as f:
            ass_content = f.read()
        
        self.log.info(f"Generated ASS captions saved to: {self.output_path}")
        self.log.info(f"Generated {len(subs)} subtitle events")
        
        return ass_content

    def apply(self, video_stream: Stream) -> list[Stream]:
        v = video_stream.video
        a = video_stream.audio

        # Use subtitles filter to apply ASS captions
        # This properly handles timing, positioning, styling, and text wrapping
        v = v.filter("subtitles", str(self.output_path))

        return [v, a]
