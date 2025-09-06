from enum import Enum
from shorts_creator.video_effect.video_effect import (
    VideoEffect,
    IncreaseVideoSpeedEffect,
    VideoRatioConversionEffect,
)
from typing import Sequence


class VideoEffectsStrategy(Enum):
    BASIC = (
        "basic",
        [
            IncreaseVideoSpeedEffect(speed_factor=1.5, fps=30),
            VideoRatioConversionEffect(target_w=1080, target_h=1920),
        ],
    )

    def __init__(self, code: str, effects: Sequence[VideoEffect]):
        self.code = code
        self.effects = effects
