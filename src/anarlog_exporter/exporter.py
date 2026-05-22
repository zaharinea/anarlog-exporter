"""Логика экспорта и фонового watcher'а."""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path

from .config import Config
from .session import Session
from .template import load_template, render_filename, render_markdown

logger = logging.getLogger(__name__)

SESSION_ID_RE = re.compile(r"^session_id:\s*(\S+)\s*$", re.MULTILINE)


@dataclass
class PassResult:
    exported: int = 0
    updated: int = 0
    skipped: int = 0
    failed: int = 0


def _read_frontmatter_session_id(path: Path) -> str | None:
    """Извлекает session_id из YAML frontmatter существующего .md."""
    try:
        with path.open("r", encoding="utf-8") as f:
            head = f.read(4096)
    except OSError:
        return None
    if not head.startswith("---"):
        return None
    end = head.find("\n---", 3)
    if end == -1:
        return None
    block = head[3:end]
    match = SESSION_ID_RE.search(block)
    return match.group(1) if match else None


def build_id_mapping(output_dir: Path) -> dict[str, tuple[Path, float]]:
    """{session_id -> (path, mtime)} для всех .md под output_dir."""
    mapping: dict[str, tuple[Path, float]] = {}
    if not output_dir.exists():
        return mapping
    for md_path in output_dir.rglob("*.md"):
        sid = _read_frontmatter_session_id(md_path)
        if sid:
            mapping[sid] = (md_path, md_path.stat().st_mtime)
    return mapping


def iter_sessions(sessions_dir: Path):
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
    id_mapping: dict[str, tuple[Path, float]],
    *,
    force: bool = False,
) -> str:
    """Возвращает 'exported' | 'updated' | 'skipped'."""
    if not session.has_content():
        return "skipped"

    rel_path = render_filename(
        cfg.filename_pattern, session, cfg.date_format, cfg.time_format
    )
    new_path = cfg.output / rel_path

    existing = id_mapping.get(session.session_id)
    if existing is not None:
        old_path, output_mtime = existing
        if not force and session.mtime <= output_mtime:
            return "skipped"
        # Удаляем старый файл, если имя изменилось
        if old_path.resolve() != new_path.resolve():
            try:
                old_path.unlink()
            except OSError:
                logger.warning("Не удалось удалить старый файл %s", old_path)

    new_path.parent.mkdir(parents=True, exist_ok=True)
    content = render_markdown(template_str, session)
    new_path.write_text(content, encoding="utf-8")
    return "updated" if existing is not None else "exported"


def run_export_pass(
    cfg: Config,
    *,
    only_session_id: str | None = None,
    force: bool = False,
    silent_skip: bool = False,
) -> PassResult:
    template_str = load_template(cfg.template)
    cfg.output.mkdir(parents=True, exist_ok=True)
    id_mapping = build_id_mapping(cfg.output)

    result = PassResult()
    for session in iter_sessions(cfg.sessions_dir):
        if only_session_id and session.session_id != only_session_id:
            continue
        try:
            outcome = export_session(
                session, cfg, template_str, id_mapping, force=force
            )
        except Exception:
            logger.exception("Ошибка экспорта сессии %s", session.session_id)
            result.failed += 1
            continue

        rel = render_filename(
            cfg.filename_pattern, session, cfg.date_format, cfg.time_format
        )
        if outcome == "exported":
            result.exported += 1
            logger.info("Exported: %s", rel)
        elif outcome == "updated":
            result.updated += 1
            logger.info("Updated:  %s", rel)
            id_mapping[session.session_id] = (cfg.output / rel, time.time())
        else:
            result.skipped += 1
            if not silent_skip:
                logger.info("Skip:     %s (up to date)", rel)

    if only_session_id and result.exported + result.updated + result.skipped == 0:
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
