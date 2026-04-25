#!/usr/bin/env bash
# =============================================================================
# db_shell.sh — Open a psql shell against the Lexora Postgres container
#
# Usage:
#   ./scripts/db_shell.sh
#   ./scripts/db_shell.sh -c "SELECT count(*) FROM language_entry;"
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"
if [ -f "$ENV_FILE" ]; then
    # shellcheck disable=SC1090
    set -o allexport; source "$ENV_FILE"; set +o allexport
fi

DB_CONTAINER="${DB_CONTAINER:-postgres}"
ODOO_DB="${ODOO_DB:-${POSTGRES_DB:-lexora}}"
PG_USER="${POSTGRES_USER:-odoo}"

docker ps --format '{{.Names}}' | grep -q "^${DB_CONTAINER}$" \
    || { echo "Error: Postgres container '${DB_CONTAINER}' is not running." >&2; exit 1; }

if [ $# -gt 0 ] && [ "$1" = "-c" ]; then
    shift
    docker exec -e PGPASSWORD="${POSTGRES_PASSWORD:-}" "$DB_CONTAINER" \
        psql -U "$PG_USER" -d "$ODOO_DB" -c "$1"
else
    docker exec -it -e PGPASSWORD="${POSTGRES_PASSWORD:-}" "$DB_CONTAINER" \
        psql -U "$PG_USER" -d "$ODOO_DB"
fi
