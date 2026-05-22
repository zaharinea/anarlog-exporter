"""Модель сессии anarlog: чтение _meta.json / transcript.json / *.md."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .transcript import build_transcript

UNSAFE_FILENAME_CHARS = re.compile(r'[/\\:*?"<>|]')


def sanitize_filename(name: str) -> str:
    return UNSAFE_FILENAME_CHARS.sub("-", name).strip()


def strip_frontmatter(content: str) -> str:
    """Удаляет YAML frontmatter из markdown-контента."""
    lines = content.split("\n")
    if not lines or lines[0].strip() != "---":
        return content
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "\n".join(lines[i + 1:]).strip()
    return content


def clean_content(content: str) -> str:
    """Убирает frontmatter и артефакты &nbsp;."""
    content = strip_frontmatter(content)
    lines = [line for line in content.split("\n") if line.strip() not in ("&nbsp;",)]
    return "\n".join(lines).strip()


def get_note_position(content: str) -> int:
    in_frontmatter = False
    for i, line in enumerate(content.split("\n")):
        stripped = line.strip()
        if i == 0 and stripped == "---":
            in_frontmatter = True
            continue
        if in_frontmatter and stripped == "---":
            break
        if line.startswith("position:"):
            try:
                return int(line.split(":", 1)[1].strip())
            except ValueError:
                pass
    return 99


def parse_created_at(value: str) -> datetime | None:
    if not value:
        return None
    # ISO 8601 c Z или offset
    try:
        v = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(v)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


@dataclass
class Session:
    session_dir: Path
    session_id: str
    title: str
    created_at_raw: str
    created_at: datetime | None
    memo: str
    extra_notes: list[str]  # без _memo.md, в порядке position
    transcript: str
    mtime: float

    @property
    def notes(self) -> str:
        """memo + extra_notes, разделённые `---`."""
        parts: list[str] = []
        for chunk in self.extra_notes:
            if chunk:
                parts.append(chunk)
        if self.memo:
            parts.append(self.memo)
        return "\n\n---\n\n".join(parts)

    @classmethod
    def from_dir(cls, session_dir: Path) -> Session | None:
        meta_path = session_dir / "_meta.json"
        if not meta_path.exists():
            return None
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None

        session_id = str(meta.get("id") or session_dir.name)
        title = str(meta.get("title") or session_id)
        created_at_raw = str(meta.get("created_at", ""))
        created_at = parse_created_at(created_at_raw)

        memo = ""
        memo_path = session_dir / "_memo.md"
        if memo_path.exists():
            memo = clean_content(memo_path.read_text(encoding="utf-8"))

        notes_with_pos: list[tuple[int, str]] = []
        for md_file in session_dir.glob("*.md"):
            if md_file.name == "_memo.md":
                continue
            raw = md_file.read_text(encoding="utf-8")
            notes_with_pos.append((get_note_position(raw), clean_content(raw)))
        notes_with_pos.sort(key=lambda x: x[0])
        extra_notes = [content for _, content in notes_with_pos if content]

        transcript = ""
        transcript_path = session_dir / "transcript.json"
        if transcript_path.exists():
            try:
                data = json.loads(transcript_path.read_text(encoding="utf-8"))
                transcript = build_transcript(data)
            except json.JSONDecodeError:
                transcript = ""

        mtime = max(
            (p.stat().st_mtime for p in session_dir.rglob("*") if p.is_file()),
            default=session_dir.stat().st_mtime,
        )

        return cls(
            session_dir=session_dir,
            session_id=session_id,
            title=title,
            created_at_raw=created_at_raw,
            created_at=created_at,
            memo=memo,
            extra_notes=extra_notes,
            transcript=transcript,
            mtime=mtime,
        )

    def has_content(self) -> bool:
        return bool(self.transcript or self.memo or self.extra_notes)
