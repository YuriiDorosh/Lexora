#!/usr/bin/env bash
# =============================================================================
# restore_odoo.sh — Restore a full Odoo backup (database + filestore)
#
# Restores an archive created by backup_odoo.sh.
#
# Usage:
#   ./scripts/restore_odoo.sh ./backups/odoo_backup_lexora_2026-04-25_03-00-00.tar.gz
#   ./scripts/restore_odoo.sh ./backups/odoo_backup_lexora_2026-04-25_03-00-00.tar.gz --force
#
# Flags:
#   --force     Skip the interactive confirmation prompt
#   --db-only   Restore database only, skip filestore
#
# Env vars (defaults match the dev stack):
#   ODOO_DB            Target database to restore into  (default: lexora)
#   ODOO_CONTAINER     Odoo container name              (default: odoo)
#   DB_CONTAINER       Postgres container name          (default: postgres)
#   POSTGRES_USER      Postgres superuser               (default: odoo)
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"
if [ -f "$ENV_FILE" ]; then
    # shellcheck disable=SC1090
    set -o allexport; source "$ENV_FILE"; set +o allexport
fi

ARCHIVE="${1:-}"
FORCE=0
DB_ONLY=0
for arg in "${@:2}"; do
    case "$arg" in
        --force)   FORCE=1 ;;
        --db-only) DB_ONLY=1 ;;
        *) echo "Unknown flag: $arg" >&2; exit 1 ;;
    esac
done

ODOO_DB="${ODOO_DB:-${POSTGRES_DB:-lexora}}"
ODOO_CONTAINER="${ODOO_CONTAINER:-odoo}"
DB_CONTAINER="${DB_CONTAINER:-postgres}"
PG_USER="${POSTGRES_USER:-odoo}"

log()  { echo "[restore] $(date '+%H:%M:%S') $*"; }
die()  { echo "[restore] ERROR: $*" >&2; exit 1; }

# ── Validate input ────────────────────────────────────────────────────────────
[ -z "$ARCHIVE" ] && die "Usage: $0 <archive.tar.gz> [--force] [--db-only]"
[ -f "$ARCHIVE" ] || die "Archive not found: $ARCHIVE"

log "=== Odoo Restore ==="
log "  Archive    : $ARCHIVE ($(du -sh "$ARCHIVE" | cut -f1))"
log "  Target DB  : $ODOO_DB"
log "  Odoo       : $ODOO_CONTAINER"
log "  Postgres   : $DB_CONTAINER"
log "  DB only    : $DB_ONLY"

# ── Confirmation ──────────────────────────────────────────────────────────────
if [ "$FORCE" = "0" ]; then
    echo ""
    echo "  ⚠  WARNING: This will DROP the existing '$ODOO_DB' database"
    echo "     and replace the Odoo filestore. This cannot be undone."
    echo ""
    read -rp "  Type 'yes' to continue: " CONFIRM
    [ "$CONFIRM" = "yes" ] || { echo "Aborted."; exit 0; }
fi

docker ps --format '{{.Names}}' | grep -q "^${DB_CONTAINER}$" \
    || die "Postgres container '${DB_CONTAINER}' is not running."
docker ps --format '{{.Names}}' | grep -q "^${ODOO_CONTAINER}$" \
    || die "Odoo container '${ODOO_CONTAINER}' is not running."

# ── Extract archive ───────────────────────────────────────────────────────────
WORK_DIR=$(mktemp -d /tmp/odoo_restore_XXXXXX)
log "Extracting to $WORK_DIR ..."
tar -xzf "$ARCHIVE" -C "$WORK_DIR"
BACKUP_SUBDIR=$(ls "$WORK_DIR")
RESTORE_ROOT="$WORK_DIR/$BACKUP_SUBDIR"

# Show manifest if present
if [ -f "$RESTORE_ROOT/manifest.json" ]; then
    log "Manifest:"
    cat "$RESTORE_ROOT/manifest.json" | sed 's/^/  /'
fi

# ── Stop Odoo (prevent writes during restore) ─────────────────────────────────
log "Stopping Odoo container to prevent concurrent writes..."
docker stop "$ODOO_CONTAINER"
trap 'log "Restarting Odoo after restore..."; docker start "$ODOO_CONTAINER"' EXIT

# ── Drop and recreate database ────────────────────────────────────────────────
log "Dropping existing database '$ODOO_DB' ..."
docker exec -e PGPASSWORD="${POSTGRES_PASSWORD:-}" "$DB_CONTAINER" \
    psql -U "$PG_USER" -d postgres \
    -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='${ODOO_DB}';" \
    > /dev/null 2>&1 || true

docker exec -e PGPASSWORD="${POSTGRES_PASSWORD:-}" "$DB_CONTAINER" \
    dropdb -U "$PG_USER" --if-exists "$ODOO_DB"

docker exec -e PGPASSWORD="${POSTGRES_PASSWORD:-}" "$DB_CONTAINER" \
    createdb -U "$PG_USER" "$ODOO_DB"
log "  Database '$ODOO_DB' recreated."

# ── Restore database ──────────────────────────────────────────────────────────
if [ -f "$RESTORE_ROOT/dump.dump" ]; then
    log "Restoring from custom-format dump (dump.dump)..."
    docker exec -i -e PGPASSWORD="${POSTGRES_PASSWORD:-}" "$DB_CONTAINER" \
        pg_restore -U "$PG_USER" -d "$ODOO_DB" \
        --no-owner --no-acl --exit-on-error \
        < "$RESTORE_ROOT/dump.dump"
elif [ -f "$RESTORE_ROOT/dump.sql" ]; then
    log "Restoring from SQL dump (dump.sql)..."
    docker exec -i -e PGPASSWORD="${POSTGRES_PASSWORD:-}" "$DB_CONTAINER" \
        psql -U "$PG_USER" -d "$ODOO_DB" \
        < "$RESTORE_ROOT/dump.sql"
else
    die "No dump.dump or dump.sql found in archive."
fi
log "  Database restore complete."

# ── Restore filestore ─────────────────────────────────────────────────────────
if [ "$DB_ONLY" = "0" ] && [ -d "$RESTORE_ROOT/filestore" ]; then
    FILESTORE_DEST="/var/lib/odoo/filestore/${ODOO_DB}"
    log "Restoring filestore to ${ODOO_CONTAINER}:${FILESTORE_DEST} ..."
    docker exec "$ODOO_CONTAINER" rm -rf "$FILESTORE_DEST" 2>/dev/null || true
    docker exec "$ODOO_CONTAINER" mkdir -p "/var/lib/odoo/filestore"
    docker cp "$RESTORE_ROOT/filestore/." "${ODOO_CONTAINER}:${FILESTORE_DEST}/"
    docker exec "$ODOO_CONTAINER" chown -R odoo:odoo "/var/lib/odoo/filestore" 2>/dev/null || true
    FILESTORE_FILES=$(find "$RESTORE_ROOT/filestore" -type f | wc -l)
    log "  Filestore  : $FILESTORE_FILES files restored."
elif [ "$DB_ONLY" = "1" ]; then
    log "  Filestore  : skipped (--db-only)"
else
    log "  Filestore  : not found in archive, skipping."
fi

# ── Clean up temp dir ─────────────────────────────────────────────────────────
rm -rf "$WORK_DIR"

# EXIT trap restarts Odoo
log "=== Restore complete. Odoo will restart now. ==="
