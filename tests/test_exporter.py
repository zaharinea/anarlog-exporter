from pathlib import Path

import pytest

from anarlog_exporter.config import Config
from anarlog_exporter.exporter import run_export_pass
from anarlog_exporter.state import INDEX_FILENAME, Index


def _cfg(tmp_path: Path) -> Config:
    return Config(
        data_dir=tmp_path / "anarlog",
        output=tmp_path / "out",
    )


def test_export_creates_file_and_writes_index(tmp_path, make_session):
    make_session()
    cfg = _cfg(tmp_path)
    result = run_export_pass(cfg)
    assert result.exported == 1 and result.skipped == 0 and result.pending == 0
    files = [p.name for p in cfg.output.glob("*.md")]
    assert files == ["2025-12-05 - Design Review.md"]
    index = Index.load(cfg.output)
    assert index.contains("11111111-2222-3333-4444-555555555555")
    assert (cfg.output / INDEX_FILENAME).exists()


def test_export_skips_when_session_in_index(tmp_path, make_session):
    make_session()
    cfg = _cfg(tmp_path)
    run_export_pass(cfg)
    second = run_export_pass(cfg)
    assert second.exported == 0
    assert second.skipped == 1


def test_export_ignores_output_files_not_in_index(tmp_path, make_session):
    """Если индекс пуст — output игнорируется, всё переэкспортируется."""
    make_session()
    cfg = _cfg(tmp_path)
    # Кладём в output чужой .md, имитирующий старый экспорт. Индекса нет.
    cfg.output.mkdir(parents=True)
    stale = cfg.output / "2025-12-05 - Design Review.md"
    stale.write_text("---\nsession_id: 11111111-2222-3333-4444-555555555555\n---\n# old", encoding="utf-8")
    result = run_export_pass(cfg)
    assert result.exported == 1
    # файл перезаписан свежим контентом
    assert "# Design Review" in stale.read_text(encoding="utf-8")


def test_export_pending_without_summary(tmp_path, make_session):
    """Сессия без любого .md (кроме _memo.md) считается незавершённой."""
    make_session(summary=None)
    cfg = _cfg(tmp_path)
    result = run_export_pass(cfg)
    assert result.exported == 0
    assert result.pending == 1
    assert list(cfg.output.glob("*.md")) == []
    assert not Index.load(cfg.output).contains("11111111-2222-3333-4444-555555555555")


@pytest.mark.parametrize(
    "summary_filename",
    ["_summary.md", "Simple Meeting.md", "1_1 Meeting.md", "Cross-Team Sync.md"],
)
def test_export_complete_with_various_summary_filenames(tmp_path, make_session, summary_filename):
    """anarlog кладёт сгенерированный summary под разными именами файла."""
    make_session(summary_filename=summary_filename)
    cfg = _cfg(tmp_path)
    result = run_export_pass(cfg)
    assert result.exported == 1


def test_export_picks_up_after_summary_appears(tmp_path, make_session):
    sdir = make_session(summary=None)
    cfg = _cfg(tmp_path)
    assert run_export_pass(cfg).pending == 1
    # Через какое-то время появляется сгенерированная заметка (любое имя)
    (sdir / "Simple Meeting.md").write_text("## Summary\nDone.", encoding="utf-8")
    second = run_export_pass(cfg)
    assert second.exported == 1
    assert second.pending == 0


def test_export_memo_only_is_still_pending(tmp_path, make_session):
    """Только _memo.md без сгенерированной заметки = pending."""
    make_session(summary=None, memo="Только пользовательские заметки.")
    cfg = _cfg(tmp_path)
    result = run_export_pass(cfg)
    assert result.exported == 0
    assert result.pending == 1


def test_export_ignores_mtime_bumps_when_indexed(tmp_path, make_session):
    """Главная регрессия: anarlog бампает mtime файлов сессии, но если session
    уже в индексе — мы её не трогаем, никаких дублей в логах."""
    import os
    sdir = make_session()
    cfg = _cfg(tmp_path)
    run_export_pass(cfg)
    out_file = next(cfg.output.glob("*.md"))
    original_content = out_file.read_text(encoding="utf-8")
    original_mtime = out_file.stat().st_mtime

    future = out_file.stat().st_mtime + 10_000
    for p in sdir.rglob("*"):
        if p.is_file():
            os.utime(p, (future, future))

    result = run_export_pass(cfg)
    assert result.exported == 0
    assert result.skipped == 1
    assert out_file.read_text(encoding="utf-8") == original_content
    assert out_file.stat().st_mtime == original_mtime  # output не трогали


def test_export_force_reexports(tmp_path, make_session):
    make_session()
    cfg = _cfg(tmp_path)
    run_export_pass(cfg)
    out_file = next(cfg.output.glob("*.md"))
    out_file.write_text("REPLACED", encoding="utf-8")

    result = run_export_pass(cfg, force=True)
    assert result.exported == 1
    assert "REPLACED" not in out_file.read_text(encoding="utf-8")
    assert Index.load(cfg.output).contains("11111111-2222-3333-4444-555555555555")


def test_export_filters_by_session_id(tmp_path, make_session):
    make_session(session_id="aaaa", title="First")
    make_session(session_id="bbbb", title="Second")
    cfg = _cfg(tmp_path)
    result = run_export_pass(cfg, only_session_id="bbbb")
    assert result.exported == 1
    files = [p.name for p in cfg.output.glob("*.md")]
    assert files == ["2025-12-05 - Second.md"]
    index = Index.load(cfg.output)
    assert index.contains("bbbb")
    assert not index.contains("aaaa")


def test_export_subdir_pattern(tmp_path, make_session):
    make_session()
    cfg = _cfg(tmp_path)
    cfg.filename_pattern = "{year}/{month}/{title}.md"
    run_export_pass(cfg)
    files = list(cfg.output.rglob("*.md"))
    assert len(files) == 1
    assert files[0].relative_to(cfg.output) == Path("2025/12/Design Review.md")
    index = Index.load(cfg.output)
    assert index.exported["11111111-2222-3333-4444-555555555555"]["filename"] == "2025/12/Design Review.md"


def test_export_skips_empty_session(tmp_path):
    """Сессия без transcript/memo/extra — pending (нет контента вообще)."""
    sessions_root = tmp_path / "anarlog" / "sessions" / "empty"
    sessions_root.mkdir(parents=True)
    import json
    (sessions_root / "_meta.json").write_text(
        json.dumps({"id": "empty", "title": "Empty", "created_at": "2025-01-01T00:00:00Z"}),
        encoding="utf-8",
    )
    cfg = _cfg(tmp_path)
    result = run_export_pass(cfg)
    assert result.exported == 0
    assert result.pending == 1
