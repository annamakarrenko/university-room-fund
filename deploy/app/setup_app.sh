#!/usr/bin/env bash
set -e

PROJECT_DIR="/opt/university-room-fund"

python3 -m venv "$PROJECT_DIR/.venv"
"$PROJECT_DIR/.venv/bin/pip" install -r "$PROJECT_DIR/requirements.txt"

sudo systemctl daemon-reload
sudo systemctl enable university-room-fund
sudo systemctl restart university-room-fund

echo "Application deployment completed"
