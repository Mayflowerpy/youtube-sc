from enum import Enum
from shorts_creator.video_effect.video_effect import (
    VideoEffect,
    IncreaseVideoSpeedEffect,
)
from typing import Sequence


class VideoEffectsStrategy(Enum):
    BASIC = (
        "basic",
        [
            IncreaseVideoSpeedEffect(speed_factor=1.5, fps=30),
        ],
    )

    def __init__(self, code: str, effects: Sequence[VideoEffect]):
        self.code = code
        self.effects = effects
