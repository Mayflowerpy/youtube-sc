import logging
from pathlib import Path
from typing import List
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
            transcript_text = f.read()
    except FileNotFoundError:
        log.error(f"Transcript file not found: {transcript_path}")
        return YouTubeShortsAnalysis(
            shorts=[],
            total_shorts_found=0,
            analysis_summary="Transcript file not found",
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
    
    For each identified segment, provide the exact start and end text from the transcript, the full transcript for that segment, reasoning why it would work as a short, estimated duration, and key topics.
    
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

        return response.choices[0].message.parsed  # type: ignore

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
    transcript_path = Path("data/text/described_text.txt")

    log.info(f"Analyzing transcript: {transcript_path}")
    analysis = analyze_transcript_for_shorts(transcript_path, settings)

    log.info(f"Analysis complete. Found {analysis.total_shorts_found} potential shorts")

    log.info(f"Analysis summary: {analysis.analysis_summary}")
    for i, short in enumerate(analysis.shorts, 1):
        log.info(f"Short {i}: {short.key_topics} ({short.estimated_duration})")

    return analysis


if __name__ == "__main__":
    main()
