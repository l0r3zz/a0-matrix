#!/usr/bin/env bash
# =============================================================================
# a0-matrix — Start Services (Embedded Mode)
# Launches MCP server and Matrix bot as background processes inside
# the Agent Zero container.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BASE_DIR="${SCRIPT_DIR%/scripts}"
BIN_DIR="$BASE_DIR/bin"
DATA_DIR="$BASE_DIR/data"
LOG_DIR="$BASE_DIR/logs"
ENV_FILE="$BASE_DIR/.env"
PID_DIR="$BASE_DIR"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log()  { echo -e "${GREEN}[a0-matrix]${NC} $*"; }
warn() { echo -e "${YELLOW}[a0-matrix]${NC} $*"; }
err()  { echo -e "${RED}[a0-matrix]${NC} $*" >&2; }

# Ensure .env exists
if [[ ! -f "$ENV_FILE" ]]; then
    err ".env not found at $ENV_FILE"
    err "Copy .env.example and fill in your Matrix credentials first."
    exit 1
fi

# Source .env
set -a
source "$ENV_FILE"
set +a

# Validate required variables
for var in MATRIX_HOMESERVER_URL MATRIX_USER_ID MATRIX_ACCESS_TOKEN; do
    if [[ -z "${!var:-}" || "${!var}" == *"your_"* || "${!var}" == *"example"* ]]; then
        err "$var is not set or contains placeholder value in $ENV_FILE"
        exit 1
    fi
done

mkdir -p "$LOG_DIR" "$DATA_DIR"

# --- Start MCP Server ---
MCP_BINARY="$BIN_DIR/matrix-mcp-server-r2"
MCP_PID_FILE="$PID_DIR/mcp.pid"
if [[ ! -f "$MCP_BINARY" ]]; then
    warn "MCP server not found"
    exit 1
fi

if [[ -f "$MCP_PID_FILE" ]] && kill -0 "$(cat "$MCP_PID_FILE")" 2>/dev/null; then
    warn "MCP server already running (PID $(cat "$MCP_PID_FILE"))"
else
    if [[ -x "$MCP_BINARY" ]]; then
        log "Starting MCP server on port ${MCP_PORT:-3000}..."
        PORT="${MCP_PORT:-3000}" \
        MATRIX_HOMESERVER_URL="$MATRIX_HOMESERVER_URL" \
        MATRIX_USER_ID="$MATRIX_USER_ID" \
        MATRIX_ACCESS_TOKEN="$MATRIX_ACCESS_TOKEN" \
        RUST_LOG="${RUST_LOG:-info}" \
            nohup "$MCP_BINARY" > "$LOG_DIR/mcp-server.log" 2>&1 &
        echo $! > "$MCP_PID_FILE"
        sleep 2

        if kill -0 "$(cat "$MCP_PID_FILE")" 2>/dev/null; then
            log "✅ MCP server started (PID $(cat "$MCP_PID_FILE"))"
        else
            err "MCP server failed to start. Check $LOG_DIR/mcp-server.log"
        fi
    else
        warn "MCP server binary not found at $MCP_BINARY"
        warn "Skipping MCP server. Use docker-compose or install the binary manually."
    fi
fi

# --- Start Matrix Bot ---
BOT_BINARY="$BIN_DIR/matrix-bot-rust"
BOT_PID_FILE="$PID_DIR/bot.pid"

if [[ -f "$BOT_PID_FILE" ]] && kill -0 "$(cat "$BOT_PID_FILE")" 2>/dev/null; then
    warn "Matrix bot already running (PID $(cat "$BOT_PID_FILE"))"
else
    if [[ -x "$BOT_BINARY" ]]; then
        log "Starting Matrix bot..."
        MATRIX_HOMESERVER_URL="$MATRIX_HOMESERVER_URL" \
        MATRIX_USER_ID="$MATRIX_USER_ID" \
        MATRIX_ACCESS_TOKEN="$MATRIX_ACCESS_TOKEN" \
        MATRIX_DEVICE_ID="${MATRIX_DEVICE_ID:-AgentZeroBot}" \
        A0_API_URL="${A0_API_URL:-http://localhost:80/api_message}" \
        A0_API_KEY="${A0_API_KEY:-}" \
        BOT_DISPLAY_NAME="${BOT_DISPLAY_NAME:-Agent Zero}" \
        AGENT_IDENTITY="${AGENT_IDENTITY:-${BOT_DISPLAY_NAME:-Agent Zero}}" \
        SYNC_TIMEOUT_MS="${SYNC_TIMEOUT_MS:-30000}" \
        TRIGGER_PREFIX="${TRIGGER_PREFIX:-}" \
        RUST_LOG="${RUST_LOG:-info}" \
            nohup "$BOT_BINARY" > "$LOG_DIR/bot.log" 2>&1 &
        echo $! > "$BOT_PID_FILE"
        sleep 2

        if kill -0 "$(cat "$BOT_PID_FILE")" 2>/dev/null; then
            log "✅ Matrix bot started (PID $(cat "$BOT_PID_FILE"))"
        else
            err "Matrix bot failed to start. Check $LOG_DIR/bot.log"
        fi
    else
        warn "Matrix bot binary not found at $BOT_BINARY"
        warn "Build it first: cd $BASE_DIR/matrix-bot/rust && cargo build --release"
    fi
fi

# --- Summary ---
echo ""
log "Service status:"
[[ -f "$MCP_PID_FILE" ]] && log "  MCP Server: PID $(cat "$MCP_PID_FILE") → http://localhost:${MCP_PORT:-3000}/mcp"
[[ -f "$BOT_PID_FILE" ]] && log "  Matrix Bot: PID $(cat "$BOT_PID_FILE")"
log "  Logs: $LOG_DIR/"
echo ""
