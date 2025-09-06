# YouTube Shorts Creator

A powerful tool to automatically convert long-form videos into engaging YouTube Shorts using AI analysis and professional video effects.

## Features

- 🎯 **AI-Powered Content Analysis** - Uses OpenAI/OpenRouter to identify the best moments for shorts
- 🎬 **Professional Video Effects Pipeline** - Automated video enhancement with:
  - 9:16 vertical format conversion with smart cropping/blurred background
  - Audio normalization to YouTube standards (-14 LUFS)
  - Dynamic text overlays (title and subscribe call-to-action)
  - Speed adjustment and visual effects
  - High-quality H.264 encoding
- 📝 **Smart Transcription** - Powered by faster-whisper for accurate speech-to-text
- 📊 **Progress Tracking** - Real-time progress bars for all operations
- ⚙️ **Highly Configurable** - Command-line arguments and environment variables

## Installation

### Prerequisites

- Python 3.13+
- FFmpeg installed on your system
- OpenAI API key (or compatible service like OpenRouter)

### Install the Package

Clone the repository and install in development mode:

```bash
git clone git@github.com:vitalii-honchar/youtube-shorts-creator.git
cd youtube-shorts-creator
uv pip install -e .
```

This creates a global `shorts-creator` command you can run from anywhere.

## Configuration

### Environment Variables

Create a `.env` file in your working directory with the required API key:

```bash
# Required: OpenAI API key
YOUTUBE_SHORTS_OPENAI_API_KEY=your-api-key-here

# Optional: Custom API endpoint (defaults to OpenRouter)
YOUTUBE_SHORTS_OPENAI_BASE_URL=https://openrouter.ai/api/v1

# Optional: Model selection (defaults to gpt-5-mini)
YOUTUBE_SHORTS_MODEL_NAME=openai/gpt-5-mini

# Optional: Default settings
YOUTUBE_SHORTS_SHORTS_NUMBER=5
YOUTUBE_SHORTS_SHORT_DURATION_SECONDS=60
YOUTUBE_SHORTS_SPEED_FACTOR=1.35
```

## Usage

### Basic Usage

```bash
# Process a video with default settings
shorts-creator -v /path/to/your/video.mp4
```

### Command Line Arguments

| Argument | Short | Description | Default |
|----------|-------|-------------|---------|
| `--video` | `-v` | Path to input video file | **Required** |
| `--shorts` | `-s` | Number of shorts to generate | 5 |
| `--short-duration` | `-sd` | Duration of each short in seconds | 60 |
| `--duration` | `-d` | Max input video duration to process (seconds) | None (full video) |
| `--refresh` | `-r` | Force regenerate all content (ignore cache) | false |

### Examples

```bash
# Generate 3 shorts of 30 seconds each
shorts-creator -v tutorial.mp4 -s 3 -sd 30

# Process only first 5 minutes of a long video
shorts-creator -v long-lecture.mp4 -d 300 -s 4

# Force regenerate everything (ignore cached transcripts/analysis)
shorts-creator -v content.mp4 -r

# Process with custom settings
shorts-creator -v podcast.mp4 -s 6 -sd 45 -d 1800
```

## Output Structure

The tool creates the following directory structure:

```
shorts_creator/
├── audios/
│   └── extracted_audio.mp3          # Extracted audio from input
├── text/
│   └── speech.json                  # Transcription with timestamps  
├── shorts/
│   ├── shorts.json                  # AI analysis and metadata
│   └── videos/
│       ├── short_0.mp4             # Generated shorts
│       ├── short_1.mp4
│       └── ...
```

## Advanced Configuration

### Custom AI Models

You can use different AI models by setting environment variables:

```bash
# Use OpenAI directly
YOUTUBE_SHORTS_OPENAI_BASE_URL=https://api.openai.com/v1
YOUTUBE_SHORTS_MODEL_NAME=gpt-4o-mini

# Use local models (if compatible with OpenAI API)
YOUTUBE_SHORTS_OPENAI_BASE_URL=http://localhost:1234/v1
```

### Video Processing Settings

The following settings control video processing quality:

- **Speed Factor**: `1.35` (35% faster playback while preserving pitch)
- **Audio Standards**: `-14 LUFS` loudness with `-1 dBFS` peak limiting
- **Video Quality**: H.264 High profile, 5 Mbps bitrate, 1080x1920 resolution
- **Text Overlays**: Auto-generated titles and subscribe calls-to-action

## Effects Pipeline Details

1. **Audio Normalization** - YouTube-standard loudness and dynamics
2. **Format Conversion** - Smart 9:16 aspect ratio with content-aware cropping
3. **Text Overlays** - AI-generated titles and subscription prompts
4. **Visual Effects** - Blur transitions and speed adjustments  
5. **Professional Encoding** - Optimized H.264 output for social media

## Troubleshooting

### Common Issues

- **FFmpeg not found**: Install FFmpeg and ensure it's in your PATH
- **API key errors**: Check your `.env` file has `YOUTUBE_SHORTS_OPENAI_API_KEY`
- **GPU/CUDA issues**: The tool uses CPU-only processing by default for compatibility
- **Font rendering**: Built-in fonts are included, no system fonts required

### Performance Tips

- Use `-d` to limit processing time for very long videos
- Smaller short durations (`-sd`) process faster
- Consider using faster models for development/testing

## License

This project is a proof-of-concept for educational and research purposes.
