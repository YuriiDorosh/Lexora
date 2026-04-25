#!/bin/bash
# Daily PostgreSQL backup — dev/staging
# Runs inside the postgres_backup container (postgres:15 image).
# Env vars injected from .env via docker-compose env_file.
set -euo pipefail

DATE=$(date +"%Y-%m-%d_%H-%M-%S")
BACKUP_DIR="/backups"
DB_NAME="${POSTGRES_DB:-lexora}"
DB_USER="${POSTGRES_USER:-odoo}"
DB_HOST="${POSTGRES_HOST:-postgres}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"

LOG_PREFIX="[backup] $(date '+%Y-%m-%d %H:%M:%S')"

echo "$LOG_PREFIX Starting backup of '$DB_NAME' on '$DB_HOST'..."
mkdir -p "$BACKUP_DIR"

# ── Plain SQL dump (readable, portable) ──────────────────────────────────────
SQL_FILE="$BACKUP_DIR/backup_${DB_NAME}_${DATE}.sql"
pg_dump -h "$DB_HOST" -U "$DB_USER" "$DB_NAME" > "$SQL_FILE"
SQL_SIZE=$(du -sh "$SQL_FILE" | cut -f1)
echo "$LOG_PREFIX SQL dump complete: $(basename "$SQL_FILE") ($SQL_SIZE)"

# ── Custom-format dump (compressed, restores faster via pg_restore) ───────────
DUMP_FILE="$BACKUP_DIR/backup_${DB_NAME}_${DATE}.dump"
pg_dump \
    -h "$DB_HOST" -U "$DB_USER" \
    --format=custom \
    --compress=9 \
    "$DB_NAME" > "$DUMP_FILE"
DUMP_SIZE=$(du -sh "$DUMP_FILE" | cut -f1)
echo "$LOG_PREFIX Custom dump complete: $(basename "$DUMP_FILE") ($DUMP_SIZE)"

# ── Sanity check: bail if output is suspiciously tiny ────────────────────────
SQL_BYTES=$(stat -c%s "$SQL_FILE")
DUMP_BYTES=$(stat -c%s "$DUMP_FILE")
if [ "$SQL_BYTES" -lt 1024 ]; then
    echo "$LOG_PREFIX ERROR: SQL dump is only ${SQL_BYTES} bytes — possible failure." >&2
    exit 1
fi
if [ "$DUMP_BYTES" -lt 512 ]; then
    echo "$LOG_PREFIX ERROR: Custom dump is only ${DUMP_BYTES} bytes — possible failure." >&2
    exit 1
fi

# ── Retention: delete backups older than RETENTION_DAYS ──────────────────────
echo "$LOG_PREFIX Pruning backups older than ${RETENTION_DAYS} days..."
find "$BACKUP_DIR" -maxdepth 1 \
    \( -name "backup_*.sql" -o -name "backup_*.dump" \) \
    -mtime "+${RETENTION_DAYS}" -print -delete

REMAINING=$(find "$BACKUP_DIR" -maxdepth 1 \
    \( -name "backup_*.sql" -o -name "backup_*.dump" \) | wc -l)
echo "$LOG_PREFIX Retention done. ${REMAINING} backup file(s) retained."
echo "$LOG_PREFIX Backup finished successfully."
