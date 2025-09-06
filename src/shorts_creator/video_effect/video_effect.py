from pathlib import Path
from abc import ABC, abstractmethod
from ffmpeg.nodes import Stream


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
