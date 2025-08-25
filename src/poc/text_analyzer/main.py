import logging
import json
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from openai import OpenAI

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

log = logging.getLogger(__name__)


class AppSettings(BaseSettings):
    openai_api_key: str
    openai_base_url: str = "https://openrouter.ai/api/v1"
    model_name: str = "deepseek/deepseek-chat"

    class Config:
        env_file = ".env"
        env_prefix = "YOUTUBE_SHORTS_"
        extra = "allow"


class YouTubeShort(BaseModel):
    start_segment_index: int = Field(
        description="Index of the starting segment (0-based)"
    )
    end_segment_index: int = Field(
        description="Index of the ending segment (0-based, inclusive)"
    )
    start_time: float = Field(
        description="Start time in seconds from the beginning of the audio"
    )
    end_time: float = Field(
        description="End time in seconds from the beginning of the audio"
    )
    full_transcript: str = Field(description="Complete transcript text for this short")
    reasoning: str = Field(
        description="Why this segment would make a good YouTube short"
    )
    estimated_duration: str = Field(
        description="Estimated duration of this segment (e.g., '30-60 seconds')"
    )
    key_topics: List[str] = Field(
        description="Main topics or themes covered in this segment"
    )


class VideoTextSegment(BaseModel):
    start_time: float = Field(
        description="Start time in seconds from the beginning of the audio"
    )
    end_time: float = Field(
        description="End time in seconds from the beginning of the audio"
    )
    text: str = Field(description="Text content of the segment")


class VideoText(BaseModel):
    language: str = Field(description="Language code of the transcript")
    duration_seconds: float = Field(
        description="Total duration of the audio in seconds"
    )
    segments: list[VideoTextSegment] = Field(
        description="List of text segments within the video"
    )


class YouTubeShortsAnalysis(BaseModel):
    shorts: List[YouTubeShort] = Field(
        description="List of identified YouTube shorts segments"
    )
    total_shorts_found: int = Field(description="Total number of shorts identified")
    analysis_summary: str = Field(description="Overall summary of the analysis")


def analyze_transcript_for_shorts(
    transcript_path: Path, settings: AppSettings
) -> YouTubeShortsAnalysis:
    """Analyze transcript file to identify potential YouTube shorts segments."""
    try:
        with open(transcript_path, "r", encoding="utf-8") as f:
            transcript_data = VideoText.model_validate_json(json.load(f))

        # Extract plain text for LLM analysis
        transcript_text = ""
        for segment in transcript_data.segments:
            transcript_text += segment.text + " "
        transcript_text = transcript_text.strip()

    except FileNotFoundError:
        log.error(f"Transcript file not found: {transcript_path}")
        return YouTubeShortsAnalysis(
            shorts=[],
            total_shorts_found=0,
            analysis_summary="Transcript file not found",
        )
    except json.JSONDecodeError:
        log.error(f"Invalid JSON format in transcript file: {transcript_path}")
        return YouTubeShortsAnalysis(
            shorts=[],
            total_shorts_found=0,
            analysis_summary="Invalid JSON format in transcript file",
        )

    client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)

    # Create numbered segments for LLM analysis
    numbered_segments = []
    for i, segment in enumerate(transcript_data.segments):
        duration = segment.end_time - segment.start_time
        numbered_segments.append(
            f"Segment {i}: [{segment.start_time:.1f}s-{segment.end_time:.1f}s, {duration:.1f}s duration] {segment.text}"
        )
    
    segments_text = "\n".join(numbered_segments)
    total_segments = len(transcript_data.segments)

    prompt = f"""
    Analyze the following video transcript segments and identify ranges that would make excellent YouTube Shorts (60 seconds or less).
    
    Look for:
    - Self-contained moments with clear beginning and end
    - Engaging hooks or surprising information
    - Practical tips or advice
    - Interesting stories or anecdotes
    - Controversial or thought-provoking statements
    - Educational content that can stand alone
    
    For each identified segment range, provide:
    1. start_segment_index: The starting segment number (0-based)
    2. end_segment_index: The ending segment number (0-based, inclusive)
    3. The full transcript text for those segments combined
    4. Reasoning why this range would work as a short
    5. Estimated duration and key topics
    
    Note: There are {total_segments} segments total (numbered 0 to {total_segments-1}).
    Each segment includes timing information to help you estimate durations.
    
    Segments:
    {segments_text}
    """

    try:
        response = client.beta.chat.completions.parse(
            model=settings.model_name,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert YouTube content creator who specializes in identifying the best moments from long-form videos that would work as engaging YouTube Shorts.",
                },
                {"role": "user", "content": prompt},
            ],
            response_format=YouTubeShortsAnalysis,
            temperature=0.3,
        )

        analysis = response.choices[0].message.parsed  # type: ignore

        # Add precise timestamps to each short using segment indices
        for short in analysis.shorts:
            # Validate segment indices
            if (short.start_segment_index < 0 or 
                short.end_segment_index >= len(transcript_data.segments) or
                short.start_segment_index > short.end_segment_index):
                log.warning(f"Invalid segment range: {short.start_segment_index}-{short.end_segment_index}")
                continue
                
            # Get timestamps from segment indices
            start_segment = transcript_data.segments[short.start_segment_index]
            end_segment = transcript_data.segments[short.end_segment_index]
            
            short.start_time = start_segment.start_time
            short.end_time = end_segment.end_time
            
            # Build full transcript for this range
            segment_texts = []
            for i in range(short.start_segment_index, short.end_segment_index + 1):
                segment_texts.append(transcript_data.segments[i].text)
            short.full_transcript = " ".join(segment_texts).strip()

        return analysis

    except Exception as e:
        log.error(f"Error analyzing transcript: {e}")
        return YouTubeShortsAnalysis(
            shorts=[],
            total_shorts_found=0,
            analysis_summary=f"Error occurred during analysis: {str(e)}",
        )



def main():
    log.info("Starting text analysis for YouTube shorts")

    settings = AppSettings()  # type: ignore
    transcript_path = Path("data/text/extracted_text_with_timestamps.json")

    log.info(f"Analyzing transcript: {transcript_path}")
    analysis = analyze_transcript_for_shorts(transcript_path, settings)

    log.info(f"Analysis complete. Found {analysis.total_shorts_found} potential shorts")

    log.info(f"Analysis summary: {analysis.analysis_summary}")
    for i, short in enumerate(analysis.shorts, 1):
        log.info(f"Short {i}: {short.key_topics} ({short.estimated_duration})")
        log.info(f"  Segments: {short.start_segment_index}-{short.end_segment_index}")
        log.info(f"  Time: {short.start_time:.1f}s - {short.end_time:.1f}s")

    return analysis


if __name__ == "__main__":
    main()
