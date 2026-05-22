"""CLI-интерфейс anarlog-exporter."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from . import __version__, config as cfg_mod, launchd
from .config import CONFIG_KEYS, CONFIG_PATH, apply_overrides, format_settings, load_config, save_config
from .exporter import run_export_pass, watch_loop


def _common_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--data-dir", type=Path, default=None, help="Корневой каталог данных anarlog")
    p.add_argument("--output", type=Path, default=None, help="Куда писать .md")
    p.add_argument("--template", type=Path, default=None, help="Путь к markdown-шаблону")


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="anarlog-exporter", description=__doc__)
    p.add_argument("--version", action="version", version=f"anarlog-exporter {__version__}")
    p.add_argument("-v", "--verbose", action="store_true", help="Подробный лог")
    sub = p.add_subparsers(dest="command", required=True)

    p_export = sub.add_parser("export", help="Однократный экспорт всех сессий")
    _common_args(p_export)
    p_export.add_argument("--session-id", help="Экспортировать только указанную сессию")
    p_export.add_argument("--force", action="store_true", help="Перезаписать существующие файлы")
    p_export.set_defaults(func=cmd_export)

    p_watch = sub.add_parser("watch", help="Фоновый цикл с периодической проверкой")
    _common_args(p_watch)
    p_watch.add_argument("--interval", type=int, default=None, help="Период опроса, сек")
    p_watch.set_defaults(func=cmd_watch)

    p_config = sub.add_parser("config", help="Показать/обновить конфиг")
    p_config.add_argument("--data-dir", type=Path, default=None)
    p_config.add_argument("--output", type=Path, default=None)
    p_config.add_argument("--interval", type=int, default=None)
    p_config.add_argument("--template", type=Path, default=None)
    p_config.add_argument("--filename-pattern", dest="filename_pattern", default=None)
    p_config.add_argument("--date-format", dest="date_format", default=None)
    p_config.add_argument("--time-format", dest="time_format", default=None)
    p_config.set_defaults(func=cmd_config)

    p_install = sub.add_parser("install", help="Установить LaunchAgent (фоновый watch)")
    p_install.add_argument("--interval", type=int, default=None, help="Период опроса, сек")
    p_install.set_defaults(func=cmd_install)

    p_uninstall = sub.add_parser("uninstall", help="Удалить LaunchAgent")
    p_uninstall.set_defaults(func=cmd_uninstall)

    p_status = sub.add_parser("status", help="Состояние LaunchAgent и хвост лога")
    p_status.set_defaults(func=cmd_status)

    return p


def _resolved_config(args: argparse.Namespace) -> cfg_mod.Config:
    cfg = load_config()
    overrides = {key: getattr(args, key, None) for key in CONFIG_KEYS}
    return apply_overrides(cfg, overrides)


def cmd_export(args: argparse.Namespace) -> int:
    cfg = _resolved_config(args)
    result = run_export_pass(
        cfg, only_session_id=args.session_id, force=args.force, silent_skip=False
    )
    print(
        f"\nDone: exported={result.exported} skipped={result.skipped} "
        f"pending={result.pending} failed={result.failed}"
    )
    return 1 if result.failed else 0


def cmd_watch(args: argparse.Namespace) -> int:
    cfg = _resolved_config(args)
    watch_loop(cfg)
    return 0


def cmd_config(args: argparse.Namespace) -> int:
    updates = {key: getattr(args, key, None) for key in CONFIG_KEYS}
    if any(v is not None for v in updates.values()):
        save_config(updates)
        print(f"Config saved to {CONFIG_PATH}\n")
    cfg = load_config()
    print(format_settings(cfg))
    return 0


def cmd_install(args: argparse.Namespace) -> int:
    launchd.install(interval=args.interval)
    return 0


def cmd_uninstall(_: argparse.Namespace) -> int:
    launchd.uninstall()
    return 0


def cmd_status(_: argparse.Namespace) -> int:
    launchd.status()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("Прервано пользователем", file=sys.stderr)
        return 130
    except Exception as exc:
        logging.error("%s", exc)
        if args.verbose:
            raise
        return 1


if __name__ == "__main__":
    sys.exit(main())
