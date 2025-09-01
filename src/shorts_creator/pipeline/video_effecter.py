import logging
from pathlib import Path

from shorts_creator.domain.models import Speech, YouTubeShort

log = logging.getLogger(__name__)


def _overlapping_segments(
    speech: Speech, start_time: float, end_time: float
):
    """Yield (text, rel_start, rel_end) for segments overlapping the window.

    rel_* are relative to start_time.
    """
    for seg in speech.segments:
        if seg.end_time <= start_time or seg.start_time >= end_time:
            continue
        rel_start = max(0.0, seg.start_time - start_time)
        rel_end = min(end_time - start_time, seg.end_time - start_time)
        if rel_end - rel_start > 0.15:  # skip super short fragments
            yield seg.text.strip(), rel_start, rel_end


def apply_video_effects(
    input_video: Path,
    output_video: Path,
    short: YouTubeShort,
    speech: Speech,
) -> Path:
    """Apply YouTube Shorts-friendly effects tailored for coding content.

    Effects:
    - 9:16 vertical formatting with blurred background pillarbox
    - Subtle Ken Burns zoom on foreground
    - Monospace, high-contrast captions with karaoke-style left-to-right reveal
    - Editor-like title bar with traffic-light dots and topic title
    - Animated progress bar at the bottom
    - Quick CTA at the end (subscribe prompt)

    Falls back to returning the original cut if MoviePy is unavailable.
    """
    try:
        from moviepy.editor import (
            VideoFileClip,
            CompositeVideoClip,
            TextClip,
            ColorClip,
            vfx,
            VideoClip,
        )
        import numpy as np
    except Exception as e:  # pragma: no cover - environment fallback
        log.warning(
            "MoviePy not available (%s). Skipping effects and returning original.", e
        )
        return input_video

    try:
        base = VideoFileClip(str(input_video))

        # Target vertical size
        target_w, target_h = 1080, 1920
        duration = float(base.duration)

        # Background: blurred, fills 9:16
        # Use resize twice: first to fit height, then to exact canvas
        bg = (
            base.resize(height=target_h)
            .fx(vfx.gaussian_blur, sigma=25)
            .resize((target_w, target_h))
        )

        # Foreground: scale to fit within 9:16 and add subtle zoom over time
        scale_factor = min(target_w / base.w, target_h / base.h)
        fg = base.resize(scale_factor)
        # 3% zoom over full duration
        fg = fg.fx(vfx.resize, lambda t: 1.0 + 0.03 * (t / max(duration, 1e-6)))

        overlays: list = [fg.set_position("center")]

        # Editor-like top bar across full duration
        try:
            title_bar = (
                ColorClip(size=(target_w, 80), color=(20, 22, 25))
                .set_opacity(0.92)
                .set_duration(duration)
                .set_position((0, 0))
            )
            # Traffic light dots using text bullets to avoid shape drawing
            dot_y = 22
            dot_xs = [24, 64, 104]
            dot_cols = ["#FF605C", "#FFBD44", "#00CA4E"]
            dots = []
            for x, col in zip(dot_xs, dot_cols):
                try:
                    dots.append(
                        TextClip("●", fontsize=46, color=col, font="DejaVu-Sans")
                        .set_start(0)
                        .set_duration(duration)
                        .set_position((x, dot_y))
                    )
                except Exception:
                    pass

            title_text = None
            if short.key_topics:
                title_text = short.key_topics[0][:42]
            elif short.full_transcript:
                title_text = short.full_transcript[:42]
            if title_text:
                try:
                    title = (
                        TextClip(
                            txt=title_text,
                            fontsize=42,
                            color="#E6EDF3",
                            font="DejaVu-Sans",
                            method="label",
                        )
                        .set_start(0)
                        .set_duration(min(duration, duration))
                        .set_position((160, 22))
                    )
                    overlays.extend([title_bar, *dots, title])
                except Exception:
                    overlays.append(title_bar)
            else:
                overlays.append(title_bar)
        except Exception:
            pass

        # Coding-style captions: monospace with karaoke wipe and a soft background panel
        caption_y = int(target_h * 0.8)
        caption_width = int(target_w * 0.92)
        for text, rel_start, rel_end in _overlapping_segments(
            speech, short.start_time, short.end_time
        ):
            start = rel_start
            cap_dur = max(0.35, rel_end - rel_start)
            try:
                # Base (grey) and highlight (white) layers
                base = TextClip(
                    txt=text,
                    fontsize=56,
                    color="#D0D7DE",
                    stroke_color="#000000",
                    stroke_width=1,
                    method="caption",
                    size=(caption_width, None),
                    align="center",
                    font="DejaVu Sans Mono",
                )
                hi = TextClip(
                    txt=text,
                    fontsize=56,
                    color="#FFFFFF",
                    stroke_color="#000000",
                    stroke_width=1,
                    method="caption",
                    size=(caption_width, None),
                    align="center",
                    font="DejaVu Sans Mono",
                )

                # Background panel behind captions
                pad_y = 18
                pad_x = int((target_w - caption_width) / 2)
                bg = (
                    ColorClip(size=(caption_width + 2, base.h + 2 * pad_y), color=(0, 0, 0))
                    .set_opacity(0.35)
                    .set_start(start)
                    .set_duration(cap_dur)
                    .set_position((pad_x - 1, caption_y - pad_y))
                )

                # Karaoke mask for highlight (left-to-right wipe)
                hi_w, hi_h = hi.w, hi.h

                def mask_frame(t):
                    import numpy as _np

                    local_t = max(0.0, min(cap_dur, t))
                    ratio = 0.0 if cap_dur <= 1e-6 else (local_t / cap_dur)
                    w = int(hi_w * ratio)
                    m = _np.zeros((hi_h, hi_w), dtype=float)
                    if w > 0:
                        m[:, :w] = 1.0
                    return m

                mask = (
                    VideoClip(mask_frame, duration=cap_dur)
                    .set_start(start)
                    .set_position((0, 0))
                )
                hi = hi.set_mask(mask)

                base = (
                    base.set_start(start)
                    .set_duration(cap_dur)
                    .set_position(("center", caption_y))
                    .crossfadein(0.06)
                    .crossfadeout(0.06)
                )
                hi = (
                    hi.set_start(start)
                    .set_duration(cap_dur)
                    .set_position(("center", caption_y))
                )

                overlays.extend([bg, base, hi])
            except Exception as ce:
                log.debug("Skipping advanced caption; fallback text. Error: %s", ce)
                try:
                    fallback = (
                        TextClip(
                            txt=text,
                            fontsize=56,
                            color="white",
                            stroke_color="black",
                            stroke_width=2,
                            method="caption",
                            size=(caption_width, None),
                            align="center",
                            font="DejaVu-Sans",
                        )
                        .set_start(start)
                        .set_duration(cap_dur)
                        .set_position(("center", caption_y))
                    )
                    overlays.append(fallback)
                except Exception:
                    pass

        # Animated progress bar along the bottom
        bar_h = 12
        bar_y = target_h - bar_h - 24

        def make_bar(t: float):  # returns HxWx3 uint8 frame
            w = int(target_w * np.clip(t / max(duration, 1e-6), 0.0, 1.0))
            frame = np.zeros((bar_h, target_w, 3), dtype=np.uint8)
            frame[:, :w] = (255, 64, 64)
            return frame

        progress = VideoClip(make_bar, duration=duration).set_position((0, bar_y)).set_opacity(0.9)
        overlays.append(progress)

        # Quick CTA near end
        try:
            cta_dur = min(1.2, duration)
            cta_start = max(0.0, duration - cta_dur)
            cta_w = int(target_w * 0.86)
            cta_h = 120
            cta_x = int((target_w - cta_w) / 2)
            cta_y = int(target_h * 0.12)
            cta_bg = (
                ColorClip(size=(cta_w, cta_h), color=(220, 56, 44))
                .set_opacity(0.88)
                .set_start(cta_start)
                .set_duration(cta_dur)
                .set_position((cta_x, cta_y))
            )
            cta_text = (
                TextClip(
                    txt="Subscribe for more coding tips",
                    fontsize=54,
                    color="white",
                    font="DejaVu-Sans",
                    method="label",
                )
                .set_start(cta_start)
                .set_duration(cta_dur)
                .set_position(("center", cta_y + 26))
            )
            overlays.extend([cta_bg, cta_text])
        except Exception:
            pass

        # Compose with audio from original cut
        final = CompositeVideoClip([bg] + overlays, size=(target_w, target_h))
        if base.audio is not None:
            final = final.set_audio(base.audio)

        output_video.parent.mkdir(parents=True, exist_ok=True)
        final.write_videofile(
            str(output_video),
            fps=30,
            codec="libx264",
            audio_codec="aac",
            preset="medium",
            threads=4,
            verbose=False,
            logger=None,
        )

        # Close clips to free resources
        try:
            final.close()
            base.close()
        except Exception:  # pragma: no cover
            pass

        log.info("Applied video effects to %s", output_video)
        return output_video

    except Exception as e:
        log.error("MoviePy processing failed: %s", e)
        # If something goes wrong, fall back to original
        return input_video
