"""a0-matrix Plugin Lifecycle Hooks

Handles installation and uninstallation of the Matrix integration plugin.
Supports two deployment modes:
  - Embedded: Services run inside the Agent Zero container as processes
  - External: Services run as separate Docker containers via docker-compose
"""

import os
import shutil
import subprocess
import json
from pathlib import Path
# Plugin paths
PLUGIN_DIR = Path(__file__).parent

# Derive the Agent Zero workdir dynamically.
# Priority:
#   1. A0_WORKDIR env var (set by custom or non-standard deployments)
#   2. Standard Agent Zero default: /a0/usr/workdir
_A0_WORKDIR = Path(os.environ.get("A0_WORKDIR", "/a0/usr/workdir"))
WORKDIR = _A0_WORKDIR / "a0-matrix"
BIN_DIR  = WORKDIR / "bin"
DATA_DIR = WORKDIR / "data"
LOG_DIR  = WORKDIR / "logs"
ENV_FILE = WORKDIR / ".env"

# GHCR image for the MCP server
MCP_SERVER_IMAGE = "ghcr.io/l0r3zz/matrix-mcp-server-r2"
MCP_SERVER_VERSION = "latest"


def install():
    """Install the a0-matrix plugin.

    Steps:
    1. Create working directories
    2. Copy configuration templates
    3. Copy bot source and scripts
    4. Attempt to pull MCP server binary from GHCR image
    5. Set up startup script
    """
    print("[a0-matrix] Starting installation...")

    # 1. Create working directories
    for d in [WORKDIR, BIN_DIR, DATA_DIR, LOG_DIR]:
        d.mkdir(parents=True, exist_ok=True)
    print(f"[a0-matrix] Created directories under {WORKDIR}")

    # 2. Copy configuration templates
    env_example = PLUGIN_DIR / ".env.example"
    if env_example.exists() and not ENV_FILE.exists():
        shutil.copy2(env_example, ENV_FILE)
        print(f"[a0-matrix] Copied .env.example → {ENV_FILE}")
        print(f"[a0-matrix] ⚠️  Edit {ENV_FILE} with your Matrix credentials before starting!")
    elif ENV_FILE.exists():
        print(f"[a0-matrix] .env already exists at {ENV_FILE}, skipping")

    # 3. Copy bot source and scripts
    bot_src = PLUGIN_DIR / "matrix-bot"
    bot_dst = WORKDIR / "matrix-bot"
    if bot_src.exists():
        if bot_dst.exists():
            shutil.rmtree(bot_dst)
        shutil.copytree(bot_src, bot_dst)
        print(f"[a0-matrix] Copied matrix-bot source → {bot_dst}")

    # Copy scripts
    scripts_src = PLUGIN_DIR / "scripts"
    scripts_dst = WORKDIR / "scripts"
    if scripts_src.exists():
        if scripts_dst.exists():
            shutil.rmtree(scripts_dst)
        shutil.copytree(scripts_src, scripts_dst)
        # Make scripts executable
        for script in scripts_dst.glob("*.sh"):
            script.chmod(0o755)
        print(f"[a0-matrix] Copied scripts → {scripts_dst}")

    # 4. Try to extract MCP server binary from GHCR image
    print("[a0-matrix] Attempting to pull MCP server from GHCR...")
    mcp_binary = BIN_DIR / "matrix-mcp-server"
    try:
        # Check if docker is available
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            image = f"{MCP_SERVER_IMAGE}:{MCP_SERVER_VERSION}"
            print(f"[a0-matrix] Pulling {image}...")
            subprocess.run(
                ["docker", "pull", image],
                capture_output=True, text=True, timeout=300
            )

            # Extract binary from image using three discrete steps
            # Step 1: create a stopped container from the image
            create_result = subprocess.run(
                ["docker", "create", "--name", "a0-matrix-extract", image],
                capture_output=True, text=True, timeout=60
            )
            if create_result.returncode != 0:
                raise RuntimeError(f"docker create failed: {create_result.stderr.strip()}")

            try:
                # Step 2: copy the binary out of the container
                cp_result = subprocess.run(
                    ["docker", "cp",
                     "a0-matrix-extract:/app/matrix-mcp-server-r2",
                     str(mcp_binary)],
                    capture_output=True, text=True, timeout=60
                )
                if cp_result.returncode != 0:
                    raise RuntimeError(f"docker cp failed: {cp_result.stderr.strip()}")
            finally:
                # Step 3: always remove the temporary container
                subprocess.run(
                    ["docker", "rm", "a0-matrix-extract"],
                    capture_output=True, text=True, timeout=30
                )

            if mcp_binary.exists():
                mcp_binary.chmod(0o755)
                print(f"[a0-matrix] ✅ MCP server binary extracted → {mcp_binary}")
            else:
                print("[a0-matrix] ⚠️  Binary not found after extraction")
                print("[a0-matrix] MCP server will need to be run via docker-compose")
        else:
            print("[a0-matrix] Docker not available; MCP server needs manual setup")
    except RuntimeError as e:
        print(f"[a0-matrix] ⚠️  Could not extract binary: {e}")
        print("[a0-matrix] MCP server will need to be run via docker-compose")
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"[a0-matrix] Docker extraction skipped: {e}")
        print("[a0-matrix] You can run the MCP server via docker-compose or install manually")

    # 5. Copy startup/management scripts to workdir
    startup_script = PLUGIN_DIR / "scripts" / "start.sh"
    if startup_script.exists():
        dst = WORKDIR / "start.sh"
        shutil.copy2(startup_script, dst)
        dst.chmod(0o755)

    stop_script = PLUGIN_DIR / "scripts" / "stop.sh"
    if stop_script.exists():
        dst = WORKDIR / "stop.sh"
        shutil.copy2(stop_script, dst)
        dst.chmod(0o755)

    print("[a0-matrix] ✅ Installation complete!")
    print("")
    print("[a0-matrix] Next steps:")
    print(f"  1. Edit {ENV_FILE} with your Matrix credentials")
    print(f"  2. Run: {WORKDIR}/start.sh")
    print(f"  3. Configure MCP in Agent Zero Settings → MCP/A2A")
    print("")


def uninstall():
    """Uninstall the a0-matrix plugin.

    Steps:
    1. Stop running services
    2. Clean up containers (if using docker-compose)
    3. Optionally remove working directory
    """
    print("[a0-matrix] Starting uninstallation...")

    # 1. Stop running services
    stop_script = WORKDIR / "stop.sh"
    if stop_script.exists():
        try:
            subprocess.run(
                [str(stop_script)],
                capture_output=True, text=True, timeout=30
            )
            print("[a0-matrix] Stopped running services")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    # 2. Kill any remaining processes
    for proc_name in ["matrix-mcp-server", "matrix-bot-rust"]:
        try:
            subprocess.run(
                ["pkill", "-f", proc_name],
                capture_output=True, text=True, timeout=10
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    # 3. Clean up docker-compose if used
    compose_file = PLUGIN_DIR / "docker-compose.yml"
    if compose_file.exists():
        try:
            subprocess.run(
                ["docker", "compose", "-f", str(compose_file), "down", "--remove-orphans"],
                capture_output=True, text=True, timeout=60
            )
            print("[a0-matrix] Removed Docker containers")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    # 4. Remove working directory (preserve .env for re-install)
    if WORKDIR.exists():
        # Backup .env if it exists
        if ENV_FILE.exists():
            backup = Path("/a0/usr/workdir/.a0-matrix-env-backup")
            shutil.copy2(ENV_FILE, backup)
            print(f"[a0-matrix] Backed up .env → {backup}")

        shutil.rmtree(WORKDIR)
        print(f"[a0-matrix] Removed {WORKDIR}")

    print("[a0-matrix] ✅ Uninstallation complete")
