#!/usr/bin/env bash
# =============================================================================
# backup_odoo.sh — Full Odoo backup (database + filestore)
#
# Creates a single timestamped .tar.gz that contains:
#   backup_<DB>_<DATE>/
#     dump.sql          — plain-text pg_dump (portable)
#     dump.dump         — custom-format pg_dump (fast pg_restore)
#     filestore/        — Odoo filestore (/var/lib/odoo/filestore/<DB>)
#     manifest.json     — metadata: date, DB name, Odoo version, file sizes
#
# Usage (from project root):
#   ./scripts/backup_odoo.sh
#   ODOO_DB=mydb BACKUP_DIR=/data/backups ./scripts/backup_odoo.sh
#   DRY_RUN=1 ./scripts/backup_odoo.sh      # validate config without writing
#
# Required env vars (all have sane defaults for the dev stack):
#   ODOO_DB                Odoo database name         (default: lexora)
#   ODOO_CONTAINER         Odoo Docker container name (default: odoo)
#   DB_CONTAINER           Postgres container name    (default: postgres)
#   POSTGRES_USER          Postgres user              (default: odoo)
#   POSTGRES_PASSWORD      Postgres password          (default: from .env)
#   BACKUP_DIR             Where to write archives    (default: ./backups)
#   RETENTION_DAYS         Days to keep old backups   (default: 7)
#   DRY_RUN                Set to 1 to skip writes    (default: 0)
# =============================================================================
set -euo pipefail

# ── Load .env from project root (if running outside Docker) ──────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"
if [ -f "$ENV_FILE" ]; then
    # shellcheck disable=SC1090
    set -o allexport; source "$ENV_FILE"; set +o allexport
fi

# ── Configuration ─────────────────────────────────────────────────────────────
ODOO_DB="${ODOO_DB:-${POSTGRES_DB:-lexora}}"
ODOO_CONTAINER="${ODOO_CONTAINER:-odoo}"
DB_CONTAINER="${DB_CONTAINER:-postgres}"
PG_USER="${POSTGRES_USER:-odoo}"
BACKUP_DIR="${BACKUP_DIR:-$PROJECT_ROOT/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
DRY_RUN="${DRY_RUN:-0}"

DATE=$(date +"%Y-%m-%d_%H-%M-%S")
BACKUP_NAME="odoo_backup_${ODOO_DB}_${DATE}"
WORK_DIR="/tmp/${BACKUP_NAME}"
ARCHIVE="$BACKUP_DIR/${BACKUP_NAME}.tar.gz"

log()  { echo "[backup] $(date '+%H:%M:%S') $*"; }
die()  { echo "[backup] ERROR: $*" >&2; exit 1; }

# ── Pre-flight checks ─────────────────────────────────────────────────────────
log "=== Odoo Full Backup ==="
log "  Database   : $ODOO_DB"
log "  Odoo       : $ODOO_CONTAINER"
log "  Postgres   : $DB_CONTAINER"
log "  Destination: $BACKUP_DIR"
log "  Retention  : ${RETENTION_DAYS} days"

if [ "$DRY_RUN" = "1" ]; then
    log "DRY_RUN=1 — config looks good, exiting without writing anything."
    exit 0
fi

docker ps --format '{{.Names}}' | grep -q "^${ODOO_CONTAINER}$" \
    || die "Odoo container '${ODOO_CONTAINER}' is not running."
docker ps --format '{{.Names}}' | grep -q "^${DB_CONTAINER}$" \
    || die "Postgres container '${DB_CONTAINER}' is not running."

mkdir -p "$BACKUP_DIR"
mkdir -p "$WORK_DIR"

# ── 1. Database dumps ─────────────────────────────────────────────────────────
log "Dumping database '$ODOO_DB'..."

docker exec -e PGPASSWORD="${POSTGRES_PASSWORD:-}" "$DB_CONTAINER" \
    pg_dump -U "$PG_USER" -d "$ODOO_DB" \
    > "$WORK_DIR/dump.sql"
log "  dump.sql   : $(du -sh "$WORK_DIR/dump.sql" | cut -f1)"

docker exec -e PGPASSWORD="${POSTGRES_PASSWORD:-}" "$DB_CONTAINER" \
    pg_dump -U "$PG_USER" -d "$ODOO_DB" \
    --format=custom --compress=9 \
    > "$WORK_DIR/dump.dump"
log "  dump.dump  : $(du -sh "$WORK_DIR/dump.dump" | cut -f1)"

# ── 2. Odoo filestore ─────────────────────────────────────────────────────────
# The filestore lives at /var/lib/odoo/filestore/<DB> inside the Odoo container.
# It contains all ir.attachment binary data (images, PDFs, audio, etc.).
FILESTORE_PATH="/var/lib/odoo/filestore/${ODOO_DB}"
log "Copying filestore from ${ODOO_CONTAINER}:${FILESTORE_PATH}..."

if docker exec "$ODOO_CONTAINER" test -d "$FILESTORE_PATH" 2>/dev/null; then
    mkdir -p "$WORK_DIR/filestore"
    docker cp "${ODOO_CONTAINER}:${FILESTORE_PATH}/." "$WORK_DIR/filestore/"
    FILESTORE_SIZE=$(du -sh "$WORK_DIR/filestore" | cut -f1)
    FILESTORE_FILES=$(find "$WORK_DIR/filestore" -type f | wc -l)
    log "  filestore  : $FILESTORE_SIZE ($FILESTORE_FILES files)"
else
    log "  filestore  : not found at $FILESTORE_PATH (empty DB or no attachments yet)"
    mkdir -p "$WORK_DIR/filestore"
fi

# ── 3. Odoo sessions (optional — lightweight, nice to have) ──────────────────
SESSIONS_PATH="/var/lib/odoo/sessions"
if docker exec "$ODOO_CONTAINER" test -d "$SESSIONS_PATH" 2>/dev/null; then
    mkdir -p "$WORK_DIR/sessions"
    docker cp "${ODOO_CONTAINER}:${SESSIONS_PATH}/." "$WORK_DIR/sessions/" 2>/dev/null || true
    log "  sessions   : $(du -sh "$WORK_DIR/sessions" 2>/dev/null | cut -f1 || echo '0')"
fi

# ── 4. Manifest ───────────────────────────────────────────────────────────────
ODOO_VERSION=$(docker exec "$ODOO_CONTAINER" \
    python3 -c "import odoo; print(odoo.release.version)" 2>/dev/null || echo "unknown")
SQL_SIZE=$(stat -c%s "$WORK_DIR/dump.sql")
DUMP_SIZE=$(stat -c%s "$WORK_DIR/dump.dump")

cat > "$WORK_DIR/manifest.json" <<EOF
{
  "backup_name": "${BACKUP_NAME}",
  "created_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "odoo_version": "${ODOO_VERSION}",
  "database": "${ODOO_DB}",
  "postgres_container": "${DB_CONTAINER}",
  "odoo_container": "${ODOO_CONTAINER}",
  "files": {
    "dump.sql":  ${SQL_SIZE},
    "dump.dump": ${DUMP_SIZE}
  },
  "filestore_files": ${FILESTORE_FILES:-0},
  "retention_days": ${RETENTION_DAYS}
}
EOF
log "  manifest.json written"

# ── 5. Archive everything ─────────────────────────────────────────────────────
log "Creating archive: $ARCHIVE ..."
tar -czf "$ARCHIVE" -C "/tmp" "$BACKUP_NAME"
ARCHIVE_SIZE=$(du -sh "$ARCHIVE" | cut -f1)
log "  Archive    : $ARCHIVE ($ARCHIVE_SIZE)"

# ── 6. Sanity check ───────────────────────────────────────────────────────────
ARCHIVE_BYTES=$(stat -c%s "$ARCHIVE")
if [ "$ARCHIVE_BYTES" -lt 4096 ]; then
    die "Archive is suspiciously small (${ARCHIVE_BYTES} bytes). Backup aborted."
fi

# ── 7. Clean up temp dir ──────────────────────────────────────────────────────
rm -rf "$WORK_DIR"
log "Cleaned up $WORK_DIR"

# ── 8. Retention ──────────────────────────────────────────────────────────────
log "Pruning backups older than ${RETENTION_DAYS} days..."
find "$BACKUP_DIR" -maxdepth 1 -name "odoo_backup_*.tar.gz" \
    -mtime "+${RETENTION_DAYS}" -print -delete
REMAINING=$(find "$BACKUP_DIR" -maxdepth 1 -name "odoo_backup_*.tar.gz" | wc -l)
log "  ${REMAINING} archive(s) retained."

log "=== Backup complete: $ARCHIVE ==="
