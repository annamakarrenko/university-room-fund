#!/usr/bin/env bash
set -e

echo "=== SERVICE STATUS ==="
systemctl is-active university-room-fund

echo
echo "=== PROCESS ==="
pgrep -af "uvicorn app.main:app"

echo
echo "=== PORT 8000 ==="
ss -lnt | grep ':8000'

echo
echo "=== HEALTH CHECK ==="
curl -fsS http://127.0.0.1:8000/health

echo
echo
echo "Deployment check completed"
