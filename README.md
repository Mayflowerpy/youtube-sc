# YouTube Shorts Creator

A powerful tool to automatically convert long-form videos into engaging YouTube Shorts using AI analysis and professional video effects.

> 👨‍💻 Want to learn more about the author? Check out [vitaliihonchar.com](https://vitaliihonchar.com/) or the [YouTube channel](https://www.youtube.com/@vhonchar) for more content!

## Features

- 🎯 **AI-Powered Content Analysis** - Uses OpenAI/OpenRouter to identify the best moments for shorts with strict duration requirements
- 🎬 **Professional Video Effects Pipeline** - Automated video enhancement with:
  - 9:16 vertical format conversion with smart cropping/blurred background
  - Audio normalization to YouTube standards (-14 LUFS)
  - Dynamic text overlays (title and captions)
  - Speed adjustment (1.35x default) with pitch preservation
  - High-quality H.264 encoding optimized for mobile viewing
- 📝 **Smart Transcription** - Powered by faster-whisper for accurate speech-to-text with timestamp precision
- 🚀 **YouTube-Ready Metadata** - Automatically generates:
  - SEO-optimized titles and descriptions (300+ characters)
  - 20-50 relevant tags for maximum discoverability
  - Upload-ready content packages with proper formatting
- 📊 **Progress Tracking** - Real-time progress bars for all pipeline operations
- 🎨 **Multiple Video Effect Strategies** - Configurable video processing approaches
- ⚙️ **Highly Configurable** - Comprehensive command-line arguments and environment variables

## Installation

### Prerequisites

- Python 3.13+
- FFmpeg installed on your system
- OpenAI API key (or compatible service like OpenRouter)

### Install the Package

Clone the repository and install as a global tool:

```bash
git clone git@github.com:vitalii-honchar/youtube-shorts-creator.git
cd youtube-shorts-creator
uv tool install -e .
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
YOUTUBE_SHORTS_SHORTS_NUMBER=3
YOUTUBE_SHORTS_SHORT_DURATION_SECONDS=60
YOUTUBE_SHORTS_SPEED_FACTOR=1.35
YOUTUBE_SHORTS_WHISPER_MODEL_SIZE=medium
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
| `--shorts` | `-s` | Number of shorts to generate | 3 |
| `--short-duration` | `-sd` | Minimum duration of each short in seconds | 60 |
| `--duration` | `-d` | Max input video duration to process (seconds) | None (full video) |
| `--strategy` | | Video effects strategy (basic) | basic |
| `--debug` | | Enable debug mode with verbose logging | false |
| `--no-refresh` | `-nr` | Use cached files if available (opposite of refresh) | true |

**Note**: By default, the tool refreshes/regenerates content. Use `-nr` to use cached files.

### Examples

```bash
# Generate 3 shorts with minimum 30 seconds each
shorts-creator -v tutorial.mp4 -s 3 -sd 30

# Process only first 5 minutes of a long video
shorts-creator -v long-lecture.mp4 -d 300 -s 4

# Use cached files (faster processing)
shorts-creator -v content.mp4 -nr

# Process with custom settings and debug mode
shorts-creator -v podcast.mp4 -s 6 -sd 45 -d 1800 --debug

# Use specific video effects strategy
shorts-creator -v demo.mp4 --strategy basic --debug
```

## Output Structure

The tool creates the following directory structure:

```
shorts-creator/                        # Output directory
├── extracted_audio.mp3                # Extracted audio from input video
├── speech.json                       # Transcription with precise timestamps
├── shorts.json                       # AI analysis with metadata
├── captions_0.ass                    # Generated captions for each short
├── captions_1.ass                    
├── short_0.mp4                       # Generated shorts (ready for upload)
├── short_1.mp4
└── ...
```

**Note**: The `poc/` directory contains proof-of-concept experiments and research code, not production functionality.

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

- **Duration Requirements**: Minimum duration enforced (can be 20-30% longer, never shorter)
- **Speed Factor**: `1.35` (35% faster playback while preserving pitch)
- **Audio Standards**: `-14 LUFS` loudness with `-1 dBFS` peak limiting
- **Video Quality**: H.264 High profile, optimized bitrate, 1080x1920 resolution
- **Text Overlays**: Auto-generated titles and subtitle captions (ASS format)
- **Whisper Model**: `medium` or `large` for high-accuracy transcription
- **Video Effects**: Configurable strategies (basic effects pipeline included)

## Effects Pipeline Details

The current **BASIC** strategy includes:

1. **Audio Normalization** - YouTube-standard loudness (-14 LUFS) and peak limiting (-1 dBFS)
2. **Format Conversion** - Smart 9:16 aspect ratio with intelligent content-aware cropping
3. **Text Overlays** - AI-generated titles positioned at top of frame
4. **Caption Generation** - Automatic subtitle creation with precise timing (ASS format)
5. **Visual Effects** - Blur transitions and speed adjustments with pitch preservation
6. **Professional Encoding** - Optimized H.264 output for mobile consumption

Additional strategies can be implemented by extending the `VideoEffectsStrategy` enum.

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
