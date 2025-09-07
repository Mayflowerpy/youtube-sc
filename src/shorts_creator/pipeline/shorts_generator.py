import logging
from pathlib import Path
from openai import OpenAI
from shorts_creator.pipeline import storage
from shorts_creator.domain.models import (
    Speech,
    YouTubeShortsRecommendation,
    YouTubeShortWithSpeech,
    YouTubeShort,
)
from pydantic import BaseModel, Field
from shorts_creator.settings.settings import AppSettings

log = logging.getLogger(__name__)


class YouTubeShortsRecommendationResponse(BaseModel):
    shorts: list[YouTubeShort] = Field(
        description="List of identified YouTube shorts segments"
    )
    total_shorts_found: int = Field(description="Total number of shorts identified")
    analysis_summary: str = Field(description="Overall summary of the analysis")


def _format_segments_for_analysis(speech: Speech) -> tuple[str, int]:
    """Format speech segments for LLM analysis."""
    numbered_segments = []
    for i, segment in enumerate(speech.segments):
        duration = segment.end_time - segment.start_time
        numbered_segments.append(
            f"Segment {i}: [{segment.start_time:.1f}s-{segment.end_time:.1f}s, {duration:.1f}s duration] {segment.text}"
        )

    segments_text = "\n".join(numbered_segments)
    total_segments = len(speech.segments)
    return segments_text, total_segments


def _create_system_prompt(
    max_shorts: int,
    max_duration_seconds: float,
) -> str:
    """Create the system prompt for YouTube shorts analysis."""
    return f"""
You are an expert YouTube Shorts content creator specializing in identifying the most engaging segments from long-form video transcripts. Your task is to analyze video transcripts and extract segments that would make compelling YouTube Shorts.

## PRIMARY OBJECTIVE
Identify and extract exactly {max_shorts} YouTube Shorts segments (≤{max_duration_seconds} seconds each) that maximize viewer engagement and retention.

## QUALITY CRITERIA (Ranked by Priority)
1. **Hook Strength**: Segments with immediate attention-grabbing openings (compelling within first 3 seconds)
2. **Self-Containment**: Complete thoughts/concepts that don't require additional context
3. **Engagement Potential**: Content likely to generate comments, shares, saves
4. **Educational Value**: Practical tips, insights, or surprising information
5. **Emotional Impact**: Funny, inspiring, shocking, or thought-provoking moments

## CONTENT PATTERNS TO PRIORITIZE
- Immediate attention-grabbing statements or questions
- Complete mini-stories or anecdotes
- Step-by-step tips or tutorials
- Before/after scenarios or transformations
- Controversial or surprising statements
- Practical advice that stands alone
- Clear value propositions

## OUTPUT REQUIREMENTS
For each identified segment, provide:
- **title**: Catchy title (≤30 characters, action words/numbers preferred)
- **subscribe_subtitle**: Call-to-action subtitle (≤50 characters)
- **description**: YouTube description (≥300 characters) with hook, value, CTA, hashtags
- **tags**: 20-50 relevant YouTube optimization tags
- **start_segment_index**: Starting segment number (0-based)
- **end_segment_index**: Ending segment number (0-based, inclusive) 
- **estimated_duration**: Duration estimate (e.g., "30-45 seconds")

## CRITICAL CONSTRAINTS
- Return EXACTLY {max_shorts} shorts - no exceptions
- Each segment must be ≤{max_duration_seconds} seconds duration
- Rank results by engagement potential (best first)
- If fewer than {max_shorts} high-quality segments exist, lower standards but maintain count requirement
- Use overlapping segments or split longer content if needed to reach {max_shorts}

## CONTENT ANALYSIS INSTRUCTIONS
The video transcript will be provided wrapped in <VIDEO_TRANSCRIPT></VIDEO_TRANSCRIPT> tags. Each segment includes timing information in the format:
"Segment N: [start_time-end_time, duration] transcript_text"

Use timing information to estimate durations and ensure segments fit within the {max_duration_seconds}-second limit.
"""


def _create_user_prompt(segments_text: str, total_segments: int) -> str:
    """Create the user prompt with the video transcript."""
    return f"""
Analyze the following video transcript and identify the best YouTube Shorts segments according to the criteria provided.

Total segments available: {total_segments} (numbered 0 to {total_segments-1})

<VIDEO_TRANSCRIPT>
{segments_text}
</VIDEO_TRANSCRIPT>
"""


def _call_openai_api(
    system_prompt: str, user_prompt: str, settings: AppSettings
) -> YouTubeShortsRecommendationResponse:
    client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)

    response = client.beta.chat.completions.parse(
        model=settings.model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format=YouTubeShortsRecommendationResponse,
        temperature=0.3,
    )

    analysis = response.choices[0].message.parsed

    if analysis is None:
        log.error("Failed to parse response from OpenAI")
        raise ValueError("Response from OpenAI is None")

    return analysis


def _add_timestamps_to_shorts(
    analysis: YouTubeShortsRecommendationResponse, speech: Speech
) -> YouTubeShortsRecommendation:
    shorts = []
    for short in analysis.shorts:
        if (
            short.start_segment_index < 0
            or short.end_segment_index >= len(speech.segments)
            or short.start_segment_index > short.end_segment_index
        ):
            log.warning(
                f"Invalid segment range: {short.start_segment_index}-{short.end_segment_index}"
            )
            continue

        short_with_speech = YouTubeShortWithSpeech.model_validate(
            {
                **short.model_dump(),
                "speech": speech.segments[
                    short.start_segment_index : short.end_segment_index + 1
                ],
                "start_time": speech.segments[short.start_segment_index].start_time,
                "end_time": speech.segments[short.end_segment_index].end_time,
            }
        )
        shorts.append(short_with_speech)

    return YouTubeShortsRecommendation(
        shorts=shorts,
        total_shorts_found=analysis.total_shorts_found,
        analysis_summary=analysis.analysis_summary,
    )


def generate_youtube_shorts_recommendations(
    speech: Speech,
    settings: AppSettings,
    output_file: Path,
) -> YouTubeShortsRecommendation:
    if output_file.exists() and not settings.refresh:
        return YouTubeShortsRecommendation.model_validate_json(
            storage.read(output_file)
        )
    segments_text, total_segments = _format_segments_for_analysis(speech)
    system_prompt = _create_system_prompt(
        settings.shorts_number,
        settings.short_duration_seconds * settings.speed_factor,
    )
    user_prompt = _create_user_prompt(segments_text, total_segments)
    analysis = _call_openai_api(system_prompt, user_prompt, settings)
    res = _add_timestamps_to_shorts(analysis, speech)
    storage.save(output_file, res.model_dump_json(indent=2))
    return res
