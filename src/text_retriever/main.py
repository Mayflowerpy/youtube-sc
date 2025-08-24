import logging
from pathlib import Path
import whisper

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

log = logging.getLogger(__name__)


def transcribe_audio():
    """Transcribe audio file to text using Whisper and save to text directory."""
    input_file = "data/audios/extracted_audio.mp3"
    output_dir = Path("data/text")
    output_file = output_dir / "extracted_text.txt"
    model_size = "medium"
    
    # Ensure output directory exists
    output_dir.mkdir(exist_ok=True)
    
    log.info(f"Loading Whisper model: {model_size}")
    
    try:
        # Load Whisper model
        model = whisper.load_model(model_size)
        
        log.info(f"Transcribing audio from {input_file}")
        
        # Transcribe audio
        result = model.transcribe(input_file)
        
        # Save transcription to file
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(result["text"].strip())
        
        log.info(f"Transcription completed and saved to {output_file}")
        log.info(f"Transcription preview: {result['text'][:100]}...")
        
    except FileNotFoundError:
        log.error(f"Audio file not found: {input_file}")
        raise
    except Exception as e:
        log.error(f"Error during transcription: {e}")
        raise


if __name__ == "__main__":
    log.info("Starting audio transcription")
    transcribe_audio()
    log.info("Audio transcription completed")
