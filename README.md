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
│                          └──────┬──────┘    │            │
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

| Component | Direction | Role |
|-----------|-----------|------|
| **matrix-mcp-server** | Agent Zero → Matrix | 20 MCP tools for rooms, messages, members, profiles, admin, discovery |
| **matrix-bot** | Matrix → Agent Zero | Listens for messages, auto-joins rooms, forwards to Agent Zero API |

Together they create a **complete two-way bridge**: humans and agents on Matrix converse with Agent Zero naturally.

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

### 2. Configure

```bash
cd /a0/usr/workdir/a0-matrix/
cp .env.example .env
# Edit .env with your Matrix credentials:
#   MATRIX_HOMESERVER_URL=https://your-homeserver.example.com
#   MATRIX_USER_ID=@your-bot:example.com
#   MATRIX_ACCESS_TOKEN=your_token_here
```

### 3. Build the Bot (if using embedded mode)

```bash
# The bot needs to be compiled from Rust source:
cd /a0/usr/workdir/a0-matrix/matrix-bot/rust
cargo build --release
cp target/release/matrix-bot-rust ../../bin/
cp target/release/set-display-name-rust ../../bin/
```

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
      "url": "http://localhost:3000/mcp",
      "headers": {
        "matrix_access_token": "your_token_here",
        "matrix_homeserver_url": "https://your-homeserver.example.com",
        "matrix_user_id": "@your-bot:example.com"
      }
    }
  }
}
```

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
| `MATRIX_HOMESERVER_URL` | ✅ | — | Matrix homeserver URL |
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
├── hooks.py                 # Install/uninstall lifecycle
├── default_config.yaml      # Default settings
├── .env.example             # Configuration template
├── docker-compose.yml       # External deployment mode
├── matrix-bot/              # Matrix bot (Rust)
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
├── index.yaml               # a0-plugins index entry
├── README.md
└── LICENSE
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
