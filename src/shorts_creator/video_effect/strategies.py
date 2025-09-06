from enum import Enum
from shorts_creator.video_effect.video_effect import (
    VideoEffect,
    IncreaseVideoSpeedEffect,
    VideoRatioConversionEffect,
    TextEffect,
    BlurFilterStartVideoEffect,
)
from shorts_creator.domain.models import YouTubeShort
from typing import Sequence


class VideoEffectsStrategy(Enum):
    BASIC = ("basic",)

    def create_effects(self, short: YouTubeShort) -> Sequence[VideoEffect]:
        match self:
            case VideoEffectsStrategy.BASIC:
                return [
                    VideoRatioConversionEffect(target_w=1080, target_h=1920),
                    TextEffect(text=short.title, text_align="top"),
                    TextEffect(text=short.subscribe_subtitle, text_align="bottom"),
                    BlurFilterStartVideoEffect(blur_strength=20, duration=1.0),
                    IncreaseVideoSpeedEffect(speed_factor=1.5, fps=30),
                ]
            case _:
                raise ValueError(f"Unknown strategy: {self}")
