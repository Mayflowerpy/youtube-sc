import logging
from openai import OpenAI
from shorts_creator.domain.models import Speech, YouTubeShortsRecommendation
from shorts_creator.settings.settings import AppSettings

log = logging.getLogger(__name__)


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


def _create_analysis_prompt(segments_text: str, total_segments: int, max_shorts: int) -> str:
    """Create the prompt for YouTube shorts analysis."""
    return f"""
    Analyze the following video transcript segments and identify ranges that would make excellent YouTube Shorts (30 seconds or less).
    
    QUALITY FIRST: Prioritize high-quality shorts that meet YouTube Shorts best practices. However, you must find the BEST available content from this video - even if it's not perfect, identify the most engaging segments that could work as shorts. Always return at least 1 short unless the content is completely unsuitable.
    
    YouTube Shorts Best Practices (ALL must be met):
    - Hook viewers in first 3 seconds with compelling opening
    - Keep content punchy and fast-paced
    - One clear message or story per short
    - Strong visual storytelling potential
    - High engagement potential (comments, shares, saves)
    - Trending topics or evergreen content
    - Clear call-to-action or cliffhanger ending
    
    Look for segments with:
    - Immediate attention-grabbing openings (strong hook within first 3 seconds)
    - Self-contained moments with clear beginning and end
    - Engaging hooks or surprising information
    - Practical tips or advice that can be consumed quickly
    - Interesting stories or anecdotes (complete mini-stories)
    - Controversial or thought-provoking statements
    - Educational content that can stand alone
    - Emotional moments (funny, inspiring, shocking)
    - Before/after scenarios or transformations
    - Clear value proposition for viewers
    
    TITLE GUIDELINES:
    - Maximum 30 characters - be concise and punchy
    - Start with action words or numbers when possible (e.g., "Fix", "Build", "3 Ways")
    - Focus on the main benefit or outcome
    - Avoid jargon - use simple, clear language
    - Create curiosity or urgency
    
    SUBSCRIBE SUBTITLE GUIDELINES:
    - Maximum 50 characters - encourage subscription
    - Be specific about value (e.g., "Subscribe for more coding tips!")
    - Use action words like "Subscribe", "Follow", "Join"
    - Mention what viewers will get by subscribing
    - Keep it friendly and enthusiastic
    
    CRITICAL REQUIREMENTS:
    - Each short must be 30 seconds or less in duration
    - You MUST return EXACTLY {max_shorts} shorts - no more, no less
    - If there are fewer than {max_shorts} high-quality segments, you must still find {max_shorts} segments by lowering your quality standards slightly
    - Find the BEST available content, but prioritize meeting the exact count requirement
    - Only return fewer than {max_shorts} shorts if the content is completely unsuitable (e.g., just silence, random noise, or completely incoherent)
    - Rank by quality - return the best segments first
    - If you're struggling to find {max_shorts} distinct segments, you can use overlapping segments or split longer segments into smaller parts
    
    For each identified segment range, provide:
    1. title: A catchy, engaging title for the short (maximum 30 characters) that captures the key value or hook
    2. subscribe_subtitle: An encouraging call-to-action subtitle to get viewers to subscribe (maximum 50 characters)
    3. start_segment_index: The starting segment number (0-based)
    4. end_segment_index: The ending segment number (0-based, inclusive)
    5. The full transcript text for those segments combined
    6. Reasoning why this range would work as a short (focus on hook, engagement, and completeness)
    7. Estimated duration (must be ≤30 seconds) and key topics
    
    Note: There are {total_segments} segments total (numbered 0 to {total_segments-1}).
    Each segment includes timing information to help you estimate durations.
    
    Segments:
    {segments_text}
    """


def _call_openai_api(prompt: str, settings: AppSettings) -> YouTubeShortsRecommendation:
    """Make API call to OpenAI for shorts analysis."""
    client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)
    
    response = client.beta.chat.completions.parse(
        model=settings.model_name,
        messages=[
            {
                "role": "system",
                "content": "You are an expert YouTube content creator who specializes in identifying the best moments from long-form videos that would work as engaging YouTube Shorts.",
            },
            {"role": "user", "content": prompt},
        ],
        response_format=YouTubeShortsRecommendation,
        temperature=0.3,
    )

    analysis = response.choices[0].message.parsed
    
    if analysis is None:
        log.error("Failed to parse response from OpenAI")
        return YouTubeShortsRecommendation(
            shorts=[],
            total_shorts_found=0,
            analysis_summary="Failed to parse response from OpenAI",
        )
    
    return analysis


def _add_timestamps_to_shorts(analysis: YouTubeShortsRecommendation, speech: Speech) -> None:
    """Add precise timestamps to each short using segment indices."""
    for short in analysis.shorts:
        # Validate segment indices
        if (
            short.start_segment_index < 0
            or short.end_segment_index >= len(speech.segments)
            or short.start_segment_index > short.end_segment_index
        ):
            log.warning(
                f"Invalid segment range: {short.start_segment_index}-{short.end_segment_index}"
            )
            continue

        # Get timestamps from segment indices
        start_segment = speech.segments[short.start_segment_index]
        end_segment = speech.segments[short.end_segment_index]

        short.start_time = start_segment.start_time
        short.end_time = end_segment.end_time

        # Build full transcript for this range
        segment_texts = []
        for i in range(short.start_segment_index, short.end_segment_index + 1):
            segment_texts.append(speech.segments[i].text)
        short.full_transcript = " ".join(segment_texts).strip()


def generate_youtube_shorts_recommendations(
    speech: Speech, settings: AppSettings
) -> YouTubeShortsRecommendation:
    """Generate YouTube shorts recommendations from speech transcript."""
    try:
        segments_text, total_segments = _format_segments_for_analysis(speech)
        prompt = _create_analysis_prompt(segments_text, total_segments, settings.shorts_number)
        analysis = _call_openai_api(prompt, settings)
        _add_timestamps_to_shorts(analysis, speech)
        return analysis
    except Exception as e:
        log.error(f"Error analyzing transcript: {e}")
        return YouTubeShortsRecommendation(
            shorts=[],
            total_shorts_found=0,
            analysis_summary=f"Error occurred during analysis: {str(e)}",
        )
