"""
test_twin_layer.py — Comprehensive tests for SintraPrime twin_layer package

Covers all 7 modules with 40+ test cases.
"""

import json
import os
import sys
import tempfile
import threading
import time
from pathlib import Path

import pytest

# Add parent dir to path for standalone running
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from twin_layer.tui_window_manager import (
    TUIWindow, TUIWindowManager, ScreenBuffer, WindowState
)
from twin_layer.session_manager import (
    AgentSession, DisplayConnection, SessionManager, SessionState
)
from twin_layer.terminal_multiplexer import (
    AgentTerminal, TerminalMultiplexer, SplitDirection, TerminalState
)
from twin_layer.network_display import (
    DisplayServer, DisplayClient, ScreenState, TwinAuth,
    ReconnectManager, compress_payload, decompress_payload
)
from twin_layer.tui_widgets import (
    AgentMonitorWidget, ClockWidget, ProgressBar, DialogWidget,
    DialogResult, ClipboardManager, AgentStatusPanel, AgentStatus,
    LogViewer, NotificationBanner, MenuBar, MenuItem
)
from twin_layer.theme_system import (
    ColorTheme, ThemeManager, BUILTIN_THEMES,
    hex_to_rgb, rgb_to_hex, rgb_to_ansi256, contrast_ratio, is_accessible
)
from twin_layer.shm_ipc import (
    SharedMemoryChannel, MessageQueue, Message, RingBuffer, LatencyTracker
)


# ═══════════════════════════════════════════════════════════════════════════════
# TUIWindowManager Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestTUIWindow:
    """Tests for TUIWindow."""

    def test_create_window(self):
        win = TUIWindow("w1", "Test", x=0, y=0, w=30, h=10)
        assert win.win_id == "w1"
        assert win.title == "Test"
        assert win.w == 30
        assert win.h == 10
        assert win.state == WindowState.NORMAL

    def test_inner_dimensions(self):
        win = TUIWindow("w1", "Test", x=0, y=0, w=20, h=10)
        assert win.inner_w == 18  # w - 2
        assert win.inner_h == 8   # h - 2

    def test_write_text(self):
        win = TUIWindow("w1", "Test", x=0, y=0, w=30, h=10)
        win.write_text(0, 0, "Hello")
        assert win._content[0][0][0] == "H"
        assert win._content[0][1][0] == "e"
        assert win._content[0][4][0] == "o"

    def test_write_text_clipping(self):
        """Writing beyond bounds should not raise."""
        win = TUIWindow("w1", "Test", x=0, y=0, w=10, h=5)
        win.write_text(100, 100, "Should not crash")

    def test_contains_point(self):
        win = TUIWindow("w1", "Test", x=5, y=3, w=20, h=10)
        assert win.contains_point(5, 3)
        assert win.contains_point(10, 7)
        assert not win.contains_point(0, 0)
        assert not win.contains_point(25, 3)

    def test_close_button_hit(self):
        win = TUIWindow("w1", "Test", x=0, y=0, w=20, h=10)
        assert win.close_button_hit(18, 0)   # last col - 1
        assert not win.close_button_hit(0, 0)

    def test_minimize_button_hit(self):
        win = TUIWindow("w1", "Test", x=0, y=0, w=20, h=10)
        assert win.minimize_button_hit(16, 0)
        assert not win.minimize_button_hit(0, 0)

    def test_render_lines_normal(self):
        win = TUIWindow("w1", "Test Window", x=0, y=0, w=30, h=6)
        lines = win.render_lines()
        assert len(lines) == 6
        assert len(lines) == win.h

    def test_render_lines_minimized(self):
        win = TUIWindow("w1", "Test", x=0, y=0, w=30, h=6)
        win.state = WindowState.MINIMIZED
        lines = win.render_lines()
        assert lines == []

    def test_resize(self):
        win = TUIWindow("w1", "Test", x=0, y=0, w=30, h=10)
        win.resize(50, 20)
        assert win.w == 50
        assert win.h == 20
        assert len(win._content) == 18   # inner_h
        assert len(win._content[0]) == 48  # inner_w

    def test_move(self):
        win = TUIWindow("w1", "Test", x=0, y=0, w=30, h=10)
        win.move(10, 5)
        assert win.x == 10
        assert win.y == 5

    def test_clear_content(self):
        win = TUIWindow("w1", "Test", x=0, y=0, w=20, h=8)
        win.write_text(0, 0, "Hello")
        win.clear_content()
        assert win._content[0][0][0] == " "


class TestTUIWindowManager:
    """Tests for TUIWindowManager."""

    def test_create(self):
        wm = TUIWindowManager(term_width=80, term_height=24)
        assert wm.term_width == 80
        assert wm.term_height == 24

    def test_create_window(self):
        wm = TUIWindowManager(80, 24)
        win = wm.create_window("w1", "Test", x=5, y=2, w=40, h=15)
        assert win.win_id == "w1"
        assert wm.get_window_count() == 1

    def test_focus_management(self):
        wm = TUIWindowManager(80, 24)
        w1 = wm.create_window("w1", "Win1", x=0, y=0, w=20, h=10)
        w2 = wm.create_window("w2", "Win2", x=5, y=5, w=20, h=10)
        assert w2.focused  # Most recently created gets focus
        assert not w1.focused

    def test_z_order_raise(self):
        wm = TUIWindowManager(80, 24)
        w1 = wm.create_window("w1", "Win1", x=0, y=0, w=20, h=10)
        w2 = wm.create_window("w2", "Win2", x=5, y=5, w=20, h=10)
        original_z = w1.z_order
        wm.raise_window("w1")
        assert w1.z_order > original_z

    def test_hit_test_basic(self):
        wm = TUIWindowManager(80, 24)
        w1 = wm.create_window("w1", "Win1", x=0, y=0, w=20, h=10)
        result = wm.hit_test(5, 5)
        assert result is not None
        assert result.win_id == "w1"

    def test_hit_test_no_window(self):
        wm = TUIWindowManager(80, 24)
        result = wm.hit_test(50, 50)
        assert result is None

    def test_minimize(self):
        wm = TUIWindowManager(80, 24)
        win = wm.create_window("w1", "Win1", x=0, y=0, w=20, h=10)
        wm.minimize("w1")
        assert win.state == WindowState.MINIMIZED

    def test_maximize(self):
        wm = TUIWindowManager(80, 24)
        win = wm.create_window("w1", "Win1", x=5, y=5, w=20, h=10)
        wm.maximize("w1")
        assert win.state == WindowState.MAXIMIZED
        assert win.x == 0
        assert win.y == 0
        assert win.w == 80
        assert win.h == 24

    def test_close(self):
        wm = TUIWindowManager(80, 24)
        wm.create_window("w1", "Win1", x=0, y=0, w=20, h=10)
        wm.close("w1")
        assert wm.get_window_count() == 0

    def test_move_window(self):
        wm = TUIWindowManager(80, 24)
        win = wm.create_window("w1", "Win1", x=0, y=0, w=20, h=10)
        wm.move("w1", 15, 8)
        assert win.x == 15
        assert win.y == 8

    def test_list_windows(self):
        wm = TUIWindowManager(80, 24)
        wm.create_window("w1", "Win1", x=0, y=0, w=20, h=10)
        wm.create_window("w2", "Win2", x=5, y=5, w=20, h=10)
        listing = wm.list_windows()
        assert len(listing) == 2
        ids = {w["win_id"] for w in listing}
        assert "w1" in ids
        assert "w2" in ids

    def test_render_to_string(self):
        wm = TUIWindowManager(80, 24)
        wm.create_window("w1", "Hello", x=0, y=0, w=30, h=8)
        output = wm.render_to_string()
        assert isinstance(output, str)
        assert len(output) > 0


class TestScreenBuffer:
    """Tests for ScreenBuffer."""

    def test_flush_empty(self):
        buf = ScreenBuffer(40, 10)
        result = buf.flush()
        assert result == ""

    def test_write_and_flush(self):
        buf = ScreenBuffer(40, 10)
        buf.write(0, 0, "Hi")
        result = buf.flush()
        assert len(result) > 0

    def test_double_flush_empty(self):
        buf = ScreenBuffer(40, 10)
        buf.write(0, 0, "Hi")
        buf.flush()
        result = buf.flush()  # Nothing changed
        assert result == ""


# ═══════════════════════════════════════════════════════════════════════════════
# SessionManager Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestSessionManager:
    """Tests for SessionManager."""

    def test_create_session(self, tmp_path):
        sm = SessionManager(sessions_file=tmp_path / "sessions.json")
        s = sm.create_session("agent-001")
        assert s.agent_id == "agent-001"
        assert s.session_state == SessionState.ACTIVE
        assert len(s.session_id) > 0

    def test_get_session(self, tmp_path):
        sm = SessionManager(sessions_file=tmp_path / "sessions.json")
        s = sm.create_session("agent-001")
        retrieved = sm.get_session(s.session_id)
        assert retrieved is not None
        assert retrieved.session_id == s.session_id

    def test_get_nonexistent(self, tmp_path):
        sm = SessionManager(sessions_file=tmp_path / "sessions.json")
        assert sm.get_session("bad-id") is None

    def test_attach_display(self, tmp_path):
        sm = SessionManager(sessions_file=tmp_path / "sessions.json")
        s = sm.create_session("agent-001")
        did = sm.attach_display(s.session_id, {"type": "terminal", "endpoint": ":0"})
        assert did is not None
        s_updated = sm.get_session(s.session_id)
        assert len(s_updated.display_connections) == 1

    def test_detach_display(self, tmp_path):
        sm = SessionManager(sessions_file=tmp_path / "sessions.json")
        s = sm.create_session("agent-001")
        did = sm.attach_display(s.session_id, {"type": "terminal", "endpoint": ":0"})
        result = sm.detach_display(s.session_id, did)
        assert result
        s_updated = sm.get_session(s.session_id)
        assert s_updated.session_state == SessionState.DETACHED

    def test_resume_session(self, tmp_path):
        sm = SessionManager(sessions_file=tmp_path / "sessions.json")
        s = sm.create_session("agent-001")
        sm.hibernate_session(s.session_id)
        assert sm.get_session(s.session_id).session_state == SessionState.HIBERNATED
        sm.resume_session(s.session_id)
        assert sm.get_session(s.session_id).session_state == SessionState.ACTIVE

    def test_destroy_session(self, tmp_path):
        sm = SessionManager(sessions_file=tmp_path / "sessions.json")
        s = sm.create_session("agent-001")
        assert sm.destroy_session(s.session_id)
        assert sm.get_session(s.session_id) is None

    def test_list_sessions(self, tmp_path):
        sm = SessionManager(sessions_file=tmp_path / "sessions.json")
        sm.create_session("agent-001")
        sm.create_session("agent-002")
        listing = sm.list_sessions()
        assert len(listing) == 2

    def test_persistence(self, tmp_path):
        path = tmp_path / "sessions.json"
        sm1 = SessionManager(sessions_file=path)
        s = sm1.create_session("agent-001")
        sid = s.session_id

        # Load fresh instance
        sm2 = SessionManager(sessions_file=path)
        retrieved = sm2.get_session(sid)
        assert retrieved is not None
        assert retrieved.agent_id == "agent-001"

    def test_attach_to_detached_reactivates(self, tmp_path):
        sm = SessionManager(sessions_file=tmp_path / "sessions.json")
        s = sm.create_session("agent-001")
        sm.detach_all_displays(s.session_id)
        assert sm.get_session(s.session_id).session_state == SessionState.DETACHED
        sm.attach_display(s.session_id, {"type": "websocket", "endpoint": "ws://localhost:8765"})
        assert sm.get_session(s.session_id).session_state == SessionState.ACTIVE


# ═══════════════════════════════════════════════════════════════════════════════
# TerminalMultiplexer Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestAgentTerminal:
    """Tests for AgentTerminal."""

    def test_create(self):
        term = AgentTerminal("t1", ["echo", "hello"], name="Echo")
        assert term.terminal_id == "t1"
        assert term.name == "Echo"
        assert term.state == TerminalState.STOPPED

    def test_start_stop(self):
        term = AgentTerminal("t1", ["echo", "hello"])
        assert term.start()
        time.sleep(0.3)
        term.stop()
        assert term.state == TerminalState.STOPPED

    def test_capture_output(self):
        term = AgentTerminal("t1", ["echo", "hello world"])
        term.start()
        time.sleep(0.5)
        output = term.capture_output(10)
        term.stop()
        assert any("hello world" in line for line in output)

    def test_scrollback_limit(self):
        term = AgentTerminal("t1", ["sh", "-c", "for i in $(seq 100); do echo line$i; done"],
                             scrollback_limit=50)
        term.start()
        time.sleep(1.0)
        output = term.get_all_output()
        term.stop()
        assert len(output) <= 50

    def test_send_line(self):
        term = AgentTerminal("t1", ["cat"])
        term.start()
        time.sleep(0.1)
        term.send_line("test input")
        time.sleep(0.2)
        output = term.capture_output(5)
        term.stop()
        assert any("test input" in line for line in output)


class TestTerminalMultiplexer:
    """Tests for TerminalMultiplexer."""

    def test_create(self):
        mux = TerminalMultiplexer(term_width=160, term_height=40)
        assert mux.term_width == 160
        assert mux.term_height == 40

    def test_create_terminal(self):
        mux = TerminalMultiplexer(80, 24)
        t = mux.create_terminal("agent1", ["echo", "hi"])
        assert t.name == "agent1"
        assert len(mux.list_terminals()) == 1

    def test_split_horizontal(self):
        mux = TerminalMultiplexer(80, 24)
        t1 = mux.create_terminal("left", ["cat"], terminal_id="t1")
        t2 = mux.create_terminal("right", ["cat"], terminal_id="t2")
        mux.split_horizontal("t1", "t2")
        assert t1.w == 40
        assert t2.w == 40

    def test_split_vertical(self):
        mux = TerminalMultiplexer(80, 24)
        t1 = mux.create_terminal("top", ["cat"], terminal_id="t1")
        t2 = mux.create_terminal("bottom", ["cat"], terminal_id="t2")
        mux.split_vertical("t1", "t2")
        assert t1.h == 12
        assert t2.h == 12

    def test_capture_output(self):
        mux = TerminalMultiplexer(80, 24)
        t = mux.create_terminal("t", ["echo", "mux test"], auto_start=True)
        time.sleep(0.5)
        output = mux.capture_output(t.terminal_id, 10)
        mux.stop_all()
        assert any("mux test" in line for line in output)

    def test_mouse_routing(self):
        mux = TerminalMultiplexer(80, 24)
        t1 = mux.create_terminal("t1", ["cat"], terminal_id="t1")
        t2 = mux.create_terminal("t2", ["cat"], terminal_id="t2")
        mux.split_horizontal("t1", "t2")
        # Left half should route to t1
        result = mux.route_mouse_event(10, 5, {})
        assert result == "t1"
        # Right half should route to t2
        result = mux.route_mouse_event(50, 5, {})
        assert result == "t2"


# ═══════════════════════════════════════════════════════════════════════════════
# NetworkDisplay Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestNetworkDisplay:
    """Tests for network_display module."""

    def test_twin_auth_issue_validate(self):
        auth = TwinAuth()
        token = auth.issue_token("test")
        assert auth.validate_token(token)

    def test_twin_auth_invalid(self):
        auth = TwinAuth()
        assert not auth.validate_token("bogus-token")

    def test_twin_auth_revoke(self):
        auth = TwinAuth()
        token = auth.issue_token("test")
        auth.revoke_token(token)
        assert not auth.validate_token(token)

    def test_reconnect_manager_backoff(self):
        rm = ReconnectManager(max_retries=5, base_delay=0.1, max_delay=2.0)
        delay1 = rm.next_delay("client1")
        delay2 = rm.next_delay("client1")
        assert delay2 > delay1  # Exponential backoff

    def test_reconnect_manager_max_retries(self):
        rm = ReconnectManager(max_retries=2, base_delay=0.1)
        rm.next_delay("c1")
        rm.next_delay("c1")
        assert rm.next_delay("c1") is None

    def test_reconnect_reset(self):
        rm = ReconnectManager(max_retries=3, base_delay=0.1)
        rm.next_delay("c1")
        rm.reset("c1")
        assert rm.get_attempt_count("c1") == 0

    def test_compress_decompress(self):
        data = '{"windows": [{"title": "Test", "x": 0, "y": 0}], "version": 1}'
        compressed = compress_payload(data)
        assert isinstance(compressed, bytes)
        restored = decompress_payload(compressed)
        assert restored == data

    def test_screen_state_to_json(self):
        state = ScreenState(
            timestamp="2026-01-01T00:00:00Z",
            term_width=80,
            term_height=24,
            windows=[{"win_id": "w1", "title": "Test"}],
            focused_id="w1",
            version=1,
        )
        j = state.to_json()
        parsed = json.loads(j)
        assert parsed["term_width"] == 80
        assert parsed["version"] == 1

    def test_display_server_creation(self):
        server = DisplayServer(host="127.0.0.1", port=18765)
        assert server.port == 18765
        assert server.client_count() == 0

    def test_display_server_build_state(self):
        # Create a mock window manager
        wm = TUIWindowManager(80, 24)
        wm.create_window("w1", "Test", x=0, y=0, w=30, h=10)
        server = DisplayServer()
        state = server.build_screen_state(wm)
        assert state.term_width == 80
        assert len(state.windows) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# TUI Widgets Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestTUIWidgets:
    """Tests for tui_widgets module."""

    def test_agent_monitor_renders(self):
        w = AgentMonitorWidget(x=0, y=0, w=60, h=10)
        w.update(agent_count=5, task_count=12, cpu_pct=45.0, mem_pct=60.0, mem_mb=2048)
        output = w.render()
        assert isinstance(output, str)
        assert "5" in output  # agent count

    def test_clock_renders(self):
        w = ClockWidget(x=0, y=0, w=30, h=5)
        output = w.render()
        assert isinstance(output, str)
        assert ":" in output  # time separator

    def test_progress_bar_renders(self):
        pb = ProgressBar(x=0, y=0, w=40, label="Task Progress", total=100)
        pb.set_progress(75)
        assert pb.percent == 75.0
        output = pb.render()
        assert isinstance(output, str)

    def test_progress_bar_clamp(self):
        pb = ProgressBar(x=0, y=0, w=40, total=100)
        pb.set_progress(200)
        assert pb.current == 100
        pb.set_progress(-10)
        assert pb.current == 0

    def test_dialog_renders(self):
        d = DialogWidget(x=5, y=5, w=50, h=8, message="Are you sure?", dialog_type="yesno")
        output = d.render()
        assert isinstance(output, str)

    def test_dialog_yes_no(self):
        d = DialogWidget(message="Confirm?", dialog_type="yesno")
        d.select_yes_ok()
        assert d.result == DialogResult.YES
        d.select_no_cancel()
        assert d.result == DialogResult.NO

    def test_clipboard_set_get(self):
        cb = ClipboardManager()
        cb.set("Hello, agents!", agent_id="agent-1")
        assert cb.get() == "Hello, agents!"

    def test_clipboard_history(self):
        cb = ClipboardManager()
        cb.set("First")
        cb.set("Second")
        cb.set("Third")
        history = cb.get_history(3)
        assert len(history) == 3
        assert history[-1][1] == "Third"

    def test_agent_status_panel_renders(self):
        panel = AgentStatusPanel(x=0, y=0, w=70, h=15)
        panel.update_agent(AgentStatus("a1", "Orchestrator", "running", tasks_done=10, tasks_pending=2))
        panel.update_agent(AgentStatus("a2", "Worker-1", "idle"))
        output = panel.render()
        assert isinstance(output, str)
        assert "Orchestrator" in output

    def test_log_viewer_add_and_render(self):
        lv = LogViewer(x=0, y=0, w=80, h=15)
        lv.add_line("System started", "INFO")
        lv.add_line("Warning: high CPU", "WARNING")
        lv.add_line("Error: timeout", "ERROR")
        output = lv.render()
        assert isinstance(output, str)

    def test_log_viewer_search(self):
        lv = LogViewer(x=0, y=0, w=80, h=15)
        lv.add_line("Normal message", "INFO")
        lv.add_line("CPU critical alert", "ERROR")
        lv.search("critical")
        filtered = lv._filtered_lines()
        assert len(filtered) == 1
        assert "critical" in filtered[0][1].lower()

    def test_notification_banner(self):
        nb = NotificationBanner(x=0, y=0, w=60)
        nb.notify("Agent task completed", level="success", ttl=60)
        assert nb.has_notifications()
        output = nb.render()
        assert isinstance(output, str)

    def test_notification_ttl_expiry(self):
        nb = NotificationBanner(x=0, y=0, w=60)
        nb.notify("Quick", level="info", ttl=0.01)
        time.sleep(0.05)
        assert not nb.has_notifications()

    def test_widget_click_handler(self):
        pb = ProgressBar(x=10, y=5, w=30)
        clicked = []
        pb.add_click_handler(lambda x, y: clicked.append((x, y)))
        pb.on_click(15, 6)   # within bounds
        assert len(clicked) == 1
        pb.on_click(0, 0)    # outside
        assert len(clicked) == 1  # no new click

    def test_menu_bar_renders(self):
        mb = MenuBar(y=0, w=80)
        mb.add_menu("File", [MenuItem("New", "Ctrl+N"), MenuItem("Exit", "Ctrl+Q")])
        mb.add_menu("Edit", [MenuItem("Copy", "Ctrl+C")])
        output = mb.render()
        assert isinstance(output, str)
        assert "File" in output


# ═══════════════════════════════════════════════════════════════════════════════
# ThemeSystem Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestThemeSystem:
    """Tests for theme_system module."""

    def test_hex_to_rgb(self):
        assert hex_to_rgb("#ff0000") == (255, 0, 0)
        assert hex_to_rgb("#00ff00") == (0, 255, 0)
        assert hex_to_rgb("0000ff") == (0, 0, 255)

    def test_hex_to_rgb_shorthand(self):
        assert hex_to_rgb("#fff") == (255, 255, 255)
        assert hex_to_rgb("#000") == (0, 0, 0)

    def test_rgb_to_hex(self):
        assert rgb_to_hex(255, 0, 0) == "#ff0000"
        assert rgb_to_hex(0, 255, 0) == "#00ff00"

    def test_rgb_to_ansi256(self):
        idx = rgb_to_ansi256(255, 0, 0)
        assert 16 <= idx <= 255

    def test_contrast_ratio_black_white(self):
        ratio = contrast_ratio((0, 0, 0), (255, 255, 255))
        assert abs(ratio - 21.0) < 0.2

    def test_contrast_ratio_same(self):
        ratio = contrast_ratio((100, 100, 100), (100, 100, 100))
        assert ratio == pytest.approx(1.0)

    def test_is_accessible_pass(self):
        assert is_accessible((0, 0, 0), (255, 255, 255), "AA")
        assert is_accessible((0, 0, 0), (255, 255, 255), "AAA")

    def test_is_accessible_fail(self):
        assert not is_accessible((128, 128, 128), (160, 160, 160), "AA")

    def test_builtin_themes(self):
        assert "dark" in BUILTIN_THEMES
        assert "light" in BUILTIN_THEMES
        assert "matrix" in BUILTIN_THEMES
        assert "ocean" in BUILTIN_THEMES
        assert "fire" in BUILTIN_THEMES

    def test_theme_manager_default(self):
        tm = ThemeManager(initial_theme="dark")
        assert tm.current_name == "dark"
        assert tm.current.name == "dark"

    def test_theme_manager_switch(self):
        tm = ThemeManager()
        assert tm.switch_theme("matrix")
        assert tm.current_name == "matrix"

    def test_theme_manager_invalid(self):
        tm = ThemeManager()
        assert not tm.switch_theme("nonexistent_theme")
        assert tm.current_name == "dark"  # unchanged

    def test_theme_list(self):
        tm = ThemeManager()
        themes = tm.list_themes()
        assert len(themes) >= 5
        assert "dark" in themes

    def test_theme_to_css(self):
        theme = BUILTIN_THEMES["dark"]
        css = theme.to_css()
        assert "--content-fg:" in css
        assert "--content-bg:" in css

    def test_theme_manager_css_export(self):
        tm = ThemeManager()
        css = tm.export_all_css()
        assert 'data-theme="dark"' in css
        assert 'data-theme="matrix"' in css

    def test_theme_accessibility_report(self):
        tm = ThemeManager()
        report = tm.accessibility_report("dark")
        assert report["theme"] == "dark"
        assert report["total_checks"] > 0

    def test_ini_save_load(self, tmp_path):
        tm = ThemeManager(initial_theme="ocean")
        ini_path = tmp_path / "ocean.ini"
        tm.save_to_ini(ini_path, "ocean")
        assert ini_path.exists()

        # Load it back
        tm2 = ThemeManager()
        loaded = tm2.load_from_ini(ini_path)
        assert loaded is not None
        assert loaded.name == "ocean"

    def test_switch_callback(self):
        tm = ThemeManager()
        switched_to = []
        tm.add_switch_callback(lambda name, theme: switched_to.append(name))
        tm.switch_theme("fire")
        assert switched_to == ["fire"]


# ═══════════════════════════════════════════════════════════════════════════════
# SHM IPC Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestSHMIPC:
    """Tests for shm_ipc module."""

    def test_ring_buffer_basic(self):
        rb = RingBuffer(capacity=10)
        seq = rb.put(b"hello")
        assert seq == 1
        assert rb.total_written == 1

    def test_ring_buffer_get_since(self):
        rb = RingBuffer(capacity=10)
        rb.put(b"msg1")
        rb.put(b"msg2")
        rb.put(b"msg3")
        msgs = rb.get_since(0)
        assert len(msgs) == 3
        assert b"msg1" in msgs
        assert b"msg3" in msgs

    def test_ring_buffer_overflow(self):
        rb = RingBuffer(capacity=3)
        for i in range(5):
            rb.put(f"msg{i}".encode())
        # Only last 3 are retained
        msgs = rb.get_latest(3)
        assert len(msgs) == 3

    def test_ring_buffer_get_latest(self):
        rb = RingBuffer(capacity=10)
        for i in range(5):
            rb.put(f"m{i}".encode())
        latest = rb.get_latest(2)
        assert len(latest) == 2

    def test_message_serialization(self):
        msg = Message(
            msg_id="test-id",
            channel="chan-1",
            sender_id="agent-1",
            timestamp=1234567890.0,
            payload={"key": "value", "count": 42},
        )
        data = msg.to_bytes()
        restored = Message.from_bytes(data)
        assert restored.msg_id == "test-id"
        assert restored.payload["count"] == 42
        assert restored.channel == "chan-1"

    def test_shared_memory_channel_publish(self):
        ch = SharedMemoryChannel("test-channel-pub", capacity=32)
        seq = ch.publish({"event": "test"}, sender_id="agent-1")
        assert seq >= 1
        ch.close()

    def test_shared_memory_channel_read(self):
        ch = SharedMemoryChannel("test-channel-read", capacity=32)
        ch.publish({"msg": "first"}, sender_id="a1")
        ch.publish({"msg": "second"}, sender_id="a1")
        msgs = ch.read_new()
        assert len(msgs) == 2
        assert msgs[0].payload["msg"] == "first"
        ch.close()

    def test_shared_memory_channel_stats(self):
        ch = SharedMemoryChannel("test-stats", capacity=32)
        ch.publish({"x": 1})
        stats = ch.get_stats()
        assert stats["messages_sent"] == 1
        assert stats["channel"] == "test-stats"
        ch.close()

    def test_message_queue_publish_poll(self):
        mq = MessageQueue(capacity=32)
        mq.publish("events", {"action": "start"}, sender="agent-1")
        msgs = mq.poll("events")
        assert len(msgs) == 1
        assert msgs[0].payload["action"] == "start"
        mq.stop()

    def test_message_queue_subscribe(self):
        mq = MessageQueue(capacity=32)
        received = []
        mq.subscribe("alerts", lambda msg: received.append(msg.payload))
        mq.publish("alerts", {"level": "critical"}, sender="monitor")
        time.sleep(0.2)  # Wait for polling thread
        assert len(received) >= 1
        assert received[0]["level"] == "critical"
        mq.stop()

    def test_message_queue_stats(self):
        mq = MessageQueue(capacity=32)
        mq.publish("ch1", {"x": 1})
        stats = mq.get_stats()
        assert stats["queue_stats"]["published"] == 1
        mq.stop()

    def test_latency_tracker(self):
        lt = LatencyTracker(window=100)
        now = time.time()
        for _ in range(50):
            lt.record(now - 0.1)  # 100ms latency each
        stats = lt.get_stats()
        assert stats["count"] == 50
        assert stats["p50"] == pytest.approx(100.0, abs=20)

    def test_latency_tracker_percentiles(self):
        lt = LatencyTracker(window=1000)
        base = time.time()
        for i in range(100):
            lt.record(base - i * 0.001)  # 1ms to 100ms
        stats = lt.get_stats()
        assert stats["p90"] > stats["p50"]
        assert stats["p99"] >= stats["p90"]


# ═══════════════════════════════════════════════════════════════════════════════
# Integration Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestIntegration:
    """Cross-module integration tests."""

    def test_window_manager_with_theme(self):
        """Ensure TUIWindowManager + ThemeManager can coordinate."""
        tm = ThemeManager(initial_theme="ocean")
        wm = TUIWindowManager(80, 24)
        win = wm.create_window("w1", "Agent Console", x=0, y=0, w=40, h=15)
        theme = tm.current

        # Apply theme colors to window
        r, g, b = theme.content_fg
        win.write_text(0, 0, f"Theme: {theme.name}", fg=r // 10)  # Map to ANSI256 range
        output = wm.render_to_string()
        assert isinstance(output, str)

    def test_session_and_display_server(self):
        """Create session, attach display, build screen state."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            sm = SessionManager(sessions_file=Path(tmp) / "sessions.json")
            session = sm.create_session("agent-001")
            did = sm.attach_display(session.session_id, {
                "type": "websocket", "endpoint": "ws://localhost:8765"
            })
            assert did is not None

            wm = TUIWindowManager(80, 24)
            wm.create_window("console", "Agent Console")
            server = DisplayServer()
            state = server.build_screen_state(wm)
            assert state.version == 1

    def test_mq_with_widgets(self):
        """Agent status panel updated via message queue."""
        panel = AgentStatusPanel(x=0, y=0, w=70, h=15)
        mq = MessageQueue(capacity=64)

        def handle_status(msg):
            data = msg.payload
            panel.update_agent(AgentStatus(
                agent_id=data["agent_id"],
                name=data["name"],
                status=data["status"],
            ))

        mq.subscribe("agent-status", handle_status)
        mq.publish("agent-status", {
            "agent_id": "a1", "name": "Orchestrator", "status": "running"
        }, sender="system")
        time.sleep(0.2)
        output = panel.render()
        assert "Orchestrator" in output
        mq.stop()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
