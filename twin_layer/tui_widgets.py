"""
tui_widgets.py — Twin-inspired TUI Widget Library for SintraPrime

Based on twin's client programs: sysmon.c, cuckoo.c, dialog.c, clip.c.
Provides reusable ANSI-rendered widgets for agent monitoring dashboards.
"""

import logging
import os
import platform
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ─── ANSI helpers ─────────────────────────────────────────────────────────────

ESC = "\033"
CSI = ESC + "["

def color(fg: Optional[int] = None, bg: Optional[int] = None,
          bold: bool = False, reset: bool = False) -> str:
    if reset:
        return f"{CSI}0m"
    codes: List[str] = []
    if bold:
        codes.append("1")
    if fg is not None:
        if fg < 8:
            codes.append(str(30 + fg))
        else:
            codes.extend(["38", "5", str(fg)])
    if bg is not None:
        if bg < 8:
            codes.append(str(40 + bg))
        else:
            codes.extend(["48", "5", str(bg)])
    return f"{CSI}{';'.join(codes)}m" if codes else ""

def truecolor(r: int, g: int, b: int, bg: bool = False) -> str:
    layer = 48 if bg else 38
    return f"{CSI}{layer};2;{r};{g};{b}m"

RESET = f"{CSI}0m"
BOLD = f"{CSI}1m"

# Box drawing
H = "─"; V = "│"; TL = "┌"; TR = "┐"; BL = "└"; BR = "┘"
BLOCK_FULL = "█"; BLOCK_LIGHT = "░"; BLOCK_MED = "▒"


# ─── Base Widget ──────────────────────────────────────────────────────────────

class Widget:
    """
    Base class for all TUI widgets.
    All widgets render via ANSI escape codes and support mouse click events.
    """

    def __init__(self, x: int = 0, y: int = 0,
                 w: int = 20, h: int = 5, title: str = ""):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.title = title
        self._click_handlers: List[Callable[[int, int], None]] = []

    def render(self) -> str:
        """Render the widget to an ANSI string. Override in subclasses."""
        raise NotImplementedError

    def on_click(self, px: int, py: int) -> bool:
        """
        Handle a mouse click at (px, py).
        Returns True if click was within this widget.
        """
        if self.x <= px < self.x + self.w and self.y <= py < self.y + self.h:
            for handler in self._click_handlers:
                try:
                    handler(px - self.x, py - self.y)
                except Exception as exc:
                    logger.warning("Click handler error: %s", exc)
            return True
        return False

    def add_click_handler(self, handler: Callable[[int, int], None]):
        """Register a click handler (relative coords)."""
        self._click_handlers.append(handler)

    def _border(self, title: Optional[str] = None) -> Tuple[str, str]:
        """Return top and bottom border strings."""
        t = title or self.title
        inner = self.w - 2
        if t:
            label = f" {t} "[:inner]
            top = TL + label + H * (inner - len(label)) + TR
        else:
            top = TL + H * inner + TR
        bottom = BL + H * inner + BR
        return top, bottom

    def _row_at(self, row: int, col: int) -> str:
        """Return ANSI cursor position string."""
        return f"{CSI}{row};{col}H"


# ─── AgentMonitorWidget ───────────────────────────────────────────────────────

class AgentMonitorWidget(Widget):
    """
    System/agent monitor widget showing CPU, memory, and agent status.
    Inspired by twin's sysmon.c client.

    Displays:
    - CPU usage (with bar)
    - Memory usage (with bar)
    - Active agent count
    - Task queue depth
    """

    def __init__(self, x: int = 0, y: int = 0, w: int = 40, h: int = 10):
        super().__init__(x, y, w, h, title="Agent Monitor")
        self._agent_count: int = 0
        self._task_count: int = 0
        self._cpu_pct: float = 0.0
        self._mem_pct: float = 0.0
        self._mem_mb: float = 0.0
        self._last_update: float = 0.0

    def update(self, agent_count: int = 0, task_count: int = 0,
               cpu_pct: Optional[float] = None, mem_pct: Optional[float] = None,
               mem_mb: Optional[float] = None):
        """
        Update widget data.

        Args:
            agent_count: Number of active agents.
            task_count: Number of pending tasks.
            cpu_pct: CPU usage 0-100.
            mem_pct: Memory usage 0-100.
            mem_mb: Memory in MB.
        """
        self._agent_count = agent_count
        self._task_count = task_count
        if cpu_pct is not None:
            self._cpu_pct = cpu_pct
        else:
            self._cpu_pct = self._get_cpu()
        if mem_pct is not None:
            self._mem_pct = mem_pct
            self._mem_mb = mem_mb or 0.0
        else:
            self._mem_pct, self._mem_mb = self._get_mem()
        self._last_update = time.time()

    def _get_cpu(self) -> float:
        """Read CPU usage from /proc/stat."""
        try:
            with open("/proc/stat") as f:
                fields = f.readline().split()
            total = sum(int(x) for x in fields[1:])
            idle = int(fields[4])
            return max(0.0, min(100.0, (1 - idle / total) * 100))
        except Exception:
            return 0.0

    def _get_mem(self) -> Tuple[float, float]:
        """Read memory usage from /proc/meminfo."""
        try:
            info: Dict[str, int] = {}
            with open("/proc/meminfo") as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 2:
                        info[parts[0].rstrip(":")] = int(parts[1])
            total = info.get("MemTotal", 1)
            available = info.get("MemAvailable", total)
            used = total - available
            mb = used / 1024
            pct = used / total * 100
            return pct, mb
        except Exception:
            return 0.0, 0.0

    def _bar(self, pct: float, width: int, color_ok: str, color_warn: str,
             color_crit: str) -> str:
        """Render a percentage bar."""
        filled = int(width * pct / 100)
        empty = width - filled
        if pct >= 90:
            bar_color = color_crit
        elif pct >= 70:
            bar_color = color_warn
        else:
            bar_color = color_ok
        return bar_color + BLOCK_FULL * filled + RESET + BLOCK_LIGHT * empty

    def render(self) -> str:
        inner_w = self.w - 2
        top, bottom = self._border()
        bar_w = inner_w - 12

        parts = [
            color(fg=3, bold=True) + top + RESET + "\n",
            color(fg=7) + V + RESET +
            color(bold=True) + f" {'AGENTS':>8}: " + RESET +
            color(fg=10) + f"{self._agent_count:<4}" + RESET +
            color(fg=7) + f"  TASKS: " + RESET +
            color(fg=14) + f"{self._task_count:<{inner_w - 24}}" + RESET +
            color(fg=7) + V + RESET + "\n",
            color(fg=7) + V + RESET + H * inner_w + color(fg=7) + V + RESET + "\n",
            # CPU row
            color(fg=7) + V + RESET +
            f" CPU  {self._cpu_pct:5.1f}% " +
            self._bar(self._cpu_pct, bar_w,
                      color(fg=2), color(fg=3), color(fg=1)) +
            " " + color(fg=7) + V + RESET + "\n",
            # Memory row
            color(fg=7) + V + RESET +
            f" MEM  {self._mem_pct:5.1f}% " +
            self._bar(self._mem_pct, bar_w,
                      color(fg=6), color(fg=5), color(fg=1)) +
            " " + color(fg=7) + V + RESET + "\n",
            color(fg=7) + V + RESET +
            color(fg=8) + f" Updated: {datetime.now().strftime('%H:%M:%S'):<{inner_w - 10}}" + RESET +
            color(fg=7) + V + RESET + "\n",
            color(fg=3, bold=True) + bottom + RESET + "\n",
        ]
        return "".join(parts)


# ─── ClockWidget ──────────────────────────────────────────────────────────────

class ClockWidget(Widget):
    """
    Digital clock widget with timezone display.
    Inspired by twin's cuckoo.c.
    """

    def __init__(self, x: int = 0, y: int = 0, w: int = 30, h: int = 5,
                 timezone_name: str = "UTC"):
        super().__init__(x, y, w, h, title="Clock")
        self.timezone_name = timezone_name

    def render(self) -> str:
        now = datetime.now(timezone.utc)
        time_str = now.strftime("%H:%M:%S")
        date_str = now.strftime("%Y-%m-%d")
        tz_str = f"UTC ({self.timezone_name})"
        inner_w = self.w - 2
        top, bottom = self._border()

        parts = [
            color(fg=6, bold=True) + top + RESET + "\n",
            color(fg=7) + V + RESET +
            truecolor(0, 200, 255) + BOLD +
            time_str.center(inner_w) + RESET +
            color(fg=7) + V + RESET + "\n",
            color(fg=7) + V + RESET +
            color(fg=14) + date_str.center(inner_w) + RESET +
            color(fg=7) + V + RESET + "\n",
            color(fg=7) + V + RESET +
            color(fg=8) + tz_str.center(inner_w) + RESET +
            color(fg=7) + V + RESET + "\n",
            color(fg=6, bold=True) + bottom + RESET + "\n",
        ]
        return "".join(parts)


# ─── ProgressBar ──────────────────────────────────────────────────────────────

class ProgressBar(Widget):
    """
    Task progress bar widget.
    """

    def __init__(self, x: int = 0, y: int = 0, w: int = 40,
                 label: str = "Progress", total: int = 100):
        super().__init__(x, y, w, h=3, title=label)
        self.total = total
        self.current = 0

    def set_progress(self, current: int):
        """Update progress value."""
        self.current = max(0, min(self.total, current))

    @property
    def percent(self) -> float:
        if self.total == 0:
            return 0.0
        return self.current / self.total * 100

    def render(self) -> str:
        inner_w = self.w - 2
        filled = int(inner_w * self.percent / 100)
        empty = inner_w - filled
        pct_str = f"{self.percent:.1f}%"

        if self.percent >= 100:
            bar_color = truecolor(0, 200, 0)
        elif self.percent >= 50:
            bar_color = truecolor(0, 150, 255)
        else:
            bar_color = truecolor(255, 150, 0)

        bar = bar_color + BLOCK_FULL * filled + RESET + color(fg=8) + BLOCK_LIGHT * empty + RESET
        label = f" {self.title}: {pct_str} ({self.current}/{self.total}) "[:inner_w]

        parts = [
            color(fg=7) + TL + H * inner_w + TR + RESET + "\n",
            color(fg=7) + V + RESET + bar + color(fg=7) + V + RESET + "\n",
            color(fg=7) + BL + H * inner_w + BR + RESET + "\n",
        ]
        return "".join(parts)


# ─── DialogWidget ─────────────────────────────────────────────────────────────

class DialogResult(Enum):
    NONE = auto()
    YES = auto()
    NO = auto()
    OK = auto()
    CANCEL = auto()


class DialogWidget(Widget):
    """
    Modal dialog with yes/no/input options.
    Inspired by twin's dialog.c client.
    """

    def __init__(self, x: int = 10, y: int = 5, w: int = 50, h: int = 8,
                 message: str = "", dialog_type: str = "yesno"):
        super().__init__(x, y, w, h, title="Dialog")
        self.message = message
        self.dialog_type = dialog_type  # "yesno", "ok", "input"
        self.result: DialogResult = DialogResult.NONE
        self.input_value: str = ""
        self._selected: int = 0  # 0=yes/ok, 1=no/cancel

    def render(self) -> str:
        inner_w = self.w - 2
        top, bottom = self._border("⚠ Dialog")
        msg_lines = [self.message[i:i+inner_w] for i in range(0, len(self.message), inner_w)]

        parts = [truecolor(255, 200, 0, bg=True) + color(fg=0, bold=True) + top + RESET + "\n"]

        # Message lines
        for line in msg_lines[:self.h - 4]:
            padded = line[:inner_w].ljust(inner_w)
            parts.append(color(fg=7) + V + RESET + f" {padded} " + color(fg=7) + V + RESET + "\n")

        # Empty padding
        for _ in range(max(0, self.h - 4 - len(msg_lines))):
            parts.append(color(fg=7) + V + " " * inner_w + V + RESET + "\n")

        # Input area
        if self.dialog_type == "input":
            input_display = self.input_value[-inner_w + 2:]
            parts.append(
                color(fg=7) + V + RESET +
                truecolor(30, 30, 30, bg=True) + f" > {input_display:<{inner_w - 3}}" + RESET +
                color(fg=7) + V + RESET + "\n"
            )

        # Buttons
        if self.dialog_type == "yesno":
            yes = (" YES " if self._selected == 0 else "  yes  ")
            no = (" NO " if self._selected == 1 else "  no  ")
            yes_color = truecolor(0, 200, 0, bg=True) if self._selected == 0 else color(fg=2)
            no_color = truecolor(200, 0, 0, bg=True) if self._selected == 1 else color(fg=1)
            btn_line = f"  {yes_color}{yes}{RESET}   {no_color}{no}{RESET}  ".ljust(inner_w)
            parts.append(color(fg=7) + V + RESET + btn_line + color(fg=7) + V + RESET + "\n")
        elif self.dialog_type in ("ok", "input"):
            ok_color = truecolor(0, 120, 255, bg=True)
            btn_line = f"  {ok_color} OK {RESET}   {color(fg=8)} Cancel {RESET}  ".ljust(inner_w)
            parts.append(color(fg=7) + V + RESET + btn_line + color(fg=7) + V + RESET + "\n")

        parts.append(truecolor(255, 200, 0, bg=True) + color(fg=0, bold=True) + bottom + RESET + "\n")
        return "".join(parts)

    def select_yes_ok(self):
        """Select Yes/OK button."""
        self._selected = 0
        self.result = DialogResult.YES if self.dialog_type == "yesno" else DialogResult.OK

    def select_no_cancel(self):
        """Select No/Cancel button."""
        self._selected = 1
        self.result = DialogResult.NO if self.dialog_type == "yesno" else DialogResult.CANCEL

    def append_input(self, char: str):
        """Append character to input field."""
        self.input_value += char

    def backspace_input(self):
        """Delete last character from input."""
        self.input_value = self.input_value[:-1]


# ─── ClipboardManager ────────────────────────────────────────────────────────

class ClipboardManager:
    """
    Shared clipboard for inter-agent communication.
    Inspired by twin's clip.c — a shared clipboard server.
    """

    def __init__(self, max_history: int = 50):
        self._clipboard: str = ""
        self._history: List[Tuple[float, str]] = []
        self.max_history = max_history

    def set(self, content: str, agent_id: str = "unknown"):
        """
        Set clipboard content.

        Args:
            content: Text to store.
            agent_id: ID of agent setting the clipboard.
        """
        self._clipboard = content
        self._history.append((time.time(), content))
        if len(self._history) > self.max_history:
            self._history.pop(0)
        logger.debug("Clipboard set by %s (%d chars)", agent_id, len(content))

    def get(self) -> str:
        """Get current clipboard content."""
        return self._clipboard

    def get_history(self, n: int = 10) -> List[Tuple[float, str]]:
        """Get last N clipboard entries."""
        return self._history[-n:]

    def clear(self):
        """Clear clipboard."""
        self._clipboard = ""

    def render_panel(self, w: int = 40, h: int = 8) -> str:
        """Render clipboard content as a widget."""
        inner_w = w - 2
        preview = self._clipboard[:inner_w * (h - 2)]
        lines = [preview[i:i+inner_w] for i in range(0, len(preview), inner_w)]
        parts = [
            color(fg=5, bold=True) + TL + " Clipboard " + H * (inner_w - 11) + TR + RESET + "\n"
        ]
        for line in lines[:h - 2]:
            parts.append(color(fg=7) + V + RESET + line.ljust(inner_w) + color(fg=7) + V + RESET + "\n")
        for _ in range(max(0, h - 2 - len(lines))):
            parts.append(color(fg=7) + V + " " * inner_w + V + RESET + "\n")
        parts.append(color(fg=5, bold=True) + BL + H * inner_w + BR + RESET + "\n")
        return "".join(parts)


# ─── AgentStatusPanel ────────────────────────────────────────────────────────

@dataclass
class AgentStatus:
    """Status record for a single agent."""
    agent_id: str
    name: str
    status: str  # "running", "idle", "error", "stopped"
    tasks_done: int = 0
    tasks_pending: int = 0
    last_seen: float = field(default_factory=time.time)


class AgentStatusPanel(Widget):
    """
    Table widget showing all agent statuses.
    """

    STATUS_COLORS = {
        "running": truecolor(0, 200, 0),
        "idle": truecolor(180, 180, 0),
        "error": truecolor(220, 0, 0),
        "stopped": truecolor(100, 100, 100),
    }

    def __init__(self, x: int = 0, y: int = 0, w: int = 60, h: int = 15):
        super().__init__(x, y, w, h, title="Agent Status")
        self._agents: Dict[str, AgentStatus] = {}

    def update_agent(self, status: AgentStatus):
        """Register or update an agent's status."""
        self._agents[status.agent_id] = status

    def remove_agent(self, agent_id: str):
        """Remove an agent from the panel."""
        self._agents.pop(agent_id, None)

    def render(self) -> str:
        inner_w = self.w - 2
        top, bottom = self._border()
        col_w = [16, 10, 8, 8, 12]  # name, status, done, pending, last_seen

        header = (f"{'Name':<{col_w[0]}}{'Status':<{col_w[1]}}"
                  f"{'Done':>{col_w[2]}}{'Pend':>{col_w[3]}}{'Last Seen':>{col_w[4]}}")
        header = header[:inner_w]

        parts = [
            color(fg=4, bold=True) + top + RESET + "\n",
            color(fg=7) + V + RESET +
            color(bold=True) + header.ljust(inner_w) + RESET +
            color(fg=7) + V + RESET + "\n",
            color(fg=7) + V + RESET + H * inner_w + color(fg=7) + V + RESET + "\n",
        ]

        agents = list(self._agents.values())
        max_rows = self.h - 4
        for ag in agents[:max_rows]:
            sc = self.STATUS_COLORS.get(ag.status, RESET)
            age = time.time() - ag.last_seen
            age_str = f"{age:.0f}s ago"
            row = (f"{ag.name[:col_w[0]-1]:<{col_w[0]}}"
                   f"{ag.status:<{col_w[1]}}"
                   f"{ag.tasks_done:>{col_w[2]}}"
                   f"{ag.tasks_pending:>{col_w[3]}}"
                   f"{age_str:>{col_w[4]}}")
            parts.append(
                color(fg=7) + V + RESET + sc + row[:inner_w].ljust(inner_w) +
                RESET + color(fg=7) + V + RESET + "\n"
            )

        # Pad remaining rows
        for _ in range(max(0, max_rows - len(agents))):
            parts.append(color(fg=7) + V + " " * inner_w + V + RESET + "\n")

        parts.append(color(fg=4, bold=True) + bottom + RESET + "\n")
        return "".join(parts)


# ─── LogViewer ───────────────────────────────────────────────────────────────

class LogViewer(Widget):
    """
    Scrollable log viewer widget with search.
    """

    def __init__(self, x: int = 0, y: int = 0, w: int = 80, h: int = 20,
                 max_lines: int = 1000):
        super().__init__(x, y, w, h, title="Log Viewer")
        self._lines: List[Tuple[str, str]] = []  # (level, message)
        self._scroll: int = 0
        self._search: str = ""
        self.max_lines = max_lines

    LEVEL_COLORS = {
        "ERROR": truecolor(220, 50, 50),
        "WARNING": truecolor(220, 150, 0),
        "INFO": truecolor(100, 200, 100),
        "DEBUG": truecolor(100, 100, 200),
    }

    def add_line(self, message: str, level: str = "INFO"):
        """Add a log line."""
        self._lines.append((level.upper(), message))
        if len(self._lines) > self.max_lines:
            self._lines.pop(0)
        # Auto-scroll to bottom
        self._scroll = max(0, len(self._lines) - (self.h - 2))

    def search(self, query: str):
        """Set search filter."""
        self._search = query.lower()

    def scroll_up(self, n: int = 1):
        self._scroll = max(0, self._scroll - n)

    def scroll_down(self, n: int = 1):
        max_scroll = max(0, len(self._filtered_lines()) - (self.h - 2))
        self._scroll = min(max_scroll, self._scroll + n)

    def _filtered_lines(self) -> List[Tuple[str, str]]:
        if not self._search:
            return self._lines
        return [(l, m) for l, m in self._lines if self._search in m.lower()]

    def render(self) -> str:
        inner_w = self.w - 2
        top, bottom = self._border(f"Logs" + (f" [{self._search}]" if self._search else ""))
        lines = self._filtered_lines()
        visible = lines[self._scroll:self._scroll + (self.h - 2)]

        parts = [color(fg=7, bold=True) + top + RESET + "\n"]
        for level, msg in visible:
            lc = self.LEVEL_COLORS.get(level, RESET)
            prefix = f"{level[:4]:4} "
            row = (lc + prefix + RESET + msg)[:inner_w + len(lc) + len(RESET)]
            parts.append(color(fg=7) + V + RESET + row.ljust(inner_w) + color(fg=7) + V + RESET + "\n")

        for _ in range(max(0, self.h - 2 - len(visible))):
            parts.append(color(fg=7) + V + " " * inner_w + V + RESET + "\n")

        scroll_info = f" {self._scroll + 1}/{len(lines)} "
        bottom_bar = BL + H * (inner_w - len(scroll_info)) + scroll_info + BR
        parts.append(color(fg=7, bold=True) + bottom_bar + RESET + "\n")
        return "".join(parts)


# ─── NotificationBanner ───────────────────────────────────────────────────────

@dataclass
class Notification:
    """A single notification message."""
    message: str
    level: str = "info"   # "info", "warn", "error", "success"
    created_at: float = field(default_factory=time.time)
    ttl: float = 5.0      # seconds to display


class NotificationBanner(Widget):
    """
    Temporary notification overlay banners.
    Notifications auto-expire after their TTL.
    """

    LEVEL_STYLES = {
        "info":    (truecolor(0, 100, 200, bg=True), truecolor(255, 255, 255)),
        "warn":    (truecolor(180, 120, 0, bg=True), truecolor(0, 0, 0)),
        "error":   (truecolor(180, 0, 0, bg=True),   truecolor(255, 255, 255)),
        "success": (truecolor(0, 150, 0, bg=True),   truecolor(255, 255, 255)),
    }

    def __init__(self, x: int = 0, y: int = 0, w: int = 60):
        super().__init__(x, y, w, h=1, title="")
        self._notifications: List[Notification] = []

    def notify(self, message: str, level: str = "info", ttl: float = 5.0):
        """
        Show a notification.

        Args:
            message: Text to display.
            level: "info", "warn", "error", or "success".
            ttl: Time to display in seconds.
        """
        self._notifications.append(Notification(message=message, level=level, ttl=ttl))
        logger.debug("Notification [%s]: %s", level, message)

    def _cleanup_expired(self):
        now = time.time()
        self._notifications = [
            n for n in self._notifications if now - n.created_at < n.ttl
        ]

    def render(self) -> str:
        self._cleanup_expired()
        if not self._notifications:
            return ""

        parts: List[str] = []
        for i, notif in enumerate(self._notifications[-3:]):  # show last 3
            bg_style, fg_style = self.LEVEL_STYLES.get(
                notif.level, self.LEVEL_STYLES["info"])
            remaining = notif.ttl - (time.time() - notif.created_at)
            msg = f" [{notif.level.upper()}] {notif.message} ({remaining:.0f}s) "
            padded = msg[:self.w].ljust(self.w)
            parts.append(bg_style + fg_style + padded + RESET + "\n")

        return "".join(parts)

    def has_notifications(self) -> bool:
        self._cleanup_expired()
        return len(self._notifications) > 0


# ─── MenuBar ──────────────────────────────────────────────────────────────────

@dataclass
class MenuItem:
    """A single menu item."""
    label: str
    shortcut: str = ""
    action: Optional[Callable] = None
    submenu: Optional[List["MenuItem"]] = None


class MenuBar(Widget):
    """
    Application menu bar with keyboard shortcuts.
    Renders a top-of-screen menu with highlighted items.
    """

    def __init__(self, y: int = 0, w: int = 80,
                 menus: Optional[List[Tuple[str, List[MenuItem]]]] = None):
        super().__init__(x=0, y=y, w=w, h=1, title="")
        self.menus: List[Tuple[str, List[MenuItem]]] = menus or []
        self._selected_menu: int = -1
        self._open_menu: int = -1

    def add_menu(self, name: str, items: List[MenuItem]):
        """Add a menu to the menu bar."""
        self.menus.append((name, items))

    def render(self) -> str:
        # Menu bar background
        bar = truecolor(30, 30, 80, bg=True) + truecolor(200, 200, 255)
        parts = [bar + " " * self.w + RESET + "\r" + bar]

        for i, (name, items) in enumerate(self.menus):
            if i == self._open_menu:
                highlight = truecolor(80, 80, 180, bg=True) + truecolor(255, 255, 255) + BOLD
            else:
                highlight = ""
            # Find shortcut (first unique uppercase letter)
            parts.append(f" {highlight}{name}{RESET}{bar} ")

        parts.append(RESET + "\n")

        # Render open submenu if any
        if self._open_menu >= 0 and self._open_menu < len(self.menus):
            _, items = self.menus[self._open_menu]
            col_offset = sum(len(n) + 3 for n, _ in self.menus[:self._open_menu])
            menu_w = max((len(item.label) + len(item.shortcut) + 4 for item in items), default=20)
            parts.append(truecolor(40, 40, 90, bg=True) + truecolor(200, 200, 255) +
                         TL + H * menu_w + TR + RESET + "\n")
            for item in items:
                row = f" {item.label:<{menu_w - len(item.shortcut) - 2}}{item.shortcut} "
                parts.append(
                    " " * col_offset +
                    truecolor(40, 40, 90, bg=True) + truecolor(200, 200, 255) +
                    V + row + V + RESET + "\n"
                )
            parts.append(" " * col_offset +
                         truecolor(40, 40, 90, bg=True) + truecolor(200, 200, 255) +
                         BL + H * menu_w + BR + RESET + "\n")

        return "".join(parts)

    def open_menu(self, index: int):
        """Open a menu by index."""
        self._open_menu = index

    def close_menus(self):
        """Close all open menus."""
        self._open_menu = -1

    def handle_key(self, key: str) -> bool:
        """
        Handle keyboard input for menu navigation.

        Args:
            key: Key string.

        Returns:
            True if key was consumed.
        """
        if key == "Escape":
            self.close_menus()
            return True
        if key.startswith("Alt+") or key.startswith("F"):
            # Try to match menu shortcut
            for i, (name, _) in enumerate(self.menus):
                if key.lower() == f"alt+{name[0].lower()}":
                    self._open_menu = i
                    return True
        return False
