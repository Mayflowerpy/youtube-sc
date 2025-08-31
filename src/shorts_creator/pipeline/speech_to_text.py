import logging
from pathlib import Path
from faster_whisper import WhisperModel
from shorts_creator.domain.models import Speech, SpeechSegment
from shorts_creator.pipeline import storage

log = logging.getLogger(__name__)


def convert_speech_to_text(
    audio_file: Path, output_file: Path, refresh: bool
) -> Speech:
    if output_file.exists() and not refresh:
        return Speech.model_validate_json(storage.read(output_file))

    model_size = "medium"

    log.info(f"Loading faster-whisper model: {model_size}")

    try:
        # Load faster-whisper model (automatically uses CoreML on Apple Silicon)
        model = WhisperModel(model_size, device="cpu", compute_type="int8")

        log.info(f"Transcribing audio from {audio_file}")

        # Transcribe audio with word-level timestamps
        segments, info = model.transcribe(
            str(audio_file),
            beam_size=5,
            word_timestamps=True,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
            language="en",
        )

        # Process segments and build Speech object
        log.info("Processing transcription segments...")
        speech_segments = []

        for segment in segments:
            speech_segment = SpeechSegment(
                start_time=segment.start,
                end_time=segment.end,
                text=segment.text.strip(),
            )
            speech_segments.append(speech_segment)

        speech = Speech(
            language=info.language,
            duration_seconds=info.duration,
            segments=speech_segments,
        )

        log.info(
            f"Transcription completed: {len(speech_segments)} segments, {info.duration:.1f}s duration"
        )

        storage.save(output_file, speech.model_dump_json(indent=2))
        return speech

    except FileNotFoundError:
        log.error(f"Audio file not found: {audio_file}")
        raise
    except Exception as e:
        log.error(f"Error during transcription: {e}")
        raise
