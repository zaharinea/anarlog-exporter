"""Индекс уже экспортированных сессий.

Хранится рядом с output: `<output>/.anarlog-exporter-index.json`.
Если session_id в индексе — больше на эту сессию не смотрим.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

INDEX_FILENAME = ".anarlog-exporter-index.json"
INDEX_VERSION = 1


@dataclass
class Index:
    path: Path
    exported: dict[str, dict]  # session_id -> {"filename": str, "exported_at": str}

    @classmethod
    def load(cls, output_dir: Path) -> "Index":
        path = output_dir / INDEX_FILENAME
        if not path.exists():
            return cls(path=path, exported={})
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            return cls(path=path, exported=dict(raw.get("exported", {})))
        except (json.JSONDecodeError, OSError):
            return cls(path=path, exported={})

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"version": INDEX_VERSION, "exported": self.exported}
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        tmp.replace(self.path)

    def contains(self, session_id: str) -> bool:
        return session_id in self.exported

    def add(self, session_id: str, filename: str) -> None:
        self.exported[session_id] = {
            "filename": filename,
            "exported_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }

    def remove(self, session_id: str) -> None:
        self.exported.pop(session_id, None)
