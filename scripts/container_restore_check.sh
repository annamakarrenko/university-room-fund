#!/usr/bin/env bash
set -euo pipefail

echo "=== LAB 4 RESTORE CHECK ==="

compose_test() {
  docker compose -p lab4-runtime \
    -f compose.yaml -f compose.test.yaml "$@"
}

# Verify the isolated source database.
compose_test exec -T db \
  psql -v ON_ERROR_STOP=1 \
  -U roomfund_app -d university_fund \
  -Atc "SELECT note FROM lab4_runtime_check WHERE id=1;" \
  | grep -Fx "PERSISTENCE_OK" > /dev/null

mkdir -p backups
chmod 700 backups

ID="$(date +%Y%m%d%H%M%S)-$$"
BACKUP="backups/lab4_restore_check_${ID}.dump"
VOLUME="lab4-restore-check-${ID}"
CONTAINER="lab4-restore-check-db-${ID}"

echo "[1] Create backup from isolated PostgreSQL"
compose_test exec -T db \
  pg_dump -U roomfund_app -d university_fund -Fc \
  > "$BACKUP"

chmod 600 "$BACKUP"
test -s "$BACKUP"

compose_test exec -T db \
  pg_restore -l < "$BACKUP" > /dev/null

echo "PASS: Backup created and validated"

echo "[2] Create new Docker volume"
docker volume create "$VOLUME"

DB_IMAGE="$(compose_test config --format json | python3 -c \
  'import json,sys; print(json.load(sys.stdin)["services"]["db"]["image"])')"

DB_PASSWORD="$(sed -n 's/^DB_PASSWORD=//p' .env)"
test -n "$DB_PASSWORD"

docker run -d \
  --name "$CONTAINER" \
  -e POSTGRES_USER=roomfund_app \
  -e POSTGRES_DB=university_fund \
  -e POSTGRES_PASSWORD="$DB_PASSWORD" \
  --mount "type=volume,source=$VOLUME,target=/var/lib/postgresql/data" \
  "$DB_IMAGE" > /dev/null

echo "[3] Wait for PostgreSQL"

READY=0
for i in $(seq 1 60); do
  if docker exec "$CONTAINER" \
    pg_isready -U roomfund_app -d university_fund \
    > /dev/null 2>&1; then
    READY=1
    break
  fi
  sleep 2
done

if [ "$READY" -ne 1 ]; then
  echo "FAIL: Restored PostgreSQL is not ready"
  exit 1
fi

echo "[4] Restore database"
docker exec -i "$CONTAINER" \
  pg_restore -U roomfund_app -d university_fund \
  --no-owner --no-acl --exit-on-error \
  < "$BACKUP"

echo "[5] Verify recovered data"

RESTORED="$(docker exec "$CONTAINER" \
  psql -v ON_ERROR_STOP=1 \
  -U roomfund_app -d university_fund \
  -Atc "SELECT note FROM lab4_runtime_check WHERE id=1;")"

if [ "$RESTORED" != "PERSISTENCE_OK" ]; then
  echo "FAIL: Restored data differs from source"
  exit 1
fi

echo "PASS: Restored data = $RESTORED"

docker exec "$CONTAINER" \
  psql -U roomfund_app -d university_fund \
  -c "SELECT version_num FROM alembic_version;"

echo "Backup: $BACKUP"
echo "Restored container: $CONTAINER"
echo "New volume: $VOLUME"
echo "=== RESTORE CHECK PASSED ==="
