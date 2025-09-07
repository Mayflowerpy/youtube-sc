from enum import Enum
from pathlib import Path
from typing import Optional, Sequence
from shorts_creator.video_effect.video_effect import (
    VideoEffect,
    IncreaseVideoSpeedEffect,
    VideoRatioConversionEffect,
    TextEffect,
    BlurFilterStartVideoEffect,
    AudioNormalizationEffect,
    CaptionsEffect,
)
from shorts_creator.domain.models import YouTubeShortWithSpeech


class VideoEffectsStrategy(Enum):
    BASIC = "basic"
    CAPTIONS = "captions"

    def create_effects(
        self,
        short: YouTubeShortWithSpeech,
        speed_factor: float,
        captions_path: Optional[Path] = None,
    ) -> Sequence[VideoEffect]:
        match self:
            case VideoEffectsStrategy.BASIC:
                return [
                    AudioNormalizationEffect(target_lufs=-14.0, peak_limit=-1.0),
                    VideoRatioConversionEffect(target_w=1080, target_h=1920),
                    TextEffect(text=short.title, text_align="top"),
                    TextEffect(text=short.subscribe_subtitle, text_align="bottom"),
                    BlurFilterStartVideoEffect(blur_strength=20, duration=1.0),
                    IncreaseVideoSpeedEffect(speed_factor=speed_factor, fps=30),
                ]
            case VideoEffectsStrategy.CAPTIONS:
                return [CaptionsEffect(youtube_short=short)]
            case _:
                raise ValueError(f"Unknown strategy: {self}")
