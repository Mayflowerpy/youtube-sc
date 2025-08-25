import logging
from pathlib import Path
from faster_whisper import WhisperModel

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

log = logging.getLogger(__name__)


def transcribe_audio():
    """Transcribe audio file to text using faster-whisper and save to text directory."""
    input_file = "data/audios/extracted_audio.mp3"
    output_dir = Path("data/text")
    output_file = output_dir / "extracted_text.txt"
    model_size = "medium"

    # Ensure output directory exists
    output_dir.mkdir(exist_ok=True)

    log.info(f"Loading faster-whisper model: {model_size}")

    try:
        # Load faster-whisper model (automatically uses CoreML on Apple Silicon)
        model = WhisperModel(model_size, device="cpu", compute_type="int8")

        log.info(f"Transcribing audio from {input_file}")

        # Transcribe audio with word-level timestamps (single pass)

        log.info("Starting transcription with progress tracking...")
        segments, info = model.transcribe(
            input_file,
            beam_size=5,
            word_timestamps=True,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
            language="en",  # Force English transcription
        )

        # Process segments with progress tracking and store them
        log.info("Processing transcription segments...")
        full_text = ""
        segment_count = 0
        segments_list = []  # Store segments for later use

        for segment in segments:
            segment_count += 1
            segments_list.append(segment)  # Store the segment
            full_text += segment.text + " "
            current_time = segment.end
            percent = (
                min((current_time / info.duration) * 100, 100)
                if hasattr(info, "duration")
                else 0
            )
            log.info(
                f"Processed {segment_count} segments - Current time: {current_time:.1f}s ({percent:.1f}%)"
            )

        full_text = full_text.strip()
        log.info(f"Completed processing {segment_count} segments")

        # Save transcription to file
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(full_text.strip())

        # Save detailed transcription with word timestamps
        detailed_output = output_dir / "extracted_text_with_timestamps.json"
        import json

        log.info("Building detailed JSON with word timestamps...")
        detailed_data = {
            "language": info.language,
            "language_probability": info.language_probability,
            "duration": info.duration,
            "segments": [],
        }

        # Use stored segments for detailed processing (no second transcription needed)
        log.info(f"Building JSON from {len(segments_list)} stored segments...")

        segment_count = 0
        for segment in segments_list:
            segment_count += 1
            segment_data = {
                "start": segment.start,
                "end": segment.end,
                "text": segment.text,
            }
            detailed_data["segments"].append(segment_data)

            if segment_count % 100 == 0:  # Log every 100 segments for JSON building
                log.info(f"Built JSON for {segment_count} segments...")

        log.info("Saving detailed JSON file...")
        with open(detailed_output, "w", encoding="utf-8") as f:
            json.dump(detailed_data, f, indent=2, ensure_ascii=False)

        log.info(f"Detailed transcription with timestamps saved to {detailed_output}")

        log.info(f"Transcription completed and saved to {output_file}")
        log.info(
            f"Detected language: {info.language} (probability: {info.language_probability:.2f})"
        )
        log.info(f"Transcription preview: {full_text[:100]}...")

    except FileNotFoundError:
        log.error(f"Audio file not found: {input_file}")
        raise
    except Exception as e:
        log.error(f"Error during transcription: {e}")
        raise


if __name__ == "__main__":
    log.info("Starting audio transcription with faster-whisper")
    transcribe_audio()
    log.info("Audio transcription completed")
