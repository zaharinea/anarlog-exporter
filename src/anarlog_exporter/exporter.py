"""Логика экспорта и фонового watcher'а.

Решения по дизайну:

- На output больше не смотрим. Состояние ведётся в индексе рядом с output:
  `<output>/.anarlog-exporter-index.json`. Если `session_id` в индексе —
  сессия пропускается, никаких mtime/content-сравнений.
- Экспортируем только «завершённые» сессии: те, у которых в директории
  есть хотя бы один `.md` помимо `_memo.md` (anarlog кладёт туда сгенерированную
  заметку — `_summary.md`, `Simple Meeting.md`, `1_1 Meeting.md` и т.п.).
  Сессии без summary пропускаются и подхватятся на следующем проходе.
- `--force` игнорирует индекс и перезаписывает файлы (после — обновляет
  индекс).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from .config import Config
from .session import Session
from .state import Index
from .template import load_template, render_filename, render_markdown

logger = logging.getLogger(__name__)

MEMO_FILENAME = "_memo.md"


@dataclass
class PassResult:
    exported: int = 0
    skipped: int = 0
    pending: int = 0  # сессии без сгенерированной заметки, ждём LLM
    failed: int = 0


def is_session_complete(session: Session) -> bool:
    """Сессия считается завершённой, если в её директории есть хотя бы один
    .md помимо _memo.md (anarlog кладёт туда summary под разными именами:
    `_summary.md`, `Simple Meeting.md`, `1_1 Meeting.md`, ...)."""
    return any(
        md.name != MEMO_FILENAME
        for md in session.session_dir.glob("*.md")
    )


def iter_sessions(sessions_dir):
    if not sessions_dir.is_dir():
        return
    for entry in sorted(sessions_dir.iterdir()):
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        session = Session.from_dir(entry)
        if session is None:
            continue
        yield session


def export_session(
    session: Session,
    cfg: Config,
    template_str: str,
    index: Index,
    *,
    force: bool = False,
) -> tuple[str, str]:
    """Возвращает (outcome, filename).

    outcome:
        "exported" — записали .md и добавили в индекс
        "skipped"  — session_id уже в индексе
        "pending"  — сессия не завершена (нет _summary.md) или пустая
    """
    if not session.has_content():
        return "pending", ""

    if not is_session_complete(session):
        return "pending", ""

    if not force and index.contains(session.session_id):
        return "skipped", index.exported[session.session_id].get("filename", "")

    rel_path = render_filename(
        cfg.filename_pattern, session, cfg.date_format, cfg.time_format
    )
    out_path = cfg.output / rel_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    content = render_markdown(template_str, session)
    out_path.write_text(content, encoding="utf-8")

    rel_str = str(rel_path)
    index.add(session.session_id, rel_str)
    return "exported", rel_str


def run_export_pass(
    cfg: Config,
    *,
    only_session_id: str | None = None,
    force: bool = False,
    silent_skip: bool = False,
) -> PassResult:
    template_str = load_template(cfg.template)
    cfg.output.mkdir(parents=True, exist_ok=True)
    index = Index.load(cfg.output)

    result = PassResult()
    matched_filter = False
    for session in iter_sessions(cfg.sessions_dir):
        if only_session_id and session.session_id != only_session_id:
            continue
        matched_filter = True
        try:
            outcome, filename = export_session(
                session, cfg, template_str, index, force=force
            )
        except Exception:
            logger.exception("Ошибка экспорта сессии %s", session.session_id)
            result.failed += 1
            continue

        if outcome == "exported":
            result.exported += 1
            logger.info("Exported: %s", filename)
        elif outcome == "pending":
            result.pending += 1
            if not silent_skip:
                logger.info(
                    "Pending:  session %s (ждём _summary.md)", session.session_id
                )
        else:  # skipped
            result.skipped += 1
            if not silent_skip:
                logger.info("Skip:     %s (уже в индексе)", filename or session.session_id)

    if result.exported:
        try:
            index.save()
        except OSError as exc:
            logger.error("Не удалось сохранить индекс %s: %s", index.path, exc)

    if only_session_id and not matched_filter:
        logger.warning("Сессия %s не найдена в %s", only_session_id, cfg.sessions_dir)
    return result


def watch_loop(cfg: Config) -> None:
    logger.info(
        "anarlog-exporter watch started: data_dir=%s output=%s interval=%ds",
        cfg.data_dir,
        cfg.output,
        cfg.interval,
    )
    while True:
        try:
            run_export_pass(cfg, silent_skip=True)
        except Exception:
            logger.exception("Сбой во время прохода экспорта")
        time.sleep(cfg.interval)
