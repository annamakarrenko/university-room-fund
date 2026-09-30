#!/usr/bin/env bash
set -e

DB_NAME="university_fund"
DB_USER="roomfund_app"
APP_IP="192.168.56.10"
DB_IP="192.168.56.20"

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

PG_VERSION=$(ls /etc/postgresql | head -n 1)
PG_CONF="/etc/postgresql/$PG_VERSION/main/postgresql.conf"
PG_HBA="/etc/postgresql/$PG_VERSION/main/pg_hba.conf"

sudo sed -i \
  "s/^#listen_addresses = 'localhost'/listen_addresses = '$DB_IP'/" \
  "$PG_CONF"

if ! grep -q "$APP_IP/32" "$PG_HBA"; then
    echo "host    $DB_NAME    $DB_USER    $APP_IP/32    scram-sha-256" \
    | sudo tee -a "$PG_HBA"
fi

sudo systemctl restart postgresql

sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp
sudo ufw allow from "$APP_IP" to any port 5432 proto tcp
sudo ufw --force enable

echo "Database preparation completed"
