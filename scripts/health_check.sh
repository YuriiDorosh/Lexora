#!/usr/bin/env bash
# =============================================================================
# health_check.sh — Ping all Lexora services and report their status
#
# Usage:
#   ./scripts/health_check.sh
#   ./scripts/health_check.sh --json    # output as JSON
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"
if [ -f "$ENV_FILE" ]; then
    # shellcheck disable=SC1090
    set -o allexport; source "$ENV_FILE"; set +o allexport
fi

JSON_MODE=0
for arg in "$@"; do
    case "$arg" in
        --json) JSON_MODE=1 ;;
        *) echo "Unknown flag: $arg" >&2; exit 1 ;;
    esac
done

ODOO_PORT="${NGINX_PORT:-5433}"
TRANSLATION_PORT="${TRANSLATION_PORT:-8001}"
LLM_PORT="${LLM_PORT:-8002}"
ANKI_PORT="${ANKI_PORT:-8003}"
AUDIO_PORT="${AUDIO_PORT:-8004}"
RABBITMQ_MGMT_PORT="${RABBITMQ_MGMT_PORT:-15672}"
REDIS_CONTAINER="${REDIS_CONTAINER:-redis}"
ODOO_CONTAINER="${ODOO_CONTAINER:-odoo}"
DB_CONTAINER="${DB_CONTAINER:-postgres}"

PASS=0
FAIL=0
declare -A RESULTS

check_http() {
    local name="$1" url="$2"
    local status
    status=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$url" 2>/dev/null || echo "000")
    if [[ "$status" =~ ^[23] ]]; then
        RESULTS["$name"]="ok ($status)"
        PASS=$((PASS + 1))
    else
        RESULTS["$name"]="fail ($status)"
        FAIL=$((FAIL + 1))
    fi
}

check_docker() {
    local name="$1" container="$2"
    if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^${container}$"; then
        RESULTS["$name"]="ok (running)"
        PASS=$((PASS + 1))
    else
        RESULTS["$name"]="fail (not running)"
        FAIL=$((FAIL + 1))
    fi
}

check_redis() {
    local name="$1" container="$2"
    local pong
    pong=$(docker exec "$container" redis-cli ping 2>/dev/null || echo "")
    if [ "$pong" = "PONG" ]; then
        RESULTS["$name"]="ok (PONG)"
        PASS=$((PASS + 1))
    else
        RESULTS["$name"]="fail (no PONG)"
        FAIL=$((FAIL + 1))
    fi
}

check_docker  "postgres"    "$DB_CONTAINER"
check_docker  "odoo"        "$ODOO_CONTAINER"
check_redis   "redis"       "$REDIS_CONTAINER"
check_http    "nginx/odoo"  "http://localhost:${ODOO_PORT}/web/health"
check_http    "rabbitmq-ui" "http://localhost:${RABBITMQ_MGMT_PORT}"
check_http    "translation" "http://localhost:${TRANSLATION_PORT}/health"
check_http    "llm"         "http://localhost:${LLM_PORT}/health"
check_http    "anki"        "http://localhost:${ANKI_PORT}/health"
check_http    "audio"       "http://localhost:${AUDIO_PORT}/health"

if [ "$JSON_MODE" = "1" ]; then
    echo "{"
    first=1
    for svc in "${!RESULTS[@]}"; do
        [ "$first" = "1" ] || echo ","
        status="${RESULTS[$svc]}"
        ok="false"
        [[ "$status" == ok* ]] && ok="true"
        printf '  "%s": {"status": "%s", "ok": %s}' "$svc" "$status" "$ok"
        first=0
    done
    echo ""
    echo "}"
else
    echo ""
    echo "  Lexora Service Health Check"
    echo "  ════════════════════════════"
    for svc in postgres odoo redis nginx/odoo rabbitmq-ui translation llm anki audio; do
        status="${RESULTS[$svc]:-unknown}"
        if [[ "$status" == ok* ]]; then
            icon="✓"
        else
            icon="✗"
        fi
        printf "  %s  %-20s %s\n" "$icon" "$svc" "$status"
    done
    echo ""
    echo "  Pass: $PASS / $((PASS + FAIL))"
    [ "$FAIL" -gt 0 ] && echo "  Fail: $FAIL" && echo ""
fi

[ "$FAIL" -eq 0 ]
