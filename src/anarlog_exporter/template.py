"""Шаблоны для рендеринга markdown-файлов встреч и имён файлов."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from string import Template

from .session import Session, sanitize_filename

DEFAULT_TEMPLATE = """---
date: ${date}
type: meeting
source: anarlog
session_id: ${session_id}
tags:
  - meeting
---

# ${title}

${notes}

## Заметки

${memo}

---

## Транскрипция

${transcript}
"""


class StrictTemplate(Template):
    """string.Template, который бросает понятную ошибку на неизвестные плейсхолдеры."""


def load_template(path: Path | None) -> str:
    if path is None:
        return DEFAULT_TEMPLATE
    return path.read_text(encoding="utf-8")


def render_markdown(template_str: str, session: Session) -> str:
    template = StrictTemplate(template_str)
    mapping = {
        "session_id": session.session_id,
        "title": session.title,
        "date": session.created_at_raw[:10] if session.created_at_raw else "",
        "memo": session.memo,
        "extra_notes": "\n\n---\n\n".join(session.extra_notes),
        "notes": session.notes,
        "transcript": session.transcript,
    }
    try:
        return template.substitute(mapping)
    except KeyError as exc:
        raise ValueError(
            f"Шаблон ссылается на неизвестную переменную ${{{exc.args[0]}}}. "
            f"Доступны: {', '.join(sorted(mapping.keys()))}"
        ) from exc


def render_filename(
    pattern: str,
    session: Session,
    date_format: str,
    time_format: str,
) -> Path:
    """Рендерит имя файла (возможно с подкаталогами) для сессии."""
    dt = session.created_at
    if dt is not None:
        date_str = dt.strftime(date_format)
        time_str = dt.strftime(time_format)
        year = f"{dt.year:04d}"
        month = f"{dt.month:02d}"
        day = f"{dt.day:02d}"
        hour = f"{dt.hour:02d}"
        minute = f"{dt.minute:02d}"
    else:
        date_str = session.created_at_raw[:10] if session.created_at_raw else "0000-00-00"
        time_str = ""
        year = month = day = hour = minute = "00"

    placeholders = {
        "date": date_str,
        "time": time_str,
        "datetime": f"{date_str} {time_str}".strip(),
        "title": sanitize_filename(session.title),
        "session_id": session.session_id,
        "year": year,
        "month": month,
        "day": day,
        "hour": hour,
        "minute": minute,
    }

    try:
        rendered = pattern.format(**placeholders)
    except KeyError as exc:
        raise ValueError(
            f"filename_pattern ссылается на неизвестный плейсхолдер {{{exc.args[0]}}}. "
            f"Доступны: {', '.join(sorted(placeholders.keys()))}"
        ) from exc

    rel = Path(rendered)
    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError(
            f"filename_pattern сгенерировал небезопасный путь: {rendered!r}"
        )
    return rel


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")
