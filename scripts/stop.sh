#!/usr/bin/env bash
# =============================================================================
# a0-matrix — Stop Services
# Gracefully stops MCP server and Matrix bot processes.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BASE_DIR="${SCRIPT_DIR%/scripts}"
PID_DIR="$BASE_DIR"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[a0-matrix]${NC} $*"; }
warn() { echo -e "${YELLOW}[a0-matrix]${NC} $*"; }

stop_service() {
    local name="$1"
    local pid_file="$2"

    if [[ -f "$pid_file" ]]; then
        local pid
        pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            log "Stopping $name (PID $pid)..."
            kill "$pid" 2>/dev/null || true
            # Wait up to 10s for graceful shutdown
            local count=0
            while kill -0 "$pid" 2>/dev/null && [[ $count -lt 10 ]]; do
                sleep 1
                ((count++))
            done
            if kill -0 "$pid" 2>/dev/null; then
                warn "$name didn't stop gracefully, sending SIGKILL..."
                kill -9 "$pid" 2>/dev/null || true
            fi
            log "$name stopped"
        else
            warn "$name not running (stale PID file)"
        fi
        rm -f "$pid_file"
    else
        warn "No PID file for $name"
    fi
}

# Stop MCP Server
stop_service "MCP Server" "$PID_DIR/mcp.pid"

# Stop Matrix Bot
stop_service "Matrix Bot" "$PID_DIR/bot.pid"

# Clean up any remaining orphan processes
for proc_name in matrix-mcp-server matrix-bot-rust; do
    if pgrep -f "$proc_name" > /dev/null 2>&1; then
        warn "Killing orphan $proc_name processes..."
        pkill -f "$proc_name" 2>/dev/null || true
    fi
done

log "✅ All services stopped"
