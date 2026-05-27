#!/usr/bin/env bash

set -e

GREEN="\033[32m"
YELLOW="\033[33m"
BLUE="\033[34m"
NC="\033[0m"

SCRIPT=$(readlink -f $0)
BASEDIR=$(dirname $SCRIPT)/..

echo -e "${GREEN}👀 Checking migrations ${NC}"

# check if the migration table exists
if
  psql $DSN -t -c "\dt" | grep 'migrations' >/dev/null
  [ $? -eq 1 ]
then
  echo -e "${YELLOW}⚠️ Migration table does not exists. Creating migrations table.${NC}"

  # create the migration table
  echo "CREATE TABLE migrations (id serial PRIMARY KEY, name VARCHAR(255) NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);" | psql $DSN -q -o /dev/null
fi

for file in $BASEDIR/sql/*.sql; do
  # Check if the file name is already in the migrations table
  if psql $DSN -t -c "SELECT name FROM migrations WHERE name = '$file';" | grep -q $file; then
    echo -e "${YELLOW}⏩ File $file is already in the migrations table. Skipping.${NC}"
  else
    PENDING_MIGRATIONS+=("$file")
  fi
done

if [ ${#PENDING_MIGRATIONS[@]} -eq 0 ]; then
  echo "✅ All migrations are up to date."
  exit 0
fi

echo -e "${BLUE}🏗️ Compiling and applying all pending migrations... ${NC}"

if [ ${#PENDING_MIGRATIONS[@]} -eq 0 ]; then
  echo "✅ All migrations are up to date."
  exit 0
fi

echo -e "${BLUE}🏗️ Compiling and applying all pending migrations in a single transaction... ${NC}"

# 1. Create and populate the temporary SQL file
TEMP_FILE=$(mktemp /tmp/migration_combined.XXXXXX.sql)
echo "BEGIN;" > $TEMP_FILE # Ensure migrations are applied in a single transaction
echo "SET timezone = 'UTC';" >> $TEMP_FILE # Ensure consistent timezone handling

# Append all migration files
for file in "${PENDING_MIGRATIONS[@]}"; do
  echo "--------------------------------------------------" >> "$TEMP_FILE"
  echo "-- Migration file: $file" >> "$TEMP_FILE"
  cat "$file" >> "$TEMP_FILE"
done

# Append the migration logging statements
echo "" >> "$TEMP_FILE"
echo "--------------------------------------------------" >> "$TEMP_FILE"
echo "-- Record migrations in the table" >> "$TEMP_FILE"
for file in "${PENDING_MIGRATIONS[@]}"; do
  echo "INSERT INTO migrations (name) VALUES ('$file');" >> "$TEMP_FILE"
done

# Commit whole migration
echo "COMMIT;" >> $TEMP_FILE

# 2. Apply the combined migration file
if psql -v ON_ERROR_STOP=1 $DSN -f "$TEMP_FILE" -q -o /dev/null; then
  echo "✅ Successfully applied all migrations and recorded them."
else
  echo -e "${RED}❌ Failed to apply migrations. Transaction rolled back. Changes were not applied.${NC}"
fi

# Clean up the temporary file
rm -f $TEMP_FILE
