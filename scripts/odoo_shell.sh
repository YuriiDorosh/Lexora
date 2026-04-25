#!/usr/bin/env bash
# =============================================================================
# odoo_shell.sh — Open an interactive Odoo shell (odoo-bin shell)
#
# Usage:
#   ./scripts/odoo_shell.sh
#   ./scripts/odoo_shell.sh -c "env['res.users'].search_count([])"
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"
if [ -f "$ENV_FILE" ]; then
    # shellcheck disable=SC1090
    set -o allexport; source "$ENV_FILE"; set +o allexport
fi

ODOO_CONTAINER="${ODOO_CONTAINER:-odoo}"
ODOO_DB="${ODOO_DB:-${POSTGRES_DB:-lexora}}"
ODOO_CONF="${ODOO_CONF:-/etc/odoo/odoo.conf}"

docker ps --format '{{.Names}}' | grep -q "^${ODOO_CONTAINER}$" \
    || { echo "Error: Odoo container '${ODOO_CONTAINER}' is not running." >&2; exit 1; }

if [ $# -gt 0 ] && [ "$1" = "-c" ]; then
    # Non-interactive: pipe the command
    shift
    echo "$1" | docker exec -i "$ODOO_CONTAINER" \
        odoo shell --config "$ODOO_CONF" -d "$ODOO_DB" --no-http
else
    # Interactive shell
    docker exec -it "$ODOO_CONTAINER" \
        odoo shell --config "$ODOO_CONF" -d "$ODOO_DB" --no-http
fi
