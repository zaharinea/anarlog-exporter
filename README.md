# anarlog-exporter

Экспортирует встречи [anarlog](https://github.com/fastrepl/anarlog) (форк hyprnote от fastrepl) в Markdown-файлы — например, в Obsidian-vault. Может работать как фоновый сервис через `launchd` и периодически подхватывать новые транскрипции/заметки.

## Установка

Через [`pipx`](https://pipx.pypa.io/):

```bash
pipx install git+https://github.com/zaharinea/anarlog-exporter.git
```

или через [`uv`](https://docs.astral.sh/uv/):

```bash
uv tool install git+https://github.com/zaharinea/anarlog-exporter.git
```

Локально из исходников:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

## Использование

```bash
# Однократный экспорт всех сессий
anarlog-exporter export

# Только одна сессия
anarlog-exporter export --session-id <uuid>

# Перезаписать существующие файлы
anarlog-exporter export --force

# Фоновый watcher (опрос каждые N сек)
anarlog-exporter watch --interval 30

# Установить как LaunchAgent
anarlog-exporter install --interval 30
anarlog-exporter status
anarlog-exporter uninstall

# Конфиг
anarlog-exporter config                                       # показать текущие значения
anarlog-exporter config --output ~/Documents/Meetings         # обновить поле
anarlog-exporter config --filename-pattern '{date} - {title}.md'
```

## Конфиг

`~/.config/anarlog-exporter/config.toml`:

```toml
data_dir         = "/Users/me/Library/Application Support/hyprnote"
output           = "/Users/me/Documents/Meetings"
interval         = 30
template         = "/Users/me/.config/anarlog-exporter/template.md"
filename_pattern = "{date} - {title}.md"
date_format      = "%Y-%m-%d"
time_format      = "%H%M"
```

`anarlog-exporter config` без аргументов показывает текущие значения с источником:

```
Current settings:
  data_dir         = /Users/me/Library/Application Support/hyprnote (default)
  output           = /Users/me/Documents/Meetings (from config)
  interval         = 30 (default)
  template         = <built-in> (default)
  filename_pattern = {date} - {title}.md (default)
  date_format      = %Y-%m-%d (default)
  time_format      = %H%M (default)
```

### Плейсхолдеры имени файла

| Плейсхолдер | Значение |
|---|---|
| `{date}` | `created_at` по `date_format` |
| `{time}` | `created_at` по `time_format` |
| `{datetime}` | `{date} {time}` |
| `{title}` | sanitized title встречи |
| `{session_id}` | UUID сессии |
| `{year}`, `{month}`, `{day}`, `{hour}`, `{minute}` | компоненты created_at |

Паттерн может содержать `/` — будут созданы подкаталоги в `output/`.

### Шаблон markdown

Если `template` не задан, используется встроенный. Переменные через `${...}` (`string.Template`):

| Переменная | Значение |
|---|---|
| `${session_id}` | UUID |
| `${title}` | название встречи |
| `${date}` | `YYYY-MM-DD` из `created_at` |
| `${memo}` | содержимое `_memo.md` |
| `${extra_notes}` | прочие `.md` сессии, объединённые `---` |
| `${notes}` | `extra_notes` + `memo` |
| `${transcript}` | транскрипт со спикерами и таймштампами |

## Логика обнаружения нового

Состояние выводится из самих markdown-файлов в `output/`: каждый файл содержит `session_id` во frontmatter. На каждом проходе:

- Если `session_id` ещё нет в `output/` — создаём файл.
- Если есть и `mtime` сессии новее `mtime` файла — перезаписываем (новое содержание `_memo.md` / новые `.md`).
- При смене имени файла (изменился `title` или `filename_pattern`) старый файл удаляется.

## Логи (LaunchAgent)

```
~/Library/Logs/anarlog-exporter.log
```

## Разработка

```bash
pip install -e ".[dev]"
pytest -q
```
