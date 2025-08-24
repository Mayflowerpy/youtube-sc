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
        
        # Transcribe audio
        segments, info = model.transcribe(input_file, beam_size=5)
        
        # Combine all segments into full text
        full_text = " ".join(segment.text for segment in segments)
        
        # Save transcription to file
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(full_text.strip())
        
        log.info(f"Transcription completed and saved to {output_file}")
        log.info(f"Detected language: {info.language} (probability: {info.language_probability:.2f})")
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