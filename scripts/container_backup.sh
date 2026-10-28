#!/usr/bin/env bash
set -euo pipefail

mkdir -p backups
chmod 700 backups

BACKUP_FILE="backups/backup_$(date +%Y%m%d_%H%M%S).dump"

docker compose exec -T db \
  pg_dump -U roomfund_app \
  -d university_fund \
  -Fc > "$BACKUP_FILE"

if [ ! -s "$BACKUP_FILE" ]; then
    echo "ERROR: Backup is empty"
    exit 1
fi

docker compose exec -T db \
  pg_restore -l < "$BACKUP_FILE" > /dev/null

chmod 600 "$BACKUP_FILE"

echo "Backup created: $BACKUP_FILE"
