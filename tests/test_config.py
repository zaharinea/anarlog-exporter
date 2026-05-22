from pathlib import Path

import pytest

from anarlog_exporter import config as cfg_mod


@pytest.fixture
def isolated_config(tmp_path, monkeypatch):
    """Перенаправляет CONFIG_DIR/PATH в tmp_path."""
    monkeypatch.setattr(cfg_mod, "CONFIG_DIR", tmp_path / ".config")
    monkeypatch.setattr(cfg_mod, "CONFIG_PATH", tmp_path / ".config" / "config.toml")
    return tmp_path


def test_load_config_defaults(isolated_config):
    cfg = cfg_mod.load_config()
    assert cfg.interval == cfg_mod.DEFAULT_INTERVAL
    assert cfg.filename_pattern == cfg_mod.DEFAULT_FILENAME_PATTERN
    assert all(src == "default" for src in cfg.sources.values())


def test_save_and_reload_config(isolated_config):
    cfg_mod.save_config({
        "output": Path("/tmp/anarlog-out"),
        "interval": 60,
        "filename_pattern": "{date} {time} - {title}.md",
    })
    cfg = cfg_mod.load_config()
    assert cfg.output == Path("/tmp/anarlog-out")
    assert cfg.interval == 60
    assert cfg.filename_pattern == "{date} {time} - {title}.md"
    assert cfg.sources["interval"] == "from config"
    assert cfg.sources["template"] == "default"


def test_apply_overrides(isolated_config):
    cfg = cfg_mod.load_config()
    cfg_mod.apply_overrides(cfg, {"interval": 10, "output": Path("/tmp/x")})
    assert cfg.interval == 10
    assert cfg.output == Path("/tmp/x")
    assert cfg.sources["interval"] == "from CLI"


def test_format_settings_renders_all_keys(isolated_config):
    cfg = cfg_mod.load_config()
    text = cfg_mod.format_settings(cfg)
    for key in ("data_dir", "output", "interval", "template", "filename_pattern"):
        assert key in text
    assert "(default)" in text
