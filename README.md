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

# Перезаписать все завершённые сессии (игнорирует индекс)
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

Состояние ведётся в индексе рядом с output:

```
<output>/.anarlog-exporter-index.json
```

Формат: `{session_id: {filename, exported_at}}`.

На каждом проходе:

1. **Сессия в индексе** → skip, мы её больше не читаем и не трогаем.
2. **Сессия не в индексе** и **завершена** → рендерим .md, пишем в `output/`, добавляем session_id в индекс.
3. **Сессия не в индексе** и **не завершена** → pending, ждём следующего прохода.

«Завершённой» считается сессия, у которой в `~/Library/Application Support/hyprnote/sessions/<uuid>/` есть хотя бы один `.md` помимо `_memo.md` (anarlog кладёт туда сгенерированную LLM-заметку под разными именами: `_summary.md`, `Simple Meeting.md`, `1_1 Meeting.md`, имя шаблона ...).

**Важно:** сам `output/` не сканируется. Если файл там удалили вручную или анарлог потом добавил новые `.md` — экспортёр об этом не узнает. Чтобы переэкспортировать конкретную сессию: либо удалить её session_id из индекса, либо запустить `export --force` (полный re-export всех сессий, помеченных как завершённые).

При первом запуске (индекса нет) — все завершённые сессии экспортируются заново.

## Логи (LaunchAgent)

```
~/Library/Logs/anarlog-exporter.log
```

## Разработка

```bash
pip install -e ".[dev]"
pytest -q
```
