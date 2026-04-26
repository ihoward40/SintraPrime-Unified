"""
SintraPrime Mobile TUI Extension
=================================
Extends the twin TUI for small screens (40-char width),
numbered menus, touch-friendly scrolling, swipe gestures,
and SSH-ready mobile access.
"""

from __future__ import annotations

import os
import sys
import time
import signal
import textwrap
import threading
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Tuple

# ─── Screen Constants ──────────────────────────────────────────────────────────
MOBILE_WIDTH = 40
DESKTOP_WIDTH = 80
MOBILE_HEIGHT = 24
SCROLL_STEP = 3

# ─── ANSI Escape Codes ─────────────────────────────────────────────────────────
ESC = "\x1b"
RESET = f"{ESC}[0m"
BOLD = f"{ESC}[1m"
DIM = f"{ESC}[2m"
UNDERLINE = f"{ESC}[4m"
REVERSE = f"{ESC}[7m"

# Colors
FG_BLACK = f"{ESC}[30m"
FG_RED = f"{ESC}[31m"
FG_GREEN = f"{ESC}[32m"
FG_YELLOW = f"{ESC}[33m"
FG_BLUE = f"{ESC}[34m"
FG_MAGENTA = f"{ESC}[35m"
FG_CYAN = f"{ESC}[36m"
FG_WHITE = f"{ESC}[37m"
FG_GOLD = f"{ESC}[38;5;214m"

BG_DARK = f"{ESC}[48;5;234m"
BG_CARD = f"{ESC}[48;5;235m"
BG_ACCENT = f"{ESC}[48;5;25m"

CLEAR_SCREEN = f"{ESC}[2J{ESC}[H"
HIDE_CURSOR = f"{ESC}[?25l"
SHOW_CURSOR = f"{ESC}[?25h"
SAVE_POS = f"{ESC}7"
RESTORE_POS = f"{ESC}8"


# ─── Data Structures ───────────────────────────────────────────────────────────
class Screen(Enum):
    MAIN_MENU = auto()
    CASES = auto()
    CASE_DETAIL = auto()
    RESEARCH = auto()
    DEADLINES = auto()
    AGENTS = auto()
    DOCUMENTS = auto()
    SETTINGS = auto()
    HELP = auto()


@dataclass
class MenuItem:
    number: int
    label: str
    icon: str
    screen: Optional[Screen] = None
    action: Optional[Callable] = None
    shortcut: str = ""


@dataclass
class TUIState:
    screen: Screen = Screen.MAIN_MENU
    scroll_offset: int = 0
    selected_case_id: Optional[str] = None
    search_query: str = ""
    status_message: str = ""
    status_color: str = FG_GREEN
    history: List[Screen] = field(default_factory=list)
    is_mobile: bool = True
    width: int = MOBILE_WIDTH
    height: int = MOBILE_HEIGHT
    swipe_start_x: Optional[int] = None
    swipe_start_y: Optional[int] = None


# ─── Terminal Utilities ────────────────────────────────────────────────────────
def detect_terminal_size() -> Tuple[int, int]:
    """Detect terminal dimensions."""
    try:
        size = os.get_terminal_size()
        return size.columns, size.lines
    except OSError:
        return MOBILE_WIDTH, MOBILE_HEIGHT


def is_mobile_terminal() -> bool:
    """Heuristic: terminals ≤ 50 cols are likely mobile SSH."""
    w, _ = detect_terminal_size()
    return w <= 50


def move_cursor(row: int, col: int) -> str:
    return f"{ESC}[{row};{col}H"


def clear_line() -> str:
    return f"{ESC}[2K\r"


def center(text: str, width: int, fill: str = " ") -> str:
    plain = strip_ansi(text)
    pad = max(0, width - len(plain))
    left = pad // 2
    right = pad - left
    return fill * left + text + fill * right


def strip_ansi(text: str) -> str:
    import re
    return re.sub(r"\x1b\[[0-9;]*[mK]", "", text)


def truncate(text: str, width: int, suffix: str = "…") -> str:
    if len(text) <= width:
        return text
    return text[:width - len(suffix)] + suffix


def wrap_text(text: str, width: int) -> List[str]:
    return textwrap.wrap(text, width=width) or [""]


def h_rule(width: int, char: str = "─") -> str:
    return char * width


def box_top(width: int) -> str:
    return "┌" + "─" * (width - 2) + "┐"


def box_bottom(width: int) -> str:
    return "└" + "─" * (width - 2) + "┘"


def box_row(content: str, width: int) -> str:
    plain_len = len(strip_ansi(content))
    padding = max(0, width - 2 - plain_len)
    return "│" + content + " " * padding + "│"


# ─── Swipe / Gesture Simulation ───────────────────────────────────────────────
class GestureDetector:
    """Simulates swipe gestures over SSH using escape sequences."""

    SWIPE_THRESHOLD = 3  # characters of movement
    
    def __init__(self):
        self._touch_x: Optional[int] = None
        self._touch_y: Optional[int] = None

    def on_mouse_event(self, event_data: bytes, state: TUIState) -> Optional[str]:
        """Parse xterm mouse tracking escape sequences."""
        # Mouse event: ESC [ M Cb Cx Cy
        if len(event_data) < 3:
            return None
        btn = event_data[0] - 32
        x = event_data[1] - 32
        y = event_data[2] - 32

        if btn == 0:  # Press
            self._touch_x = x
            self._touch_y = y
        elif btn == 3:  # Release
            if self._touch_x is not None:
                dx = x - self._touch_x
                dy = y - self._touch_y
                self._touch_x = None
                self._touch_y = None
                return self._classify_swipe(dx, dy)
        return None

    def _classify_swipe(self, dx: int, dy: int) -> Optional[str]:
        if abs(dx) > abs(dy) and abs(dx) >= self.SWIPE_THRESHOLD:
            return "swipe_right" if dx > 0 else "swipe_left"
        elif abs(dy) > abs(dx) and abs(dy) >= self.SWIPE_THRESHOLD:
            return "swipe_down" if dy > 0 else "swipe_up"
        return "tap"


# ─── Screens ──────────────────────────────────────────────────────────────────
class MobileTUI:
    """Main mobile TUI controller."""

    MAIN_MENU_ITEMS = [
        MenuItem(1, "Dashboard", "📊", Screen.CASES),
        MenuItem(2, "Cases", "📁", Screen.CASES),
        MenuItem(3, "Research", "🔍", Screen.RESEARCH),
        MenuItem(4, "Deadlines", "📅", Screen.DEADLINES),
        MenuItem(5, "AI Agents", "🤖", Screen.AGENTS),
        MenuItem(6, "Documents", "📄", Screen.DOCUMENTS),
        MenuItem(7, "Settings", "⚙️", Screen.SETTINGS),
        MenuItem(8, "Help", "❓", Screen.HELP),
        MenuItem(0, "Quit", "✕", None),
    ]

    def __init__(self):
        self.state = TUIState()
        self.state.is_mobile = is_mobile_terminal()
        w, h = detect_terminal_size()
        self.state.width = min(w, MOBILE_WIDTH) if self.state.is_mobile else min(w, DESKTOP_WIDTH)
        self.state.height = h
        self.gesture = GestureDetector()
        self._running = False
        self._render_lock = threading.Lock()

    def start(self):
        """Start the mobile TUI."""
        self._running = True
        self._setup_terminal()
        signal.signal(signal.SIGINT, self._handle_interrupt)
        signal.signal(signal.SIGTERM, self._handle_interrupt)
        try:
            self._main_loop()
        finally:
            self._restore_terminal()

    def _setup_terminal(self):
        print(HIDE_CURSOR, end="", flush=True)
        # Enable mouse tracking for swipe gestures
        print(f"{ESC}[?1000h", end="", flush=True)  # Mouse click tracking
        print(f"{ESC}[?1002h", end="", flush=True)  # Mouse motion tracking

    def _restore_terminal(self):
        print(SHOW_CURSOR, end="", flush=True)
        print(f"{ESC}[?1000l", end="", flush=True)
        print(f"{ESC}[?1002l", end="", flush=True)
        print(CLEAR_SCREEN, end="", flush=True)

    def _handle_interrupt(self, sig, frame):
        self._running = False

    def _main_loop(self):
        while self._running:
            self.render()
            choice = self._get_input()
            if choice is not None:
                self._handle_input(choice)

    def render(self):
        """Render the current screen."""
        with self._render_lock:
            output = CLEAR_SCREEN
            output += self._render_header()
            output += self._render_screen()
            output += self._render_footer()
            print(output, end="", flush=True)

    def _render_header(self) -> str:
        w = self.state.width
        lines = []
        lines.append(f"{FG_GOLD}{BOLD}" + h_rule(w, "═") + RESET)
        title = "⚖ SintraPrime"
        sub = "Legal Intelligence"
        lines.append(f"{FG_GOLD}{BOLD}" + center(title, w) + RESET)
        lines.append(f"{DIM}" + center(sub, w) + RESET)
        lines.append(f"{FG_GOLD}" + h_rule(w, "─") + RESET)
        return "\n".join(lines) + "\n"

    def _render_screen(self) -> str:
        s = self.state.screen
        if s == Screen.MAIN_MENU:
            return self._render_main_menu()
        elif s == Screen.CASES:
            return self._render_cases()
        elif s == Screen.RESEARCH:
            return self._render_research()
        elif s == Screen.DEADLINES:
            return self._render_deadlines()
        elif s == Screen.AGENTS:
            return self._render_agents()
        elif s == Screen.SETTINGS:
            return self._render_settings()
        elif s == Screen.HELP:
            return self._render_help()
        return self._render_main_menu()

    def _render_main_menu(self) -> str:
        w = self.state.width
        lines = []
        lines.append(f"\n{FG_CYAN}{BOLD}  MAIN MENU{RESET}\n")
        for item in self.MAIN_MENU_ITEMS:
            num = f"  [{item.number}]" if item.number > 0 else "  [0]"
            label = f" {item.icon} {item.label}"
            row = f"{FG_YELLOW}{BOLD}{num}{RESET}{FG_WHITE}{label}{RESET}"
            lines.append(row)
        return "\n".join(lines) + "\n"

    def _render_cases(self) -> str:
        w = self.state.width
        lines = [f"\n{FG_CYAN}{BOLD}  CASES{RESET}\n"]
        # In production, fetches from API
        stubs = [
            {"id": "C001", "title": "Smith v. Jones", "status": "Active"},
            {"id": "C002", "title": "Estate of Brown", "status": "Pending"},
            {"id": "C003", "title": "Williams Contract", "status": "Active"},
        ]
        for i, c in enumerate(stubs, 1):
            status_color = FG_GREEN if c["status"] == "Active" else FG_YELLOW
            title = truncate(c["title"], w - 12)
            lines.append(f"  {FG_YELLOW}[{i}]{RESET} {FG_WHITE}{title}{RESET}")
            lines.append(f"      {DIM}{c['id']}{RESET} {status_color}{c['status']}{RESET}")
            lines.append("")
        lines.append(f"  {FG_YELLOW}[0]{RESET} ← Back")
        return "\n".join(lines) + "\n"

    def _render_research(self) -> str:
        lines = [f"\n{FG_CYAN}{BOLD}  LEGAL RESEARCH{RESET}\n"]
        lines.append(f"  {DIM}Enter your legal question{RESET}")
        lines.append(f"  {FG_YELLOW}[1]{RESET} Case Law Search")
        lines.append(f"  {FG_YELLOW}[2]{RESET} Statute Lookup")
        lines.append(f"  {FG_YELLOW}[3]{RESET} Regulation Search")
        lines.append(f"  {FG_YELLOW}[4]{RESET} Citation Check")
        lines.append("")
        lines.append(f"  {FG_YELLOW}[0]{RESET} ← Back")
        return "\n".join(lines) + "\n"

    def _render_deadlines(self) -> str:
        lines = [f"\n{FG_CYAN}{BOLD}  DEADLINES{RESET}\n"]
        stubs = [
            {"title": "Motion to Dismiss", "case": "C001", "days": 2},
            {"title": "Discovery Due", "case": "C002", "days": 7},
            {"title": "Trial Date", "case": "C001", "days": 45},
        ]
        for i, d in enumerate(stubs, 1):
            urgency = FG_RED if d["days"] <= 3 else FG_YELLOW if d["days"] <= 14 else FG_GREEN
            title = truncate(d["title"], self.state.width - 14)
            lines.append(f"  {FG_YELLOW}[{i}]{RESET} {urgency}{title}{RESET}")
            lines.append(f"      {DIM}{d['case']}{RESET} · {urgency}{d['days']}d{RESET}")
            lines.append("")
        lines.append(f"  {FG_YELLOW}[0]{RESET} ← Back")
        return "\n".join(lines) + "\n"

    def _render_agents(self) -> str:
        lines = [f"\n{FG_CYAN}{BOLD}  AI AGENTS{RESET}\n"]
        lines.append(f"  {FG_YELLOW}[1]{RESET} Run Research Agent")
        lines.append(f"  {FG_YELLOW}[2]{RESET} Document Analyzer")
        lines.append(f"  {FG_YELLOW}[3]{RESET} Case Summarizer")
        lines.append(f"  {FG_YELLOW}[4]{RESET} View Running Tasks")
        lines.append("")
        lines.append(f"  {FG_YELLOW}[0]{RESET} ← Back")
        return "\n".join(lines) + "\n"

    def _render_settings(self) -> str:
        lines = [f"\n{FG_CYAN}{BOLD}  SETTINGS{RESET}\n"]
        w, h = detect_terminal_size()
        lines.append(f"  {DIM}Terminal: {w}×{h}{RESET}")
        lines.append(f"  {DIM}Mode: {'Mobile' if self.state.is_mobile else 'Desktop'}{RESET}")
        lines.append("")
        lines.append(f"  {FG_YELLOW}[1]{RESET} Toggle Mobile/Desktop")
        lines.append(f"  {FG_YELLOW}[2]{RESET} API Server URL")
        lines.append(f"  {FG_YELLOW}[3]{RESET} Clear Cache")
        lines.append("")
        lines.append(f"  {FG_YELLOW}[0]{RESET} ← Back")
        return "\n".join(lines) + "\n"

    def _render_help(self) -> str:
        w = self.state.width
        lines = [f"\n{FG_CYAN}{BOLD}  HELP & SSH GUIDE{RESET}\n"]
        help_text = [
            "Navigation:",
            "  Type the number to select",
            "  [0] or [B] = Back",
            "  Ctrl+C = Quit",
            "",
            "Swipe Gestures (SSH):",
            "  Swipe Right → Back",
            "  Swipe Left → Forward",
            "  Swipe Up → Scroll up",
            "  Swipe Down → Scroll dn",
            "",
            "SSH Access:",
            "  ssh user@your-server",
            "  sintra-mobile",
        ]
        for line in help_text:
            lines.append(f"  {DIM if line.startswith(' ') else FG_WHITE}{line}{RESET}")
        lines.append(f"\n  {FG_YELLOW}[0]{RESET} ← Back")
        return "\n".join(lines) + "\n"

    def _render_footer(self) -> str:
        w = self.state.width
        lines = []
        lines.append(f"{FG_GOLD}" + h_rule(w, "─") + RESET)
        if self.state.status_message:
            msg = truncate(self.state.status_message, w - 2)
            lines.append(f"{self.state.status_color}{msg}{RESET}")
        else:
            if self.state.screen == Screen.MAIN_MENU:
                lines.append(f"{DIM}  Select option (0-8){RESET}")
            else:
                lines.append(f"{DIM}  [0] Back  [?] Help{RESET}")
        lines.append(f"\n{FG_CYAN}> {RESET}")
        return "\n".join(lines)

    def _get_input(self) -> Optional[str]:
        """Read a single line of input."""
        try:
            return input().strip()
        except (EOFError, KeyboardInterrupt):
            self._running = False
            return None

    def _handle_input(self, choice: str):
        """Route input to the appropriate handler."""
        self.state.status_message = ""

        # Back navigation
        if choice in ("0", "b", "B", "back"):
            self._go_back()
            return

        # Help
        if choice in ("?", "h", "H", "help"):
            self._navigate_to(Screen.HELP)
            return

        # Screen-specific handling
        if self.state.screen == Screen.MAIN_MENU:
            self._handle_main_menu(choice)
        elif self.state.screen == Screen.CASES:
            self._handle_cases(choice)
        elif self.state.screen == Screen.SETTINGS:
            self._handle_settings(choice)
        else:
            self.state.status_message = f"Unhandled: {choice}"
            self.state.status_color = FG_YELLOW

    def _handle_main_menu(self, choice: str):
        menu_map = {
            "1": Screen.CASES,
            "2": Screen.CASES,
            "3": Screen.RESEARCH,
            "4": Screen.DEADLINES,
            "5": Screen.AGENTS,
            "6": Screen.DOCUMENTS,
            "7": Screen.SETTINGS,
            "8": Screen.HELP,
        }
        if choice in menu_map:
            self._navigate_to(menu_map[choice])
        elif choice == "0":
            self._running = False
        else:
            self._set_status(f"Invalid choice: {choice}", FG_RED)

    def _handle_cases(self, choice: str):
        if choice in ("1", "2", "3"):
            self._set_status(f"Case {choice} selected", FG_GREEN)
        else:
            self._set_status("Invalid case number", FG_RED)

    def _handle_settings(self, choice: str):
        if choice == "1":
            self.state.is_mobile = not self.state.is_mobile
            self.state.width = MOBILE_WIDTH if self.state.is_mobile else DESKTOP_WIDTH
            mode = "Mobile" if self.state.is_mobile else "Desktop"
            self._set_status(f"Switched to {mode} mode", FG_GREEN)

    def _navigate_to(self, screen: Screen):
        self.state.history.append(self.state.screen)
        self.state.screen = screen
        self.state.scroll_offset = 0

    def _go_back(self):
        if self.state.history:
            self.state.screen = self.state.history.pop()
        else:
            self.state.screen = Screen.MAIN_MENU
        self.state.scroll_offset = 0

    def _set_status(self, msg: str, color: str = FG_GREEN):
        self.state.status_message = msg
        self.state.status_color = color

    def scroll_up(self):
        self.state.scroll_offset = max(0, self.state.scroll_offset - SCROLL_STEP)

    def scroll_down(self):
        self.state.scroll_offset += SCROLL_STEP


# ─── SSH Entry Point ───────────────────────────────────────────────────────────
def launch_mobile_tui():
    """Launch the mobile TUI — SSH-friendly entry point."""
    tui = MobileTUI()
    tui.start()


def main():
    """CLI entry point: sintra-mobile"""
    print(f"{FG_GOLD}SintraPrime Mobile TUI starting...{RESET}", flush=True)
    time.sleep(0.3)
    launch_mobile_tui()


if __name__ == "__main__":
    main()
