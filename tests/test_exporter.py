from pathlib import Path

import pytest

from anarlog_exporter.config import Config
from anarlog_exporter.exporter import build_id_mapping, run_export_pass


def _cfg(tmp_path: Path) -> Config:
    return Config(
        data_dir=tmp_path / "anarlog",
        output=tmp_path / "out",
    )


def test_export_creates_file(tmp_path, make_session):
    make_session()
    cfg = _cfg(tmp_path)
    result = run_export_pass(cfg)
    assert result.exported == 1
    files = list(cfg.output.glob("*.md"))
    assert len(files) == 1
    assert files[0].name == "2025-12-05 - Design Review.md"
    content = files[0].read_text(encoding="utf-8")
    assert "session_id: 11111111-2222-3333-4444-555555555555" in content


def test_export_is_idempotent(tmp_path, make_session):
    make_session()
    cfg = _cfg(tmp_path)
    run_export_pass(cfg)
    second = run_export_pass(cfg)
    assert second.exported == 0
    assert second.skipped == 1


def test_export_force_overwrites(tmp_path, make_session):
    make_session()
    cfg = _cfg(tmp_path)
    run_export_pass(cfg)
    out_file = next(cfg.output.glob("*.md"))
    # Ставим mtime файла в будущее, чтобы обычный проход его пропускал,
    # и проверяем, что force всё равно перезапишет.
    import os
    future = out_file.stat().st_mtime + 100_000
    os.utime(out_file, (future, future))

    skip = run_export_pass(cfg)
    assert skip.skipped == 1 and skip.updated == 0

    result = run_export_pass(cfg, force=True)
    assert result.updated == 1
    content = out_file.read_text(encoding="utf-8")
    assert "session_id: 11111111-2222-3333-4444-555555555555" in content


def test_export_filters_by_session_id(tmp_path, make_session):
    make_session(session_id="aaaa", title="First")
    make_session(session_id="bbbb", title="Second")
    cfg = _cfg(tmp_path)
    result = run_export_pass(cfg, only_session_id="bbbb")
    assert result.exported == 1
    files = [p.name for p in cfg.output.glob("*.md")]
    assert files == ["2025-12-05 - Second.md"]


def test_export_renames_when_pattern_changes(tmp_path, make_session):
    make_session()
    cfg = _cfg(tmp_path)
    run_export_pass(cfg)
    old = next(cfg.output.glob("*.md"))
    cfg.filename_pattern = "{date} {time} - {title}.md"
    result = run_export_pass(cfg, force=True)
    assert result.updated == 1
    assert not old.exists()
    new_files = list(cfg.output.glob("*.md"))
    assert len(new_files) == 1
    assert new_files[0].name == "2025-12-05 1430 - Design Review.md"


def test_export_subdir_pattern(tmp_path, make_session):
    make_session()
    cfg = _cfg(tmp_path)
    cfg.filename_pattern = "{year}/{month}/{title}.md"
    run_export_pass(cfg)
    files = list(cfg.output.rglob("*.md"))
    assert len(files) == 1
    assert files[0].relative_to(cfg.output) == Path("2025/12/Design Review.md")


def test_export_picks_up_modified_session(tmp_path, make_session):
    sdir = make_session()
    cfg = _cfg(tmp_path)
    run_export_pass(cfg)
    out_file = next(cfg.output.glob("*.md"))
    # обновляем mtime у memo, чтобы он был новее output-файла
    memo = sdir / "_memo.md"
    new_mtime = out_file.stat().st_mtime + 10
    import os
    os.utime(memo, (new_mtime, new_mtime))
    memo.write_text(memo.read_text(encoding="utf-8") + "\nДоп изменения.", encoding="utf-8")
    os.utime(memo, (new_mtime, new_mtime))
    result = run_export_pass(cfg)
    assert result.updated == 1


def test_build_id_mapping(tmp_path, make_session):
    make_session()
    cfg = _cfg(tmp_path)
    run_export_pass(cfg)
    mapping = build_id_mapping(cfg.output)
    assert "11111111-2222-3333-4444-555555555555" in mapping


def test_export_skips_empty_session(tmp_path):
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
    assert result.skipped == 1
