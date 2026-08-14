# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Назначение и границы

Claude Daily Memory — Linux/Python-приложение, которое строит локальную очищенную дневную память, один раз добавляет её в Google Docs и обновляет постоянный источник NotebookLM. Эта же установка регистрирует полный локальный `notebooklm-mcp` для Claude Code. Проект находится на стадии alpha; поддерживаются Python 3.11–3.13 и пользовательский timer systemd.

Безопасность является частью контракта, а не отдельной надстройкой:

- автоматический путь не читает JSONL-стенограммы Claude Code, полные запросы/ответы, сырые команды и данные инструментов, Gmail, произвольные файлы проектов или ответы NotebookLM;
- содержимое каждого выбранного артефакта и итогового digest проходит fail-closed очистку;
- Google refresh token и Gemini API key хранятся в системном keyring; конфигурация содержит только идентификаторы и имеет режим `0600`;
- NotebookLM работает только локально через `stdio`; не добавлять HTTP transport, перенос cookies в облако, `NOTEBOOKLM_AUTH_JSON` или master-token flow;
- удаление данных и расширение общего доступа должны сохранять preview и отдельное явное подтверждение;
- Gmail-модуль только определяет точные совпадения для переноса в корзину; безвозвратное удаление не поддерживается.

## Разработка и проверки

Создать окружение с полным набором интеграций:

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[google,gemini,notebooklm]' build
```

Тесты синтетические: реальные Google/NotebookLM credentials не нужны.

```bash
# Весь набор
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests

# Один файл
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_job.py'

# Один класс или метод (tests/ не является Python-пакетом, поэтому добавьте его в PYTHONPATH)
PYTHONPATH=src:tests .venv/bin/python -m unittest test_job.JobIntegrationTests
PYTHONPATH=src:tests .venv/bin/python -m unittest test_job.JobIntegrationTests.test_drive_failure_never_calls_notebooklm
```

Обязательный порядок для изменений: сначала добавить или изменить синтетический тест и увидеть ожидаемое падение; затем внести минимальное изменение; запустить целевые тесты, после них полный набор дважды. Не ослаблять safety assertion ради зелёного теста.

Проверки релизного контракта и упаковки:

```bash
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_installer.py'
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_release_safety.py'
.venv/bin/python -m build
.venv/bin/python -m pip check
bash -n install.sh
git diff --check
```

CI также устанавливает собранный wheel в чистое окружение и проверяет `claude-daily-memory --help`, `claude-daily-memory-setup --help`, `notebooklm --help` и `notebooklm-mcp --help`. При изменении упаковки или entry points воспроизводить эту проверку локально.

## Архитектура и поток данных

### Локальный сбор

`hooks.py` получает payload событий Claude Code через stdin, принимает только разрешённые имена событий и инструментов и записывает в JSONL лишь время, тип события и HMAC-псевдонимы session/project. Hook намеренно не блокирует Claude Code при собственной ошибке.

`DailyDigestBuilder` в `digest.py` — граница чтения данных. Он:

1. читает только разрешённые типы Trailmark-артефактов (`plan`, `decision`, `note`, `report`) из SQLite в read-only режиме;
2. разрешает пути артефактов только внутри `workspace/tasks/log`;
3. агрегирует безопасные поля событий и отображает HMAC проекта в имя через `workspace/aihub/projects.yml`;
4. пропускает каждый артефакт и затем весь итог через `sanitize_text()`;
5. под файловой блокировкой атомарно пишет приватный `digest-YYYY-MM-DD.md`.

`sanitize.py` полностью отклоняет текст при известной форме секрета, высокой энтропии, неправильном типе/Markdown или превышении лимита; email, телефон и домашний путь редактируются. Не менять fail-closed результат на частичную публикацию сомнительного текста.

`audit.py` хранит только ограниченный allowlist метаданных, HMAC-идентификатор Drive и коды ошибок. Не добавлять туда содержимое, credentials, notebook/source IDs или исходные пути.

### Облачная цепочка и восстановление

`job.py` оркестрирует строго последовательную цепочку:

```text
DailyDigestBuilder → GoogleDriveMemory.append_once → NotebookLMCLI.refresh_source → state.json
```

`google_drive.py` использует официальный Drive/Docs API и узкий scope `drive.file`. Идемпотентность обеспечивается HMAC-маркером внутри документа и revision control. Если Drive не сработал, NotebookLM не вызывается. Если refresh NotebookLM не сработал, `last_successful_day` не продвигается; следующая попытка повторит refresh без дублирования записи Google Docs.

`notebooklm_integration.py` — адаптер к закреплённому CLI `notebooklm-py`. Он выбирает notebook/source по точному соответствию, отказывается при неоднозначности, запускает пассивную реальную проверку auth и регистрирует MCP из того же virtualenv с `--transport stdio`. Не заменять неизвестную существующую MCP-регистрацию.

### Установка и внешние интеграции

`install.sh` создаёт одно окружение в `~/.local/share/claude-daily-memory/venv`, устанавливает все extras и Chromium, размещает systemd units, но оставляет timer выключенным. `setup.py` после `--confirm` связывает Google Doc, локальный вход NotebookLM, постоянные notebook/source, MCP и Gemini keyring; timer включается только после успеха всех этапов. Операции setup должны оставаться повторяемыми и не создавать дубликаты.

`gemini_bridge.py` отправляет только явно переданный `--text` и без `--confirm` показывает preview. Он никогда не должен сам читать локальные файлы. `gmail_rules.py` — чистый детерминированный механизм совпадений, а не Gmail connector.

`systemd/claude-daily-memory.service` запускает `claude_daily_memory.job` в hardened oneshot unit; timer задаёт ежедневный запуск. Изменения путей, аргументов CLI, прав доступа или порядка job должны сопровождаться обновлением unit-файлов и контрактных тестов.

## Согласованность изменений

- Для любого пользовательского изменения обновлять английскую и русскую публичную документацию вместе: `README.md` / `README-RU.md`, а при затронутой теме также парные файлы в `docs/` и обе версии сайта.
- `notebooklm-py[browser,mcp]` закреплён точной версией; обновление требует просмотра upstream-изменений, threat model, документации и release-safety тестов.
- Номер релиза должен совпадать в `pyproject.toml`, `src/claude_daily_memory/__init__.py` и `CITATION.cff`.
- Перед публикацией использовать только синтетические примеры. `tests/test_release_safety.py` проверяет дерево tracked/untracked файлов на auth-артефакты, персональные пути, email и формы секретов.
- Изменения сетевых направлений требуют обновления документированной модели угроз в `SECURITY.md`.
