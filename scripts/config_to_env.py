#!/usr/bin/env python3
"""a0-matrix: Generate .env from config.json for Rust binaries.

Reads the plugin's config.json (populated by the WebUI settings page)
and writes a .env file that the Rust MCP server and bot binaries consume.

Auto-detects the Agent Zero API key from /a0/usr/settings.json.
"""

import json
import sys
from pathlib import Path

# Paths
WORKDIR = Path(__file__).resolve().parent.parent  # /a0/usr/workdir/a0-matrix
PLUGIN_DIR = Path("/a0/usr/plugins/a0_matrix")
CONFIG_JSON = PLUGIN_DIR / "config.json"
ENV_FILE = WORKDIR / ".env"
A0_SETTINGS = Path("/a0/usr/settings.json")


def load_config() -> dict:
    """Load config.json, return empty dict if missing."""
    if not CONFIG_JSON.exists():
        print(f"[config_to_env] ⚠️  {CONFIG_JSON} not found")
        return {}
    with open(CONFIG_JSON) as f:
        return json.load(f)


def detect_a0_api_key() -> str:
    """Read the auto-generated mcp_server_token from Agent Zero settings."""
    try:
        if A0_SETTINGS.exists():
            with open(A0_SETTINGS) as f:
                settings = json.load(f)
            token = settings.get("mcp_server_token", "")
            if token:
                return token
    except Exception as e:
        print(f"[config_to_env] ⚠️  Could not read A0 settings: {e}")
    return ""


def generate_env(config: dict) -> str:
    """Generate .env content from config.json values."""
    matrix = config.get("matrix", {})
    bot = config.get("bot", {})

    # Auto-detect API key
    a0_api_key = detect_a0_api_key()
    if a0_api_key:
        print(f"[config_to_env] ✅ Auto-detected A0 API key")
    else:
        print(f"[config_to_env] ⚠️  A0 API key not found — bot→agent forwarding will fail")

    lines = [
        "# ==============================================================================",
        "# a0-matrix — Auto-generated from plugin config.json",
        "# Do not edit manually — changes will be overwritten on next start.",
        "# Configure via: Agent Zero Settings → Plugins → a0-matrix → ⚙️",
        "# ==============================================================================",
        "",
        "# Matrix Connection",
        f'MATRIX_HOMESERVER_URL={matrix.get("homeserver_url", "")}',
        f'MATRIX_USER_ID={matrix.get("user_id", "")}',
        f'MATRIX_ACCESS_TOKEN={matrix.get("access_token", "")}',
        f'MATRIX_DEVICE_ID={matrix.get("device_id", "A0-bot")}',
        "",
        "# Bot Behavior",
        f'BOT_DISPLAY_NAME={bot.get("display_name", "Agent Zero")}',
        f'AGENT_IDENTITY={bot.get("agent_identity", "Agent Zero")}',
        "",
        "# Agent Zero API (auto-detected)",
        f"A0_API_URL=http://localhost:80/api/api_message",
        f"A0_API_KEY={a0_api_key}",
        f"A0_AGENT_PROFILE=",
        "",
        "# MCP Server",
        "MCP_PORT=3000",
        "",
        "# Sync",
        "SYNC_TIMEOUT_MS=30000",
        "TRIGGER_PREFIX=",
        "",
        "# Logging",
        "RUST_LOG=info",
        "",
    ]

    return "\n".join(lines)


def main():
    config = load_config()

    # Check if required fields are set
    matrix = config.get("matrix", {})
    missing = []
    for field in ["homeserver_url", "user_id", "access_token"]:
        if not matrix.get(field):
            missing.append(field)

    if missing:
        print(f"[config_to_env] ⚠️  Missing required config: {', '.join(missing)}")
        print(f"[config_to_env]    Configure via: Agent Zero Settings → Plugins → a0-matrix → ⚙️")

        # If .env already exists (manual setup), keep it
        if ENV_FILE.exists():
            print(f"[config_to_env]    Keeping existing .env")
            return 0

        print(f"[config_to_env]    No .env exists either — services will fail to start")
        # Still generate .env with empty values so start.sh can report the error

    env_content = generate_env(config)

    # Write .env with restrictive permissions
    ENV_FILE.write_text(env_content)
    ENV_FILE.chmod(0o600)
    print(f"[config_to_env] ✅ Generated {ENV_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
