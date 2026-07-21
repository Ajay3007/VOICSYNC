# Voice Timeline

Audio: `{audio_name}`
Duration: **{duration}s** · Words: **{word_count}** · Sentences: **{sentence_count}** · Speaking speed: **{wpm} WPM** · Language: **{language}**

## Word timestamps

Format: `start  word` (seconds). Emphasized words are marked in **bold** with their importance.

{word_block}

## Sentences

{sentence_block}

## Pauses

{pause_block}

## Instructions for Claude

Synchronize every Manim animation with these timestamps.

- Visuals should begin slightly before the spoken keyword (start each animation about 0.15–0.30 s early).
- Finish each animation before the next important keyword begins.
- Use pauses for scene transitions — a long pause is a natural cut point.
- Use sentence boundaries for camera changes and section headers.
- Words marked **high** importance deserve the strongest visual moment (highlight, zoom, color flash); **medium** importance words deserve a secondary accent.
- Keep total scene durations aligned to the sentence spans above so audio and video never drift.
