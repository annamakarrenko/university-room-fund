#!/usr/bin/env bash
set -euo pipefail

BACKUP_FILE="${1:?Usage: container_restore.sh BACKUP_FILE}"

if [ ! -s "$BACKUP_FILE" ]; then
    echo "ERROR: Backup file is missing or empty"
    exit 1
fi

DB_IMAGE=$(docker compose config --format json | python3 -c '
import json,sys
print(json.load(sys.stdin)["services"]["db"]["image"])
')

RESTORE_ID=$(date +%Y%m%d%H%M%S)
VOLUME="lab4-restore-${RESTORE_ID}"
CONTAINER="lab4-restore-db-${RESTORE_ID}"

DB_PASSWORD=$(sed -n 's/^DB_PASSWORD=//p' .env)

if [ -z "$DB_PASSWORD" ]; then
    echo "ERROR: DB_PASSWORD is missing"
    exit 1
fi

docker volume create "$VOLUME"

docker run -d \
    --name "$CONTAINER" \
    -e POSTGRES_USER=roomfund_app \
    -e POSTGRES_DB=university_fund \
    -e POSTGRES_PASSWORD="$DB_PASSWORD" \
    -v "$VOLUME:/var/lib/postgresql/data" \
    "$DB_IMAGE" > /dev/null

echo "Waiting for restored PostgreSQL..."

READY=0
for i in $(seq 1 30); do
    if docker exec "$CONTAINER" \
        pg_isready -U roomfund_app -d university_fund \
        > /dev/null 2>&1; then
        READY=1
        break
    fi
    sleep 2
done

if [ "$READY" -ne 1 ]; then
    echo "ERROR: PostgreSQL is not ready"
    exit 1
fi

docker exec -i "$CONTAINER" \
    pg_restore \
    -U roomfund_app \
    -d university_fund \
    --no-owner \
    --no-acl \
    --exit-on-error \
    < "$BACKUP_FILE"

echo "Restore completed"
echo "Container: $CONTAINER"
echo "Volume: $VOLUME"

docker exec "$CONTAINER" \
    psql -U roomfund_app -d university_fund \
    -c "SELECT * FROM lab4_persistence_test;"
