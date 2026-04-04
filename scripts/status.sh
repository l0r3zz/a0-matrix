#!/usr/bin/env bash
# =============================================================================
# a0-matrix — Service Status Check
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BASE_DIR="${SCRIPT_DIR%/scripts}"
PID_DIR="$BASE_DIR"
LOG_DIR="$BASE_DIR/logs"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

check_service() {
    local name="$1"
    local pid_file="$2"
    local health_url="${3:-}"

    if [[ -f "$pid_file" ]]; then
        local pid
        pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            echo -e "  ${GREEN}●${NC} $name: running (PID $pid)"
            if [[ -n "$health_url" ]]; then
                if curl -sf "$health_url" > /dev/null 2>&1; then
                    echo -e "    ${GREEN}✓${NC} Health check passed: $health_url"
                else
                    echo -e "    ${YELLOW}!${NC} Health check failed: $health_url"
                fi
            fi
        else
            echo -e "  ${RED}●${NC} $name: stopped (stale PID $pid)"
        fi
    else
        echo -e "  ${RED}●${NC} $name: not running (no PID file)"
    fi
}

echo ""
echo "a0-matrix Service Status"
echo "========================"
echo ""

# Source .env for port info
ENV_FILE="$BASE_DIR/.env"
MCP_PORT=3000
if [[ -f "$ENV_FILE" ]]; then
    set -a
    source "$ENV_FILE" 2>/dev/null || true
    set +a
    MCP_PORT="${MCP_PORT:-3000}"
fi

check_service "MCP Server" "$PID_DIR/mcp.pid" "http://localhost:${MCP_PORT}/health"
check_service "Matrix Bot" "$PID_DIR/bot.pid"

# Show recent log activity
echo ""
echo "Recent Logs:"
for logfile in "$LOG_DIR"/*.log; do
    if [[ -f "$logfile" ]]; then
        local_name=$(basename "$logfile")
        echo "  --- $local_name (last 3 lines) ---"
        tail -3 "$logfile" 2>/dev/null | sed 's/^/    /'
    fi
done
echo ""
