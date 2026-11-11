#!/usr/bin/env bash
set -euo pipefail

echo "=== CI MIGRATION CHECK ==="

CI_PROJECT="${CI_PROJECT:-urf-ci-local}"
CI_NETWORK="${CI_PROJECT}_ci_backend"


: "${CI_DB_PASSWORD:?CI_DB_PASSWORD is required}"

docker compose \
  -p "$CI_PROJECT" \
  --env-file .env.ci \
  -f compose.ci.yaml \
  up -d --wait --wait-timeout 120

docker run --rm \
  --network "$CI_NETWORK" \
  -e CI_DB_PASSWORD="$CI_DB_PASSWORD" \
  --entrypoint sh \
  university-room-fund:lab4 \
  -c '
    export DATABASE_URL="postgresql://ci_user:${CI_DB_PASSWORD}@ci-db:5432/university_fund_ci"
    python -m alembic upgrade head
    python -m alembic current
  '

echo "=== CI MIGRATION CHECK PASSED ==="
