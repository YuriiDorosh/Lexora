#!/usr/bin/env bash
# =============================================================================
# logs.sh — Tail logs from one or all Lexora containers
#
# Usage:
#   ./scripts/logs.sh              # tail all dev-stack containers
#   ./scripts/logs.sh odoo         # tail a specific container
#   ./scripts/logs.sh odoo --lines 200
# =============================================================================
set -euo pipefail

TARGET="${1:-all}"
LINES=50
for arg in "$@"; do
    case "$arg" in
        --lines) shift; LINES="${1:-50}" ;;
    esac
done

ALL_CONTAINERS=(odoo postgres redis nginx rabbitmq translation_service llm_service anki_service audio_service)

if [ "$TARGET" = "all" ]; then
    # Build the list of running containers from our set
    RUNNING=()
    for c in "${ALL_CONTAINERS[@]}"; do
        docker ps --format '{{.Names}}' | grep -q "^${c}$" && RUNNING+=("$c")
    done
    if [ ${#RUNNING[@]} -eq 0 ]; then
        echo "No dev-stack containers are running." >&2
        exit 1
    fi
    echo "[logs] Tailing ${#RUNNING[@]} containers (last ${LINES} lines each)..."
    # Use docker logs --follow for all running containers; multiplex with prefix
    for c in "${RUNNING[@]}"; do
        docker logs --tail "$LINES" --follow --timestamps "$c" 2>&1 | sed "s/^/[$c] /" &
    done
    wait
else
    docker logs --tail "$LINES" --follow --timestamps "$TARGET" 2>&1
fi
