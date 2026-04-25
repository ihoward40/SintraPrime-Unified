"""
tui_window_manager.py — Twin-inspired Textmode Window Manager for SintraPrime

Based on twin's server/wm.cpp and server/draw.cpp.
Manages overlapping TUI windows with ANSI escape codes, z-order stacking,
double-buffer rendering, and mouse hit-testing.
"""

import os
import sys
import logging
import copy
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional, Tuple, Dict, Any

logger = logging.getLogger(__name__)

# ─── ANSI helpers ────────────────────────────────────────────────────────────

ESC = "\033"
CSI = ESC + "["

def ansi_move(row: int, col: int) -> str:
    """Return ANSI escape to move cursor to (row, col) 1-indexed."""
    return f"{CSI}{row};{col}H"

def ansi_color(fg: Optional[int] = None, bg: Optional[int] = None,
               bold: bool = False, reset: bool = False) -> str:
    """Return ANSI SGR color escape sequence."""
    if reset:
        return f"{CSI}0m"
    codes: List[str] = []
    if bold:
        codes.append("1")
    if fg is not None:
        if fg < 8:
            codes.append(str(30 + fg))
        elif fg < 16:
            codes.append(str(90 + fg - 8))
        else:
            codes.extend(["38", "5", str(fg)])
    if bg is not None:
        if bg < 8:
            codes.append(str(40 + bg))
        elif bg < 16:
            codes.append(str(100 + bg - 8))
        else:
            codes.extend(["48", "5", str(bg)])
    return f"{CSI}{';'.join(codes)}m" if codes else ""

def ansi_truecolor(r: int, g: int, b: int, bg: bool = False) -> str:
    """Return ANSI 24-bit truecolor escape."""
    layer = 48 if bg else 38
    return f"{CSI}{layer};2;{r};{g};{b}m"

def ansi_clear_screen() -> str:
    return f"{CSI}2J{CSI}H"

def ansi_hide_cursor() -> str:
    return f"{CSI}?25l"

def ansi_show_cursor() -> str:
    return f"{CSI}?25h"

def ansi_save_cursor() -> str:
    return f"{ESC}7"

def ansi_restore_cursor() -> str:
    return f"{ESC}8"

# Box-drawing characters (like twin's draw.cpp)
BOX = {
    "tl": "╔", "tr": "╗", "bl": "╚", "br": "╝",
    "h": "═", "v": "║",
    "close": "✕", "min": "─", "max": "□",
}

# ─── Enums ────────────────────────────────────────────────────────────────────

class WindowState(Enum):
    NORMAL = auto()
    MINIMIZED = auto()
    MAXIMIZED = auto()
    CLOSED = auto()


class WindowColor(Enum):
    """Color presets for window chrome."""
    FOCUSED_TITLE_FG = 15    # bright white
    FOCUSED_TITLE_BG = 4     # blue
    UNFOCUSED_TITLE_FG = 7   # white
    UNFOCUSED_TITLE_BG = 8   # dark gray
    BORDER_FG = 7
    CONTENT_FG = 15
    CONTENT_BG = 0


# ─── TUIWindow ────────────────────────────────────────────────────────────────

@dataclass
class TUIWindow:
    """
    A single textmode window, inspired by twin's window structure.

    Attributes:
        win_id: Unique window identifier.
        title: Title shown in the title bar.
        x, y: Top-left position (0-indexed terminal column/row).
        w, h: Width and height (including border).
        z_order: Stack order; higher = on top.
        state: WindowState enum.
        content: 2D list of (char, fg_color, bg_color) tuples for content area.
        focused: Whether this window has keyboard focus.
        metadata: Arbitrary metadata dict for SintraPrime agent info.
    """
    win_id: str
    title: str
    x: int
    y: int
    w: int
    h: int
    z_order: int = 0
    state: WindowState = WindowState.NORMAL
    focused: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    _content: List[List[Tuple[str, int, int]]] = field(default_factory=list)

    def __post_init__(self):
        """Initialize content buffer."""
        self._reset_content()

    def _reset_content(self):
        """Allocate a blank content buffer (interior size)."""
        inner_h = max(0, self.h - 2)
        inner_w = max(0, self.w - 2)
        self._content = [
            [(" ", WindowColor.CONTENT_FG.value, WindowColor.CONTENT_BG.value)
             for _ in range(inner_w)]
            for _ in range(inner_h)
        ]

    @property
    def inner_w(self) -> int:
        """Width of content area."""
        return max(0, self.w - 2)

    @property
    def inner_h(self) -> int:
        """Height of content area."""
        return max(0, self.h - 2)

    def write_text(self, row: int, col: int, text: str,
                   fg: int = 15, bg: int = 0):
        """Write text into the content buffer at (row, col)."""
        if row < 0 or row >= self.inner_h:
            return
        for i, ch in enumerate(text):
            c = col + i
            if 0 <= c < self.inner_w:
                self._content[row][c] = (ch, fg, bg)

    def clear_content(self):
        """Clear the window's content buffer."""
        self._reset_content()

    def resize(self, w: int, h: int):
        """Resize window and reallocate content buffer."""
        self.w = max(4, w)
        self.h = max(3, h)
        self._reset_content()

    def move(self, x: int, y: int):
        """Move window to new position."""
        self.x = x
        self.y = y

    def contains_point(self, px: int, py: int) -> bool:
        """Hit-test: does this window cover terminal column px, row py?"""
        return (self.x <= px < self.x + self.w and
                self.y <= py < self.y + self.h)

    def title_bar_hit(self, px: int, py: int) -> bool:
        """Check if click is in title bar row."""
        return py == self.y and self.x <= px < self.x + self.w

    def close_button_hit(self, px: int, py: int) -> bool:
        """Check if click hits the close button (top-right corner area)."""
        return py == self.y and px == self.x + self.w - 2

    def minimize_button_hit(self, px: int, py: int) -> bool:
        """Check if click hits the minimize button."""
        return py == self.y and px == self.x + self.w - 4

    def render_lines(self) -> List[str]:
        """
        Render this window to a list of ANSI strings (one per row).
        Returns empty list if minimized/closed.
        """
        if self.state in (WindowState.MINIMIZED, WindowState.CLOSED):
            return []

        lines: List[str] = []
        focused = self.focused

        # ── Title bar colors ──
        if focused:
            tfg = WindowColor.FOCUSED_TITLE_FG.value
            tbg = WindowColor.FOCUSED_TITLE_BG.value
        else:
            tfg = WindowColor.UNFOCUSED_TITLE_FG.value
            tbg = WindowColor.UNFOCUSED_TITLE_BG.value

        bfg = WindowColor.BORDER_FG.value
        cbg = WindowColor.CONTENT_BG.value

        # ── Top border (title bar) ──
        title_space = self.w - 6  # leave room for buttons and corners
        truncated_title = self.title[:title_space].center(title_space)
        top_line = (
            ansi_color(tfg, tbg, bold=focused) +
            BOX["tl"] +
            f" {BOX['min']} {BOX['close']} " +
            truncated_title +
            BOX["tr"] +
            ansi_color(reset=True)
        )
        lines.append(top_line)

        # ── Content rows ──
        for row_idx in range(self.inner_h):
            row_buf = [
                ansi_color(bfg, cbg) + BOX["v"] + ansi_color(reset=True)
            ]
            for col_idx in range(self.inner_w):
                if row_idx < len(self._content) and col_idx < len(self._content[row_idx]):
                    ch, fg, bg = self._content[row_idx][col_idx]
                else:
                    ch, fg, bg = " ", 15, 0
                row_buf.append(ansi_color(fg, bg) + ch + ansi_color(reset=True))
            row_buf.append(ansi_color(bfg, cbg) + BOX["v"] + ansi_color(reset=True))
            lines.append("".join(row_buf))

        # ── Bottom border ──
        bottom_line = (
            ansi_color(bfg, cbg) +
            BOX["bl"] + BOX["h"] * (self.w - 2) + BOX["br"] +
            ansi_color(reset=True)
        )
        lines.append(bottom_line)
        return lines


# ─── Screen buffer ────────────────────────────────────────────────────────────

class ScreenBuffer:
    """
    Double buffer for flicker-free rendering (inspired by twin's draw.cpp).
    Stores a 2D grid of (char, ansi_prefix) cells.
    """

    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self._front: List[List[str]] = self._blank()
        self._back: List[List[str]] = self._blank()

    def _blank(self) -> List[List[str]]:
        return [[" " for _ in range(self.width)] for _ in range(self.height)]

    def write(self, row: int, col: int, text: str):
        """Write text string into back buffer at (row, col)."""
        for i, ch in enumerate(text):
            c = col + i
            if 0 <= row < self.height and 0 <= c < self.width:
                self._back[row][c] = ch

    def flush(self) -> str:
        """
        Compare front vs back buffers and return minimal ANSI diff string.
        Swaps buffers after.
        """
        output_parts: List[str] = []
        for r in range(self.height):
            for c in range(self.width):
                if self._back[r][c] != self._front[r][c]:
                    output_parts.append(ansi_move(r + 1, c + 1))
                    output_parts.append(self._back[r][c])
                    self._front[r][c] = self._back[r][c]
        # Copy front state to back (both buffers now match)
        # New writes to back will be compared against front on next flush
        self._back = [list(row) for row in self._front]
        return "".join(output_parts)

    def resize(self, width: int, height: int):
        """Resize buffers."""
        self.width = width
        self.height = height
        self._front = self._blank()
        self._back = self._blank()


# ─── TUIWindowManager ─────────────────────────────────────────────────────────

class TUIWindowManager:
    """
    Manages a collection of TUIWindows, handling z-order, focus, and rendering.

    Inspired by twin's wm.cpp server-side window manager.

    Usage:
        wm = TUIWindowManager()
        win = wm.create_window("w1", "My Window", x=5, y=3, w=40, h=15)
        win.write_text(0, 0, "Hello, SintraPrime!")
        wm.render()
    """

    def __init__(self, term_width: int = 0, term_height: int = 0):
        """
        Initialize window manager.

        Args:
            term_width: Terminal width (auto-detected if 0).
            term_height: Terminal height (auto-detected if 0).
        """
        self.windows: List[TUIWindow] = []
        self._next_z: int = 0
        self._focused_id: Optional[str] = None

        # Auto-detect terminal size
        if term_width <= 0 or term_height <= 0:
            try:
                size = os.get_terminal_size()
                self.term_width = size.columns
                self.term_height = size.lines
            except OSError:
                self.term_width = 80
                self.term_height = 24
        else:
            self.term_width = term_width
            self.term_height = term_height

        self._screen = ScreenBuffer(self.term_width, self.term_height)
        logger.info("TUIWindowManager initialized %dx%d", self.term_width, self.term_height)

    # ── Window lifecycle ──────────────────────────────────────────────────────

    def create_window(self, win_id: str, title: str,
                      x: int = 0, y: int = 0,
                      w: int = 40, h: int = 15,
                      metadata: Optional[Dict[str, Any]] = None) -> TUIWindow:
        """Create and register a new window."""
        self._next_z += 1
        win = TUIWindow(
            win_id=win_id, title=title,
            x=x, y=y, w=w, h=h,
            z_order=self._next_z,
            metadata=metadata or {},
        )
        self.windows.append(win)
        self.focus_window(win_id)
        logger.debug("Created window '%s' at (%d,%d) size %dx%d", win_id, x, y, w, h)
        return win

    def get_window(self, win_id: str) -> Optional[TUIWindow]:
        """Look up a window by ID."""
        for w in self.windows:
            if w.win_id == win_id:
                return w
        return None

    def remove_window(self, win_id: str):
        """Remove a window from management."""
        self.windows = [w for w in self.windows if w.win_id != win_id]
        if self._focused_id == win_id:
            self._focused_id = None
            self._auto_focus()

    # ── Z-order and focus ─────────────────────────────────────────────────────

    def _sorted_windows(self) -> List[TUIWindow]:
        """Return windows sorted by z_order ascending (bottom to top)."""
        return sorted(
            [w for w in self.windows if w.state not in (WindowState.CLOSED,)],
            key=lambda w: w.z_order
        )

    def raise_window(self, win_id: str):
        """Bring window to front."""
        win = self.get_window(win_id)
        if win:
            self._next_z += 1
            win.z_order = self._next_z

    def lower_window(self, win_id: str):
        """Send window to back."""
        win = self.get_window(win_id)
        if win:
            win.z_order = 0

    def focus_window(self, win_id: str):
        """Give keyboard focus to window."""
        if self._focused_id:
            old = self.get_window(self._focused_id)
            if old:
                old.focused = False
        self._focused_id = win_id
        win = self.get_window(win_id)
        if win:
            win.focused = True
            self.raise_window(win_id)

    def _auto_focus(self):
        """Focus the topmost visible window."""
        sorted_wins = self._sorted_windows()
        if sorted_wins:
            self.focus_window(sorted_wins[-1].win_id)

    # ── Window operations ─────────────────────────────────────────────────────

    def minimize(self, win_id: str):
        """Minimize a window."""
        win = self.get_window(win_id)
        if win:
            win.state = WindowState.MINIMIZED
            logger.debug("Minimized window '%s'", win_id)

    def maximize(self, win_id: str):
        """Maximize window to fill terminal."""
        win = self.get_window(win_id)
        if win:
            win.state = WindowState.MAXIMIZED
            win.x, win.y = 0, 0
            win.w, win.h = self.term_width, self.term_height
            win._reset_content()
            logger.debug("Maximized window '%s'", win_id)

    def restore(self, win_id: str):
        """Restore minimized/maximized window."""
        win = self.get_window(win_id)
        if win:
            win.state = WindowState.NORMAL

    def close(self, win_id: str):
        """Close and remove a window."""
        win = self.get_window(win_id)
        if win:
            win.state = WindowState.CLOSED
            self.remove_window(win_id)
            logger.debug("Closed window '%s'", win_id)

    def move(self, win_id: str, x: int, y: int):
        """Move window to new position."""
        win = self.get_window(win_id)
        if win:
            win.move(x, y)

    def resize(self, win_id: str, w: int, h: int):
        """Resize a window."""
        win = self.get_window(win_id)
        if win:
            win.resize(w, h)

    # ── Hit testing ───────────────────────────────────────────────────────────

    def hit_test(self, px: int, py: int) -> Optional[TUIWindow]:
        """
        Return the topmost window containing point (px, py).
        Mimics twin's click-to-focus hit testing.
        """
        for win in reversed(self._sorted_windows()):
            if win.contains_point(px, py):
                return win
        return None

    def handle_click(self, px: int, py: int) -> Optional[str]:
        """
        Process a mouse click at (px, py).
        Returns the win_id of the clicked window, or None.
        Handles close/minimize buttons automatically.
        """
        win = self.hit_test(px, py)
        if not win:
            return None

        if win.close_button_hit(px, py):
            self.close(win.win_id)
            return None
        elif win.minimize_button_hit(px, py):
            self.minimize(win.win_id)
            return win.win_id
        else:
            self.focus_window(win.win_id)
            return win.win_id

    # ── Rendering ─────────────────────────────────────────────────────────────

    def render(self, output: Any = None) -> str:
        """
        Render all windows to ANSI string using double-buffer technique.
        Writes to output (sys.stdout by default) and returns the string.
        """
        if output is None:
            output = sys.stdout

        parts: List[str] = [ansi_hide_cursor()]

        # Render each window bottom-to-top into ANSI lines
        for win in self._sorted_windows():
            if win.state in (WindowState.MINIMIZED, WindowState.CLOSED):
                continue
            lines = win.render_lines()
            for row_offset, line in enumerate(lines):
                row = win.y + row_offset
                col = win.x
                if 0 <= row < self.term_height:
                    parts.append(ansi_move(row + 1, col + 1))
                    parts.append(line)

        parts.append(ansi_show_cursor())
        result = "".join(parts)

        try:
            output.write(result)
            output.flush()
        except Exception as exc:
            logger.warning("Render write failed: %s", exc)

        return result

    def render_to_string(self) -> str:
        """Render all windows and return ANSI string without writing to stdout."""
        import io
        buf = io.StringIO()
        return self.render(output=buf)

    def get_window_count(self) -> int:
        """Return the number of managed windows."""
        return len(self.windows)

    def list_windows(self) -> List[Dict[str, Any]]:
        """Return list of window info dicts."""
        return [
            {
                "win_id": w.win_id,
                "title": w.title,
                "x": w.x, "y": w.y,
                "w": w.w, "h": w.h,
                "z_order": w.z_order,
                "state": w.state.name,
                "focused": w.focused,
                "metadata": w.metadata,
            }
            for w in self._sorted_windows()
        ]
