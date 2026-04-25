#!/bin/bash
# Daily PostgreSQL backup — production
# Runs inside the postgres_backup-prod container (postgres:15 image).
# Env vars injected from .env via docker-compose env_file.
set -euo pipefail

DATE=$(date +"%Y-%m-%d_%H-%M-%S")
BACKUP_DIR="/backups"
DB_NAME="${POSTGRES_DB:-lexora}"
DB_USER="${POSTGRES_USER:-odoo}"
DB_HOST="${POSTGRES_HOST:-postgres-prod}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"

LOG_PREFIX="[backup-prod] $(date '+%Y-%m-%d %H:%M:%S')"

echo "$LOG_PREFIX Starting production backup of '$DB_NAME' on '$DB_HOST'..."
mkdir -p "$BACKUP_DIR"

# ── Custom-format dump (primary — compressed, parallel-restore capable) ───────
DUMP_FILE="$BACKUP_DIR/backup_${DB_NAME}_${DATE}.dump"
pg_dump \
    -h "$DB_HOST" -U "$DB_USER" \
    --format=custom \
    --compress=9 \
    "$DB_NAME" > "$DUMP_FILE"
DUMP_SIZE=$(du -sh "$DUMP_FILE" | cut -f1)
echo "$LOG_PREFIX Custom dump: $(basename "$DUMP_FILE") ($DUMP_SIZE)"

# ── Plain SQL dump (secondary — human-readable fallback) ─────────────────────
SQL_FILE="$BACKUP_DIR/backup_${DB_NAME}_${DATE}.sql"
pg_dump -h "$DB_HOST" -U "$DB_USER" "$DB_NAME" > "$SQL_FILE"
SQL_SIZE=$(du -sh "$SQL_FILE" | cut -f1)
echo "$LOG_PREFIX SQL dump: $(basename "$SQL_FILE") ($SQL_SIZE)"

# ── Sanity check ─────────────────────────────────────────────────────────────
DUMP_BYTES=$(stat -c%s "$DUMP_FILE")
SQL_BYTES=$(stat -c%s "$SQL_FILE")
if [ "$DUMP_BYTES" -lt 512 ] || [ "$SQL_BYTES" -lt 1024 ]; then
    echo "$LOG_PREFIX ERROR: backup file(s) are suspiciously small. Check DB connectivity." >&2
    exit 1
fi

# ── Retention ────────────────────────────────────────────────────────────────
echo "$LOG_PREFIX Pruning backups older than ${RETENTION_DAYS} days..."
find "$BACKUP_DIR" -maxdepth 1 \
    \( -name "backup_*.sql" -o -name "backup_*.dump" \) \
    -mtime "+${RETENTION_DAYS}" -print -delete

REMAINING=$(find "$BACKUP_DIR" -maxdepth 1 \
    \( -name "backup_*.sql" -o -name "backup_*.dump" \) | wc -l)
echo "$LOG_PREFIX Retention done. ${REMAINING} backup file(s) retained."
echo "$LOG_PREFIX Production backup finished successfully."
