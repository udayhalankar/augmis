#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKUP_DIR="/mnt/d/Backups/Infomentica_Backup"
CRON_SCHEDULE="${1:-*/15 * * * *}"
CRON_COMMAND="cd $REPO_ROOT && $REPO_ROOT/scripts/backup_code.sh >> $BACKUP_DIR/backup.log 2>&1"

mkdir -p "$BACKUP_DIR"

CURRENT_CRONTAB="$(mktemp)"
trap 'rm -f "$CURRENT_CRONTAB"' EXIT

if crontab -l > "$CURRENT_CRONTAB" 2>/dev/null; then
  true
else
  : > "$CURRENT_CRONTAB"
fi

if grep -Fq "$REPO_ROOT/scripts/backup_code.sh" "$CURRENT_CRONTAB"; then
  echo "Backup cron entry already exists."
  exit 0
fi

printf "%s %s\n" "$CRON_SCHEDULE" "$CRON_COMMAND" >> "$CURRENT_CRONTAB"
crontab "$CURRENT_CRONTAB"

echo "Installed backup cron entry:"
echo "$CRON_SCHEDULE $CRON_COMMAND"
