"""Конфигурация anarlog-exporter."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

CONFIG_DIR = Path.home() / ".config" / "anarlog-exporter"
CONFIG_PATH = CONFIG_DIR / "config.toml"

DEFAULT_DATA_DIR = Path.home() / "Library" / "Application Support" / "hyprnote"
DEFAULT_OUTPUT = Path.home() / "Documents" / "AnarlogExporter"
DEFAULT_INTERVAL = 30
DEFAULT_FILENAME_PATTERN = "{date} - {title}.md"
DEFAULT_DATE_FORMAT = "%Y-%m-%d"
DEFAULT_TIME_FORMAT = "%H%M"

CONFIG_KEYS = (
    "data_dir",
    "output",
    "interval",
    "template",
    "filename_pattern",
    "date_format",
    "time_format",
)


@dataclass
class Config:
    data_dir: Path = DEFAULT_DATA_DIR
    output: Path = DEFAULT_OUTPUT
    interval: int = DEFAULT_INTERVAL
    template: Path | None = None
    filename_pattern: str = DEFAULT_FILENAME_PATTERN
    date_format: str = DEFAULT_DATE_FORMAT
    time_format: str = DEFAULT_TIME_FORMAT
    sources: dict[str, str] = field(default_factory=dict)

    @property
    def sessions_dir(self) -> Path:
        return self.data_dir / "sessions"


def _expand(value: str) -> str:
    return os.path.expanduser(os.path.expandvars(value))


def load_raw() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {}
    with CONFIG_PATH.open("rb") as f:
        return tomllib.load(f)


def load_config() -> Config:
    raw = load_raw()
    cfg = Config()
    for key in CONFIG_KEYS:
        if key in raw:
            value = raw[key]
            if key in {"data_dir", "output", "template"}:
                setattr(cfg, key, Path(_expand(str(value))))
            else:
                setattr(cfg, key, value)
            cfg.sources[key] = "from config"
        else:
            cfg.sources[key] = "default"
    return cfg


def save_config(updates: dict[str, Any]) -> None:
    raw = load_raw()
    for key, value in updates.items():
        if value is None:
            continue
        if isinstance(value, Path):
            raw[key] = str(value)
        else:
            raw[key] = value
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    lines = []
    for key in CONFIG_KEYS:
        if key not in raw:
            continue
        val = raw[key]
        if isinstance(val, int):
            lines.append(f"{key} = {val}")
        else:
            lines.append(f'{key} = "{_toml_escape(str(val))}"')
    CONFIG_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _toml_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def apply_overrides(cfg: Config, overrides: dict[str, Any]) -> Config:
    """Применяет CLI-флаги (если не None) поверх загруженного конфига."""
    for key, value in overrides.items():
        if value is None:
            continue
        if key in {"data_dir", "output", "template"}:
            setattr(cfg, key, Path(_expand(str(value))))
        else:
            setattr(cfg, key, value)
        cfg.sources[key] = "from CLI"
    return cfg


def format_settings(cfg: Config) -> str:
    """Отрисовывает конфиг в человекочитаемом виде с источником значений."""
    rows = [
        ("data_dir", cfg.data_dir),
        ("output", cfg.output),
        ("interval", cfg.interval),
        ("template", cfg.template if cfg.template else "<built-in>"),
        ("filename_pattern", cfg.filename_pattern),
        ("date_format", cfg.date_format),
        ("time_format", cfg.time_format),
    ]
    width = max(len(name) for name, _ in rows)
    out = ["Current settings:"]
    for name, value in rows:
        src = cfg.sources.get(name, "default")
        out.append(f"  {name:<{width}} = {value} ({src})")
    return "\n".join(out)
