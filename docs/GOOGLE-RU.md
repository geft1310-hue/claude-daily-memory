# Настройка Google и Gemini

[English](GOOGLE.md)

Claude Daily Memory использует одну команду настройки. Google Drive/Docs дают растущий документ-источник, Gemini устанавливается в то же окружение приложения, а связь с NotebookLM создаётся в том же сценарии.

## 1. Создать проект Google Cloud

1. Откройте <https://console.cloud.google.com/>.
2. Создайте или выберите проект.
3. Включите **Google Drive API** и **Google Docs API**.
4. Настройте экран согласия OAuth. Для личного использования достаточно тестового режима и вашего аккаунта в списке тестовых пользователей.
5. Создайте OAuth-клиент типа **Приложение для компьютера (Desktop app)** и скачайте JSON.

## 2. Положить OAuth-клиент в защищённое место

```bash
mkdir -p ~/.config/claude-daily-memory
mv ~/Загрузки/client_secret_*.json ~/.config/claude-daily-memory/google-client.json
chmod 600 ~/.config/claude-daily-memory/google-client.json
```

Никогда не добавляйте этот файл в GitHub.

## 3. Подготовить ключ Gemini Developer API

Создайте ключ Gemini API в Google AI Studio. Не вставляйте его в команду, `.env`, задачу GitHub или файл проекта. Единая настройка запросит ключ скрытым вводом и сохранит в системном хранилище паролей: service `claude-daily-memory`, account `gemini-api-key`.

Vertex AI не используется по умолчанию. Отдельный мост явного текста включает его только при намеренно указанном `--project`.

## 4. Запустить единую настройку

Сначала безопасный просмотр без изменений:

```bash
~/.local/share/claude-daily-memory/venv/bin/claude-daily-memory-setup \
  --client ~/.config/claude-daily-memory/google-client.json \
  --config ~/.config/claude-daily-memory/config.json
```

Затем подтверждённый запуск:

```bash
~/.local/share/claude-daily-memory/venv/bin/claude-daily-memory-setup \
  --client ~/.config/claude-daily-memory/google-client.json \
  --config ~/.config/claude-daily-memory/config.json \
  --confirm
```

В браузере запрашивается только `drive.file`. Refresh token сохраняется в системном keyring. Настройка создаёт или повторно использует документ Google, выполняет локальный вход и привязку NotebookLM, регистрирует локальный stdio MCP, запрашивает отсутствующий ключ Gemini, обновляет источник NotebookLM и только затем включает timer.

Приватная конфигурация содержит идентификаторы для безопасных повторных попыток. В ней нет refresh token Google, ключа Gemini, cookies NotebookLM или master token.

## 5. Проверить

```bash
systemctl --user status claude-daily-memory.timer
claude mcp get notebooklm
```

Восстановление входа и устройство MCP описаны в [NOTEBOOKLM-RU.md](NOTEBOOKLM-RU.md).

## Отключить или отозвать доступ

```bash
systemctl --user disable --now claude-daily-memory.timer
```

Отзовите приложение в настройках безопасности аккаунта Google. При необходимости удалите ключ Gemini через системный менеджер паролей. Выход из NotebookLM и удаление локальной сессии выполняются только на компьютере; не отправляйте браузерное состояние в поддержку.
