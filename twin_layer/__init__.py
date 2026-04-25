"""
twin_layer — Twin-inspired TUI infrastructure for SintraPrime-Unified

This package ports key architectural concepts from cosmos72/twin (a textmode
window environment) into Python modules for SintraPrime's agent infrastructure.

Modules
-------
tui_window_manager  : Textmode window manager with ANSI rendering and z-ordering
session_manager     : Agent session lifecycle with attach/detach display support
terminal_multiplexer: Multi-terminal manager with scrollback and split views
network_display     : Network-transparent TUI display over WebSocket
tui_widgets         : Reusable ANSI TUI widgets (monitor, clock, logs, etc.)
theme_system        : Color theme management with INI support and CSS export
shm_ipc             : Shared memory pub/sub IPC between agents

Quick Start
-----------
>>> from twin_layer import TUIWindowManager, SessionManager, ThemeManager
>>> wm = TUIWindowManager()
>>> win = wm.create_window("w1", "Agent Console", x=5, y=2, w=60, h=20)
>>> win.write_text(0, 0, "SintraPrime Agent Online")
>>> sm = SessionManager()
>>> session = sm.create_session("agent-001")
>>> tm = ThemeManager(initial_theme="ocean")

Integration
-----------
SintraPrime agents use this layer for:
- TUI dashboards via TUIWindowManager + tui_widgets
- Session persistence via SessionManager
- Multi-agent terminal output via TerminalMultiplexer
- Remote monitoring via DisplayServer/DisplayClient
- Fast inter-agent messaging via MessageQueue
- Consistent theming via ThemeManager
"""

# ── Window Manager ────────────────────────────────────────────────────────────
from .tui_window_manager import (
    TUIWindow,
    TUIWindowManager,
    ScreenBuffer,
    WindowState,
    WindowColor,
)

# ── Session Manager ───────────────────────────────────────────────────────────
from .session_manager import (
    AgentSession,
    DisplayConnection,
    SessionManager,
    SessionState,
)

# ── Terminal Multiplexer ──────────────────────────────────────────────────────
from .terminal_multiplexer import (
    AgentTerminal,
    TerminalMultiplexer,
    SplitDirection,
    TerminalState,
)

# ── Network Display ───────────────────────────────────────────────────────────
from .network_display import (
    DisplayServer,
    DisplayClient,
    ScreenState,
    TwinAuth,
    ReconnectManager,
    compress_payload,
    decompress_payload,
)

# ── TUI Widgets ───────────────────────────────────────────────────────────────
from .tui_widgets import (
    Widget,
    AgentMonitorWidget,
    ClockWidget,
    ProgressBar,
    DialogWidget,
    DialogResult,
    ClipboardManager,
    AgentStatusPanel,
    AgentStatus,
    LogViewer,
    NotificationBanner,
    MenuBar,
    MenuItem,
)

# ── Theme System ──────────────────────────────────────────────────────────────
from .theme_system import (
    ColorTheme,
    ThemeManager,
    BUILTIN_THEMES,
    hex_to_rgb,
    rgb_to_hex,
    rgb_to_ansi256,
    contrast_ratio,
    is_accessible,
)

# ── Shared Memory IPC ─────────────────────────────────────────────────────────
from .shm_ipc import (
    SharedMemoryChannel,
    MessageQueue,
    Message,
    RingBuffer,
    LatencyTracker,
    SHM_AVAILABLE,
    MSGPACK_AVAILABLE,
)

__version__ = "1.0.0"
__author__ = "SintraPrime"

__all__ = [
    # Window Manager
    "TUIWindow", "TUIWindowManager", "ScreenBuffer", "WindowState", "WindowColor",
    # Session Manager
    "AgentSession", "DisplayConnection", "SessionManager", "SessionState",
    # Terminal Multiplexer
    "AgentTerminal", "TerminalMultiplexer", "SplitDirection", "TerminalState",
    # Network Display
    "DisplayServer", "DisplayClient", "ScreenState", "TwinAuth", "ReconnectManager",
    "compress_payload", "decompress_payload",
    # TUI Widgets
    "Widget", "AgentMonitorWidget", "ClockWidget", "ProgressBar",
    "DialogWidget", "DialogResult", "ClipboardManager",
    "AgentStatusPanel", "AgentStatus", "LogViewer",
    "NotificationBanner", "MenuBar", "MenuItem",
    # Theme System
    "ColorTheme", "ThemeManager", "BUILTIN_THEMES",
    "hex_to_rgb", "rgb_to_hex", "rgb_to_ansi256", "contrast_ratio", "is_accessible",
    # SHM IPC
    "SharedMemoryChannel", "MessageQueue", "Message", "RingBuffer",
    "LatencyTracker", "SHM_AVAILABLE", "MSGPACK_AVAILABLE",
]
