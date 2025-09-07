from pathlib import Path
from abc import ABC, abstractmethod
from typing import Optional, Literal, List
import logging
import re
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
        output_dir: Path,
        short_index: int,
        font_name: str = "comic-neue-bold",
        font_size: int = 84,
        font_color: tuple[int, int, int] = (255, 255, 255),
        outline_color: tuple[int, int, int] = (0, 0, 0),
        outline_width: int = 5,
        margin_bottom: int = 150,
        max_chars_per_line: int = 20,
        alignment: Alignment = Alignment.BOTTOM_CENTER,
        bold: bool = True,
        target_w: int = 1080,
        target_h: int = 1920,
        enable_word_highlighting: bool = True,
        highlight_color: tuple[int, int, int] = (255, 255, 0),
        dim_color: tuple[int, int, int] = (255, 255, 255),
        use_ffmpeg_captions: bool = True,
    ):
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
        self.enable_word_highlighting = enable_word_highlighting
        self.highlight_color = highlight_color
        self.dim_color = dim_color
        self.use_ffmpeg_captions = use_ffmpeg_captions
        self.log = logging.getLogger(__name__)

        # Get the actual font path
        self.font_path = str(get_font_path(font_name))

        # Create ASS file path in the output directory
        self.output_path = output_dir / f"short_{short_index}_captions.ass"

        # Generate the ASS file
        self._generate_ass_file()

    def _capitalize_sentence(self, text: str) -> str:
        """
        Ensure the first word of the text starts with a capital letter for proper sentences.

        Args:
            text: Input text

        Returns:
            Text with first letter capitalized
        """
        if not text:
            return text

        # Find the first alphabetic character and capitalize it
        text = text.strip()
        if text:
            # Handle cases where text might start with quotes or other punctuation
            for i, char in enumerate(text):
                if char.isalpha():
                    return text[:i] + char.upper() + text[i + 1 :]

        return text

    def _calculate_word_timings(
        self, text: str, start_time: float, end_time: float
    ) -> List[tuple[str, float, float]]:
        """
        Calculate timing for each word in a text segment based on actual speech duration.

        Args:
            text: The text to split into words
            start_time: Segment start time in seconds
            end_time: Segment end time in seconds

        Returns:
            List of (word, word_start_time, word_end_time) tuples
        """
        words = text.split()
        if not words:
            return []

        # Calculate total duration available
        segment_duration = end_time - start_time

        # Handle very short segments - skip word highlighting
        if segment_duration < 0.3:
            return [(text, start_time, end_time)]

        # Calculate weight for each word (longer words take more time)
        word_weights = []
        for word in words:
            # Base weight + character-based weight + punctuation consideration
            base_weight = 1.0
            char_weight = len(word.strip(".,!?;:")) * 0.08
            punct_weight = 0.1 if any(c in word for c in ".,!?;:") else 0
            word_weights.append(base_weight + char_weight + punct_weight)

        total_weight = sum(word_weights)

        # Distribute timing proportionally
        word_timings = []
        current_time = start_time

        for i, (word, weight) in enumerate(zip(words, word_weights)):
            # Calculate word duration based on weight
            word_duration = (weight / total_weight) * segment_duration
            word_end_time = current_time + word_duration

            # Ensure last word ends exactly at segment end
            if i == len(words) - 1:
                word_end_time = end_time

            word_timings.append((word, current_time, word_end_time))
            current_time = word_end_time

        return word_timings

    def _create_highlighted_text(self, words: List[str], highlight_index: int) -> str:
        """
        Create ASS-formatted text with one word highlighted and others dimmed.

        Args:
            words: List of words in the text
            highlight_index: Index of word to highlight (0-based)

        Returns:
            ASS-formatted text with color tags
        """
        if (
            not self.enable_word_highlighting
            or highlight_index < 0
            or highlight_index >= len(words)
        ):
            return " ".join(words)

        # Convert RGB to BGR hex format for ASS (ASS uses BGR, not RGB)
        highlight_hex = f"{self.highlight_color[2]:02X}{self.highlight_color[1]:02X}{self.highlight_color[0]:02X}"
        dim_hex = (
            f"{self.dim_color[2]:02X}{self.dim_color[1]:02X}{self.dim_color[0]:02X}"
        )

        formatted_words = []
        for i, word in enumerate(words):
            if i == highlight_index:
                # Highlighted word - bright white
                formatted_words.append(
                    f"{{\\c&H{highlight_hex}&}}{word}{{\\c&H{dim_hex}&}}"
                )
            else:
                # Dimmed word - gray
                formatted_words.append(word)

        # Apply dimmed color to the entire text, then override highlighted word
        full_text = " ".join(words)
        if highlight_index < len(words):
            # Replace the specific word with highlighted version
            words_before = words[:highlight_index]
            highlighted_word = words[highlight_index]
            words_after = words[highlight_index + 1 :]

            text_before = " ".join(words_before) + (" " if words_before else "")
            text_after = (" " if words_after else "") + " ".join(words_after)

            return f"{{\\c&H{dim_hex}&}}{text_before}{{\\c&H{highlight_hex}&}}{highlighted_word}{{\\c&H{dim_hex}&}}{text_after}"

        return f"{{\\c&H{dim_hex}&}}{full_text}"

    def _wrap_text_for_mobile(self, text: str) -> str:
        """
        Wrap text intelligently for mobile YouTube Shorts captions.
        Preserves ASS color tags and handles them properly.

        Args:
            text: Text to wrap (may contain ASS color tags)

        Returns:
            Formatted text with \\N line breaks for ASS format (max 2 lines)
        """
        # If text contains ASS color tags, handle it carefully
        if "{\\c&H" in text:
            # For highlighted text, don't wrap to avoid breaking color tags
            return text

        # Clean up text - remove extra spaces and normalize
        text = re.sub(r"\s+", " ", text.strip())

        # If text fits in one line, return as is
        if len(text) <= self.max_chars_per_line:
            return text

        # Split into words and build lines with strict 2-line limit
        words = text.split()
        if not words:
            return text

        line1 = ""
        line2 = ""

        # Build first line
        for i, word in enumerate(words):
            test_line = f"{line1} {word}".strip() if line1 else word
            if len(test_line) <= self.max_chars_per_line:
                line1 = test_line
            else:
                # First line is full, start building second line with remaining words
                remaining_words = words[i:]

                # Build second line from remaining words
                for j, remaining_word in enumerate(remaining_words):
                    test_line2 = (
                        f"{line2} {remaining_word}".strip() if line2 else remaining_word
                    )
                    if len(test_line2) <= self.max_chars_per_line:
                        line2 = test_line2
                    else:
                        # Second line would be full, truncate with ellipsis
                        if not line2:
                            # Single word too long for line 2
                            if len(remaining_word) > self.max_chars_per_line - 1:
                                line2 = (
                                    remaining_word[: self.max_chars_per_line - 1] + "…"
                                )
                            else:
                                line2 = remaining_word
                        else:
                            # Add ellipsis to indicate more text
                            if len(line2) < self.max_chars_per_line - 1:
                                line2 += "…"
                        break
                break

        # Return maximum 2 lines
        if line1 and line2:
            return f"{line1}\\N{line2}"
        elif line1:
            return line1
        else:
            return text

    def _create_strict_two_lines(self, text: str) -> tuple[str, str]:
        """
        Create exactly 2 lines of text, no more, no less.

        Args:
            text: Input text

        Returns:
            Tuple of (line1, line2) - both strings, line2 may be empty
        """
        # Clean and split text
        text = text.strip()
        words = text.split()

        if not words:
            return ("", "")

        # If text is short enough for one line, return it as line1
        if len(text) <= self.max_chars_per_line:
            return (text, "")

        line1_words = []
        line2_words = []

        # Build line1
        current_length = 0
        for i, word in enumerate(words):
            test_length = current_length + len(word) + (1 if current_length > 0 else 0)
            if test_length <= self.max_chars_per_line:
                line1_words.append(word)
                current_length = test_length
            else:
                # Remaining words go to line2
                line2_words = words[i:]
                break

        # Build line2 from remaining words
        line2_text = ""
        if line2_words:
            current_length = 0
            final_line2_words = []
            for word in line2_words:
                test_length = (
                    current_length + len(word) + (1 if current_length > 0 else 0)
                )
                if test_length <= self.max_chars_per_line:
                    final_line2_words.append(word)
                    current_length = test_length
                else:
                    # If we can't fit more words, add ellipsis
                    if final_line2_words:
                        # Try to add ellipsis
                        test_with_ellipsis = " ".join(final_line2_words) + "…"
                        if len(test_with_ellipsis) <= self.max_chars_per_line:
                            line2_text = test_with_ellipsis
                        else:
                            line2_text = " ".join(final_line2_words)
                    else:
                        # Single word too long, truncate it
                        if len(word) <= self.max_chars_per_line:
                            line2_text = word
                        else:
                            line2_text = word[: self.max_chars_per_line - 1] + "…"
                    break
            else:
                # All remaining words fit
                line2_text = " ".join(final_line2_words)

        line1_text = " ".join(line1_words)
        return (line1_text, line2_text)

    def _create_style(self) -> SSAStyle:
        """Create ASS style with configurable parameters."""
        # Use font family name for ASS, not file path
        font_family_name = (
            "Comic Neue" if "comic-neue" in self.font_name.lower() else "Roboto"
        )

        return SSAStyle(
            fontname=font_family_name,
            fontsize=self.font_size,
            primarycolor=Color(
                r=self.font_color[0], g=self.font_color[1], b=self.font_color[2], a=0
            ),
            outlinecolor=Color(
                r=self.outline_color[0],
                g=self.outline_color[1],
                b=self.outline_color[2],
                a=0,
            ),
            outline=self.outline_width,
            shadow=0,  # No shadow (outline provides contrast)
            alignment=self.alignment,
            marginv=self.margin_bottom,
            bold=self.bold,
            encoding=1,  # UTF-8 encoding
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

        # Generate subtitle events for each speech segment
        for segment in self.youtube_short.speech:
            if segment.text.strip():  # Skip empty segments
                # Convert to seconds and adjust for short offset
                start_time = segment.start_time - self.youtube_short.start_time
                end_time = segment.end_time - self.youtube_short.start_time

                # Ensure positive timing
                start_time = max(0.0, start_time)
                end_time = max(start_time + 0.1, end_time)  # Minimum 100ms duration

                # Capitalize first letter for proper sentence structure
                capitalized_text = self._capitalize_sentence(segment.text)

                # Wrap text for mobile viewing
                formatted_text = self._wrap_text_for_mobile(capitalized_text)

                if self.enable_word_highlighting:
                    # Generate word-by-word highlighted events
                    word_timings = self._calculate_word_timings(
                        capitalized_text, start_time, end_time
                    )
                    words = capitalized_text.split()

                    # Create overlapping events for each word highlight
                    for word_idx, (_, word_start, word_end) in enumerate(word_timings):
                        # Create highlighted text for this word
                        highlighted_text = self._create_highlighted_text(
                            words, word_idx
                        )
                        wrapped_text = self._wrap_text_for_mobile(highlighted_text)

                        # Convert to milliseconds
                        start_ms = int(word_start * 1000)
                        end_ms = int(word_end * 1000)

                        event = SSAEvent(
                            start=start_ms,
                            end=end_ms,
                            text=wrapped_text,
                            style="CaptionsStyle",
                        )

                        subs.append(event)
                else:
                    # Standard non-highlighted caption
                    start_ms = int(start_time * 1000)
                    end_ms = int(end_time * 1000)

                    event = SSAEvent(
                        start=start_ms,
                        end=end_ms,
                        text=formatted_text,
                        style="CaptionsStyle",
                    )

                    subs.append(event)

        # Save ASS file
        subs.save(str(self.output_path), encoding="utf-8")

        # Also return the content as string for debugging/testing
        ass_content = ""
        with open(self.output_path, "r", encoding="utf-8") as f:
            ass_content = f.read()

        self.log.info(f"Generated ASS captions saved to: {self.output_path}")
        self.log.info(f"Generated {len(subs)} subtitle events")

        return ass_content

    def apply(self, video_stream: Stream) -> list[Stream]:
        v = video_stream.video
        a = video_stream.audio

        if self.use_ffmpeg_captions:
            # Use FFmpeg drawtext filters for strict 2-line control
            return self._apply_ffmpeg_captions(v, a)
        else:
            # Use subtitles filter to apply ASS captions
            v = v.filter("subtitles", str(self.output_path))
            return [v, a]

    def _apply_ffmpeg_captions(self, v: Stream, a: Stream) -> list[Stream]:
        """Apply captions using FFmpeg drawtext filters with strict 2-line control."""

        # Calculate timing offset (short's actual start time)
        offset_time = self.youtube_short.start_time

        # Process each speech segment
        for segment in self.youtube_short.speech:
            if not segment.text.strip():
                continue

            # Calculate timing relative to the short
            start_time = max(0.0, segment.start_time - offset_time)
            end_time = max(start_time + 0.1, segment.end_time - offset_time)

            # Capitalize and create strict 2-line text
            capitalized_text = self._capitalize_sentence(segment.text)
            line1, line2 = self._create_strict_two_lines(capitalized_text)

            if not line1:
                continue

            # Calculate positions for 2 lines
            y1_pos = self.target_h - self.margin_bottom - self.font_size
            y2_pos = self.target_h - self.margin_bottom

            # Apply line 1
            v = v.filter(  # type: ignore
                "drawtext",
                text=line1.replace("'", "\\'").replace(":", "\\:"),
                fontfile=self.font_path,
                fontsize=self.font_size,
                fontcolor="white",
                x="(w-text_w)/2",
                y=str(y1_pos),
                enable=f"between(t,{start_time},{end_time})",
                borderw=self.outline_width,
                bordercolor="black",
            )

            # Apply line 2 if it exists
            if line2:
                v = v.filter(  # type: ignore
                    "drawtext",
                    text=line2.replace("'", "\\'").replace(":", "\\:"),
                    fontfile=self.font_path,
                    fontsize=self.font_size,
                    fontcolor="white",
                    x="(w-text_w)/2",
                    y=str(y2_pos),
                    enable=f"between(t,{start_time},{end_time})",
                    borderw=self.outline_width,
                    bordercolor="black",
                )

        return [v, a]
