"""
MCP Configuration & Installation Helpers.

Generates ready-to-use configuration snippets for:
  - Claude Desktop (claude_desktop_config.json)
  - Cursor (.cursor/mcp.json)
  - VS Code (settings.json)
  - Generic MCP clients

Also validates that the server is properly installed.
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional


# ---------------------------------------------------------------------------
# Config generation
# ---------------------------------------------------------------------------

def _server_command(cwd: Optional[str] = None) -> Dict[str, Any]:
    """Return the base server command config."""
    cwd = cwd or str(Path(__file__).parent.parent)
    python = sys.executable
    return {
        "command": python,
        "args": ["-m", "mcp_server"],
        "cwd": cwd,
        "env": {
            "SINTRA_ENV": "production",
            "SINTRA_LOG_LEVEL": "INFO",
        },
    }


def generate_claude_desktop_config(cwd: Optional[str] = None) -> str:
    """
    Generate the claude_desktop_config.json snippet for Claude Desktop.

    Returns a JSON string ready to paste into:
      macOS: ~/Library/Application Support/Claude/claude_desktop_config.json
      Windows: %APPDATA%\\Claude\\claude_desktop_config.json
    """
    config = {
        "mcpServers": {
            "sintra-prime": _server_command(cwd),
        }
    }
    return json.dumps(config, indent=2)


def generate_cursor_config(cwd: Optional[str] = None) -> str:
    """
    Generate the .cursor/mcp.json config for Cursor IDE.

    Returns a JSON string ready to save as .cursor/mcp.json
    in your project root.
    """
    config = {
        "mcpServers": {
            "sintra-prime": _server_command(cwd),
        }
    }
    return json.dumps(config, indent=2)


def generate_vscode_config(cwd: Optional[str] = None) -> str:
    """
    Generate the VS Code settings.json snippet for MCP support.

    Returns a JSON string to merge into .vscode/settings.json.
    Requires the VS Code MCP extension.
    """
    config = {
        "mcp.servers": {
            "sintra-prime": {
                **_server_command(cwd),
                "description": "SintraPrime Legal & Financial AI",
            }
        }
    }
    return json.dumps(config, indent=2)


def generate_windsurf_config(cwd: Optional[str] = None) -> str:
    """Generate config for Windsurf IDE."""
    return generate_cursor_config(cwd)  # Same format


def generate_all_configs(cwd: Optional[str] = None) -> Dict[str, str]:
    """Generate all client configurations at once."""
    return {
        "claude_desktop": generate_claude_desktop_config(cwd),
        "cursor": generate_cursor_config(cwd),
        "vscode": generate_vscode_config(cwd),
        "windsurf": generate_windsurf_config(cwd),
    }


# ---------------------------------------------------------------------------
# Installation
# ---------------------------------------------------------------------------

def install_globally(target_dir: Optional[str] = None) -> bool:
    """
    Register the SintraPrime MCP server globally.

    Copies the claude_desktop_config.json to the OS-appropriate location
    so Claude Desktop can discover the server automatically.

    Returns True on success, False on failure.
    """
    system = platform.system()

    if system == "Darwin":
        config_path = Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    elif system == "Windows":
        config_path = Path(os.environ.get("APPDATA", "~")) / "Claude" / "claude_desktop_config.json"
    elif system == "Linux":
        config_path = Path.home() / ".config" / "Claude" / "claude_desktop_config.json"
    else:
        print(f"Unknown platform: {system}")
        return False

    cwd = target_dir or str(Path(__file__).parent.parent)
    config_json = generate_claude_desktop_config(cwd)

    # Merge with existing config if present
    if config_path.exists():
        try:
            existing = json.loads(config_path.read_text())
            existing.setdefault("mcpServers", {})
            new_config = json.loads(config_json)
            existing["mcpServers"]["sintra-prime"] = new_config["mcpServers"]["sintra-prime"]
            config_json = json.dumps(existing, indent=2)
        except (json.JSONDecodeError, KeyError):
            pass  # Overwrite if unparseable

    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(config_json, encoding="utf-8")
        print(f"✅ SintraPrime MCP server registered at: {config_path}")
        print("   Restart Claude Desktop to activate.")
        return True
    except PermissionError as exc:
        print(f"❌ Permission error writing to {config_path}: {exc}")
        return False


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_installation() -> Dict[str, Any]:
    """
    Check that the server is properly installed and can be started.

    Returns a dict with validation results.
    """
    results: Dict[str, Any] = {
        "python_version": sys.version,
        "server_path": str(Path(__file__).parent),
        "checks": {},
    }

    # Check Python version
    major, minor = sys.version_info[:2]
    results["checks"]["python_version"] = {
        "ok": major == 3 and minor >= 10,
        "value": f"{major}.{minor}",
        "required": "3.10+",
    }

    # Check required files exist
    server_dir = Path(__file__).parent
    required_files = [
        "__init__.py",
        "mcp_server.py",
        "mcp_types.py",
        "mcp_transport.py",
        "sintra_tools.py",
        "sintra_resources.py",
        "sintra_prompts.py",
    ]
    for fname in required_files:
        results["checks"][f"file_{fname}"] = {
            "ok": (server_dir / fname).exists(),
            "path": str(server_dir / fname),
        }

    # Check importability
    try:
        import mcp_server  # noqa: F401
        results["checks"]["importable"] = {"ok": True}
    except ImportError as exc:
        results["checks"]["importable"] = {"ok": False, "error": str(exc)}

    # Check Claude Desktop config location
    system = platform.system()
    if system == "Darwin":
        config_path = Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    elif system == "Windows":
        config_path = Path(os.environ.get("APPDATA", "~")) / "Claude" / "claude_desktop_config.json"
    else:
        config_path = Path.home() / ".config" / "Claude" / "claude_desktop_config.json"

    registered = False
    if config_path.exists():
        try:
            cfg = json.loads(config_path.read_text())
            registered = "sintra-prime" in cfg.get("mcpServers", {})
        except (json.JSONDecodeError, OSError):
            pass

    results["checks"]["claude_desktop_registered"] = {
        "ok": registered,
        "config_path": str(config_path),
    }

    results["overall"] = all(c.get("ok", False) for c in results["checks"].values())
    return results


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Command-line interface for MCP configuration management."""
    import argparse

    parser = argparse.ArgumentParser(
        description="SintraPrime MCP Server Configuration Manager"
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("install", help="Install globally for Claude Desktop")
    subparsers.add_parser("validate", help="Validate installation")

    show = subparsers.add_parser("show", help="Show configuration")
    show.add_argument("client", choices=["claude", "cursor", "vscode", "all"], default="all", nargs="?")

    args = parser.parse_args()

    if args.command == "install":
        install_globally()

    elif args.command == "validate":
        results = validate_installation()
        print(json.dumps(results, indent=2))
        sys.exit(0 if results["overall"] else 1)

    elif args.command == "show":
        client = getattr(args, "client", "all")
        configs = generate_all_configs()
        if client == "all":
            for name, cfg in configs.items():
                print(f"\n{'='*60}")
                print(f"  {name.upper()} CONFIG")
                print(f"{'='*60}")
                print(cfg)
        else:
            key_map = {"claude": "claude_desktop", "cursor": "cursor", "vscode": "vscode"}
            print(configs.get(key_map.get(client, client), "Unknown client"))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
