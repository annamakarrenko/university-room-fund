#!/usr/bin/env bash
set -e

DB_NAME="university_fund"
DB_USER="roomfund_app"
APP_IP="192.168.56.10"

if [ -z "$DB_PASSWORD" ]; then
    echo "Set DB_PASSWORD before running this script"
    exit 1
fi

sudo apt update
sudo apt install -y postgresql postgresql-contrib ufw

sudo -u postgres psql -tc \
  "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" \
  | grep -q 1 \
  || sudo -u postgres psql -c \
  "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"

sudo -u postgres psql -tc \
  "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" \
  | grep -q 1 \
  || sudo -u postgres psql -c \
  "CREATE DATABASE $DB_NAME OWNER $DB_USER;"

sudo -u postgres psql -c \
  "REVOKE ALL ON DATABASE $DB_NAME FROM PUBLIC;"

sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp
sudo ufw allow from "$APP_IP" to any port 5432 proto tcp

echo "Database preparation completed"
