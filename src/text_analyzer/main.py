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
    start_text: str = Field(description="Starting text of the YouTube short segment")
    end_text: str = Field(description="Ending text of the YouTube short segment")
    start_time: float = Field(description="Start time in seconds from the beginning of the audio")
    end_time: float = Field(description="End time in seconds from the beginning of the audio")
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
            transcript_data = json.load(f)
        
        # Extract plain text for LLM analysis
        transcript_text = ""
        for segment in transcript_data["segments"]:
            transcript_text += segment["text"] + " "
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

    prompt = f"""
    Analyze the following video transcript and identify segments that would make excellent YouTube Shorts (60 seconds or less).
    
    Look for:
    - Self-contained moments with clear beginning and end
    - Engaging hooks or surprising information
    - Practical tips or advice
    - Interesting stories or anecdotes
    - Controversial or thought-provoking statements
    - Educational content that can stand alone
    
    For each identified segment, provide:
    1. The exact start and end text from the transcript
    2. Start and end timestamps in seconds (I'll provide these separately)
    3. The full transcript for that segment
    4. Reasoning why it would work as a short
    5. Estimated duration and key topics
    
    Transcript:
    {transcript_text}
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
        
        # Add precise timestamps to each short by matching text to transcript segments
        for short in analysis.shorts:
            start_time, end_time = find_timestamps_for_text(
                short.start_text, short.end_text, transcript_data
            )
            short.start_time = start_time
            short.end_time = end_time
        
        return analysis

    except Exception as e:
        log.error(f"Error analyzing transcript: {e}")
        return YouTubeShortsAnalysis(
            shorts=[],
            total_shorts_found=0,
            analysis_summary=f"Error occurred during analysis: {str(e)}",
        )


def find_timestamps_for_text(start_text: str, end_text: str, transcript_data: dict) -> tuple[float, float]:
    """Find precise timestamps for start and end text in the transcript data."""
    start_time = 0.0
    end_time = 0.0
    
    # Clean the text for better matching
    start_text_clean = start_text.strip().lower()
    end_text_clean = end_text.strip().lower()
    
    found_start = False
    
    for segment in transcript_data["segments"]:
        segment_text = segment["text"].strip().lower()
        
        # Look for start text
        if not found_start and start_text_clean in segment_text:
            # Try to find word-level timestamp if available
            if "words" in segment and segment["words"]:
                for word in segment["words"]:
                    if start_text_clean.startswith(word["word"].lower().strip()):
                        start_time = word["start"]
                        found_start = True
                        break
            if not found_start:
                start_time = segment["start"]
                found_start = True
        
        # Look for end text
        if found_start and end_text_clean in segment_text:
            # Try to find word-level timestamp if available
            if "words" in segment and segment["words"]:
                for word in reversed(segment["words"]):
                    if end_text_clean.endswith(word["word"].lower().strip()):
                        end_time = word["end"]
                        break
            if end_time == 0.0:
                end_time = segment["end"]
            break
    
    # If we didn't find end_text, use the last segment's end time
    if end_time == 0.0 and transcript_data["segments"]:
        end_time = transcript_data["segments"][-1]["end"]
    
    return start_time, end_time


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
        log.info(f"  Time: {short.start_time:.1f}s - {short.end_time:.1f}s")

    return analysis


if __name__ == "__main__":
    main()
