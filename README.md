# a0-matrix — Agent Zero Matrix Integration Plugin

[![Agent Zero Plugin](https://img.shields.io/badge/Agent%20Zero-Plugin-blue)](https://github.com/agent0ai/agent-zero)
[![Matrix Protocol](https://img.shields.io/badge/Matrix-Protocol-green)](https://matrix.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Complete **bidirectional Matrix protocol integration** for [Agent Zero](https://github.com/agent0ai/agent-zero). Gives your AI agent a first-class presence on the Matrix network — it can be talked to by humans, collaborate with other agents, and proactively interact with any Matrix room or user.

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    Agent Zero Container                   │
│                                                          │
│  ┌─────────────┐    MCP Tools    ┌─────────────────────┐ │
│  │  Agent Zero  │◄──────────────►│  matrix-mcp-server  │ │
│  │   (LLM +    │   (20 tools)    │    (Rust, :3000)    │ │
│  │   Framework)│                 └──────────┬──────────┘ │
│  │             │                            │            │
│  │             │◄─── A0 API ────┐           │            │
│  └─────────────┘                │           │            │
│                          ┌──────┴──────┐    │            │
│                          │  matrix-bot │    │            │
│                          │   (Rust)    │    │            │
│                          └──────┴──────┘    │            │
└─────────────────────────────────┼───────────┼────────────┘
                                  │           │
                          Matrix CS API    Matrix CS API
                                  │           │
                           ┌──────▼───────────▼──────┐
                           │    Matrix Homeserver     │
                           │  (Synapse / Dendrite /   │
                           │   Continuwuity / etc.)   │
                           └──────────────────────────┘
                                      │
                              Federation (optional)
                                      │
                           ┌──────────▼──────────┐
                           │  Other Homeservers   │
                           │  (humans, agents,    │
                           │   other services)    │
                           └─────────────────────┘
```

### Two Complementary Components

| Component | Direction | Role | Source |
|-----------|-----------|------|--------|
| **matrix-mcp-server** | Agent Zero → Matrix | 20 MCP tools for rooms, messages, members, profiles, admin, discovery | [matrix-mcp-server-r2](https://github.com/l0r3zz/matrix-mcp-server-r2) |
| **matrix-bot** | Matrix → Agent Zero | Listens for messages, auto-joins rooms, forwards to Agent Zero API | [agent-matrix](https://github.com/l0r3zz/agent-matrix) |

Together they create a **complete two-way bridge**: humans and agents on Matrix converse with Agent Zero naturally.

> **No Docker or Rust toolchain required.** Pre-built binaries are automatically downloaded from GitHub Releases during plugin installation.

## Quick Start

### Prerequisites

- [Agent Zero](https://github.com/agent0ai/agent-zero) instance (v1.0+)
- A Matrix homeserver with a registered bot account
- Matrix access token for the bot account

### 1. Install the Plugin

In Agent Zero, navigate to **Settings → Plugins** and search for `a0_matrix`, or install manually:

```bash
cd /a0/usr/plugins/
git clone https://github.com/l0r3zz/a0-matrix.git
```

During installation, `hooks.py` automatically downloads the pre-built binaries:
- `matrix-mcp-server-r2` — from [matrix-mcp-server-r2 releases](https://github.com/l0r3zz/matrix-mcp-server-r2/releases)
- `matrix-bot-rust` — from [agent-matrix releases](https://github.com/l0r3zz/agent-matrix/releases)
- `set-display-name-rust` — from [agent-matrix releases](https://github.com/l0r3zz/agent-matrix/releases)

If the automatic download fails (e.g., network issues), you can re-run it manually:

```bash
/a0/usr/workdir/a0-matrix/install.sh
```

### 2. Configure

```bash
cd /a0/usr/workdir/a0-matrix/
# Edit .env with your Matrix credentials:
#   MATRIX_HOMESERVER_URL=https://your-homeserver.example.com
#   MATRIX_USER_ID=@your-bot:example.com
#   MATRIX_ACCESS_TOKEN=your_token_here
nano .env
```

> **Important:** Use `https://` for your homeserver URL. Using `http://` can cause authentication failures due to HTTP redirects stripping the access token.

### 3. Set the Agent Zero API Key

The Matrix bot needs an API key to forward messages to Agent Zero.

1. In the Agent Zero web UI, go to **Settings → External**
2. Find **Agent0 API Key** and set it to a secure secret (e.g., generate one with `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`)
3. Copy that same key into your `.env`:

```bash
# Replace YOUR_KEY with the value you set in Agent Zero Settings
sed -i 's/^A0_API_KEY=.*/A0_API_KEY=YOUR_KEY/' /a0/usr/workdir/a0-matrix/.env
```

> Both sides **must have the same key** — the bot sends it as `X-API-KEY` when forwarding Matrix messages to Agent Zero's `/api/api_message` endpoint.

### 4. Start Services

```bash
/a0/usr/workdir/a0-matrix/start.sh
```

### 5. Configure MCP in Agent Zero

In Agent Zero **Settings → MCP/A2A**, add the Matrix MCP server:

```json
{
  "mcpServers": {
    "matrix": {
      "url": "http://localhost:3000/mcp"
    }
  }
}
```

> **Note:** The MCP server URL uses `http://` (not `https://`) because it's a local connection inside the container. The MCP server reads Matrix credentials from its `.env` file — no need to pass them as headers.

### 6. Test the Connection

Verify the MCP server is healthy:

```bash
curl http://localhost:3000/health
```

Expected response:
```json
{"server":"matrix-mcp-server-r2","status":"healthy","user_id":"@your-bot:example.com","version":"0.1.1"}
```

To test the bot, use a different Matrix account to send a DM to your bot's user ID, or invite the bot to a room and mention it.

## Deployment Modes

### Embedded Mode (Recommended for single agent)

Both services run as processes inside the Agent Zero container.
Managed by `start.sh` / `stop.sh` / `status.sh` scripts.

```bash
./start.sh   # Start both services
./stop.sh    # Stop both services
./status.sh  # Check service health
```

### External Mode (Multi-agent / production)

Services run as separate Docker containers alongside Agent Zero.
Useful for the [Agent-Matrix](https://github.com/l0r3zz/agent-matrix) multi-instance fleet.

```bash
# Edit .env with your credentials, then:
docker compose up -d

# Check status
docker compose ps
docker compose logs -f
```

## MCP Tools Reference

Once configured, Agent Zero gains access to 20 Matrix tools:

| Category | Tools |
|----------|-------|
| **Rooms** | `list_joined_rooms`, `get_room_info`, `create_room`, `join_room`, `leave_room` |
| **Messages** | `get_room_messages`, `get_messages_by_date`, `send_message`, `send_direct_message` |
| **Members** | `get_room_members`, `invite_user`, `identify_active_users` |
| **Profiles** | `get_user_profile`, `get_my_profile`, `get_all_users` |
| **Admin** | `set_room_name`, `set_room_topic` |
| **Discovery** | `search_public_rooms`, `get_notification_counts`, `get_direct_messages` |

## Matrix Bot Features

- **Auto-join**: Automatically joins rooms when invited
- **Smart triggers**: Responds to `@botname:` mentions in groups, all messages in DMs
- **Typing indicators**: Shows typing status while processing
- **Markdown rendering**: Converts Markdown to HTML for rich messages
- **Context persistence**: Maintains per-room conversation context
- **Message chunking**: Splits long responses into manageable segments
- **Crash recovery**: Automatic restart with exponential backoff
- **Graceful shutdown**: Clean SIGTERM handling

## Configuration Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MATRIX_HOMESERVER_URL` | ✅ | — | Matrix homeserver URL (use `https://`) |
| `MATRIX_USER_ID` | ✅ | — | Bot's Matrix user ID |
| `MATRIX_ACCESS_TOKEN` | ✅ | — | Authentication token |
| `MATRIX_DEVICE_ID` | — | `AgentZeroBot` | Device ID for session |
| `MCP_PORT` | — | `3000` | MCP server HTTP port |
| `A0_API_URL` | — | `http://localhost:80/api_message` | Agent Zero API endpoint |
| `A0_API_KEY` | — | `""` | Agent Zero API key |
| `BOT_DISPLAY_NAME` | — | `Agent Zero` | Name shown in rooms |
| `AGENT_IDENTITY` | — | (= display name) | System prompt identity |
| `SYNC_TIMEOUT_MS` | — | `30000` | Sync poll timeout |
| `TRIGGER_PREFIX` | — | (auto) | Custom trigger prefix |
| `RUST_LOG` | — | `info` | Log verbosity |

## File Structure

```
a0-matrix/
├── plugin.yaml              # Plugin manifest
├── hooks.py                 # Install/uninstall lifecycle (downloads binaries)
├── install.sh               # Standalone binary installer (manual re-download)
├── default_config.yaml      # Default settings
├── .env.example             # Configuration template
├── docker-compose.yml       # External deployment mode
├── matrix-bot/              # Matrix bot (Rust source, for reference)
│   ├── Dockerfile           # Container build
│   └── rust/                # Rust source
│       ├── Cargo.toml
│       └── src/
│           ├── main.rs      # Bot binary
│           └── bin/
│               └── set_display_name.rs
├── scripts/
│   ├── start.sh             # Start services
│   ├── stop.sh              # Stop services
│   └── status.sh            # Health check
├── README.md
└── LICENSE
```

### Runtime Working Directory

After installation, the plugin creates a working directory at `/a0/usr/workdir/a0-matrix/`:

```
/a0/usr/workdir/a0-matrix/
├── bin/                         # Pre-built binaries (auto-downloaded)
│   ├── matrix-mcp-server-r2     # MCP server binary
│   ├── matrix-bot-rust          # Matrix bot binary
│   └── set-display-name-rust    # Display name utility
├── data/                        # Persistent bot data
├── logs/                        # Service logs
│   ├── mcp-server.log
│   └── bot.log
├── scripts/                     # Service management
├── .env                         # Your configuration (from .env.example)
├── install.sh                   # Re-download binaries if needed
├── start.sh                     # Start services
└── stop.sh                      # Stop services
```

## Troubleshooting

### `M_MISSING_TOKEN` error on startup

The homeserver URL is probably using `http://` instead of `https://`. HTTP requests get redirected, and the `Authorization` header is stripped during the redirect.

**Fix:** Change `MATRIX_HOMESERVER_URL` in `.env` to use `https://`.

### SSL error when connecting Agent Zero to MCP

```
httpx.ConnectError: [SSL] record layer failure
```

The MCP server URL in Agent Zero settings is using `https://` but the MCP server runs plain HTTP.

**Fix:** Use `http://localhost:3000/mcp` (not `https://`) in Settings → MCP/A2A.

### `Got the same sync response twice` in MCP server logs

This is a normal INFO message from the `matrix_sdk` library. It means the sync loop is running but the homeserver has no new events. **Not an error.**

### `Consecutive empty syncs` in bot logs

The bot hasn't received any messages yet. It periodically resets its sync token as a precaution. **This is normal idle behavior.**

### Binaries not found after install

If automatic download failed during plugin install, run the installer manually:

```bash
/a0/usr/workdir/a0-matrix/install.sh
```

Or delete existing binaries and re-run to force a fresh download:

```bash
rm -f /a0/usr/workdir/a0-matrix/bin/*
/a0/usr/workdir/a0-matrix/install.sh
```

## Generating a Matrix Access Token

```bash
curl -s -X POST "https://your-homeserver/_matrix/client/v3/login" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "m.login.password",
    "user": "your-bot-username",
    "password": "your-bot-password"
  }' | jq -r '.access_token'
```

Or use the `create-account` utility if you control the homeserver:

```bash
# Dendrite
docker exec dendrite /usr/bin/create-account -config /etc/dendrite/dendrite.yaml -username bot

# Synapse
docker exec synapse register_new_matrix_user -u bot -p password -a -c /data/homeserver.yaml http://localhost:8008
```

## Related Projects

- [Agent Zero](https://github.com/agent0ai/agent-zero) — The AI agent framework
- [matrix-mcp-server-r2](https://github.com/l0r3zz/matrix-mcp-server-r2) — Rust MCP server for Matrix
- [Agent-Matrix](https://github.com/l0r3zz/agent-matrix) — Multi-agent federation lab
- [Matrix Protocol](https://matrix.org) — Decentralized communication standard

## License

MIT — see [LICENSE](LICENSE)
