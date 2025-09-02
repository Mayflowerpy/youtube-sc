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

# YouTube Shorts Clip Effects — Requirements (Software Engineering Channel)

This document defines **must/should** requirements for producing fast, legible, and rewatchable YouTube Shorts tailored to software‑engineering topics (code, CLI, APIs). Treat it as a checklist for scripting, editing, and QC.

---

## 1) Core Objectives

* **Clarity first:** Make the key idea understandable on a 6–6.7″ phone screen in noisy environments.
* **Retention:** Reset attention every **2–3 seconds** with a visual change (cut, zoom, highlight, overlay, B‑roll).
* **Replay loop:** The last **0.5–1.0 s** visually or verbally matches the opening to encourage automatic replays.

**Acceptance metrics (targets):**

* Average watch time ≥ **70%** of clip length.
* Rewatches (loops) ≥ **10%** of views for educational Shorts.
* Swipe‑away in first 3 s ≤ **25%**.

---

## 2) Technical Specs

* **Aspect & Resolution:** **9:16**, **1080×1920** (deliver in vertical sequence; no rotation hacks).
* **FPS:** 30 or 60 FPS. Use 60 FPS for cursor‑heavy UI or fast scrolling.
* **Codec/Container:** H.264 (High profile), MP4.
* **Bitrate target:** 12–20 Mbps VBR.
* **Audio:** AAC, 48 kHz, 320 kbps.
* **Safe areas:** Keep essential text/UI **≥130 px** from bottom/top edges to avoid UI overlays.

---

## 3) Visual Language & Effects (Required Behaviors)

### 3.1 Cuts & Pacing (MUST)

* **Hook in 1–2 s**: present the payoff or problem immediately.
* **Jump cuts** to remove all hesitations; no pauses > **300 ms** without a purposeful visual.
* **Cut cadence:** a visible change every **2–3 s** (hard cut, zoom, overlay swap, highlight move).

### 3.2 Zooms & Punch‑ins (SHOULD)

* **Punch‑in** on the important line/UI element: scale from **100%→115–135%** over **6–12 frames**.
* Keep **anchor** on the focal element (no drifting).
* Do not exceed **140%** total scale to avoid softness.

### 3.3 Speed Ramps (SHOULD)

* Use **1.25×–1.5×** on scrolling or typing sections.
* Ramp in/out over **4–6 frames**; avoid abrupt stutters.

### 3.4 Transitions (MUST)

* Prefer **hard cuts** or **cut‑on‑action**. Fancy wipes/whirls are disallowed.
* **SFX markers** (optional): 6–8 frame whoosh/pop to signal "before→after". Keep tasteful.

### 3.5 Overlays (MUST)

* **Highlight box** around code line/API parameter.
  * Border **4 px**, corner radius **8 px**, outer drop shadow (soft, subtle).
  * **Dim rest**: add a 60–75% blur/darken outside the highlight for 0.4–0.6 s during callouts.
* **Cursor halo** for clicks: radius **24–32 px**, 200–300 ms fade.
* **Keystroke overlay** (for CLI): monospace, top‑center, auto‑hide after **1.2–1.8 s**.

---

## 4) Code & UI Readability (MUST)

* **Editor theme:** high‑contrast light or dark; avoid low‑contrast "aesthetic" themes.
* **Font:** Monospace; **min 44 px** at 1080×1920 for primary code. Line height **1.2–1.3**.
* **Line focus:** use a left rule or background tint to mark the active line.
* **Scrolling:** page‑at‑a‑time or snap‑to‑line; never free‑scroll mid‑explanation.
* **Colors:** Do not rely on color alone; pair with underline/box for accessibility.

---

## 5) Captions/Subtitles (MUST)

* **Always present** (burn‑in or edited auto‑captions).
* **Casing:** Sentence case; avoid camelCase breaks across lines.
* **Layout:** Max **2 lines**, **28–32 characters/line**.
* **Placement:** Above bottom safe area; never cover code or key UI.
* **Style:** High contrast. Stroke **2–3 px** or soft drop shadow. No animated karaoke except selective **word‑highlight** synced to speech.

---

## 6) Audio, Music, and SFX

* **Voice is king** (MUST):
  * Peak ‑3 to ‑1 dBFS, average around **‑16 LUFS** for speech clarity.
  * Remove hums; gate light‑handedly to avoid pumping.
* **Music** (OPTIONAL, default OFF for heavy code demos):
  * Low‑key bed at **‑25 to ‑30 dBFS relative to voice**; duck under narration.
  * No lyrical vocals during explanations.
* **SFX** (SPARING): clicks/whooshes under **‑12 dBFS** peaks; never mask consonants.

---

## 7) Graphics & Typography

* **Brand kit:** consistent colors (≤1 primary, 1 accent), logo usage ≤ **1.0 s** in the hook or not at all.
* **Text cards:** max **6–10 words**; animate in ≤ **250 ms**.
* **Do not** use heavy gradients, drop‑shadows, or busy backgrounds behind small code.

---

## 8) Narrative Structure (MUST)

**Template:** Hook (≤2 s) → Demo (10–20 s) → Why it works (1–2 lines) → Payoff + loop (≤2 s).

* Keep a single **teachable moment**. If there are two, split into two Shorts.

---

## 9) Compliance & Rights (MUST)

* **Royalty‑free** music/SFX only.
* Only show code you have rights to publish; redact secrets.
* No licensed UI/brand elements unless permitted.

---

## 10) Delivery & Export (MUST)

* **Master export:** MP4, H.264 High, 1080×1920, 30/60 FPS, 12–20 Mbps, AAC 48 kHz/320 kbps.
* **File naming:** `shorts_YYYYMMDD_topic_hook_v01.mp4`.
* **Thumbnail/frame:** Choose a frame with readable code + clear promise text (≤4 words).

---

## 11) QC Checklist (Tick All Before Upload)

* [ ] Hook is visible & understandable in **≤2 s**.
* [ ] Visual change every **≤3 s**.
* [ ] Key line/API parameter is clearly highlighted during explanation.
* [ ] Captions: 2 lines max, no overlaps with UI.
* [ ] Speech intelligible on phone speaker; music bed, if any, doesn't mask.
* [ ] Loop: last second ties back to the first.
* [ ] No copyrighted audio/visuals.
* [ ] Export meets spec; safe areas respected.

---

## 12) Templates (Editor‑Agnostic)

**Punch‑in preset**
* Scale: 100→122%
* Duration: 8 frames
* Ease: out‑quad

**Highlight callout**
* Box: 4 px border, 8 px radius
* Dim: 40–50% black overlay outside box (300–500 ms)

**Speed ramp for scroll**
* 1.0×→1.35× (6‑frame ramp) → hold → 1.0× (6‑frame ramp)

**Whoosh SFX marker**
* Start on cut, length 200–250 ms, low‑mid emphasis

---

## 13) Disallowed

* Long animated transitions (spins, wipes, page curls).
* Low‑contrast code themes.
* Music louder than narration at any time.
* Caption karaoke for full sentences.
* More than one complex idea per Short.

---

### Notes for Software‑Engineering Content

* Prefer **cursor halo + line box** to laser pointers.
* Show **before/after** diffs with a vertical wipe or two‑up split for ≤ **1.2 s**.
* Provide copyable snippet via pinned comment; on‑screen text is summary only.

# Basic Effects Strategy

**Goal:** Convert a 1920×1080 (16:9) screen-recording with English speech into a crisp, vertical **1080×1920 (9:16)** Short with captions, title, and clean pacing—optimized for mobile legibility.

---

## Assumptions

* Input: `in.mp4` (1920×1080), 30/60 fps, English narration.
* Content type: screen recording with small facecam (bottom-left), diagrams/code/CLI.

---

## Pipeline (high level)

1. **Ingest → Audio cleanup → Speed/pitch → Smart reframing to 9:16 → Overlays (title, captions, progress bar) → Optional readability boosts → Export.**

---

## Requirements

### 1) Audio Cleanup (MUST)

* Normalize speech loudness to **-16 LUFS** (±1 LU).
* Peak limit at **-1 dBFS**; true peak ≤ **-1 dBTP**.
* Light broadband denoise and **de-ess** (center \~5–8 kHz) without lisping.
* Remove DC offset; resample to **48 kHz**, AAC at **320 kbps** on export.

### 2) Speed Change (MUST)

* Apply global speed **1.35×** to video **and** audio.
* Preserve voice pitch with time-stretch (no "chipmunk").
* Fallback ladder if artifacts detected: **1.30× → 1.25× → 1.15×**.

### 3) Reframe to 9:16 (MUST)

* Output canvas: **1080×1920**.
* **Smart crop** order:

  1. Try to keep **facecam + primary content** inside 9:16 window using face detection + saliency.
  2. If facecam blocks key UI, **reposition/scale** facecam to a free corner (see §6).
  3. If crop would hide important text, **pillarbox fill**: scale source to fit **height** and add a **blurred, darkened (20–30%)** duplicate as background. No black bars.
* Soft limit: avoid scaling the source above **100%** of its native vertical resolution to prevent softness.
* Safe areas: keep overlays **≥120 px** from top/bottom edges.

### 4) Captions (MUST)

* Source: ASR from English speech; auto-correct obvious terms (CLI/code).
* Style: **2 lines max**, **28–32 chars/line**, sentence case.
* Font: high-contrast sans; **stroke 2–3 px** or soft shadow.
* Position: **bottom** above safe area (≈ **MarginV 96–120 px**), never covering key UI.
* Timing: snap to speech with max **120 ms** offset; no karaoke except **single-word emphasis**.

### 5) Title Strap (MUST)

* Show for **0.8–1.5 s** starting at **0.0 s** (can persist up to 3 s if short).
* Position: **top** safe area; horizontal strap or compact pill.
* Copy: ≤ **6–10 words**; avoid jargon. Example: "LLM Task Flow: Core Data Model".
* Animation: fade/slide ≤ **180–250 ms**; no bouncy easing.

### 6) Facecam Handling (SHOULD)

* If present, **mask to circle** (soft 12–16 px feather), add subtle shadow.
* Size: **15–22%** of canvas width; opacity 100%.
* Auto-reposition to a corner **not** overlapping important content; add **4%** inset margin.
* If face adds no value for >5 s, **auto-hide** and re-show on new segment.

### 7) Readability Boosts (SHOULD)

* **Punch-in** on focal region: scale **1.15–1.25×** over **6–12 frames** (ease-out).
* **Spotlight** when explaining a line/box: darken outside a rectangle by **40–55%** for **0.4–0.8 s**.
* **Cursor halo** on clicks: radius **24–32 px**, 200–300 ms fade.
* **Speed-ramp scrolling** sections to **1.25–1.5×** with 4–6-frame ramps.

### 8) Progress Bar (MAY)

* Thin bar at bottom safe area (height **6–10 px**), animates linearly through duration.
* Color: brand accent; 60–80% opacity; never under captions.

### 9) Silence/Dead-Air Trim (MAY)

* Detect silence below `speech_dBFS − 20 dB` for ≥ **250 ms** and remove with **120 ms** pre/post handles.
* Ensure cut cadence does not exceed **1 cut / 500 ms**.

### 10) Color & Sharpness (MAY)

* Gentle contrast/levels auto; avoid crushed blacks on code.
* Add tiny unsharp mask on downscaled regions (radius 0.6–0.8, amount 0.4–0.6).

### 11) Branding (MAY)

* Tiny logo watermark (≤ **2.5%** width) top-right; auto-hide during title strap.

### 12) Export (MUST)

* Container: **MP4**, codec **H.264 High**, **30 or 60 fps** (match source).
* Bitrate target: **12–20 Mbps** VBR; keyint ≤ **2×fps**.
* Audio: AAC **48 kHz**, **320 kbps**.
* Filename: `shorts_YYYYMMDD_topic_v01.mp4`.

---

## Acceptance Criteria

* Output is **1080×1920** with no letterboxing; background blur used if needed.
* Speech intelligible on phone speakers; loudness around **-16 LUFS**.
* Title readable in <2 s and doesn't collide with captions.
* Captions never cover important UI; max 2 lines; consistent style.
* If facecam exists, it never obscures focal content and respects margins.
* Visual change (cut/zoom/overlay) at least every **≤3 s** during explanations.

---

## Tunable Parameters (defaults)

* `speed_factor = 1.35`
* `caption_fontsize = 42` (1080×1920), `caption_marginV = 100`
* `spotlight_opacity = 0.45`, `punch_in_max = 1.22`, `punch_in_frames = 8`
* `progress_bar_height = 8`
* `bg_blur_sigma = 18–24`, `bg_darkening = 0.25`
* `facecam_size_pct = 0.18`, `facecam_margin_pct = 0.04`

---

## Fallback Rules

* If ASR confidence < **0.8** on a segment, keep captions but mark with lighter emphasis; never skip.
* If smart crop cannot keep both facecam and focal UI, **prioritize focal UI**, downscale and move facecam.
* If readability falls below threshold (small text), force **pillarbox fill** and **no additional zoom** to avoid softness.