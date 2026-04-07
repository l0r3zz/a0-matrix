"""a0-matrix Plugin Lifecycle Hooks

Handles installation and uninstallation of the Matrix integration plugin.
Downloads pre-built binaries from GitHub Releases (no Docker or Rust
toolchain required inside the Agent Zero container).
"""

import os
import shutil
import subprocess
import urllib.request
from pathlib import Path

# Plugin paths
PLUGIN_DIR = Path(__file__).parent

# Derive the Agent Zero workdir dynamically.
_A0_WORKDIR = Path(os.environ.get("A0_WORKDIR", "/a0/usr/workdir"))
WORKDIR = _A0_WORKDIR / "a0-matrix"
BIN_DIR  = WORKDIR / "bin"
DATA_DIR = WORKDIR / "data"
LOG_DIR  = WORKDIR / "logs"
ENV_FILE = WORKDIR / ".env"

# GitHub Release URLs for pre-built binaries
MCP_SERVER_RELEASE_URL = (
    "https://github.com/l0r3zz/matrix-mcp-server-r2/releases/latest/download"
)
BOT_RELEASE_URL = (
    "https://github.com/l0r3zz/agent-matrix/releases/latest/download"
)

# Binary manifest: (name, download_url, local_dest)
BINARIES = [
    ("matrix-mcp-server-r2", f"{MCP_SERVER_RELEASE_URL}/matrix-mcp-server-r2",
     BIN_DIR / "matrix-mcp-server-r2"),
    ("matrix-bot-rust", f"{BOT_RELEASE_URL}/matrix-bot-rust",
     BIN_DIR / "matrix-bot-rust"),
    ("set-display-name-rust", f"{BOT_RELEASE_URL}/set-display-name-rust",
     BIN_DIR / "set-display-name-rust"),
]


def _download_binary(name: str, url: str, dest: Path) -> bool:
    """Download a single binary from a GitHub Release URL."""
    if dest.exists():
        print(f"[a0-matrix] {name} already exists at {dest}, skipping")
        return True
    print(f"[a0-matrix] Downloading {name}...")
    try:
        urllib.request.urlretrieve(url, dest)
        dest.chmod(0o755)
        size_mb = dest.stat().st_size / (1024 * 1024)
        print(f"[a0-matrix] ✅ {name} → {dest} ({size_mb:.1f} MB)")
        return True
    except Exception as e:
        # Clean up partial download
        if dest.exists():
            dest.unlink()
        print(f"[a0-matrix] ⚠️  Failed to download {name}: {e}")
        print(f"[a0-matrix]    URL: {url}")
        return False


def _download_binaries() -> int:
    """Download all pre-built binaries. Returns count of failures."""
    BIN_DIR.mkdir(parents=True, exist_ok=True)
    failures = 0
    for name, url, dest in BINARIES:
        if not _download_binary(name, url, dest):
            failures += 1
    return failures


def install():
    """Install the a0-matrix plugin.

    Steps:
    1. Create working directories
    2. Copy configuration templates
    3. Download pre-built binaries from GitHub Releases
    4. Copy scripts and set up management tools
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

    # 3. Download pre-built binaries from GitHub Releases
    print("[a0-matrix] Downloading pre-built binaries from GitHub Releases...")
    failures = _download_binaries()
    if failures > 0:
        print(f"[a0-matrix] ⚠️  {failures} binary download(s) failed.")
        print("[a0-matrix]    You can download them manually or run install.sh later.")

    # 4. Copy scripts
    scripts_src = PLUGIN_DIR / "scripts"
    scripts_dst = WORKDIR / "scripts"
    if scripts_src.exists():
        if scripts_dst.exists():
            shutil.rmtree(scripts_dst)
        shutil.copytree(scripts_src, scripts_dst)
        for script in scripts_dst.glob("*.sh"):
            script.chmod(0o755)
        print(f"[a0-matrix] Copied scripts → {scripts_dst}")

    # Copy startup/stop shortcuts to workdir root
    for script_name in ["start.sh", "stop.sh"]:
        src = PLUGIN_DIR / "scripts" / script_name
        if src.exists():
            dst = WORKDIR / script_name
            shutil.copy2(src, dst)
            dst.chmod(0o755)

    # Copy install.sh to workdir for manual re-runs
    install_src = PLUGIN_DIR / "install.sh"
    if install_src.exists():
        install_dst = WORKDIR / "install.sh"
        shutil.copy2(install_src, install_dst)
        install_dst.chmod(0o755)

    print("[a0-matrix] ✅ Installation complete!")
    print("")
    print("[a0-matrix] Next steps:")
    print(f"  1. Edit {ENV_FILE} with your Matrix credentials")
    print(f"  2. Run: {WORKDIR}/start.sh")
    print(f"  3. Configure MCP in Agent Zero Settings → MCP/A2A")
    print(f"     URL: http://localhost:3000/mcp")
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
            backup = _A0_WORKDIR / ".a0-matrix-env-backup"
            shutil.copy2(ENV_FILE, backup)
            print(f"[a0-matrix] Backed up .env → {backup}")

        shutil.rmtree(WORKDIR)
        print(f"[a0-matrix] Removed {WORKDIR}")

    print("[a0-matrix] ✅ Uninstallation complete")
