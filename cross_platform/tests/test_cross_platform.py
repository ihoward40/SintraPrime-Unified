"""
SintraPrime Cross-Platform Test Suite
=====================================
65+ tests covering API gateway, mobile TUI, push notifications,
platform detector, and PWA configuration.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Ensure the cross_platform directory is on sys.path for direct imports
_CP_DIR = str(Path(__file__).parent.parent)
if _CP_DIR not in sys.path:
    sys.path.insert(0, _CP_DIR)

import pytest

# ─── Fixtures ─────────────────────────────────────────────────────────────────
@pytest.fixture
def temp_dir(tmp_path):
    return tmp_path


@pytest.fixture
def mock_env(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("COLUMNS", "80")
    monkeypatch.setenv("LINES", "24")
    return tmp_path


# ═══════════════════════════════════════════════════════════════════════════════
# PLATFORM DETECTOR TESTS
# ═══════════════════════════════════════════════════════════════════════════════
class TestPlatformDetector:

    def test_import(self):
        from platform_detector import PlatformDetector
        assert PlatformDetector is not None

    def test_platform_enum_values(self):
        from platform_detector import Platform
        assert Platform.WINDOWS.value == "windows"
        assert Platform.MACOS.value == "macos"
        assert Platform.LINUX.value == "linux"
        assert Platform.IOS.value == "ios"
        assert Platform.ANDROID.value == "android"
        assert Platform.WEB.value == "web"

    def test_feature_enum_values(self):
        from platform_detector import Feature
        assert Feature.PUSH_NOTIFICATIONS.value == "push_notifications"
        assert Feature.OFFLINE_MODE.value == "offline_mode"
        assert Feature.BIOMETRIC_AUTH.value == "biometric_auth"
        assert Feature.LOCAL_LLM.value == "local_llm"

    def test_detect_returns_config(self):
        from platform_detector import PlatformDetector
        detector = PlatformDetector()
        config = detector.detect()
        assert config is not None
        assert config.platform is not None
        assert config.runtime is not None

    def test_detect_cached(self):
        from platform_detector import PlatformDetector
        detector = PlatformDetector()
        config1 = detector.detect()
        config2 = detector.detect()
        assert config1 is config2  # Same object (cached)

    def test_ios_detection_via_user_agent(self):
        from platform_detector import PlatformDetector, Platform
        det = PlatformDetector(user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0)")
        config = det.detect()
        assert config.platform == Platform.IOS

    def test_android_detection_via_user_agent(self):
        from platform_detector import PlatformDetector, Platform
        det = PlatformDetector(user_agent="Mozilla/5.0 (Linux; Android 14) AppleWebKit")
        config = det.detect()
        assert config.platform == Platform.ANDROID

    def test_ipad_detection(self):
        from platform_detector import PlatformDetector, Platform
        det = PlatformDetector(user_agent="Mozilla/5.0 (iPad; CPU OS 17_0)")
        config = det.detect()
        assert config.platform == Platform.IOS

    def test_config_has_features_set(self):
        from platform_detector import PlatformDetector
        config = PlatformDetector().detect()
        assert isinstance(config.features, set)
        assert len(config.features) > 0

    def test_config_has_method(self):
        from platform_detector import PlatformDetector, Feature
        config = PlatformDetector().detect()
        assert callable(config.has)
        assert config.has(Feature.TLS_PINNING)

    def test_terminal_width_detected(self):
        from platform_detector import PlatformDetector
        config = PlatformDetector().detect()
        assert isinstance(config.terminal_width, int)
        assert config.terminal_width > 0

    def test_terminal_height_detected(self):
        from platform_detector import PlatformDetector
        config = PlatformDetector().detect()
        assert isinstance(config.terminal_height, int)
        assert config.terminal_height > 0

    def test_mobile_terminal_flag(self):
        from platform_detector import PlatformDetector
        from unittest.mock import MagicMock, patch
        with patch("os.get_terminal_size", return_value=MagicMock(columns=40, lines=20)):
            det = PlatformDetector()
            config = det.detect()
            assert config.terminal_width == 40

    def test_to_dict(self):
        from platform_detector import PlatformDetector
        config = PlatformDetector().detect()
        d = config.to_dict()
        assert "platform" in d
        assert "runtime" in d
        assert "features" in d
        assert isinstance(d["features"], list)

    def test_get_platform_config_function(self):
        from platform_detector import get_platform_config
        config = get_platform_config()
        assert config is not None

    def test_supports_function(self):
        from platform_detector import supports, Feature
        result = supports(Feature.TLS_PINNING)
        assert result is True

    def test_get_optimal_tui_width(self):
        from platform_detector import get_optimal_tui_width
        width = get_optimal_tui_width()
        assert isinstance(width, int)
        assert width > 0

    def test_color_detection_no_color(self, monkeypatch):
        from platform_detector import PlatformDetector
        monkeypatch.setenv("NO_COLOR", "1")
        det = PlatformDetector()
        config = det.detect()
        assert config.color_support == 0

    def test_docker_runtime_detection(self):
        from platform_detector import PlatformDetector, RuntimeEnvironment
        from unittest.mock import patch
        with patch("os.path.exists", side_effect=lambda p: p == "/.dockerenv"):
            det = PlatformDetector()
            runtime = det._detect_runtime()
            assert runtime == RuntimeEnvironment.DOCKER

    def test_ci_runtime_detection(self, monkeypatch):
        from platform_detector import PlatformDetector, RuntimeEnvironment
        monkeypatch.setenv("CI", "true")
        det = PlatformDetector()
        runtime = det._detect_runtime()
        assert runtime == RuntimeEnvironment.CI

    def test_runtime_enum_values(self):
        from platform_detector import RuntimeEnvironment
        assert RuntimeEnvironment.SSH.value == "ssh"
        assert RuntimeEnvironment.DOCKER.value == "docker"
        assert RuntimeEnvironment.CI.value == "ci"

    def test_config_dirs_set(self):
        from platform_detector import PlatformDetector
        config = PlatformDetector().detect()
        assert config.config_dir != ""
        assert config.cache_dir != ""

    def test_cpu_count(self):
        from platform_detector import PlatformDetector
        config = PlatformDetector().detect()
        assert config.cpu_count >= 1

    def test_arch_detected(self):
        from platform_detector import PlatformDetector
        config = PlatformDetector().detect()
        assert config.arch != ""

    def test_python_version_detected(self):
        from platform_detector import PlatformDetector
        config = PlatformDetector().detect()
        assert config.python_version.startswith("3.")


# ═══════════════════════════════════════════════════════════════════════════════
# MOBILE TUI TESTS
# ═══════════════════════════════════════════════════════════════════════════════
class TestMobileTUI:

    def test_import(self):
        from mobile_tui import MobileTUI
        assert MobileTUI is not None

    def test_tui_state_defaults(self):
        from mobile_tui import TUIState, Screen
        state = TUIState()
        assert state.screen == Screen.MAIN_MENU
        assert state.scroll_offset == 0
        assert state.history == []

    def test_mobile_width_constant(self):
        from mobile_tui import MOBILE_WIDTH
        assert MOBILE_WIDTH == 40

    def test_desktop_width_constant(self):
        from mobile_tui import DESKTOP_WIDTH
        assert DESKTOP_WIDTH == 80

    def test_screens_enum(self):
        from mobile_tui import Screen
        assert Screen.MAIN_MENU is not None
        assert Screen.CASES is not None
        assert Screen.RESEARCH is not None
        assert Screen.DEADLINES is not None
        assert Screen.SETTINGS is not None
        assert Screen.HELP is not None

    def test_menu_items_count(self):
        from mobile_tui import MobileTUI
        assert len(MobileTUI.MAIN_MENU_ITEMS) >= 8

    def test_menu_items_numbered(self):
        from mobile_tui import MobileTUI
        numbers = [item.number for item in MobileTUI.MAIN_MENU_ITEMS]
        assert 0 in numbers
        assert 1 in numbers

    def test_render_header(self):
        from mobile_tui import MobileTUI
        tui = MobileTUI()
        header = tui._render_header()
        assert "SintraPrime" in header

    def test_render_main_menu(self):
        from mobile_tui import MobileTUI
        tui = MobileTUI()
        menu = tui._render_main_menu()
        assert "MAIN MENU" in menu

    def test_render_cases(self):
        from mobile_tui import MobileTUI
        tui = MobileTUI()
        output = tui._render_cases()
        assert "CASES" in output

    def test_render_research(self):
        from mobile_tui import MobileTUI
        tui = MobileTUI()
        output = tui._render_research()
        assert "RESEARCH" in output

    def test_render_deadlines(self):
        from mobile_tui import MobileTUI
        tui = MobileTUI()
        output = tui._render_deadlines()
        assert "DEADLINES" in output

    def test_render_settings(self):
        from mobile_tui import MobileTUI
        tui = MobileTUI()
        output = tui._render_settings()
        assert "SETTINGS" in output

    def test_render_help(self):
        from mobile_tui import MobileTUI
        tui = MobileTUI()
        output = tui._render_help()
        assert "HELP" in output or "SSH" in output

    def test_navigate_to(self):
        from mobile_tui import MobileTUI, Screen
        tui = MobileTUI()
        tui._navigate_to(Screen.CASES)
        assert tui.state.screen == Screen.CASES
        assert Screen.MAIN_MENU in tui.state.history

    def test_go_back(self):
        from mobile_tui import MobileTUI, Screen
        tui = MobileTUI()
        tui._navigate_to(Screen.CASES)
        tui._go_back()
        assert tui.state.screen == Screen.MAIN_MENU

    def test_go_back_empty_history(self):
        from mobile_tui import MobileTUI, Screen
        tui = MobileTUI()
        tui._go_back()
        assert tui.state.screen == Screen.MAIN_MENU

    def test_scroll_up(self):
        from mobile_tui import MobileTUI
        tui = MobileTUI()
        tui.state.scroll_offset = 10
        tui.scroll_up()
        assert tui.state.scroll_offset < 10

    def test_scroll_down(self):
        from mobile_tui import MobileTUI
        tui = MobileTUI()
        tui.scroll_down()
        assert tui.state.scroll_offset > 0

    def test_scroll_up_floor(self):
        from mobile_tui import MobileTUI
        tui = MobileTUI()
        tui.state.scroll_offset = 0
        tui.scroll_up()
        assert tui.state.scroll_offset == 0

    def test_center_function(self):
        from mobile_tui import center
        result = center("hello", 10)
        assert len(result) == 10

    def test_truncate_function(self):
        from mobile_tui import truncate
        result = truncate("hello world", 8)
        assert len(result) <= 8

    def test_truncate_short_string(self):
        from mobile_tui import truncate
        result = truncate("hi", 10)
        assert result == "hi"

    def test_strip_ansi(self):
        from mobile_tui import strip_ansi
        colored = "\x1b[31mRed Text\x1b[0m"
        plain = strip_ansi(colored)
        assert plain == "Red Text"

    def test_gesture_detector(self):
        from mobile_tui import GestureDetector, TUIState
        gd = GestureDetector()
        state = TUIState()
        assert gd is not None

    def test_handle_back_input(self):
        from mobile_tui import MobileTUI, Screen
        tui = MobileTUI()
        tui._navigate_to(Screen.CASES)
        tui._handle_input("0")
        assert tui.state.screen == Screen.MAIN_MENU

    def test_handle_invalid_input(self):
        from mobile_tui import MobileTUI
        tui = MobileTUI()
        tui._handle_input("999")
        assert tui.state.status_message != ""

    def test_h_rule(self):
        from mobile_tui import h_rule
        result = h_rule(10)
        assert len(result) == 10

    def test_wrap_text(self):
        from mobile_tui import wrap_text
        lines = wrap_text("hello world this is a test", 10)
        assert isinstance(lines, list)
        assert all(len(l) <= 10 for l in lines)

    def test_box_top_bottom(self):
        from mobile_tui import box_top, box_bottom
        top = box_top(10)
        bottom = box_bottom(10)
        assert top.startswith("┌")
        assert bottom.startswith("└")

    def test_main_menu_navigation_cases(self):
        from mobile_tui import MobileTUI, Screen
        tui = MobileTUI()
        tui._handle_main_menu("2")
        assert tui.state.screen == Screen.CASES

    def test_main_menu_navigation_research(self):
        from mobile_tui import MobileTUI, Screen
        tui = MobileTUI()
        tui._handle_main_menu("3")
        assert tui.state.screen == Screen.RESEARCH

    def test_main_menu_navigation_deadlines(self):
        from mobile_tui import MobileTUI, Screen
        tui = MobileTUI()
        tui._handle_main_menu("4")
        assert tui.state.screen == Screen.DEADLINES

    def test_mobile_detection(self):
        from mobile_tui import is_mobile_terminal
        from unittest.mock import patch, MagicMock
        with patch("os.get_terminal_size", return_value=MagicMock(columns=40, lines=20)):
            result = is_mobile_terminal()
            assert result is True

    def test_desktop_detection(self):
        from mobile_tui import is_mobile_terminal
        from unittest.mock import patch, MagicMock
        with patch("os.get_terminal_size", return_value=MagicMock(columns=120, lines=40)):
            result = is_mobile_terminal()
            assert result is False


# ═══════════════════════════════════════════════════════════════════════════════
# PUSH NOTIFICATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════
class TestPushNotifications:

    def test_import(self):
        from push_notifications import PushNotificationService
        assert PushNotificationService is not None

    def test_notification_types(self):
        from push_notifications import NotificationType
        assert NotificationType.COURT_DEADLINE.value == "court_deadline"
        assert NotificationType.CASE_LAW_UPDATE.value == "case_law_update"
        assert NotificationType.DOCUMENT_READY.value == "document_ready"
        assert NotificationType.AGENT_COMPLETED.value == "agent_completed"
        assert NotificationType.EMERGENCY.value == "emergency"

    def test_vapid_manager_generates_keys(self, tmp_path):
        from push_notifications import VAPIDManager
        manager = VAPIDManager(tmp_path / "vapid.json")
        assert len(manager.public_key) > 0
        assert len(manager.private_key) > 0

    def test_vapid_keys_persist(self, tmp_path):
        from push_notifications import VAPIDManager
        path = tmp_path / "vapid.json"
        m1 = VAPIDManager(path)
        key1 = m1.public_key
        m2 = VAPIDManager(path)
        key2 = m2.public_key
        assert key1 == key2

    def test_vapid_rotate_keys(self, tmp_path):
        from push_notifications import VAPIDManager
        m = VAPIDManager(tmp_path / "vapid.json")
        key1 = m.public_key
        m.rotate_keys()
        assert m.public_key != key1

    def test_vapid_jwt_creation(self, tmp_path):
        from push_notifications import VAPIDManager
        m = VAPIDManager(tmp_path / "vapid.json")
        jwt = m.create_vapid_jwt("https://push.example.com")
        parts = jwt.split(".")
        assert len(parts) == 3

    def test_subscription_store_add(self, tmp_path):
        from push_notifications import SubscriptionStore
        store = SubscriptionStore(tmp_path / "subs.json")
        sub = store.add("https://fcm.example.com/endpoint", "p256dh_key", "auth_key", "user1")
        assert sub.subscription_id is not None
        assert sub.endpoint == "https://fcm.example.com/endpoint"
        assert sub.user_id == "user1"

    def test_subscription_store_get(self, tmp_path):
        from push_notifications import SubscriptionStore
        store = SubscriptionStore(tmp_path / "subs.json")
        sub = store.add("https://endpoint.test", "key", "auth", "u1")
        retrieved = store.get(sub.subscription_id)
        assert retrieved is not None
        assert retrieved.subscription_id == sub.subscription_id

    def test_subscription_store_remove(self, tmp_path):
        from push_notifications import SubscriptionStore
        store = SubscriptionStore(tmp_path / "subs.json")
        sub = store.add("https://endpoint.test", "key", "auth")
        assert store.remove(sub.subscription_id)
        retrieved = store.get(sub.subscription_id)
        assert not retrieved.active

    def test_subscription_store_count(self, tmp_path):
        from push_notifications import SubscriptionStore
        store = SubscriptionStore(tmp_path / "subs.json")
        assert store.count() == 0
        store.add("https://ep1.test", "k1", "a1")
        store.add("https://ep2.test", "k2", "a2")
        assert store.count() == 2

    def test_subscription_get_by_user(self, tmp_path):
        from push_notifications import SubscriptionStore
        store = SubscriptionStore(tmp_path / "subs.json")
        store.add("https://ep1.test", "k1", "a1", "alice")
        store.add("https://ep2.test", "k2", "a2", "bob")
        store.add("https://ep3.test", "k3", "a3", "alice")
        alice_subs = store.get_by_user("alice")
        assert len(alice_subs) == 2

    def test_preferences_default(self, tmp_path):
        from push_notifications import PreferencesStore, NotificationType
        store = PreferencesStore(tmp_path / "prefs.json")
        prefs = store.get("user1")
        assert prefs.user_id == "user1"
        assert NotificationType.EMERGENCY in prefs.enabled_types

    def test_preferences_quiet_hours(self, tmp_path):
        from push_notifications import PreferencesStore
        store = PreferencesStore(tmp_path / "prefs.json")
        prefs = store.get("user1")
        prefs.quiet_hours_start = 22
        prefs.quiet_hours_end = 7
        store.set(prefs)
        retrieved = store.get("user1")
        assert retrieved.quiet_hours_start == 22

    def test_notification_payload_to_json(self):
        from push_notifications import NotificationPayload, NotificationType
        payload = NotificationPayload(
            notification_type=NotificationType.COURT_DEADLINE,
            title="Motion Due",
            body="Your motion is due tomorrow",
            url="/cases/123",
        )
        data = json.loads(payload.to_json_bytes())
        assert data["type"] == "court_deadline"
        assert "Motion Due" in data["title"]
        assert data["url"] == "/cases/123"

    def test_service_init(self, tmp_path, monkeypatch):
        import push_notifications as pn
        monkeypatch.setattr(pn, "DATA_DIR", tmp_path / "push_data")
        monkeypatch.setattr(pn, "VAPID_KEYS_FILE", tmp_path / "push_data" / "vapid_keys.json")
        monkeypatch.setattr(pn, "SUBSCRIPTIONS_FILE", tmp_path / "push_data" / "subscriptions.json")
        monkeypatch.setattr(pn, "PREFERENCES_FILE", tmp_path / "push_data" / "preferences.json")
        from push_notifications import PushNotificationService
        svc = PushNotificationService()
        assert svc.vapid is not None
        assert svc.subscriptions is not None
        assert svc.preferences is not None

    def test_service_get_vapid_public_key(self, tmp_path, monkeypatch):
        import push_notifications as pn
        monkeypatch.setattr(pn, "DATA_DIR", tmp_path / "push_data2")
        monkeypatch.setattr(pn, "VAPID_KEYS_FILE", tmp_path / "push_data2" / "vapid_keys.json")
        monkeypatch.setattr(pn, "SUBSCRIPTIONS_FILE", tmp_path / "push_data2" / "subs.json")
        monkeypatch.setattr(pn, "PREFERENCES_FILE", tmp_path / "push_data2" / "prefs.json")
        from push_notifications import PushNotificationService
        svc = PushNotificationService()
        key = svc.get_vapid_public_key()
        assert isinstance(key, str)
        assert len(key) > 20

    def test_service_get_stats(self, tmp_path, monkeypatch):
        import push_notifications as pn
        monkeypatch.setattr(pn, "DATA_DIR", tmp_path / "push_data3")
        monkeypatch.setattr(pn, "VAPID_KEYS_FILE", tmp_path / "push_data3" / "vapid_keys.json")
        monkeypatch.setattr(pn, "SUBSCRIPTIONS_FILE", tmp_path / "push_data3" / "subs.json")
        monkeypatch.setattr(pn, "PREFERENCES_FILE", tmp_path / "push_data3" / "prefs.json")
        from push_notifications import PushNotificationService
        svc = PushNotificationService()
        stats = svc.get_stats()
        assert "active_subscriptions" in stats
        assert "vapid_public_key_prefix" in stats

    @pytest.mark.asyncio
    async def test_subscribe(self, tmp_path, monkeypatch):
        import push_notifications as pn
        monkeypatch.setattr(pn, "DATA_DIR", tmp_path / "push_data4")
        monkeypatch.setattr(pn, "VAPID_KEYS_FILE", tmp_path / "push_data4" / "vapid_keys.json")
        monkeypatch.setattr(pn, "SUBSCRIPTIONS_FILE", tmp_path / "push_data4" / "subs.json")
        monkeypatch.setattr(pn, "PREFERENCES_FILE", tmp_path / "push_data4" / "prefs.json")
        from push_notifications import PushNotificationService
        svc = PushNotificationService()
        sub = await svc.subscribe({
            "endpoint": "https://push.example.com/endpoint123",
            "keys": {"p256dh": "key_data", "auth": "auth_data"},
            "user_id": "test_user",
        })
        assert sub.subscription_id is not None
        assert sub.endpoint == "https://push.example.com/endpoint123"

    @pytest.mark.asyncio
    async def test_subscribe_missing_fields(self, tmp_path, monkeypatch):
        import push_notifications as pn
        monkeypatch.setattr(pn, "DATA_DIR", tmp_path / "push_data5")
        monkeypatch.setattr(pn, "VAPID_KEYS_FILE", tmp_path / "push_data5" / "vapid_keys.json")
        monkeypatch.setattr(pn, "SUBSCRIPTIONS_FILE", tmp_path / "push_data5" / "subs.json")
        monkeypatch.setattr(pn, "PREFERENCES_FILE", tmp_path / "push_data5" / "prefs.json")
        from push_notifications import PushNotificationService
        svc = PushNotificationService()
        with pytest.raises(ValueError):
            await svc.subscribe({"endpoint": "", "keys": {}})

    @pytest.mark.asyncio
    async def test_send_to_suppressed_user(self, tmp_path, monkeypatch):
        import push_notifications as pn
        monkeypatch.setattr(pn, "DATA_DIR", tmp_path / "push_data6")
        monkeypatch.setattr(pn, "VAPID_KEYS_FILE", tmp_path / "push_data6" / "vapid_keys.json")
        monkeypatch.setattr(pn, "SUBSCRIPTIONS_FILE", tmp_path / "push_data6" / "subs.json")
        monkeypatch.setattr(pn, "PREFERENCES_FILE", tmp_path / "push_data6" / "prefs.json")
        from push_notifications import PushNotificationService, NotificationType, NotificationPayload
        svc = PushNotificationService()
        prefs = svc.get_preferences("user_no_notifs")
        prefs.enabled_types = set()
        svc.preferences.set(prefs)
        payload = NotificationPayload(
            notification_type=NotificationType.GENERAL,
            title="Test", body="test body",
        )
        result = await svc.send_to_user("user_no_notifs", payload)
        assert result["suppressed"] >= 1

    def test_notification_configs_complete(self):
        from push_notifications import NOTIFICATION_CONFIGS, NotificationType
        for ntype in NotificationType:
            assert ntype in NOTIFICATION_CONFIGS
            config = NOTIFICATION_CONFIGS[ntype]
            assert "ttl" in config
            assert "urgency" in config

    def test_preferences_allows_type(self, tmp_path):
        from push_notifications import PreferencesStore, NotificationType, NotificationPreferences
        store = PreferencesStore(tmp_path / "prefs.json")
        prefs = store.get("u1")
        assert prefs.allows_type(NotificationType.EMERGENCY)

    def test_preferences_quiet_hour_check(self, tmp_path):
        from push_notifications import PreferencesStore
        store = PreferencesStore(tmp_path / "prefs.json")
        prefs = store.get("u2")
        # No quiet hours set = never quiet
        assert prefs.is_quiet_hour() is False


# ═══════════════════════════════════════════════════════════════════════════════
# API GATEWAY TESTS
# ═══════════════════════════════════════════════════════════════════════════════
class TestAPIGateway:

    @pytest.fixture
    def client(self, tmp_path, monkeypatch):
        import api_gateway as gw
        monkeypatch.setattr(gw, "API_KEYS_FILE", tmp_path / ".api_keys.json")
        monkeypatch.setattr(gw, "api_key_store", gw.APIKeyStore(tmp_path / ".api_keys.json"))
        monkeypatch.setattr(gw, "_rate_limit_store", {})
        from fastapi.testclient import TestClient
        return TestClient(gw.app)

    def test_health_endpoint(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "modules" in data
        assert "uptime_seconds" in data

    def test_health_modules_present(self, client):
        response = client.get("/api/health")
        data = response.json()
        assert "cases" in data["modules"]
        assert "research" in data["modules"]
        assert "deadlines" in data["modules"]

    def test_health_timestamp(self, client):
        response = client.get("/api/health")
        data = response.json()
        assert "timestamp" in data
        assert "T" in data["timestamp"]

    def test_create_api_key(self, client):
        response = client.post("/api/keys", json={"name": "test-key", "scopes": ["read"]})
        assert response.status_code == 200
        data = response.json()
        assert "key" in data
        assert data["key"].startswith("sp_")
        assert data["name"] == "test-key"

    def test_create_api_key_with_scopes(self, client):
        response = client.post("/api/keys", json={"name": "write-key", "scopes": ["read", "write"]})
        assert response.status_code == 200
        data = response.json()
        assert "read" in data["scopes"]
        assert "write" in data["scopes"]

    def test_list_api_keys(self, client):
        client.post("/api/keys", json={"name": "k1"})
        response = client.get("/api/keys")
        assert response.status_code == 200
        data = response.json()
        assert "keys" in data

    def test_revoke_api_key(self, client):
        create_resp = client.post("/api/keys", json={"name": "to-revoke"})
        key = create_resp.json()["key"]
        response = client.delete(f"/api/keys/{key}")
        assert response.status_code == 200
        assert response.json()["revoked"] is True

    def test_revoke_nonexistent_key(self, client):
        response = client.delete("/api/keys/nonexistent_key_xyz")
        assert response.status_code == 404

    def test_cases_endpoint(self, client):
        response = client.get("/api/cases")
        assert response.status_code == 200

    def test_deadlines_endpoint(self, client):
        response = client.get("/api/deadlines")
        assert response.status_code == 200

    def test_activity_endpoint(self, client):
        response = client.get("/api/activity")
        assert response.status_code == 200

    def test_agents_endpoint(self, client):
        response = client.get("/api/agents")
        assert response.status_code == 200

    def test_documents_endpoint(self, client):
        response = client.get("/api/documents")
        assert response.status_code == 200

    def test_rate_limit_headers(self, client):
        response = client.get("/api/health")
        assert "x-ratelimit-remaining" in response.headers

    def test_request_id_header(self, client):
        response = client.get("/api/health")
        assert "x-request-id" in response.headers

    def test_api_key_store_generate(self, tmp_path):
        from api_gateway import APIKeyStore
        store = APIKeyStore(tmp_path / "keys.json")
        record = store.generate("test", ["read"])
        assert record["key"].startswith("sp_")
        assert record["name"] == "test"
        assert record["active"] is True

    def test_api_key_store_validate(self, tmp_path):
        from api_gateway import APIKeyStore
        store = APIKeyStore(tmp_path / "keys.json")
        record = store.generate("test", ["read"])
        validated = store.validate(record["key"])
        assert validated is not None
        assert validated["usage_count"] == 1

    def test_api_key_store_revoke(self, tmp_path):
        from api_gateway import APIKeyStore
        store = APIKeyStore(tmp_path / "keys.json")
        record = store.generate("test", ["read"])
        assert store.revoke(record["key"])
        assert store.validate(record["key"]) is None

    def test_api_key_invalid_returns_none(self, tmp_path):
        from api_gateway import APIKeyStore
        store = APIKeyStore(tmp_path / "keys.json")
        assert store.validate("sp_invalid_key_xyz") is None

    def test_rate_limit_check_function(self):
        from api_gateway import check_rate_limit, _rate_limit_store
        _rate_limit_store.clear()
        allowed, remaining, _ = check_rate_limit("test_ip_unique_xyz_abc")
        assert allowed is True
        assert remaining < 100

    def test_modules_dict_has_correct_keys(self):
        from api_gateway import MODULES
        expected = ["cases", "research", "deadlines", "documents", "agents"]
        for key in expected:
            assert key in MODULES

    def test_api_key_store_list(self, tmp_path):
        from api_gateway import APIKeyStore
        store = APIKeyStore(tmp_path / "keys.json")
        store.generate("k1", ["read"])
        store.generate("k2", ["write"])
        keys = store.list_keys()
        assert len(keys) == 2
        # Ensure actual keys are masked
        for k in keys:
            assert "key_prefix" in k
            assert "key" not in k

    def test_health_version(self, client):
        response = client.get("/api/health")
        data = response.json()
        assert data["version"] == "1.0.0"


# ═══════════════════════════════════════════════════════════════════════════════
# PWA CONFIG TESTS
# ═══════════════════════════════════════════════════════════════════════════════
class TestPWAConfig:

    def _pwa_path(self, filename: str) -> Path:
        return Path(__file__).parent.parent / "pwa" / filename

    def test_manifest_file_exists(self):
        assert self._pwa_path("manifest.json").exists()

    def test_manifest_valid_json(self):
        data = json.loads(self._pwa_path("manifest.json").read_text())
        assert data is not None

    def test_manifest_required_fields(self):
        data = json.loads(self._pwa_path("manifest.json").read_text())
        assert "name" in data
        assert "short_name" in data
        assert "start_url" in data
        assert "display" in data
        assert data["display"] == "standalone"

    def test_manifest_icons(self):
        data = json.loads(self._pwa_path("manifest.json").read_text())
        assert "icons" in data
        assert len(data["icons"]) > 0
        icon = data["icons"][0]
        assert "src" in icon
        assert "sizes" in icon

    def test_manifest_theme_color(self):
        data = json.loads(self._pwa_path("manifest.json").read_text())
        assert "theme_color" in data
        assert data["theme_color"].startswith("#")

    def test_manifest_shortcuts(self):
        data = json.loads(self._pwa_path("manifest.json").read_text())
        assert "shortcuts" in data
        assert len(data["shortcuts"]) > 0

    def test_manifest_background_color(self):
        data = json.loads(self._pwa_path("manifest.json").read_text())
        assert "background_color" in data

    def test_manifest_lang(self):
        data = json.loads(self._pwa_path("manifest.json").read_text())
        assert "lang" in data
        assert data["lang"] == "en-US"

    def test_service_worker_file_exists(self):
        assert self._pwa_path("service_worker.js").exists()

    def test_service_worker_has_install_listener(self):
        content = self._pwa_path("service_worker.js").read_text()
        assert "addEventListener('install'" in content

    def test_service_worker_has_activate_listener(self):
        content = self._pwa_path("service_worker.js").read_text()
        assert "addEventListener('activate'" in content

    def test_service_worker_has_fetch_listener(self):
        content = self._pwa_path("service_worker.js").read_text()
        assert "addEventListener('fetch'" in content

    def test_service_worker_has_push_listener(self):
        content = self._pwa_path("service_worker.js").read_text()
        assert "addEventListener('push'" in content

    def test_service_worker_has_sync_listener(self):
        content = self._pwa_path("service_worker.js").read_text()
        assert "addEventListener('sync'" in content

    def test_service_worker_has_cache_name(self):
        content = self._pwa_path("service_worker.js").read_text()
        assert "STATIC_CACHE" in content or "sintra-static" in content

    def test_service_worker_notification_click(self):
        content = self._pwa_path("service_worker.js").read_text()
        assert "notificationclick" in content

    def test_index_html_exists(self):
        assert self._pwa_path("index.html").exists()

    def test_index_html_manifest_link(self):
        content = self._pwa_path("index.html").read_text()
        assert 'manifest.json' in content

    def test_index_html_viewport_meta(self):
        content = self._pwa_path("index.html").read_text()
        assert 'viewport' in content

    def test_index_html_apple_capable(self):
        content = self._pwa_path("index.html").read_text()
        assert 'apple-mobile-web-app-capable' in content

    def test_app_js_exists(self):
        assert self._pwa_path("app.js").exists()

    def test_app_js_service_worker_registration(self):
        content = self._pwa_path("app.js").read_text()
        assert "serviceWorker" in content

    def test_app_js_indexeddb(self):
        content = self._pwa_path("app.js").read_text()
        assert "indexedDB" in content

    def test_app_js_install_prompt(self):
        content = self._pwa_path("app.js").read_text()
        assert "beforeinstallprompt" in content

    def test_app_js_background_sync(self):
        content = self._pwa_path("app.js").read_text()
        assert "sync" in content.lower()

    def test_styles_css_exists(self):
        assert self._pwa_path("styles.css").exists()

    def test_styles_mobile_first(self):
        content = self._pwa_path("styles.css").read_text()
        assert "min-width" in content

    def test_styles_css_variables(self):
        content = self._pwa_path("styles.css").read_text()
        assert "--bg-primary" in content
        assert "--accent" in content

    def test_styles_safe_area(self):
        content = self._pwa_path("styles.css").read_text()
        assert "safe-area-inset" in content
