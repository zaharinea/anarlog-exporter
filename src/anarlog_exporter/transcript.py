"""Сборка транскрипции встречи из transcript.json anarlog.

Портировано из examples/import-char.py: группировка слов по каналу (спикеру)
и паузам, формирование строк вида `**[MM:SS] Спикер N:** text`.
"""

from __future__ import annotations

from typing import Any

PAUSE_THRESHOLD_MS = 2000


def format_timestamp(total_ms: int) -> str:
    total_sec = total_ms // 1000
    return f"{total_sec // 60:02d}:{total_sec % 60:02d}"


def build_transcript(transcript_data: dict[str, Any]) -> str:
    """Группирует слова по спикеру (channel) и паузам, возвращает текст транскрипции."""
    all_words: list[dict[str, Any]] = []
    for segment in transcript_data.get("transcripts", []):
        started_at = segment.get("started_at", 0)
        for word in segment.get("words", []):
            all_words.append({
                "channel": word["channel"],
                "abs_start": started_at + word["start_ms"],
                "abs_end": started_at + word["end_ms"],
                "text": word["text"],
            })

    if not all_words:
        return ""

    all_words.sort(key=lambda w: w["abs_start"])
    origin = all_words[0]["abs_start"]

    segments: list[str] = []
    cur_channel: int | None = None
    cur_words: list[dict[str, Any]] = []
    cur_start = 0

    def flush() -> None:
        if not cur_words:
            return
        text = "".join(w["text"] for w in cur_words).strip()
        if text:
            ts = format_timestamp(cur_start - origin)
            segments.append(f"**[{ts}] Спикер {cur_channel + 1}:** {text}")

    for word in all_words:
        channel = word["channel"]
        speaker_changed = channel != cur_channel
        long_pause = (
            bool(cur_words)
            and (word["abs_start"] - cur_words[-1]["abs_end"] > PAUSE_THRESHOLD_MS)
        )

        if speaker_changed or long_pause:
            flush()
            cur_channel = channel
            cur_words = [word]
            cur_start = word["abs_start"]
        else:
            cur_words.append(word)

    flush()
    return "\n\n".join(segments)
