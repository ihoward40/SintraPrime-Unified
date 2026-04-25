# Twin Layer — Feature Documentation

This document describes all features implemented in `twin_layer`, their origins
in the [cosmos72/twin](https://github.com/cosmos72/twin) textmode window
environment, and how they integrate with SintraPrime's agent infrastructure.

---

## Module Overview

| Module | Twin Source | Status |
|--------|-------------|--------|
| `tui_window_manager.py` | `server/wm.cpp`, `server/draw.cpp` | ✅ Implemented |
| `session_manager.py` | `server/display.cpp`, `server/remote.cpp` | ✅ Implemented |
| `terminal_multiplexer.py` | `server/pty.cpp`, `server/tty.cpp` | ✅ Implemented |
| `network_display.py` | `server/socket.cpp`, libtw API | ✅ Implemented |
| `tui_widgets.py` | `clients/sysmon.c`, `cuckoo.c`, `dialog.c`, `clip.c` | ✅ Implemented |
| `theme_system.py` | `server/palette.cpp`, `server/ini.cpp` | ✅ Implemented |
| `shm_ipc.py` | `server/shm.cpp` | ✅ Implemented |

---

## 1. tui_window_manager.py

### Twin Origin
twin's `server/wm.cpp` manages window state, focus, and z-ordering. `server/draw.cpp`
handles actual screen rendering with clipping and compositing.

### Implementation
```python
from twin_layer import TUIWindowManager, TUIWindow

wm = TUIWindowManager(term_width=160, term_height=50)
win = wm.create_window("console", "Agent Console", x=5, y=2, w=80, h=25)
win.write_text(0, 0, "SintraPrime Agent v1.0 — Online")
win.write_text(1, 0, "Tasks: 12 active | 3 pending")
wm.render()  # Writes ANSI to stdout

# Hit testing (mouse click handling)
clicked_win = wm.hit_test(px=20, py=10)

# Window operations
wm.minimize("console")
wm.maximize("console")
wm.move("console", x=10, y=5)
wm.resize("console", w=100, h=30)
wm.close("console")
```

### Key Features
- **TUIWindow**: Full content buffer with per-cell (char, fg, bg) storage
- **TUIWindowManager**: Z-order stacking, focus management
- **ScreenBuffer**: Double-buffer rendering to eliminate flicker (twin's key optimization)
- **Hit testing**: Click events routed to correct window by coordinate
- **ANSI rendering**: Box-drawing characters for borders, truecolor title bars
- **Auto-focus**: Clicking a window raises and focuses it

### SintraPrime Integration
Each SintraPrime agent gets its own TUIWindow. The orchestrator renders the
full window manager stack as the agent monitoring dashboard.

---

## 2. session_manager.py

### Twin Origin
twin's core innovation: the server keeps running after all displays disconnect.
`server/display.cpp` manages display attach/detach; `server/remote.cpp` handles
remote connections.

### Implementation
```python
from twin_layer import SessionManager, SessionState

sm = SessionManager()

# Create a session for an agent
session = sm.create_session("agent-001", tags=["worker"])

# Attach a terminal display
did = sm.attach_display(session.session_id, {
    "type": "terminal",
    "endpoint": ":0",
    "metadata": {"cols": 80, "rows": 24}
})

# Detach without killing session (twin's killer feature)
sm.detach_display(session.session_id, did)
# session.state is now DETACHED

# Re-attach from another terminal
sm.attach_display(session.session_id, {"type": "websocket", "endpoint": "ws://..."})
# session.state is now ACTIVE again

# Resume explicitly
sm.resume_session(session.session_id)

# List all sessions
for s in sm.list_sessions(state=SessionState.ACTIVE):
    print(s["agent_id"], s["state"])
```

### Key Features
- **AgentSession**: Full session state with multiple display connections
- **Attach/detach**: Sessions survive display disconnection
- **JSON persistence**: Sessions saved to `/agent/home/sessions.json`
- **Atomic writes**: Temp file + rename for crash safety
- **State machine**: ACTIVE → DETACHED → HIBERNATED / TERMINATED

### SintraPrime Integration
When an agent's terminal connection drops, its work session persists. The agent
can reconnect from another machine and resume exactly where it left off.

---

## 3. terminal_multiplexer.py

### Twin Origin
`server/pty.cpp` wraps processes in pseudo-terminals. `server/tty.cpp` implements
the terminal emulator. twin supports many simultaneous terminal clients.

### Implementation
```python
from twin_layer import TerminalMultiplexer, AgentTerminal

mux = TerminalMultiplexer(term_width=200, term_height=60)

# Create named terminals for agents
t_orch = mux.create_terminal("orchestrator", ["python3", "orchestrator.py"])
t_work = mux.create_terminal("worker-1", ["python3", "worker.py"])

# Start all processes
mux.start_all()

# Split view (side-by-side)
mux.split_horizontal(t_orch.terminal_id, t_work.terminal_id)

# Broadcast a command to all terminals
mux.broadcast("PAUSE\n")

# Capture output
last_50 = mux.capture_output(t_orch.terminal_id, n=50)

# Route mouse clicks to the right terminal
target_id = mux.route_mouse_event(px=90, py=15, event_data={})

# Render all panels to ANSI
screen = mux.render_all()
```

### Key Features
- **AgentTerminal**: subprocess wrapper with scrollback buffer (1000 lines)
- **TerminalMultiplexer**: manages N terminals simultaneously
- **Split layouts**: horizontal (side-by-side) and vertical (stacked)
- **Mouse routing**: coordinates → correct terminal panel
- **Broadcast**: send messages to all running terminals
- **Truecolor headers**: each panel has a colored status header

### SintraPrime Integration
The orchestrator agent's terminal is shown in the top-left panel; worker agents
fill the remaining panels. The user can click to focus any agent's output.

---

## 4. network_display.py

### Twin Origin
twin is *network transparent* — a remote display can attach to a running server
via TCP. `server/socket.cpp` implements this; the libtw library provides the client API.

### Implementation
```python
import asyncio
from twin_layer import DisplayServer, DisplayClient, TwinAuth

# Server side
server = DisplayServer(host="0.0.0.0", port=8765)
token = server.auth.issue_token("admin", ttl=86400)
await server.start()

# Update state from window manager
state = server.build_screen_state(window_manager)
await server.broadcast_screen_state(state)

# Client side (web dashboard or remote terminal)
client = DisplayClient("ws://localhost:8765", token=token)
await client.connect()

state = client.get_latest_state()
print(state.windows)  # List of window info dicts

await client.disconnect()
```

### Key Features
- **DisplayServer**: WebSocket server with token authentication
- **DisplayClient**: Reconnecting client with exponential backoff
- **JSON protocol**: Window states serialized and streamed
- **Compression**: zlib for screen updates > 4KB
- **TwinAuth**: Token management with TTL and revocation
- **ReconnectManager**: Exponential backoff (1s → 60s max)
- **REST simulation**: `handle_rest_state()` for GET /api/display/state
- **Broadcast**: One server → many web dashboard clients

### SintraPrime Integration
The SintraPrime web UI connects to DisplayServer via WebSocket to show
a real-time view of the agent TUI dashboard without requiring a terminal.

---

## 5. tui_widgets.py

### Twin Origin
twin ships client programs that run inside its windows:
- `sysmon.c`: System monitor (CPU, memory)
- `cuckoo.c`: Clock widget
- `dialog.c`: Modal dialog boxes
- `clip.c`: Shared clipboard server

### Implementation
```python
from twin_layer import (
    AgentMonitorWidget, ClockWidget, ProgressBar, DialogWidget,
    ClipboardManager, AgentStatusPanel, AgentStatus, LogViewer,
    NotificationBanner, MenuBar, MenuItem
)

# System monitor
monitor = AgentMonitorWidget(x=0, y=0, w=60, h=10)
monitor.update(agent_count=8, task_count=24)
print(monitor.render())

# Agent status table
panel = AgentStatusPanel(x=0, y=12, w=80, h=15)
panel.update_agent(AgentStatus("a1", "Orchestrator", "running", tasks_done=42))
print(panel.render())

# Scrollable log viewer
lv = LogViewer(x=0, y=28, w=80, h=20)
lv.add_line("Task batch-001 started", "INFO")
lv.add_line("Worker timeout detected", "WARNING")
lv.search("timeout")
print(lv.render())

# Shared clipboard between agents
cb = ClipboardManager()
cb.set("shared data payload", agent_id="agent-001")
data = cb.get()  # accessible by any agent

# Dialog
d = DialogWidget(message="Delete all tasks?", dialog_type="yesno")
d.select_yes_ok()
print(d.result)  # DialogResult.YES

# Notifications
nb = NotificationBanner(x=0, y=0, w=80)
nb.notify("New task batch received", level="success")
print(nb.render())
```

### SintraPrime Integration
Each widget is placed in a dedicated TUIWindow. The orchestrator dashboard
shows monitor + status panel; each agent window shows a log viewer.

---

## 6. theme_system.py

### Twin Origin
twin's `server/palette.cpp` manages color palettes. `server/ini.cpp` loads
configuration from `~/.twin/theme.ini` (twin's own INI format).

### Implementation
```python
from twin_layer import ThemeManager, ColorTheme, contrast_ratio, is_accessible

tm = ThemeManager(initial_theme="ocean")

# Switch theme live (no restart needed)
tm.switch_theme("matrix")

# Callback when theme changes
tm.add_switch_callback(lambda name, theme: print(f"Theme changed to {name}"))

# Export as CSS for web UI
css = tm.export_all_css()

# Check WCAG accessibility
report = tm.accessibility_report("light")
print(f"AA pass: {report['AA_passed']}/{report['total_checks']}")

# Save/load INI (twin-compatible format)
tm.save_to_ini(Path("~/.twin/themes/custom.ini"))
tm.load_from_ini(Path("~/.twin/themes/custom.ini"))

# Check specific pair
ratio = contrast_ratio((255, 255, 255), (0, 0, 0))  # 21.0
print(is_accessible((220, 220, 220), (20, 20, 30)))  # True
```

### Built-in Themes
| Theme | Description |
|-------|-------------|
| `dark` | Dark background, blue accents (default) |
| `light` | Light background for bright environments |
| `matrix` | Classic green-on-black hacker aesthetic |
| `ocean` | Deep blues with teal highlights |
| `fire` | Warm red/orange tones |

### SintraPrime Integration
Theme selection is exposed in the web UI settings panel. The selected theme
drives both the TUI ANSI output and the web dashboard CSS.

---

## 7. shm_ipc.py

### Twin Origin
twin uses shared memory (`server/shm.cpp`) to pass display data between
the server and locally-attached displays without socket overhead.

### Implementation
```python
from twin_layer import SharedMemoryChannel, MessageQueue, LatencyTracker

# Direct channel usage
ch = SharedMemoryChannel("agent-events", capacity=256)
ch.publish({"event": "task_done", "task_id": "t-42"}, sender_id="worker-1")
messages = ch.read_new()

# Pub/Sub via MessageQueue
mq = MessageQueue(capacity=256)

# Subscriber (in agent-2's thread)
mq.subscribe("task-events", lambda msg: handle(msg.payload))

# Publisher (from agent-1)
mq.publish("task-events", {"action": "start", "batch": 7}, sender="agent-1")

# Stats
stats = mq.get_stats()
print(f"Published: {stats['queue_stats']['published']}")

# Latency tracking
lt = LatencyTracker(window=1000)
send_time = time.time()
# ... message travels ...
lt.record(send_time)
print(lt.get_stats())  # p50, p90, p99, mean, max

mq.stop()
```

### Key Features
- **RingBuffer**: Fixed-capacity FIFO with overwrite-oldest semantics
- **SharedMemoryChannel**: Optional SHM backing via `multiprocessing.shared_memory`
- **MessageQueue**: Full pub/sub with background polling thread
- **Message**: Typed envelope with sender_id, timestamp, seq number
- **LatencyTracker**: Rolling window percentile statistics
- **Serialization**: msgpack (preferred) or JSON fallback
- **Fallback**: In-process ring buffer when SHM unavailable

### SintraPrime Integration
Used for high-frequency agent coordination (task assignments, status updates,
heartbeats) without going through Redis for sub-millisecond local messaging.

---

## Test Coverage

Tests are located in `twin_layer/tests/test_twin_layer.py`.

Run tests:
```bash
cd /agent/home/SintraPrime-Unified
python -m pytest twin_layer/tests/test_twin_layer.py -v
```

| Module | Test Class | Tests |
|--------|-----------|-------|
| tui_window_manager | TestTUIWindow, TestTUIWindowManager, TestScreenBuffer | 18 |
| session_manager | TestSessionManager | 9 |
| terminal_multiplexer | TestAgentTerminal, TestTerminalMultiplexer | 10 |
| network_display | TestNetworkDisplay | 10 |
| tui_widgets | TestTUIWidgets | 14 |
| theme_system | TestThemeSystem | 17 |
| shm_ipc | TestSHMIPC | 13 |
| integration | TestIntegration | 3 |
| **Total** | | **~94** |

---

## Docker Compose Integration

The `twin-display-server` service (port 8765) is added to docker-compose.yml.
Web dashboard clients connect to `ws://localhost:8765/ws/display`.

---

## Simplifications and Adaptations

1. **No PTY**: AgentTerminal uses subprocess pipes rather than real PTY devices.
   Real PTY would require `pty` module but adds complexity for headless agents.

2. **No X11/Wayland**: twin bridges TUI to graphical displays. SintraPrime uses
   WebSocket for remote display instead of twin's X11 forwarding.

3. **Python threading vs C event loops**: twin uses a single-threaded event loop
   in C. Python's GIL makes single-threaded concurrency less attractive; we use
   background threads with proper locking.

4. **Shared memory segment**: Python's `multiprocessing.shared_memory` doesn't
   support named ring buffers as efficiently as C `mmap`/`shmget`. The ring buffer
   is maintained in Python process memory with optional SHM backing.

5. **No widget event loop**: twin's widgets register with a central event loop.
   SintraPrime widgets are passive renderers called from the parent manager.
