from pydantic import BaseModel, Field


class SpeechSegment(BaseModel):
    start_time: float = Field(
        description="Start time in seconds from the beginning of the audio"
    )
    end_time: float = Field(
        description="End time in seconds from the beginning of the audio"
    )
    text: str = Field(description="Text content of the segment")


class Speech(BaseModel):
    language: str = Field(description="Language code of the transcript")
    duration_seconds: float = Field(
        description="Total duration of the audio in seconds"
    )
    segments: list[SpeechSegment] = Field(
        description="List of text segments within the video"
    )


class YouTubeShort(BaseModel):
    title: str = Field(description="Catchy title for the short (max 30 characters)")
    subscribe_subtitle: str = Field(
        description="Subtitle encouraging viewers to subscribe (max 50 characters)",
    )
    start_segment_index: int = Field(
        description="Index of the starting segment (0-based)"
    )
    end_segment_index: int = Field(
        description="Index of the ending segment (0-based, inclusive)"
    )
    description: str = Field(
        min_length=300,
        description="Detailed description for the short video (can include hashtags)",
    )
    estimated_duration: str = Field(
        description="Estimated duration of this segment (e.g., '30-60 seconds')"
    )
    tags: list[str] = Field(
        min_length=20,
        max_length=50,
        description="YouTube tags relevant to this short video.",
    )


class YouTubeShortWithSpeech(YouTubeShort):
    speech: list[SpeechSegment] = Field(
        default=[],
        description="Precise speech segments with timestamps for this short",
    )


class YouTubeShortsRecommendation(BaseModel):
    shorts: list[YouTubeShortWithSpeech] = Field(
        description="List of identified YouTube shorts segments"
    )
    total_shorts_found: int = Field(description="Total number of shorts identified")
    analysis_summary: str = Field(description="Overall summary of the analysis")
