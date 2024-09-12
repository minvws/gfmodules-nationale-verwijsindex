#!/usr/bin/env bash

set -e

DB_STARTUP_WAIT=1

DB_HOST=${1}
DB_USER=${2:-postgres}
DB_PASS=${3:-postgres}
DB_NAME=${4:-postgres}

export PGPASSWORD=$DB_PASS

set +e
psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT 1" >/dev/null
while [ $? -ne 0 ]; do
  echo "Waiting for db container to finish startup..."
  sleep $DB_STARTUP_WAIT
  psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "SELECT 1" >/dev/null
done
set -e

echo "➡️ Generating TLS certificates"
./tools/generate_certs.sh

echo "➡️ Creating the configuration file"
if [ -e app.conf ]; then
    echo "⚠️ Configuration file already exists. Skipping."
else
    cp app.conf.autopilot app.conf
fi

echo "Migrating"
tools/./migrate_db.sh $DB_HOST $DB_USER $DB_PASS $DB_NAME

echo "Seeding"
tools/./seed.sh $DB_HOST $DB_USER $DB_PASS $DB_NAME

echo "Start main process"
python -m app.main
