"""
terminal_multiplexer.py — Twin-inspired Terminal Multiplexer for SintraPrime

Based on twin's PTY management (server/pty.cpp) and terminal emulator (server/tty.cpp).
Manages multiple agent terminals with scrollback, output capture, and split views.
"""

import collections
import logging
import os
import queue
import select
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ANSI helpers for truecolor
ESC = "\033"
CSI = ESC + "["

def tc_fg(r: int, g: int, b: int) -> str:
    """Return 24-bit truecolor foreground escape."""
    return f"{CSI}38;2;{r};{g};{b}m"

def tc_bg(r: int, g: int, b: int) -> str:
    """Return 24-bit truecolor background escape."""
    return f"{CSI}48;2;{r};{g};{b}m"

def ansi_reset() -> str:
    return f"{CSI}0m"

def ansi_move(row: int, col: int) -> str:
    return f"{CSI}{row};{col}H"

SCROLLBACK_LIMIT = 1000


# ─── Enums ────────────────────────────────────────────────────────────────────

class SplitDirection(Enum):
    HORIZONTAL = auto()  # two panels side by side
    VERTICAL = auto()    # two panels stacked


class TerminalState(Enum):
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"
    ERROR = "ERROR"


# ─── AgentTerminal ────────────────────────────────────────────────────────────

class AgentTerminal:
    """
    Wraps a subprocess or agent process in a virtual terminal.
    Maintains a scrollback buffer and supports output capture.

    Inspired by twin's PTY wrapper (server/pty.cpp) which connects
    client programs to pseudo-terminals.

    Usage:
        term = AgentTerminal("agent-1", ["python3", "-c", "print('hello')"])
        term.start()
        lines = term.capture_output(10)
        term.stop()
    """

    def __init__(self, terminal_id: str, command: List[str],
                 name: Optional[str] = None,
                 env: Optional[Dict[str, str]] = None,
                 scrollback_limit: int = SCROLLBACK_LIMIT):
        """
        Initialize a terminal.

        Args:
            terminal_id: Unique ID.
            command: Command + args to run.
            name: Human-readable name for the panel.
            env: Environment variables (inherits os.environ if None).
            scrollback_limit: Maximum scrollback lines to retain.
        """
        self.terminal_id = terminal_id
        self.command = command
        self.name = name or terminal_id
        self.env = env
        self.scrollback_limit: int = scrollback_limit

        self._scrollback: Deque[str] = collections.deque(maxlen=scrollback_limit)
        self._process: Optional[subprocess.Popen] = None
        self._state: TerminalState = TerminalState.STOPPED
        self._reader_thread: Optional[threading.Thread] = None
        self._stdin_queue: queue.Queue = queue.Queue()
        self._output_callbacks: List[Callable[[str], None]] = []
        self._lock = threading.Lock()

        # Layout position for split view
        self.x: int = 0
        self.y: int = 0
        self.w: int = 80
        self.h: int = 24

        # Stats
        self.lines_received: int = 0
        self.started_at: Optional[float] = None

    @property
    def state(self) -> TerminalState:
        return self._state

    def start(self) -> bool:
        """
        Start the terminal process.

        Returns:
            True if started successfully, False otherwise.
        """
        if self._state == TerminalState.RUNNING:
            logger.warning("Terminal %s already running", self.terminal_id)
            return False
        try:
            env = dict(os.environ)
            if self.env:
                env.update(self.env)
            # Add TERM for color support
            env.setdefault("TERM", "xterm-256color")
            env.setdefault("COLORTERM", "truecolor")

            self._process = subprocess.Popen(
                self.command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=env,
                text=True,
                bufsize=1,
            )
            self._state = TerminalState.RUNNING
            self.started_at = time.time()
            self._reader_thread = threading.Thread(
                target=self._reader_loop,
                daemon=True,
                name=f"term-reader-{self.terminal_id}",
            )
            self._reader_thread.start()
            logger.info("Started terminal %s: %s", self.terminal_id, self.command)
            return True
        except Exception as exc:
            self._state = TerminalState.ERROR
            logger.error("Failed to start terminal %s: %s", self.terminal_id, exc)
            return False

    def _reader_loop(self):
        """Background thread reading stdout from the process."""
        try:
            while self._process and self._process.poll() is None:
                line = self._process.stdout.readline()
                if line:
                    line = line.rstrip("\n")
                    with self._lock:
                        self._scrollback.append(line)
                        self.lines_received += 1
                    for cb in self._output_callbacks:
                        try:
                            cb(line)
                        except Exception:
                            pass
            # Drain remaining output
            if self._process:
                remaining = self._process.stdout.read()
                if remaining:
                    for line in remaining.splitlines():
                        with self._lock:
                            self._scrollback.append(line)
                            self.lines_received += 1
        except Exception as exc:
            logger.warning("Terminal %s reader error: %s", self.terminal_id, exc)
        finally:
            self._state = TerminalState.STOPPED
            logger.debug("Terminal %s reader loop ended", self.terminal_id)

    def send_input(self, text: str):
        """
        Send text to the terminal's stdin.

        Args:
            text: Text to send (newline included if needed).
        """
        if self._process and self._process.stdin and self._state == TerminalState.RUNNING:
            try:
                self._process.stdin.write(text)
                self._process.stdin.flush()
            except Exception as exc:
                logger.warning("Failed to send to terminal %s: %s", self.terminal_id, exc)

    def send_line(self, line: str):
        """Send a line of text (appends newline)."""
        self.send_input(line + "\n")

    def capture_output(self, n: int = 50) -> List[str]:
        """
        Get the last N lines from the scrollback buffer.

        Args:
            n: Number of lines to return.

        Returns:
            List of strings (most recent last).
        """
        with self._lock:
            buf = list(self._scrollback)
        return buf[-n:] if len(buf) > n else buf

    def get_all_output(self) -> List[str]:
        """Return entire scrollback buffer."""
        with self._lock:
            return list(self._scrollback)

    def add_output_callback(self, callback: Callable[[str], None]):
        """Register a callback invoked whenever a new line arrives."""
        self._output_callbacks.append(callback)

    def stop(self, timeout: float = 5.0):
        """
        Stop the terminal process.

        Args:
            timeout: Seconds to wait before killing.
        """
        if self._process:
            try:
                self._process.terminate()
                self._process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                self._process.kill()
            except Exception as exc:
                logger.warning("Error stopping terminal %s: %s", self.terminal_id, exc)
            self._process = None
        self._state = TerminalState.STOPPED

    def is_running(self) -> bool:
        """Check if terminal process is alive."""
        if self._process is None:
            return False
        return self._process.poll() is None

    def render_panel(self, n_lines: Optional[int] = None) -> str:
        """
        Render the terminal panel content as an ANSI string.
        Shows the last n_lines lines with truecolor header.

        Args:
            n_lines: Lines to show (defaults to panel height - 1).

        Returns:
            ANSI-formatted string.
        """
        display_lines = n_lines or max(1, self.h - 1)
        output = self.capture_output(display_lines)
        parts: List[str] = []

        # Header bar
        state_color = (0, 200, 0) if self._state == TerminalState.RUNNING else (200, 0, 0)
        parts.append(
            tc_bg(*state_color) + tc_fg(255, 255, 255) +
            f" {self.name} [{self._state.value}] " +
            ansi_reset() + "\n"
        )

        # Content lines
        for line in output[-display_lines:]:
            parts.append(line + "\n")

        # Pad to height
        padding = display_lines - len(output[-display_lines:])
        parts.extend(["~\n"] * max(0, padding))

        return "".join(parts)

    def __repr__(self) -> str:
        return f"AgentTerminal(id={self.terminal_id!r}, name={self.name!r}, state={self._state.value})"


# ─── Split layout ─────────────────────────────────────────────────────────────

@dataclass
class SplitPanel:
    """Represents a panel in a split terminal layout."""
    panel_id: str
    terminal_id: str
    x: int
    y: int
    w: int
    h: int
    direction: Optional[SplitDirection] = None
    children: List[str] = field(default_factory=list)  # child panel_ids


# ─── TerminalMultiplexer ──────────────────────────────────────────────────────

class TerminalMultiplexer:
    """
    Manages multiple AgentTerminals simultaneously.

    Inspired by twin's tty.cpp which manages many terminal clients,
    routing I/O and rendering each in its own region.

    Features:
    - Multiple named terminals
    - Horizontal/vertical split layout
    - Broadcast messages to all terminals
    - Output capture per terminal
    - Mouse event routing to correct panel

    Usage:
        mux = TerminalMultiplexer(term_width=200, term_height=50)
        t1 = mux.create_terminal("orchestrator", ["python3", "orchestrator.py"])
        t2 = mux.create_terminal("worker", ["python3", "worker.py"])
        t1.start(); t2.start()
        mux.split_horizontal("orchestrator", "worker")
        mux.broadcast("PING\\n")
    """

    def __init__(self, term_width: int = 80, term_height: int = 24):
        """
        Initialize the multiplexer.

        Args:
            term_width: Terminal display width.
            term_height: Terminal display height.
        """
        self.term_width = term_width
        self.term_height = term_height
        self._terminals: Dict[str, AgentTerminal] = {}
        self._panels: Dict[str, SplitPanel] = {}
        self._panel_order: List[str] = []
        self._focused_terminal: Optional[str] = None
        self._lock = threading.Lock()
        logger.info("TerminalMultiplexer initialized %dx%d", term_width, term_height)

    # ── Terminal management ───────────────────────────────────────────────────

    def create_terminal(self, name: str, command: List[str],
                        terminal_id: Optional[str] = None,
                        env: Optional[Dict[str, str]] = None,
                        auto_start: bool = False) -> AgentTerminal:
        """
        Create a named terminal panel.

        Args:
            name: Human-readable name.
            command: Command to run.
            terminal_id: Optional explicit ID (UUID generated if not given).
            env: Environment variables.
            auto_start: If True, start the process immediately.

        Returns:
            The new AgentTerminal.
        """
        tid = terminal_id or str(uuid.uuid4())
        term = AgentTerminal(
            terminal_id=tid,
            command=command,
            name=name,
            env=env,
        )
        with self._lock:
            self._terminals[tid] = term
            self._panel_order.append(tid)
        self._recalculate_layout()

        if auto_start:
            term.start()

        if self._focused_terminal is None:
            self._focused_terminal = tid

        logger.info("Created terminal '%s' (id=%s)", name, tid)
        return term

    def get_terminal(self, terminal_id: str) -> Optional[AgentTerminal]:
        """Look up a terminal by ID."""
        return self._terminals.get(terminal_id)

    def get_terminal_by_name(self, name: str) -> Optional[AgentTerminal]:
        """Find a terminal by name."""
        for t in self._terminals.values():
            if t.name == name:
                return t
        return None

    def remove_terminal(self, terminal_id: str):
        """Stop and remove a terminal."""
        term = self._terminals.pop(terminal_id, None)
        if term:
            term.stop()
        self._panel_order = [t for t in self._panel_order if t != terminal_id]
        if self._focused_terminal == terminal_id:
            self._focused_terminal = self._panel_order[0] if self._panel_order else None
        self._recalculate_layout()

    def start_all(self):
        """Start all registered terminals."""
        for term in self._terminals.values():
            if not term.is_running():
                term.start()

    def stop_all(self):
        """Stop all terminals."""
        for term in self._terminals.values():
            term.stop()

    # ── I/O routing ───────────────────────────────────────────────────────────

    def broadcast(self, message: str):
        """
        Send a message to all running terminals.

        Args:
            message: Text to send (e.g., control commands).
        """
        with self._lock:
            terminals = list(self._terminals.values())
        for term in terminals:
            if term.is_running():
                try:
                    term.send_input(message)
                except Exception as exc:
                    logger.warning("Broadcast to %s failed: %s", term.terminal_id, exc)
        logger.debug("Broadcasted %d bytes to %d terminals",
                     len(message), len(terminals))

    def send_to(self, terminal_id: str, message: str):
        """Send message to a specific terminal."""
        term = self._terminals.get(terminal_id)
        if term:
            term.send_input(message)
        else:
            logger.warning("send_to: terminal %s not found", terminal_id)

    def route_mouse_event(self, px: int, py: int, event_data: Dict[str, Any]) -> Optional[str]:
        """
        Route a mouse event to the correct terminal panel based on (px, py).

        Args:
            px: Column coordinate.
            py: Row coordinate.
            event_data: Mouse event details.

        Returns:
            terminal_id that received the event, or None.
        """
        with self._lock:
            panels = list(self._panels.values())
        for panel in panels:
            if (panel.x <= px < panel.x + panel.w and
                    panel.y <= py < panel.y + panel.h):
                term = self._terminals.get(panel.terminal_id)
                if term:
                    logger.debug("Mouse event routed to terminal %s", panel.terminal_id)
                    self._focused_terminal = panel.terminal_id
                    return panel.terminal_id
        return None

    # ── Output capture ────────────────────────────────────────────────────────

    def capture_output(self, terminal_id: str, n: int = 50) -> List[str]:
        """
        Get last N lines from a terminal's scrollback buffer.

        Args:
            terminal_id: Target terminal.
            n: Number of lines.

        Returns:
            List of output lines.
        """
        term = self._terminals.get(terminal_id)
        if not term:
            logger.warning("capture_output: terminal %s not found", terminal_id)
            return []
        return term.capture_output(n)

    def capture_all(self, n: int = 20) -> Dict[str, List[str]]:
        """Capture last N lines from all terminals."""
        return {tid: t.capture_output(n) for tid, t in self._terminals.items()}

    # ── Layout ────────────────────────────────────────────────────────────────

    def _recalculate_layout(self):
        """Redistribute panel areas evenly across all terminals."""
        count = len(self._panel_order)
        if count == 0:
            self._panels.clear()
            return

        # Simple equal-width horizontal split
        panel_w = self.term_width // count
        self._panels.clear()
        for i, tid in enumerate(self._panel_order):
            x = i * panel_w
            w = panel_w if i < count - 1 else self.term_width - x
            panel = SplitPanel(
                panel_id=f"panel-{i}",
                terminal_id=tid,
                x=x, y=0,
                w=w, h=self.term_height,
            )
            self._panels[tid] = panel
            term = self._terminals.get(tid)
            if term:
                term.x, term.y = x, 0
                term.w, term.h = w, self.term_height

    def split_horizontal(self, terminal_id_left: str, terminal_id_right: str):
        """
        Split view horizontally: left and right panels side by side.

        Args:
            terminal_id_left: Terminal for left panel.
            terminal_id_right: Terminal for right panel.
        """
        half = self.term_width // 2
        for tid, x, w in [
            (terminal_id_left, 0, half),
            (terminal_id_right, half, self.term_width - half),
        ]:
            term = self._terminals.get(tid)
            if term:
                term.x, term.y = x, 0
                term.w, term.h = w, self.term_height
                self._panels[tid] = SplitPanel(
                    panel_id=f"panel-{tid}",
                    terminal_id=tid,
                    x=x, y=0, w=w, h=self.term_height,
                    direction=SplitDirection.HORIZONTAL,
                )
        logger.debug("Split horizontal: %s | %s", terminal_id_left, terminal_id_right)

    def split_vertical(self, terminal_id_top: str, terminal_id_bottom: str):
        """
        Split view vertically: top and bottom panels stacked.

        Args:
            terminal_id_top: Terminal for top panel.
            terminal_id_bottom: Terminal for bottom panel.
        """
        half = self.term_height // 2
        for tid, y, h in [
            (terminal_id_top, 0, half),
            (terminal_id_bottom, half, self.term_height - half),
        ]:
            term = self._terminals.get(tid)
            if term:
                term.x, term.y = 0, y
                term.w, term.h = self.term_width, h
                self._panels[tid] = SplitPanel(
                    panel_id=f"panel-{tid}",
                    terminal_id=tid,
                    x=0, y=y, w=self.term_width, h=h,
                    direction=SplitDirection.VERTICAL,
                )
        logger.debug("Split vertical: %s / %s", terminal_id_top, terminal_id_bottom)

    # ── Render all panels ─────────────────────────────────────────────────────

    def render_all(self) -> str:
        """
        Render all terminal panels to a combined ANSI string.

        Returns:
            Combined ANSI output for the full display.
        """
        parts: List[str] = []
        with self._lock:
            panels = list(self._panels.values())
            terminals = dict(self._terminals)

        for panel in panels:
            term = terminals.get(panel.terminal_id)
            if not term:
                continue
            n_lines = panel.h - 1
            output = term.capture_output(n_lines)
            # Position the panel
            parts.append(ansi_move(panel.y + 1, panel.x + 1))
            # Focused border
            is_focused = panel.terminal_id == self._focused_terminal
            header_color = (0, 120, 255) if is_focused else (80, 80, 80)
            parts.append(
                tc_bg(*header_color) + tc_fg(255, 255, 255) +
                f" {term.name[:panel.w - 2]:<{panel.w - 2}} " +
                ansi_reset()
            )
            for i, line in enumerate(output[-n_lines:]):
                parts.append(ansi_move(panel.y + 2 + i, panel.x + 1))
                truncated = line[:panel.w]
                parts.append(truncated)

        return "".join(parts)

    def list_terminals(self) -> List[Dict[str, Any]]:
        """Return info about all managed terminals."""
        return [
            {
                "terminal_id": t.terminal_id,
                "name": t.name,
                "state": t.state.value,
                "command": t.command,
                "lines_received": t.lines_received,
                "started_at": t.started_at,
            }
            for t in self._terminals.values()
        ]

    def __repr__(self) -> str:
        return f"TerminalMultiplexer(terminals={len(self._terminals)}, size={self.term_width}x{self.term_height})"
