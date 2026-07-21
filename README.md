# voice-sync — Voiceover Timeline Generator

A desktop application that turns an AI voiceover (`.mp3`, `.wav`, `.m4a`, …)
into a **highly accurate, word-level timeline** for synchronizing
[Manim](https://www.manim.community/) animations. It transcribes with
**WhisperX** (word-level forced alignment), detects natural pauses,
speaking speed and emphasized words, and exports everything as JSON, CSV,
SRT and a ready-to-paste **Claude prompt**.

```
audio in  ──►  WhisperX transcribe ──► forced alignment ──► pauses / speed /
                                                            emphasis analysis
          ◄──  timeline.json · timeline.csv · timeline.srt ·
               analysis.json · claude_prompt.md
```

---

## Requirements

| Requirement | Notes |
|---|---|
| **Python 3.10 – 3.12** | PyTorch/WhisperX wheels are published for these versions. Python 3.13/3.14 will usually **fail to install torch** — create a 3.11/3.12 venv instead. |
| **FFmpeg** | Needed to decode mp3/m4a. Windows: `winget install Gyan.FFmpeg` (reopen the terminal afterwards). |
| **NVIDIA GPU** (optional) | Used automatically when available (`float16`). CPU fallback (`int8`) works everywhere, just slower. |
| Disk space | Whisper models are downloaded automatically on first run (75 MB for `tiny` up to ~3 GB for `large-v3`). |

## Installation

```bash
# 1. Create and activate a virtual environment (Python 3.11 or 3.12)
py -3.12 -m venv .venv          # Windows
.venv\Scripts\activate

# macOS / Linux:
# python3.12 -m venv .venv && source .venv/bin/activate

# 2. (Optional, NVIDIA GPU) install CUDA torch first
#    cu128 supports modern cards including RTX 50-series (Blackwell).
#    Keep torchaudio at 2.8.x — whisperx requires it.
pip install torch==2.8.0 torchaudio==2.8.0 --index-url https://download.pytorch.org/whl/cu128

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run
python app.py
```

The first processing run downloads the Whisper model and the wav2vec2
alignment model automatically; later runs reuse the local cache.

## Usage

1. **Upload Audio** — pick your voiceover (`mp3`, `wav`, `m4a`, `flac`, `ogg`, `aac`).
2. **Upload Script** *(optional)* — a `.txt` of the intended narration.
   The app reports a *script match* percentage in the statistics and
   `analysis.json` so you can verify the TTS said what it should.
3. **Select Model** — `tiny`/`base` for drafts, `small` (default) for a
   good balance, `large-v3` for maximum accuracy.
4. **Select Language** — *Auto detect* (default) or force a language.
5. **Export Folder** — defaults to `output/` next to the app.
6. **Start** — progress, elapsed time and estimated remaining time are
   shown live; the transcription streams into the center log. The UI
   never freezes: all processing runs on a background thread and can be
   cancelled.

When the run finishes, **all export files are written automatically** to
the export folder. The bottom buttons re-export individual formats,
copy the Claude prompt to the clipboard, or open the output folder.

## Output files

| File | Content |
|---|---|
| `timeline.json` | Words (`start`, `end`, `duration`, `importance`, `confidence`), sentences, pauses, metadata. |
| `timeline.csv` | The same events as a flat spreadsheet (`type` column = `word` / `sentence` / `pause`). |
| `timeline.srt` | Sentence-level subtitles for previewing sync in any video player. |
| `analysis.json` | Duration, WPM (overall + articulation), pause statistics, fast/slow speech regions, emphasized words, script similarity. |
| `claude_prompt.md` | Ready-to-paste prompt: every word timestamp, sentences, pauses, plus synchronization instructions for Claude to generate Manim code. |

### Emphasis detection

Each word gets an `importance` of `low` / `medium` / `high`, estimated
from z-normalized prosodic features: stretched duration (per character),
pause before/after the word, relative loudness (RMS dB) and relative
pitch (median F0 via `librosa.yin`, skipped gracefully if unavailable).

## Project structure

```
voice-sync/
├── app.py                    # entry point (python app.py)
├── ui/                       # CustomTkinter dark UI
│   ├── main_window.py        # layout + worker event pump
│   ├── left_panel.py         # inputs, model/language, start/cancel
│   ├── center_panel.py       # live log, progress, elapsed/ETA
│   ├── right_panel.py        # statistics
│   ├── bottom_bar.py         # export buttons
│   ├── worker.py             # background pipeline thread
│   └── theme.py              # colors and fonts
├── engine/                   # analysis core (UI-independent)
│   ├── base.py               # TranscriptionEngine ABC + result types
│   ├── whisperx_engine.py    # WhisperX backend (GPU/CPU, model cache)
│   ├── pipeline.py           # orchestrator: audio -> Timeline
│   ├── analysis.py           # sentences, pauses, speed regions, stats
│   ├── emphasis.py           # low/medium/high emphasis scoring
│   ├── audio_features.py     # loudness (RMS) + pitch (YIN) profiles
│   ├── device.py             # CUDA detection, CPU fallback
│   └── config.py             # PipelineConfig + model/language lists
├── exporters/                # one class per output format
│   ├── base.py               # TimelineExporter ABC
│   ├── json_exporter.py      # timeline.json
│   ├── csv_exporter.py       # timeline.csv
│   ├── srt_exporter.py       # timeline.srt
│   ├── analysis_exporter.py  # analysis.json
│   └── claude_prompt.py      # claude_prompt.md
├── models/                   # typed dataclasses (Timeline, WordEntry, …)
├── utils/                    # logging, time formatting, text helpers
├── assets/                   # claude_prompt_template.md
├── output/                   # default export folder + logs
├── requirements.txt
└── README.md
```

## Architecture & extensibility

The three layers are strictly separated:

* **engine** knows nothing about the UI — it reports through a
  `progress(fraction, message)` callback and a `cancel()` predicate, so
  it can be driven from a CLI or tests unchanged.
* **exporters** consume only the typed `Timeline` model.
* **ui** talks to the engine exclusively through a background thread and
  a thread-safe event queue.

Adding capabilities later requires no core changes:

* **New speech backend** (ElevenLabs, OpenAI TTS, Azure Speech, Google
  TTS): subclass `engine.base.TranscriptionEngine`, return a
  `TranscriptionResult`, and hand it to `VoicePipeline`.
* **New export target** (Premiere Pro XML, After Effects markers,
  DaVinci Resolve markers, CapCut timeline, automatic Manim scene
  generation): subclass `exporters.base.TimelineExporter` and append it
  to `exporters.ALL_EXPORTERS`.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `Could not decode …` | FFmpeg missing — install it and restart the terminal. |
| `pip` cannot find `torch` | Your Python is too new (3.13/3.14). Use a 3.11/3.12 venv. |
| Very slow processing | You are on CPU. Use a smaller model (`tiny`/`base`) or install CUDA torch. |
| `No alignment model available for language 'xx'` | WhisperX has no wav2vec2 model for that language; force English or another supported language. |
| `CUDA error: no kernel image is available` | Your torch build lacks kernels for the GPU (e.g. RTX 50-series needs cu128). The app auto-falls back to CPU; for GPU speed reinstall: `pip install torch==2.8.0 torchaudio==2.8.0 --index-url https://download.pytorch.org/whl/cu128`. |
| `module 'torchaudio' has no attribute 'AudioMetaData'` | torchaudio 2.9+ is too new for whisperx/pyannote — pin `torchaudio==2.8.0`. |
| Weird timestamps on numbers/symbols | Tokens WhisperX cannot align are interpolated between neighbours — expected behaviour. |

Logs are written to `output/logs/voice-sync.log`.
