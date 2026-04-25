#!/bin/bash
# Backup integrity verification script.
# Run inside the postgres_backup container or any host with pg_restore available.
#
# Usage:
#   ./verify_backup.sh                   # checks latest backup in /backups
#   ./verify_backup.sh /backups          # explicit backup directory
#   BACKUP_DIR=/data/backups ./verify_backup.sh
#
# Exit codes:
#   0 — all checks passed
#   1 — one or more checks failed (details printed to stderr)
set -euo pipefail

BACKUP_DIR="${1:-${BACKUP_DIR:-/backups}}"
MAX_AGE_HOURS="${MAX_AGE_HOURS:-25}"   # alert if newest backup is older than this
MIN_SIZE_BYTES="${MIN_SIZE_BYTES:-1024}"

PASS=0
FAIL=0
WARNINGS=()
ERRORS=()

log()  { echo "[verify] $(date '+%H:%M:%S') $*"; }
warn() { WARNINGS+=("$*"); echo "[verify] WARN: $*" >&2; }
fail() { ERRORS+=("$*"); echo "[verify] FAIL: $*" >&2; FAIL=$((FAIL + 1)); }
ok()   { echo "[verify] OK:   $*"; PASS=$((PASS + 1)); }

# ── 1. Directory exists and is non-empty ─────────────────────────────────────
log "Checking backup directory: $BACKUP_DIR"

if [ ! -d "$BACKUP_DIR" ]; then
    fail "Backup directory does not exist: $BACKUP_DIR"
    echo ""
    echo "Result: FAILED ($FAIL failure(s))"
    exit 1
fi

DUMP_FILES=$(find "$BACKUP_DIR" -maxdepth 1 -name "backup_*.dump" -type f | sort)
SQL_FILES=$(find "$BACKUP_DIR" -maxdepth 1 -name "backup_*.sql" -type f | sort)
TOTAL_FILES=$(echo "$DUMP_FILES $SQL_FILES" | wc -w)

if [ "$TOTAL_FILES" -eq 0 ]; then
    fail "No backup files found in $BACKUP_DIR"
    echo ""
    echo "Result: FAILED ($FAIL failure(s))"
    exit 1
fi

ok "Found $(echo "$DUMP_FILES" | grep -c . || true) .dump and $(echo "$SQL_FILES" | grep -c . || true) .sql backup file(s)"

# ── 2. Newest backup is recent enough ────────────────────────────────────────
NEWEST_FILE=$(find "$BACKUP_DIR" -maxdepth 1 \
    \( -name "backup_*.dump" -o -name "backup_*.sql" \) \
    -type f -printf "%T@ %p\n" | sort -rn | head -1 | awk '{print $2}')

if [ -z "$NEWEST_FILE" ]; then
    fail "Could not determine newest backup file"
else
    FILE_AGE_SECONDS=$(( $(date +%s) - $(date +%s -r "$NEWEST_FILE") ))
    FILE_AGE_HOURS=$(( FILE_AGE_SECONDS / 3600 ))
    MAX_AGE_SECONDS=$(( MAX_AGE_HOURS * 3600 ))

    if [ "$FILE_AGE_SECONDS" -gt "$MAX_AGE_SECONDS" ]; then
        fail "Newest backup is ${FILE_AGE_HOURS}h old (threshold: ${MAX_AGE_HOURS}h): $(basename "$NEWEST_FILE")"
    else
        ok "Newest backup is ${FILE_AGE_HOURS}h old (within ${MAX_AGE_HOURS}h threshold): $(basename "$NEWEST_FILE")"
    fi
fi

# ── 3. File size checks ───────────────────────────────────────────────────────
log "Checking file sizes (min: ${MIN_SIZE_BYTES} bytes)..."
while IFS= read -r f; do
    [ -z "$f" ] && continue
    SIZE=$(stat -c%s "$f")
    if [ "$SIZE" -lt "$MIN_SIZE_BYTES" ]; then
        fail "$(basename "$f") is too small: ${SIZE} bytes (min: ${MIN_SIZE_BYTES})"
    else
        ok "$(basename "$f"): ${SIZE} bytes"
    fi
done <<< "$(find "$BACKUP_DIR" -maxdepth 1 \( -name "backup_*.dump" -o -name "backup_*.sql" \) -type f | sort)"

# ── 4. Custom-format dump structure validation (pg_restore --list) ────────────
if command -v pg_restore &>/dev/null; then
    log "Validating custom-format .dump files with pg_restore --list..."
    while IFS= read -r f; do
        [ -z "$f" ] && continue
        if pg_restore --list "$f" > /dev/null 2>&1; then
            ok "$(basename "$f"): pg_restore --list passed"
        else
            fail "$(basename "$f"): pg_restore --list failed — file may be corrupt"
        fi
    done <<< "$(find "$BACKUP_DIR" -maxdepth 1 -name "backup_*.dump" -type f | sort)"
else
    warn "pg_restore not available — skipping custom-format validation"
fi

# ── 5. SQL dump header check ──────────────────────────────────────────────────
log "Checking SQL dump headers..."
while IFS= read -r f; do
    [ -z "$f" ] && continue
    HEADER=$(head -c 256 "$f" 2>/dev/null)
    if echo "$HEADER" | grep -q "PostgreSQL database dump"; then
        ok "$(basename "$f"): valid pg_dump header"
    else
        fail "$(basename "$f"): missing expected pg_dump header — file may be corrupt or empty"
    fi
done <<< "$(find "$BACKUP_DIR" -maxdepth 1 -name "backup_*.sql" -type f | sort)"

# ── 6. Disk space check ───────────────────────────────────────────────────────
AVAIL_KB=$(df -k "$BACKUP_DIR" | awk 'NR==2 {print $4}')
AVAIL_GB=$(echo "scale=1; $AVAIL_KB / 1048576" | bc 2>/dev/null || echo "?")
if [ "$AVAIL_KB" -lt 524288 ]; then  # warn if less than 512 MB free
    warn "Low disk space on backup volume: ${AVAIL_GB} GB available"
else
    ok "Disk space: ${AVAIL_GB} GB available on backup volume"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "────────────────────────────────────────"
echo "Backup verification summary"
echo "  Directory : $BACKUP_DIR"
echo "  Passed    : $PASS"
echo "  Failed    : $FAIL"
echo "  Warnings  : ${#WARNINGS[@]}"
echo "────────────────────────────────────────"

if [ "${#WARNINGS[@]}" -gt 0 ]; then
    echo "Warnings:"
    for w in "${WARNINGS[@]}"; do echo "  ⚠  $w"; done
fi

if [ "$FAIL" -gt 0 ]; then
    echo "Errors:"
    for e in "${ERRORS[@]}"; do echo "  ✗  $e"; done
    echo ""
    echo "Result: FAILED ($FAIL failure(s), $PASS passed)"
    exit 1
fi

echo ""
echo "Result: ALL CHECKS PASSED"
exit 0
