#!/usr/bin/env bash

set -e

GREEN="\033[32m"
YELLOW="\033[33m"
BLUE="\033[34m"
NC="\033[0m"

source <(grep dsn app.conf | sed -r 's/\+psycopg//')

echo -e "${GREEN}👀 Checking seed migrations ${NC}"

# check if the seed_migrations table exists
if
  psql $dsn -t -c "\dt" | grep 'seed_migrations' >/dev/null
  [ $? -eq 1 ]
then
  echo -e "${YELLOW}⚠️ Seed migration table does not exists. Creating seed migrations table.${NC}"

  # create the seed_migrations table
  echo "CREATE TABLE seed_migrations (id serial PRIMARY KEY, name VARCHAR(255) NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);" | psql $dsn -q -o /dev/null
fi

for file in seed-sql/*.sql; do
  # Check each SQL file to see if it's already in the migrations table
  if psql $dsn -c "SELECT name FROM seed_migrations WHERE name = '$file';" | grep -q $file; then
    echo -e "${YELLOW}⏩ File $file is already in the seed_migrations table. Skipping.${NC}"
  else
    echo -e "${GREEN}▶️ Running seed_migrations $file${NC}"
    psql $dsn -f $file -q -o /dev/null
    echo "INSERT INTO seed_migrations (name) VALUES ('$file');" | psql $dsn -o /dev/null
  fi
done
