#!/usr/bin/env bash
# =============================================================================
# update_module.sh — Update one or more Odoo modules without restarting Odoo
#
# Usage:
#   ./scripts/update_module.sh language_portal
#   ./scripts/update_module.sh language_portal,language_learning
#   ./scripts/update_module.sh language_portal --test
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"
if [ -f "$ENV_FILE" ]; then
    # shellcheck disable=SC1090
    set -o allexport; source "$ENV_FILE"; set +o allexport
fi

MODULES="${1:-}"
RUN_TESTS=0
for arg in "${@:2}"; do
    case "$arg" in
        --test) RUN_TESTS=1 ;;
        *) echo "Unknown flag: $arg" >&2; exit 1 ;;
    esac
done

ODOO_CONTAINER="${ODOO_CONTAINER:-odoo}"
ODOO_DB="${ODOO_DB:-${POSTGRES_DB:-lexora}}"
ODOO_CONF="${ODOO_CONF:-/etc/odoo/odoo.conf}"

[ -z "$MODULES" ] && { echo "Usage: $0 <module[,module2]> [--test]" >&2; exit 1; }

docker ps --format '{{.Names}}' | grep -q "^${ODOO_CONTAINER}$" \
    || { echo "Error: Odoo container '${ODOO_CONTAINER}' is not running." >&2; exit 1; }

echo "[update] Updating modules: $MODULES"

CMD="odoo --config $ODOO_CONF -d $ODOO_DB --update $MODULES --stop-after-init --no-http"
[ "$RUN_TESTS" = "1" ] && CMD="$CMD --test-enable"

docker exec "$ODOO_CONTAINER" bash -c "$CMD"
echo "[update] Done. Restart Odoo if new routes were added: docker restart $ODOO_CONTAINER"
