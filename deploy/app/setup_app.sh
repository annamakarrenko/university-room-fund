#!/usr/bin/env bash
set -e

PROJECT_DIR="/opt/university-room-fund"
SERVICE_FILE="$PROJECT_DIR/deploy/app/university-room-fund.service"

python3 -m venv "$PROJECT_DIR/.venv"
"$PROJECT_DIR/.venv/bin/pip" install -r "$PROJECT_DIR/requirements.txt"

sudo cp "$SERVICE_FILE" /etc/systemd/system/university-room-fund.service

sudo systemctl daemon-reload
sudo systemctl enable university-room-fund
sudo systemctl restart university-room-fund

echo "Application deployment completed"
