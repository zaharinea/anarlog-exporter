"""Общие фикстуры pytest."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture
def make_session(tmp_path: Path):
    """Создаёт минимальную сессию anarlog в tmp_path/sessions/<id>/."""

    def _make(
        session_id: str = "11111111-2222-3333-4444-555555555555",
        title: str = "Design Review",
        created_at: str = "2025-12-05T14:30:00Z",
        memo: str | None = "Главное:\n- решили запустить.",
        extra_notes: list[tuple[str, int, str]] | None = None,
        transcript_words: list[dict] | None = None,
        summary: str | None = "## Summary\nWe agreed to ship.",
        summary_filename: str = "_summary.md",
    ) -> Path:
        sessions_root = tmp_path / "anarlog" / "sessions"
        sdir = sessions_root / session_id
        sdir.mkdir(parents=True, exist_ok=True)
        (sdir / "_meta.json").write_text(
            json.dumps({"id": session_id, "title": title, "created_at": created_at}),
            encoding="utf-8",
        )
        if memo is not None:
            (sdir / "_memo.md").write_text(
                f"---\nid: {session_id}\n---\n\n{memo}\n", encoding="utf-8"
            )
        if summary is not None:
            (sdir / summary_filename).write_text(summary, encoding="utf-8")
        for name, position, content in extra_notes or []:
            (sdir / f"{name}.md").write_text(
                f"---\nposition: {position}\n---\n\n{content}\n", encoding="utf-8"
            )
        if transcript_words is None:
            transcript_words = [
                {"channel": 0, "start_ms": 0, "end_ms": 500, "text": "Привет."},
                {"channel": 1, "start_ms": 600, "end_ms": 1100, "text": "Привет!"},
                {"channel": 1, "start_ms": 1200, "end_ms": 1800, "text": " Как дела?"},
            ]
        (sdir / "transcript.json").write_text(
            json.dumps({
                "transcripts": [{"started_at": 1_700_000_000_000, "words": transcript_words}]
            }),
            encoding="utf-8",
        )
        return sdir

    return _make
