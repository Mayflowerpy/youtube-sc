from enum import Enum
from shorts_creator.video_effect.video_effect import (
    VideoEffect,
    IncreaseVideoSpeedEffect,
    VideoRatioConversionEffect,
    TextEffect,
    PixelateFilterStartVideoEffect,
    BlurFilterStartVideoEffect,
)
from typing import Sequence


class VideoEffectsStrategy(Enum):
    BASIC = ("basic",)

    def create_effects(self) -> Sequence[VideoEffect]:
        match self:
            case VideoEffectsStrategy.BASIC:
                return [
                    VideoRatioConversionEffect(target_w=1080, target_h=1920),
                    TextEffect(text="New Video", text_align="top"),
                    TextEffect(text="SUBSCRIBE ON ME", text_align="bottom"),
                    BlurFilterStartVideoEffect(blur_strength=20, duration=1.0),
                    IncreaseVideoSpeedEffect(speed_factor=1.5, fps=30),
                ]
            case _:
                raise ValueError(f"Unknown strategy: {self}")
