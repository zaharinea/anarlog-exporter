"""Управление LaunchAgent для фонового watch-режима."""

from __future__ import annotations

import os
import plistlib
import shutil
import subprocess
import sys
from pathlib import Path

LAUNCH_AGENT_LABEL = "com.zaharinea.anarlog-exporter"
LAUNCH_AGENTS_DIR = Path.home() / "Library" / "LaunchAgents"
PLIST_PATH = LAUNCH_AGENTS_DIR / f"{LAUNCH_AGENT_LABEL}.plist"
LOG_PATH = Path.home() / "Library" / "Logs" / "anarlog-exporter.log"


def _executable_args() -> list[str]:
    """Команда запуска watch — предпочтительно установленный бинарь."""
    binary = shutil.which("anarlog-exporter")
    if binary:
        return [binary, "watch"]
    return [sys.executable, "-m", "anarlog_exporter", "watch"]


def build_plist(interval: int | None = None) -> dict:
    args = _executable_args()
    if interval is not None:
        args = [*args, "--interval", str(interval)]
    return {
        "Label": LAUNCH_AGENT_LABEL,
        "ProgramArguments": args,
        "RunAtLoad": True,
        "KeepAlive": True,
        "StandardOutPath": str(LOG_PATH),
        "StandardErrorPath": str(LOG_PATH),
        "EnvironmentVariables": {
            "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
            "LANG": os.environ.get("LANG", "en_US.UTF-8"),
        },
    }


def write_plist(interval: int | None = None) -> Path:
    LAUNCH_AGENTS_DIR.mkdir(parents=True, exist_ok=True)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.touch(exist_ok=True)
    plist = build_plist(interval)
    with PLIST_PATH.open("wb") as f:
        plistlib.dump(plist, f)
    return PLIST_PATH


def _launchctl(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["launchctl", *args], capture_output=True, text=True, check=False
    )


def install(interval: int | None = None) -> None:
    path = write_plist(interval)
    _launchctl("unload", str(path))  # на случай переустановки, ошибку игнорируем
    result = _launchctl("load", "-w", str(path))
    if result.returncode != 0:
        msg = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"launchctl load failed: {msg}")
    print(f"Installed LaunchAgent: {path}")
    print(f"Logs: {LOG_PATH}")


def uninstall() -> None:
    if PLIST_PATH.exists():
        _launchctl("unload", str(PLIST_PATH))
        PLIST_PATH.unlink()
        print(f"Removed LaunchAgent: {PLIST_PATH}")
    else:
        print(f"LaunchAgent не найден: {PLIST_PATH}")


def status() -> None:
    result = _launchctl("list")
    pid_line: str | None = None
    for line in result.stdout.splitlines():
        if LAUNCH_AGENT_LABEL in line:
            pid_line = line
            break

    if pid_line is None:
        print(f"LaunchAgent {LAUNCH_AGENT_LABEL}: не запущен")
    else:
        parts = pid_line.split()
        pid, exit_code = parts[0], parts[1]
        print(f"LaunchAgent {LAUNCH_AGENT_LABEL}: pid={pid} exit={exit_code}")

    if LOG_PATH.exists():
        print(f"\nПоследние строки лога ({LOG_PATH}):")
        with LOG_PATH.open("r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()[-20:]
        for line in lines:
            print(f"  {line.rstrip()}")
    else:
        print(f"\nЛог отсутствует: {LOG_PATH}")
