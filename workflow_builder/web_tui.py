"""
SintraPrime-Unified Web TUI (Terminal UI in Browser)
WebSocket-based terminal emulator server with VT100/ANSI escape code support.
Provides an xterm.js-compatible terminal over WebSocket.
"""

from pathlib import Path
from __future__ import annotations

import asyncio
import json
import logging
import os
import shlex
import sys
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# ANSI / VT100 Color Codes
# ---------------------------------------------------------------------------

class ANSI:
    """VT100/ANSI escape code constants."""
    RESET = "\x1b[0m"
    BOLD = "\x1b[1m"
    DIM = "\x1b[2m"
    ITALIC = "\x1b[3m"
    UNDERLINE = "\x1b[4m"
    BLINK = "\x1b[5m"
    REVERSE = "\x1b[7m"

    # Foreground colors
    FG_BLACK = "\x1b[30m"
    FG_RED = "\x1b[31m"
    FG_GREEN = "\x1b[32m"
    FG_YELLOW = "\x1b[33m"
    FG_BLUE = "\x1b[34m"
    FG_MAGENTA = "\x1b[35m"
    FG_CYAN = "\x1b[36m"
    FG_WHITE = "\x1b[37m"
    FG_BRIGHT_BLACK = "\x1b[90m"
    FG_BRIGHT_RED = "\x1b[91m"
    FG_BRIGHT_GREEN = "\x1b[92m"
    FG_BRIGHT_YELLOW = "\x1b[93m"
    FG_BRIGHT_BLUE = "\x1b[94m"
    FG_BRIGHT_MAGENTA = "\x1b[95m"
    FG_BRIGHT_CYAN = "\x1b[96m"
    FG_BRIGHT_WHITE = "\x1b[97m"

    # Background colors
    BG_BLACK = "\x1b[40m"
    BG_RED = "\x1b[41m"
    BG_GREEN = "\x1b[42m"
    BG_YELLOW = "\x1b[43m"
    BG_BLUE = "\x1b[44m"
    BG_MAGENTA = "\x1b[45m"
    BG_CYAN = "\x1b[46m"
    BG_WHITE = "\x1b[47m"

    # Cursor control
    CLEAR_SCREEN = "\x1b[2J\x1b[H"
    CLEAR_LINE = "\x1b[2K\r"
    CURSOR_UP = "\x1b[A"
    CURSOR_DOWN = "\x1b[B"
    CURSOR_FORWARD = "\x1b[C"
    CURSOR_BACK = "\x1b[D"

    @staticmethod
    def move_cursor(row: int, col: int) -> str:
        return f"\x1b[{row};{col}H"

    @staticmethod
    def fg_256(color: int) -> str:
        return f"\x1b[38;5;{color}m"

    @staticmethod
    def bg_256(color: int) -> str:
        return f"\x1b[48;5;{color}m"


def colorize(text: str, fg: str = "", bg: str = "", bold: bool = False) -> str:
    """Apply ANSI color codes to text."""
    codes = []
    if bold:
        codes.append(ANSI.BOLD)
    if fg:
        codes.append(fg)
    if bg:
        codes.append(bg)
    prefix = "".join(codes)
    return f"{prefix}{text}{ANSI.RESET}" if codes else text


# ---------------------------------------------------------------------------
# Terminal Session
# ---------------------------------------------------------------------------

class TerminalSession:
    """Represents a single WebSocket terminal session."""

    def __init__(self, session_id: str, send_fn: Callable[[str], Any]):
        self.session_id = session_id
        self.send_fn = send_fn
        self.history: List[str] = []
        self.history_index: int = -1
        self.current_line: str = ""
        self.cursor_pos: int = 0
        self.running: bool = True
        self.cwd: str = os.getcwd()
        self.env: Dict[str, str] = {
            "USER": "sintra",
            "HOME": os.environ.get("HOME", str(Path.home())),
            "SHELL": "sintratui",
            "TERM": "xterm-256color",
        }
        self._tab_completions: List[str] = []
        self._tab_index: int = 0

    async def write(self, text: str) -> None:
        """Send text to the terminal."""
        await self.send_fn(text)

    async def writeln(self, text: str) -> None:
        """Send a line of text to the terminal."""
        await self.send_fn(text + "\r\n")

    async def show_prompt(self) -> None:
        """Display the shell prompt."""
        prompt = (
            colorize("sintra", ANSI.FG_BRIGHT_GREEN, bold=True)
            + colorize("@", ANSI.FG_WHITE)
            + colorize("prime", ANSI.FG_BRIGHT_CYAN, bold=True)
            + colorize(":~$ ", ANSI.FG_BRIGHT_WHITE)
        )
        await self.write(prompt)

    def add_to_history(self, cmd: str) -> None:
        if cmd.strip() and (not self.history or self.history[-1] != cmd):
            self.history.append(cmd)
        self.history_index = len(self.history)

    def get_tab_completions(self, partial: str) -> List[str]:
        """Return tab completion suggestions."""
        commands = list(COMMANDS.keys())
        completions = [c for c in commands if c.startswith(partial)]
        completions.sort()
        return completions


# ---------------------------------------------------------------------------
# Command Registry
# ---------------------------------------------------------------------------

COMMANDS: Dict[str, Dict[str, Any]] = {}


def command(name: str, description: str, usage: str = ""):
    """Decorator to register a TUI command."""
    def decorator(fn: Callable):
        COMMANDS[name] = {
            "fn": fn,
            "description": description,
            "usage": usage or name,
        }
        return fn
    return decorator


# ---------------------------------------------------------------------------
# Command Implementations
# ---------------------------------------------------------------------------

@command("help", "Show available commands", "help [command]")
async def cmd_help(session: TerminalSession, args: List[str]) -> None:
    if args:
        cmd_name = args[0]
        if cmd_name in COMMANDS:
            cmd_info = COMMANDS[cmd_name]
            await session.writeln(colorize(f"\n{cmd_name}", ANSI.FG_BRIGHT_CYAN, bold=True))
            await session.writeln(f"  {cmd_info['description']}")
            await session.writeln(f"  Usage: {cmd_info['usage']}\n")
        else:
            await session.writeln(colorize(f"Unknown command: {cmd_name}", ANSI.FG_RED))
        return

    await session.writeln(colorize("\n╔══════════════════════════════════════════╗", ANSI.FG_BRIGHT_BLUE))
    await session.writeln(colorize("║      SintraPrime Workflow Terminal       ║", ANSI.FG_BRIGHT_BLUE))
    await session.writeln(colorize("╚══════════════════════════════════════════╝\n", ANSI.FG_BRIGHT_BLUE))
    await session.writeln(colorize("Available Commands:", ANSI.FG_BRIGHT_YELLOW, bold=True))
    await session.writeln("")

    max_name_len = max(len(n) for n in COMMANDS)
    for name, info in sorted(COMMANDS.items()):
        padding = " " * (max_name_len - len(name) + 2)
        await session.writeln(
            f"  {colorize(name, ANSI.FG_BRIGHT_GREEN)}{padding}"
            f"{colorize(info['description'], ANSI.FG_WHITE)}"
        )
    await session.writeln("")


@command("clear", "Clear the terminal screen", "clear")
async def cmd_clear(session: TerminalSession, args: List[str]) -> None:
    await session.write(ANSI.CLEAR_SCREEN)


@command("workflow", "Manage workflows", "workflow <list|run|status|create|delete> [args]")
async def cmd_workflow(session: TerminalSession, args: List[str]) -> None:
    if not args:
        await session.writeln(colorize("Usage: workflow <list|run|status|create|delete>", ANSI.FG_YELLOW))
        return

    sub = args[0].lower()

    if sub == "list":
        try:
            from workflow_builder.workflow_engine import WorkflowTemplateRegistry
            templates = WorkflowTemplateRegistry.list_templates()
            await session.writeln(colorize(f"\n{'ID':<30} {'Name':<40} {'Tags'}", ANSI.FG_BRIGHT_YELLOW, bold=True))
            await session.writeln("─" * 85)
            for t in templates:
                tags_str = ", ".join(t.get("tags", []))
                await session.writeln(
                    f"{colorize(t['id'][:28], ANSI.FG_CYAN):<30} "
                    f"{t['name'][:38]:<40} "
                    f"{colorize(tags_str, ANSI.FG_BRIGHT_BLACK)}"
                )
            await session.writeln(f"\n{colorize(str(len(templates)), ANSI.FG_BRIGHT_GREEN)} workflow template(s) available\n")
        except Exception as exc:
            await session.writeln(colorize(f"Error: {exc}", ANSI.FG_RED))

    elif sub == "run":
        if len(args) < 2:
            await session.writeln(colorize("Usage: workflow run <template_id>", ANSI.FG_YELLOW))
            return
        template_id = args[1]
        await session.writeln(colorize(f"\n▶ Running workflow: {template_id}", ANSI.FG_BRIGHT_GREEN))
        await asyncio.sleep(0.1)
        try:
            from workflow_builder.workflow_engine import WorkflowTemplateRegistry
            template = WorkflowTemplateRegistry.get(template_id)
            if not template:
                await session.writeln(colorize(f"Template '{template_id}' not found.", ANSI.FG_RED))
                return
            topo = template.topological_sort()
            for nid in topo:
                node = template.nodes[nid]
                icon = {"START": "▶", "END": "⏹", "ACTION": "⚡", "DECISION": "◆",
                        "PARALLEL": "⫶", "WAIT": "⏳", "AGENT_CALL": "🤖", "HUMAN_REVIEW": "👤"}.get(
                    node.node_type.value, "•"
                )
                await session.writeln(
                    f"  {icon} {colorize(node.node_type.value, ANSI.FG_BRIGHT_CYAN):<16} "
                    f"{node.label}"
                )
                await asyncio.sleep(0.05)
            await session.writeln(colorize("\n✓ Workflow simulation complete\n", ANSI.FG_BRIGHT_GREEN))
        except Exception as exc:
            await session.writeln(colorize(f"Error: {exc}", ANSI.FG_RED))

    elif sub == "status":
        execution_id = args[1] if len(args) > 1 else "all"
        await session.writeln(colorize(f"\nWorkflow Execution Status", ANSI.FG_BRIGHT_YELLOW, bold=True))
        await session.writeln("─" * 50)
        await session.writeln(f"  {colorize('No active executions', ANSI.FG_BRIGHT_BLACK)}\n")

    elif sub == "create":
        if len(args) < 2:
            await session.writeln(colorize("Usage: workflow create <name>", ANSI.FG_YELLOW))
            return
        name = " ".join(args[1:])
        import uuid
        wf_id = str(uuid.uuid4())[:8]
        await session.writeln(colorize(f"\n✓ Workflow '{name}' created (id: {wf_id})\n", ANSI.FG_BRIGHT_GREEN))

    elif sub == "validate":
        if len(args) < 2:
            await session.writeln(colorize("Usage: workflow validate <template_id>", ANSI.FG_YELLOW))
            return
        template_id = args[1]
        try:
            from workflow_builder.workflow_engine import WorkflowTemplateRegistry
            template = WorkflowTemplateRegistry.get(template_id)
            if not template:
                await session.writeln(colorize(f"Template '{template_id}' not found.", ANSI.FG_RED))
                return
            errors = template.validate()
            if errors:
                await session.writeln(colorize(f"\n✗ Validation failed:", ANSI.FG_RED))
                for err in errors:
                    await session.writeln(f"  • {err}")
            else:
                await session.writeln(colorize(f"\n✓ Workflow '{template.name}' is valid\n", ANSI.FG_BRIGHT_GREEN))
        except Exception as exc:
            await session.writeln(colorize(f"Error: {exc}", ANSI.FG_RED))

    else:
        await session.writeln(colorize(f"Unknown workflow subcommand: {sub}", ANSI.FG_RED))


@command("agent", "Manage AI agents", "agent <list|status|start|stop> [args]")
async def cmd_agent(session: TerminalSession, args: List[str]) -> None:
    if not args:
        await session.writeln(colorize("Usage: agent <list|status|start|stop>", ANSI.FG_YELLOW))
        return

    sub = args[0].lower()

    agents_data = [
        {"id": "agt_legal_001", "name": "Legal Research Agent", "status": "active", "load": "23%"},
        {"id": "agt_doc_002", "name": "Document Drafting Agent", "status": "active", "load": "45%"},
        {"id": "agt_review_003", "name": "Contract Review Agent", "status": "idle", "load": "0%"},
        {"id": "agt_compliance_004", "name": "Compliance Agent", "status": "active", "load": "67%"},
        {"id": "agt_research_005", "name": "Case Research Agent", "status": "idle", "load": "0%"},
    ]

    if sub == "list":
        await session.writeln(colorize(f"\n{'ID':<20} {'Name':<30} {'Status':<10} {'Load'}", ANSI.FG_BRIGHT_YELLOW, bold=True))
        await session.writeln("─" * 70)
        for agent in agents_data:
            status_color = ANSI.FG_BRIGHT_GREEN if agent["status"] == "active" else ANSI.FG_BRIGHT_BLACK
            await session.writeln(
                f"  {colorize(agent['id'], ANSI.FG_CYAN):<20} "
                f"{agent['name']:<30} "
                f"{colorize(agent['status'], status_color):<10} "
                f"{agent['load']}"
            )
        await session.writeln(f"\n{colorize('5', ANSI.FG_BRIGHT_GREEN)} agent(s) registered\n")

    elif sub == "status":
        active = sum(1 for a in agents_data if a["status"] == "active")
        idle = len(agents_data) - active
        await session.writeln(colorize("\nAgent System Status", ANSI.FG_BRIGHT_YELLOW, bold=True))
        await session.writeln("─" * 40)
        await session.writeln(f"  Total agents:  {colorize(str(len(agents_data)), ANSI.FG_BRIGHT_WHITE)}")
        await session.writeln(f"  Active:        {colorize(str(active), ANSI.FG_BRIGHT_GREEN)}")
        await session.writeln(f"  Idle:          {colorize(str(idle), ANSI.FG_BRIGHT_BLACK)}")
        await session.writeln(f"  System load:   {colorize('moderate', ANSI.FG_BRIGHT_YELLOW)}\n")

    else:
        await session.writeln(colorize(f"Unknown agent subcommand: {sub}", ANSI.FG_RED))


@command("logs", "View system logs", "logs [--lines N] [--filter KEYWORD]")
async def cmd_logs(session: TerminalSession, args: List[str]) -> None:
    lines_count = 20
    filter_kw = ""

    i = 0
    while i < len(args):
        if args[i] in ("--lines", "-n") and i + 1 < len(args):
            try:
                lines_count = int(args[i + 1])
            except ValueError:
                pass
            i += 2
        elif args[i] in ("--filter", "-f") and i + 1 < len(args):
            filter_kw = args[i + 1]
            i += 2
        else:
            i += 1

    sample_logs = [
        ("INFO", "workflow_engine", "Trust Creation Workflow started"),
        ("INFO", "agent", "Legal Research Agent: task received"),
        ("DEBUG", "workflow_engine", "Node 'Collect Grantor Information' executing"),
        ("INFO", "workflow_engine", "Node complete: Collect Grantor Information"),
        ("INFO", "agent", "Document Drafting Agent: generating trust draft"),
        ("WARN", "scheduler", "Task queue depth: 12 items"),
        ("INFO", "workflow_engine", "Attorney Review node: awaiting human input"),
        ("INFO", "api", "POST /workflows/run — 200 OK (245ms)"),
        ("INFO", "workflow_engine", "Node complete: Attorney Review"),
        ("INFO", "agent", "Compliance Agent: running AML check"),
        ("INFO", "workflow_engine", "Execute & Sign Documents: starting"),
        ("DEBUG", "esignature", "DocuSign envelope created: env_abc123"),
        ("INFO", "esignature", "All parties signed"),
        ("INFO", "workflow_engine", "Trust Creation Workflow: COMPLETE"),
        ("INFO", "api", "GET /workflows — 200 OK (12ms)"),
        ("INFO", "scheduler", "Next run: estate_planning_review in 2h"),
        ("DEBUG", "memory", "Context checkpoint saved"),
        ("INFO", "agent", "Legal Research Agent: task complete"),
        ("INFO", "api", "WebSocket /tui — client connected"),
        ("INFO", "system", "Health check: all systems nominal"),
    ]

    await session.writeln(colorize(f"\nSystem Logs (last {lines_count} entries)\n", ANSI.FG_BRIGHT_YELLOW, bold=True))

    level_colors = {
        "DEBUG": ANSI.FG_BRIGHT_BLACK,
        "INFO": ANSI.FG_BRIGHT_GREEN,
        "WARN": ANSI.FG_BRIGHT_YELLOW,
        "ERROR": ANSI.FG_BRIGHT_RED,
    }

    shown = 0
    for level, component, message in sample_logs[-lines_count:]:
        if filter_kw and filter_kw.lower() not in message.lower() and filter_kw.lower() not in component.lower():
            continue
        ts = datetime.now().strftime("%H:%M:%S")
        level_str = colorize(f"[{level:<5}]", level_colors.get(level, ANSI.FG_WHITE))
        comp_str = colorize(f"[{component}]", ANSI.FG_BRIGHT_CYAN)
        await session.writeln(f"  {colorize(ts, ANSI.FG_BRIGHT_BLACK)} {level_str} {comp_str} {message}")
        shown += 1

    await session.writeln(f"\n{colorize(str(shown), ANSI.FG_BRIGHT_GREEN)} log entries shown\n")


@command("status", "Show system status", "status")
async def cmd_status(session: TerminalSession, args: List[str]) -> None:
    await session.writeln(colorize("\n╔══════════════════════════════════════╗", ANSI.FG_BRIGHT_BLUE))
    await session.writeln(colorize("║     SintraPrime System Status        ║", ANSI.FG_BRIGHT_BLUE))
    await session.writeln(colorize("╚══════════════════════════════════════╝\n", ANSI.FG_BRIGHT_BLUE))

    components = [
        ("Workflow Engine", "operational", "v2.1.0"),
        ("Agent Orchestrator", "operational", "v1.8.3"),
        ("Legal Intelligence", "operational", "v3.0.1"),
        ("Document Generator", "operational", "v2.5.0"),
        ("Compliance Engine", "degraded", "v1.2.0"),
        ("eSignature Service", "operational", "v1.0.5"),
        ("Memory System", "operational", "v4.1.0"),
        ("Database", "operational", "SQLite 3.42"),
    ]

    await session.writeln(colorize(f"  {'Component':<25} {'Status':<15} {'Version'}", ANSI.FG_BRIGHT_YELLOW, bold=True))
    await session.writeln("  " + "─" * 55)
    for comp, status, version in components:
        status_color = ANSI.FG_BRIGHT_GREEN if status == "operational" else ANSI.FG_BRIGHT_YELLOW
        status_icon = "✓" if status == "operational" else "⚠"
        await session.writeln(
            f"  {comp:<25} "
            f"{colorize(status_icon + ' ' + status, status_color):<15} "
            f"{colorize(version, ANSI.FG_BRIGHT_BLACK)}"
        )

    await session.writeln(f"\n  {colorize('System Health:', ANSI.FG_BRIGHT_WHITE)} {colorize('98% (1 component degraded)', ANSI.FG_BRIGHT_YELLOW)}\n")


@command("templates", "List workflow templates", "templates [--tag TAG]")
async def cmd_templates(session: TerminalSession, args: List[str]) -> None:
    filter_tag = ""
    if "--tag" in args:
        idx = args.index("--tag")
        if idx + 1 < len(args):
            filter_tag = args[idx + 1]

    try:
        from workflow_builder.workflow_engine import WorkflowTemplateRegistry
        templates = WorkflowTemplateRegistry.list_templates()

        if filter_tag:
            templates = [t for t in templates if filter_tag.lower() in [tag.lower() for tag in t.get("tags", [])]]

        await session.writeln(colorize(f"\nWorkflow Templates ({len(templates)} found)\n", ANSI.FG_BRIGHT_YELLOW, bold=True))
        for t in templates:
            tags = colorize(", ".join(t.get("tags", [])), ANSI.FG_BRIGHT_BLACK)
            await session.writeln(f"  {colorize('•', ANSI.FG_BRIGHT_CYAN)} {colorize(t['name'], ANSI.FG_BRIGHT_WHITE)}")
            await session.writeln(f"    {colorize('ID:', ANSI.FG_BRIGHT_BLACK)} {t['id']}  {colorize('Tags:', ANSI.FG_BRIGHT_BLACK)} {tags}")
            if t.get("description"):
                await session.writeln(f"    {colorize(t['description'][:70], ANSI.FG_WHITE)}")
            await session.writeln("")
    except Exception as exc:
        await session.writeln(colorize(f"Error: {exc}", ANSI.FG_RED))


@command("version", "Show version information", "version")
async def cmd_version(session: TerminalSession, args: List[str]) -> None:
    await session.writeln(colorize("\n  SintraPrime-Unified", ANSI.FG_BRIGHT_CYAN, bold=True))
    await session.writeln(f"  Version: {colorize('2.1.0', ANSI.FG_BRIGHT_WHITE)}")
    await session.writeln(f"  Build:   {colorize('2025.04.26', ANSI.FG_BRIGHT_BLACK)}")
    await session.writeln(f"  Python:  {colorize(sys.version.split()[0], ANSI.FG_BRIGHT_BLACK)}")
    await session.writeln(f"  License: {colorize('Proprietary', ANSI.FG_BRIGHT_BLACK)}\n")


@command("exit", "Disconnect from the terminal", "exit")
async def cmd_exit(session: TerminalSession, args: List[str]) -> None:
    await session.writeln(colorize("\nGoodbye! Disconnecting...\n", ANSI.FG_BRIGHT_YELLOW))
    session.running = False


@command("echo", "Echo text to terminal", "echo <text>")
async def cmd_echo(session: TerminalSession, args: List[str]) -> None:
    await session.writeln(" ".join(args))


@command("env", "Show environment variables", "env")
async def cmd_env(session: TerminalSession, args: List[str]) -> None:
    await session.writeln(colorize("\nEnvironment Variables:\n", ANSI.FG_BRIGHT_YELLOW))
    for k, v in session.env.items():
        await session.writeln(f"  {colorize(k, ANSI.FG_BRIGHT_CYAN)}={v}")
    await session.writeln("")


# ---------------------------------------------------------------------------
# TUI Command Processor
# ---------------------------------------------------------------------------

class TUICommandProcessor:
    """Process TUI commands from a terminal session."""

    @staticmethod
    async def process(session: TerminalSession, raw_input: str) -> None:
        """Parse and execute a command."""
        line = raw_input.strip()
        if not line:
            return

        session.add_to_history(line)

        try:
            parts = shlex.split(line)
        except ValueError:
            parts = line.split()

        if not parts:
            return

        cmd_name = parts[0].lower()
        cmd_args = parts[1:]

        if cmd_name not in COMMANDS:
            await session.writeln(
                colorize(f"Command not found: {cmd_name}", ANSI.FG_RED)
                + f"  (type {colorize('help', ANSI.FG_BRIGHT_GREEN)} for available commands)"
            )
            return

        try:
            await COMMANDS[cmd_name]["fn"](session, cmd_args)
        except Exception as exc:
            await session.writeln(colorize(f"Error executing '{cmd_name}': {exc}", ANSI.FG_RED))
            logger.exception(f"Error in command '{cmd_name}'")


# ---------------------------------------------------------------------------
# WebSocket TUI Server
# ---------------------------------------------------------------------------

class WebTUIServer:
    """
    WebSocket-based terminal server.
    Handles multiple concurrent sessions.
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        self.host = host
        self.port = port
        self.sessions: Dict[str, TerminalSession] = {}
        self._server = None

    def _generate_banner(self) -> str:
        lines = [
            colorize("\r\n╔══════════════════════════════════════════════════╗", ANSI.FG_BRIGHT_BLUE),
            colorize("║                                                  ║", ANSI.FG_BRIGHT_BLUE),
            colorize("║   " + ANSI.BOLD + "SintraPrime Workflow Terminal  v2.1.0" + ANSI.RESET + colorize("          ║", ANSI.FG_BRIGHT_BLUE), ""),
            colorize("║   AI-Powered Legal Workflow Management           ║", ANSI.FG_BRIGHT_BLUE),
            colorize("║                                                  ║", ANSI.FG_BRIGHT_BLUE),
            colorize("╚══════════════════════════════════════════════════╝", ANSI.FG_BRIGHT_BLUE),
            "",
            f"  Type {colorize('help', ANSI.FG_BRIGHT_GREEN)} for available commands",
            f"  Type {colorize('workflow list', ANSI.FG_BRIGHT_GREEN)} to see workflow templates",
            f"  Type {colorize('status', ANSI.FG_BRIGHT_GREEN)} for system status",
            "",
        ]
        return "\r\n".join(lines)

    async def handle_websocket(self, websocket) -> None:
        """Handle a new WebSocket connection."""
        import uuid
        session_id = str(uuid.uuid4())

        async def send_text(text: str) -> None:
            try:
                await websocket.send(text)
            except Exception:
                pass

        session = TerminalSession(session_id, send_text)
        self.sessions[session_id] = session
        logger.info(f"TUI session connected: {session_id}")

        try:
            # Send banner
            await session.write(self.generate_banner())
            await session.show_prompt()

            input_buffer = ""

            async for message in websocket:
                if not session.running:
                    break

                if isinstance(message, bytes):
                    try:
                        message = message.decode("utf-8")
                    except UnicodeDecodeError:
                        continue

                # Handle special key sequences
                if message == "\r" or message == "\n":
                    await session.write("\r\n")
                    if input_buffer.strip():
                        await TUICommandProcessor.process(session, input_buffer)
                    input_buffer = ""
                    if session.running:
                        await session.show_prompt()

                elif message in ("\x7f", "\x08"):  # Backspace / DEL
                    if input_buffer:
                        input_buffer = input_buffer[:-1]
                        await session.write("\x08 \x08")

                elif message == "\x03":  # Ctrl+C
                    await session.write("^C\r\n")
                    input_buffer = ""
                    await session.show_prompt()

                elif message == "\x04":  # Ctrl+D
                    await cmd_exit(session, [])
                    break

                elif message == "\x0c":  # Ctrl+L
                    await session.write(ANSI.CLEAR_SCREEN)
                    await session.show_prompt()
                    await session.write(input_buffer)

                elif message == "\t":  # Tab completion
                    completions = session.get_tab_completions(input_buffer)
                    if len(completions) == 1:
                        completion = completions[0][len(input_buffer):]
                        input_buffer += completion
                        await session.write(completion)
                    elif len(completions) > 1:
                        await session.write("\r\n")
                        await session.writeln("  " + "  ".join(colorize(c, ANSI.FG_BRIGHT_GREEN) for c in completions))
                        await session.show_prompt()
                        await session.write(input_buffer)

                elif message.startswith("\x1b"):  # Escape sequences
                    if message == "\x1b[A":  # Up arrow
                        if session.history and session.history_index > 0:
                            session.history_index -= 1
                            new_cmd = session.history[session.history_index]
                            await session.write(ANSI.CLEAR_LINE)
                            await session.show_prompt()
                            await session.write(new_cmd)
                            input_buffer = new_cmd
                    elif message == "\x1b[B":  # Down arrow
                        if session.history_index < len(session.history) - 1:
                            session.history_index += 1
                            new_cmd = session.history[session.history_index]
                            await session.write(ANSI.CLEAR_LINE)
                            await session.show_prompt()
                            await session.write(new_cmd)
                            input_buffer = new_cmd
                        else:
                            session.history_index = len(session.history)
                            await session.write(ANSI.CLEAR_LINE)
                            await session.show_prompt()
                            input_buffer = ""

                elif len(message) == 1 and ord(message) >= 32:  # Printable character
                    input_buffer += message
                    await session.write(message)

        except Exception as exc:
            logger.exception(f"WebSocket error for session {session_id}: {exc}")
        finally:
            del self.sessions[session_id]
            logger.info(f"TUI session disconnected: {session_id}")

    def generate_banner(self) -> str:
        """Generate the welcome banner."""
        lines = [
            "\r\n\x1b[34m╔══════════════════════════════════════════════════╗\x1b[0m",
            "\x1b[34m║                                                  ║\x1b[0m",
            "\x1b[34m║  \x1b[1m\x1b[96mSintraPrime Workflow Terminal  v2.1.0\x1b[0m\x1b[34m           ║\x1b[0m",
            "\x1b[34m║  AI-Powered Legal Workflow Management            ║\x1b[0m",
            "\x1b[34m║                                                  ║\x1b[0m",
            "\x1b[34m╚══════════════════════════════════════════════════╝\x1b[0m",
            "",
            f"  Type \x1b[92mhelp\x1b[0m for available commands",
            f"  Type \x1b[92mworkflow list\x1b[0m to see workflow templates",
            f"  Type \x1b[92mstatus\x1b[0m for system status",
            "",
        ]
        return "\r\n".join(lines)

    async def start(self) -> None:
        """Start the WebSocket TUI server."""
        try:
            import websockets
            self._server = await websockets.serve(
                self.handle_websocket,
                self.host,
                self.port,
            )
            logger.info(f"Web TUI server running on ws://{self.host}:{self.port}")
            await self._server.wait_closed()
        except ImportError:
            logger.error("websockets package not installed. Run: pip install websockets")
            raise

    def stop(self) -> None:
        """Stop the WebSocket TUI server."""
        if self._server:
            self._server.close()


# ---------------------------------------------------------------------------
# FastAPI WebSocket handler (for integration with workflow_api.py)
# ---------------------------------------------------------------------------

class FastAPITUIHandler:
    """
    Handler for FastAPI WebSocket endpoint.
    Adapts the TUI logic for use with FastAPI/Starlette WebSocket.
    """

    def __init__(self):
        self.sessions: Dict[str, TerminalSession] = {}
        self.banner_text = WebTUIServer("", 0).generate_banner()

    async def handle(self, websocket) -> None:
        """Handle a FastAPI WebSocket connection."""
        import uuid
        session_id = str(uuid.uuid4())
        await websocket.accept()

        async def send_text(text: str) -> None:
            try:
                await websocket.send_text(text)
            except Exception:
                pass

        session = TerminalSession(session_id, send_text)
        self.sessions[session_id] = session

        try:
            await session.write(self.banner_text)
            await session.show_prompt()

            input_buffer = ""

            while True:
                try:
                    message = await asyncio.wait_for(websocket.receive_text(), timeout=300)
                except asyncio.TimeoutError:
                    await session.writeln(colorize("\nSession timeout.", ANSI.FG_YELLOW))
                    break

                if not session.running:
                    break

                if message == "\r" or message == "\n":
                    await session.write("\r\n")
                    if input_buffer.strip():
                        await TUICommandProcessor.process(session, input_buffer)
                    input_buffer = ""
                    if session.running:
                        await session.show_prompt()
                elif message in ("\x7f", "\x08"):
                    if input_buffer:
                        input_buffer = input_buffer[:-1]
                        await session.write("\x08 \x08")
                elif message == "\x03":
                    await session.write("^C\r\n")
                    input_buffer = ""
                    await session.show_prompt()
                elif message == "\x04":
                    break
                elif message == "\t":
                    completions = session.get_tab_completions(input_buffer)
                    if len(completions) == 1:
                        completion = completions[0][len(input_buffer):]
                        input_buffer += completion
                        await session.write(completion)
                    elif len(completions) > 1:
                        await session.write("\r\n")
                        await session.writeln("  " + "  ".join(completions))
                        await session.show_prompt()
                        await session.write(input_buffer)
                elif message.startswith("\x1b"):
                    if message == "\x1b[A" and session.history and session.history_index > 0:
                        session.history_index -= 1
                        new_cmd = session.history[session.history_index]
                        await session.write(ANSI.CLEAR_LINE)
                        await session.show_prompt()
                        await session.write(new_cmd)
                        input_buffer = new_cmd
                elif len(message) == 1 and ord(message) >= 32:
                    input_buffer += message
                    await session.write(message)

        except Exception as exc:
            logger.exception(f"FastAPI TUI error for session {session_id}: {exc}")
        finally:
            if session_id in self.sessions:
                del self.sessions[session_id]
            try:
                await websocket.close()
            except Exception:
                pass


# Global handler instance
tui_handler = FastAPITUIHandler()


if __name__ == "__main__":
    import asyncio
    server = WebTUIServer(host="0.0.0.0", port=8765)
    print("Starting Web TUI server on ws://0.0.0.0:8765")
    asyncio.run(server.start())
