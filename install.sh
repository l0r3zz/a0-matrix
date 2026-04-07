#!/usr/bin/env bash
# =============================================================================
# a0-matrix — Download & Install Pre-built Binaries
#
# Downloads the MCP server and Matrix bot binaries from GitHub Releases
# into the plugin's bin/ directory. Called by hooks.py install() or
# can be run standalone.
#
# Usage:
#   ./install.sh                     # install to default location
#   ./install.sh /custom/bin/dir     # install to custom directory
# =============================================================================
set -euo pipefail

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log()  { echo -e "${GREEN}[a0-matrix]${NC} $*"; }
warn() { echo -e "${YELLOW}[a0-matrix]${NC} $*"; }
err()  { echo -e "${RED}[a0-matrix]${NC} $*" >&2; }

# --- Configuration -----------------------------------------------------------

# GitHub Release URLs (using /latest/download/ for automatic redirect)
MCP_SERVER_RELEASE_URL="https://github.com/l0r3zz/matrix-mcp-server-r2/releases/latest/download"
BOT_RELEASE_URL="https://github.com/l0r3zz/agent-matrix/releases/latest/download"

# Binary names as published in GitHub Releases
MCP_SERVER_BINARY="matrix-mcp-server-r2"
BOT_BINARY="matrix-bot-rust"
DISPLAY_NAME_BINARY="set-display-name-rust"

# Default install directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEFAULT_BIN_DIR="${A0_WORKDIR:-/a0/usr/workdir}/a0-matrix/bin"
BIN_DIR="${1:-$DEFAULT_BIN_DIR}"

# --- Functions ---------------------------------------------------------------

download_binary() {
    local url="$1"
    local dest="$2"
    local name
    name=$(basename "$dest")

    if [[ -f "$dest" ]]; then
        warn "$name already exists at $dest — skipping (delete to re-download)"
        return 0
    fi

    log "Downloading $name..."

    # Try curl first, fall back to wget
    if command -v curl >/dev/null 2>&1; then
        if curl -fSL --connect-timeout 30 --max-time 120 -o "$dest" "$url"; then
            chmod +x "$dest"
            log "✅ $name → $dest"
            return 0
        fi
    elif command -v wget >/dev/null 2>&1; then
        if wget -q --timeout=30 -O "$dest" "$url"; then
            chmod +x "$dest"
            log "✅ $name → $dest"
            return 0
        fi
    else
        err "Neither curl nor wget found. Cannot download binaries."
        return 1
    fi

    # Download failed — clean up partial file
    rm -f "$dest"
    err "⚠️  Failed to download $name from $url"
    err "    Check the URL or download manually."
    return 1
}

# --- Main --------------------------------------------------------------------

log "Installing a0-matrix binaries to: $BIN_DIR"
mkdir -p "$BIN_DIR"

FAILED=0

# 1. MCP Server (from matrix-mcp-server-r2 repo)
download_binary "${MCP_SERVER_RELEASE_URL}/${MCP_SERVER_BINARY}" "${BIN_DIR}/${MCP_SERVER_BINARY}" || ((FAILED++))

# 2. Matrix Bot (from agent-matrix repo)
download_binary "${BOT_RELEASE_URL}/${BOT_BINARY}" "${BIN_DIR}/${BOT_BINARY}" || ((FAILED++))

# 3. Display Name Utility (from agent-matrix repo)
download_binary "${BOT_RELEASE_URL}/${DISPLAY_NAME_BINARY}" "${BIN_DIR}/${DISPLAY_NAME_BINARY}" || ((FAILED++))

# --- Summary -----------------------------------------------------------------

echo ""
if [[ $FAILED -eq 0 ]]; then
    log "✅ All binaries installed successfully!"
    echo ""
    log "Installed binaries:"
    for bin in "$BIN_DIR"/*; do
        if [[ -x "$bin" ]]; then
            log "  $(basename "$bin")  $(ls -lh "$bin" | awk '{print $5}')"
        fi
    done
else
    err "⚠️  $FAILED binary download(s) failed."
    err "    Check network connectivity and GitHub Release URLs."
    err "    You can also download manually and place binaries in: $BIN_DIR"
    exit 1
fi

echo ""
log "Next steps:"
log "  1. Edit /a0/usr/workdir/a0-matrix/.env with your Matrix credentials"
log "  2. Run: /a0/usr/workdir/a0-matrix/start.sh"
log "  3. Configure MCP in Agent Zero Settings → MCP/A2A"
echo ""
