#!/usr/bin/env bash
set -euo pipefail
umask 077

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
APP_DIR="${HOME}/.local/share/claude-daily-memory"
CONFIG_DIR="${HOME}/.config/claude-daily-memory"
STATE_DIR="${HOME}/.local/state/claude-daily-memory"
UNIT_DIR="${HOME}/.config/systemd/user"

if [[ "${1:-}" == "--disable" ]]; then
  systemctl --user disable --now claude-daily-memory.timer 2>/dev/null || true
  printf '%s\n' "Claude Daily Memory timer disabled. Documents, credentials, and local history were not deleted."
  exit 0
fi

python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' || {
  printf '%s\n' "Python 3.11 or newer is required." >&2
  exit 1
}

install -d -m 0700 "${APP_DIR}" "${CONFIG_DIR}" "${STATE_DIR}" "${UNIT_DIR}"
python3 -m venv "${APP_DIR}/venv"
"${APP_DIR}/venv/bin/python" -m pip install "${PROJECT_DIR}[google]"

if [[ ! -f "${CONFIG_DIR}/hmac.key" ]]; then
  "${APP_DIR}/venv/bin/python" -c 'import secrets,sys; sys.stdout.buffer.write(secrets.token_bytes(32))' > "${CONFIG_DIR}/hmac.key"
fi
chmod 0600 "${CONFIG_DIR}/hmac.key"
install -m 0600 "${PROJECT_DIR}/systemd/claude-daily-memory.service" "${UNIT_DIR}/claude-daily-memory.service"
install -m 0600 "${PROJECT_DIR}/systemd/claude-daily-memory.timer" "${UNIT_DIR}/claude-daily-memory.timer"
systemctl --user daemon-reload
systemctl --user disable --now claude-daily-memory.timer 2>/dev/null || true

printf '%s\n' "Installed safely. The timer is staged but remains off until Google OAuth setup is completed."
printf '%s\n' "After OAuth setup, enable it with: systemctl --user enable --now claude-daily-memory.timer"
