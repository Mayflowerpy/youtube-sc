# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a YouTube Shorts Creator project - a proof of concept for converting long YouTube videos into YouTube shorts. The project is in early development stage with a basic audio retrieval module.

## Development Environment

- **Python Version**: 3.13 (specified in `.python-version`)
- **Package Manager**: uv (modern Python package manager)
- **Project Structure**: Standard Python package with `pyproject.toml` configuration

## Key Commands

### Package Management
```bash
# Install dependencies
uv sync

# Add new dependency
uv add <package-name>

# Remove dependency
uv remove <package-name>

# Run Python module
uv run python -m src.audio_retriever.main
```

### Running the Application
```bash
# Run the main audio retriever module
uv run python src/audio_retriever/main.py

# Or as a module
uv run python -m src.audio_retriever.main
```

## Project Architecture

### Directory Structure
```
src/
└── audio_retriever/          # Audio processing module
    ├── __init__.py           # Empty package marker
    └── main.py               # Main entry point with logging setup
```

### Current Implementation
- **Single Module**: `audio_retriever` - handles audio extraction/processing
- **Logging**: Centralized logging configuration in main.py with INFO level and timestamp formatting
- **Entry Point**: Basic stub that logs "Retrieve audio" message

### Development Notes
- The project uses modern Python tooling (uv, pyproject.toml)
- Currently minimal implementation - likely needs significant expansion
- No testing framework configured yet
- No dependencies specified in pyproject.toml yet

## Code Conventions
- Standard Python package structure
- Logging configured at INFO level with timestamp formatting
- Module-level logger instances using `__name__`