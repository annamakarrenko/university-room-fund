#!/usr/bin/env bash
set -euo pipefail

echo "=== LAB 4 RUNTIME CHECK ==="

docker_compose() {
  docker compose -p lab4-runtime \
    -f compose.yaml -f compose.test.yaml "$@"
}

echo "[1] Check application readiness"
docker_compose up -d --wait --wait-timeout 120
curl --fail --silent --show-error \
  http://127.0.0.1:18000/health
echo

echo "[2] Check application user"
APP_UID=$(docker_compose exec -T app id -u)

if [ "$APP_UID" != "10001" ]; then
  echo "FAIL: Unexpected UID $APP_UID"
  exit 1
fi

echo "PASS: Application UID is 10001"

echo "[3] Check database persistence"

docker_compose exec -T db \
  psql -v ON_ERROR_STOP=1 \
  -U roomfund_app -d university_fund \
  -c "CREATE TABLE IF NOT EXISTS lab4_runtime_check (id INTEGER PRIMARY KEY, note TEXT NOT NULL);"

docker_compose exec -T db \
  psql -v ON_ERROR_STOP=1 \
  -U roomfund_app -d university_fund \
  -c "INSERT INTO lab4_runtime_check VALUES (1, 'PERSISTENCE_OK') ON CONFLICT (id) DO UPDATE SET note=EXCLUDED.note;"

docker_compose up -d --force-recreate \
  --wait --wait-timeout 120

RESULT=$(docker_compose exec -T db \
  psql -U roomfund_app -d university_fund \
  -Atc "SELECT note FROM lab4_runtime_check WHERE id=1;")

if [ "$RESULT" != "PERSISTENCE_OK" ]; then
  echo "FAIL: Database persistence check"
  exit 1
fi

echo "PASS: Data survived recreation"

echo "[4] Check graceful shutdown"
docker_compose stop -t 15 app

APP_CONTAINER=$(docker_compose ps -a -q app)

EXIT_CODE=$(docker inspect "$APP_CONTAINER" \
  --format '{{.State.ExitCode}}')

OOM_KILLED=$(docker inspect "$APP_CONTAINER" \
  --format '{{.State.OOMKilled}}')

if [ "$EXIT_CODE" != "0" ] || \
   [ "$OOM_KILLED" != "false" ]; then
  echo "FAIL: Graceful shutdown"
  exit 1
fi

echo "PASS: Graceful shutdown"

echo "[5] Restart application"
docker_compose up -d --wait --wait-timeout 120

echo "=== RUNTIME CHECK PASSED ==="
